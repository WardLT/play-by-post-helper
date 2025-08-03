"""Services related to backing up channels"""
import asyncio
import logging
import json
import os
import pickle as pkl
from pathlib import Path
from lzma import LZMAFile
from shutil import copyfileobj
from typing import List, Dict, Tuple, Union
from datetime import datetime, timedelta
from functools import cached_property
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from math import inf, isclose

import humanize
from discord import Guild, TextChannel, Message, User, CategoryChannel
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload

from modron.discord import get_last_activity
from modron.services import BaseService
from modron.config import config

logger = logging.getLogger(__name__)


@contextmanager
def make_compressed_version(in_path: Path) -> Path:
    with TemporaryDirectory() as out_dir:
        out_path = Path(out_dir) / (in_path.name + '.gz')
        logger.info(f'Compressing data to {out_path}')
        with open(in_path, 'rb') as fi, LZMAFile(out_path, mode='wb') as fo:
            copyfileobj(fi, fo)
        yield out_path


def _get_last_write_time(output_path) -> float:
    """Get the last timestamp from a file

    Args:
        output_path: Path to a backup file
    Returns:
        Timestamp of latest message
    """
    start_time = 0
    with open(output_path) as fp:
        for line in fp:
            msg = json.loads(line)
            start_time = max(start_time, float(msg["timestamp"]))
    return start_time


def _write_messages(messages: List[Dict], output_path: str):
    """Write messages to disk

    Converts the timestamps to UTC to avoid any timezone nonsense

    Args:
        messages: List of messages to write to disk
        output_path: Output path
    """
    logger.debug(f'Writing {len(messages)} to {output_path}')
    with open(output_path, 'a') as fp:
        for msg in messages:
            # Write it out
            msg = dict(msg)
            print(json.dumps(msg), file=fp)


class BackupService(BaseService):
    """Download and write messages from certain channels to disk

    Messages are written in a special "backup directory" which contains the channels
    being backed up as separate json files.
    """

    def __init__(self,
                 guild: Guild,
                 backup_dir: str,
                 frequency: timedelta = timedelta(days=1),
                 channels: List[int] = (),
                 max_sleep_time: float = inf):
        """

        Args:
            guild: Connection to the guild
            backup_dir: Directory in which
            channels: List of channels or categories to back up
            max_sleep_time: Longest time to sleep before
        """
        short_name = config.team_options[guild.id].name
        super().__init__(guild, max_sleep_time, name=f'backup_{short_name}')
        self.frequency = frequency
        self.backup_dir = Path(backup_dir) / short_name
        self.channels = channels
        self.guild_name = short_name

        # Store status information
        self.last_backup_date = datetime.now()
        self.last_backup_successful = True
        self.total_uploaded = 0
        self.next_run_time = datetime.now()

        # Determine where to upload to Google, if credentials are available
        cred_path = config.get_gdrive_credentials_path()
        self._creds = None
        if os.path.isfile(cred_path):
            with open(cred_path, 'rb') as fp:
                self._creds = pkl.load(fp)
            logger.info('Loaded Google Drive credentials')
        else:
            logger.info('No Google Drive conventions available')

    @property
    def since_last_backup(self) -> timedelta:
        """Time since the last backup"""
        return datetime.now() - self.last_backup_date

    @property
    def until_next_backup(self) -> timedelta:
        """Time until the next backup"""
        return self.next_run_time - datetime.now()

    @property
    def using_gdrive(self) -> bool:
        """Whether we will upload chat history to Google drive"""
        return self._creds is not None

    @cached_property
    def gdrive_client(self) -> Resource:
        """Build the GDrive client with stored credentials"""
        return build('drive', 'v3', credentials=self._creds)

    def get_folder_id(self) -> str:
        """Create or locate the backup folder for this channel

        Returns:
            Identifier for the Google Drive backup folder for this particular channel
        """

        # Get the root folder
        result = self.gdrive_client.files().list(
            q=f"name = '{self.guild_name}' and '{config.gdrive_backup_folder}' in parents and trashed = false",
            pageSize=2
        ).execute()
        hits = result.get('files', [])

        # Operate!
        if len(hits) > 1:
            raise ValueError('>1 folder with this name in the backup directory')
        elif len(hits) == 1:
            return hits[0].get('id')
        else:
            file_metadata = {
                'name': self.guild_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [config.gdrive_backup_folder]
            }
            result = self.gdrive_client.files().create(
                body=file_metadata
            ).execute()
            logger.info('Created a new upload folder')
            return result.get('id')

    async def backup_messages(self, channel: TextChannel) -> int:
        """Backup all messages from a certain channel

        Args:
            channel: Link to the channel to back up
        Returns:
            (int) Number of messages written
        """
        # Determine where backup the channels
        output_path = self.backup_dir / f'{channel}.jsonl'
        logger.info(f'Starting to backup chanel {channel} from {self.guild_name} to {output_path}')

        # Get the time of the last message
        if not os.path.isfile(output_path):
            start_time = 0
            output_path.parent.mkdir(exist_ok=True, parents=True)
        else:
            # Get the last line of the file
            start_time = _get_last_write_time(output_path)
        logger.info(f'Starting timestamp {start_time}, which is {datetime.fromtimestamp(start_time)}')

        # Pulling the most recent message
        last_time, _ = await get_last_activity(channel)
        if isclose((last_time - datetime.fromtimestamp(start_time)).total_seconds(), 0.0):
            logger.info(f'No new messages in {channel}')
            return 0

        # Make one query to the system
        n_msg = 0
        with open(output_path, 'a') as fp:
            after = datetime.fromtimestamp(start_time) if start_time > 0 else None
            async for message in channel.history(after=after, limit=None, oldest_first=True):
                message: Message = message
                n_msg += 1
                author: User = message.author

                print(json.dumps({
                    'id': message.id,
                    'user_id': author.id,
                    'user_name': author.name,
                    'message': message.content,
                    'timestamp': message.created_at.timestamp()
                }), file=fp)
        logger.info(f'Backed up {n_msg} messages from {channel.name}')
        return n_msg

    async def backup_all_channels(self) -> Dict[str, int]:
        """Download messages for all channels

        Returns:
            (dict) Number of messages downloaded per channel
        """
        # Get the channels to back up
        to_backup = []
        for channel_id in self.channels:
            channel = self._guild.get_channel(channel_id)
            if isinstance(channel, CategoryChannel):
                to_backup.extend(channel.channels)
            else:
                to_backup.append(channel)

        # Submit all backups as asynchronous tasks
        tasks = dict((c.name, asyncio.create_task(self.backup_messages(c))) for c in to_backup)

        # Wait until they all finish
        return dict([
            (c, await t) for c, t in tasks.items()
        ])

    def upload_to_gdrive(self) -> Tuple[int, int]:
        """Upload the log files to the Google Drive

        Returns:
            - Number of files uploaded
            - Size of files updated
        """

        # Make sure the gdrive credentials are available
        if not self.using_gdrive:
            raise ValueError('No Google Drive credentials were provided')

        # Make sure the root folder exists
        output = self.gdrive_client.files().get(fileId=config.gdrive_backup_folder).execute()
        assert output.get('mimeType', None) == 'application/vnd.google-apps.folder'
        logger.info(f'Ready to upload to \"{output["name"]}\" ({config.gdrive_backup_folder})')

        # List out all files to be backed-up
        files = list(Path(self.backup_dir).glob('*.jsonl'))
        folders = set(Path(p).parent.name for p in files)
        logger.info(f'Found {len(files)} files to upload in {len(folders)} folders')

        # Upload the documents
        updated_count = 0
        uploaded_size = 0
        for file in files:
            was_updated, file_size = self.upload_file(file)
            if was_updated:
                updated_count += 1
                uploaded_size += file_size
        return updated_count, uploaded_size

    def upload_file(self, file: Union[str, Path]) -> Tuple[bool, int]:
        """Upload a file if it has changed

        Args:
            file: Path to the file to be uploaded
        Returns:
            - (bool) Whether the file was updated
            - (int) Amount of data uploaded
        """
        # Get the appropriate folder
        file_path = Path(file)

        # See if the file already exists
        folder_id = self.get_folder_id()
        result = self.gdrive_client.files().list(
            q=f"name = '{file_path.name}.xz' and '{folder_id}' in parents and trashed = false",
            pageSize=2, fields='files/id,files/md5Checksum,files/size,files/modifiedTime'
        ).execute()
        hits = result.get('files', [])

        # Determine whether to upload the file
        if len(hits) > 1:
            raise ValueError('>1 file with this name in the backup directory')
        elif len(hits) == 1:
            # Determine whether we need to update the file
            file_id = hits[0].get('id')
            logger.info(f'Matched existing file {file_id} to {file}')

            # Check the last time this file was modified
            last_message_time = datetime.fromtimestamp(_get_last_write_time(file))
            last_uploaded = datetime.strptime(hits[0]['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if last_message_time <= last_uploaded:
                return False, 0

            # Update the file
            with make_compressed_version(file_path) as to_upload:
                file_metadata = {'name': to_upload.name}
                media = MediaFileUpload(str(to_upload), mimetype='application/jsonlines')
                result = self.gdrive_client.files().update(
                    fileId=file_id, body=file_metadata, media_body=media, fields='id,size').execute()
                logger.info(f'Uploaded {file} to {result.get("id")}')
                return True, int(result.get('size'))
        else:
            # Upload the file
            with make_compressed_version(file_path) as to_upload:
                file_metadata = {'name': to_upload.name,
                                 'parents': [folder_id]}
                media = MediaFileUpload(str(to_upload), mimetype='application/jsonlines')
                result = self.gdrive_client.files().create(body=file_metadata,
                                                           media_body=media,
                                                           fields='id,size').execute()
                logger.info(f'Uploaded {file} to {result.get("id")}')
                return True, int(result.get('size'))

    async def run(self):
        # Run the main loop
        logger.info('Starting backup thread')
        while True:
            # Run the backup
            result = await self.backup_all_channels()
            logger.info(f'Backed up {sum(result.values())} messages in total. From: {", ".join(result.keys())}')
            self.last_backup_successful = False

            # Upload backed-up files to GoogleDrive
            if self._creds is not None:
                try:
                    count, data_size = self.upload_to_gdrive()
                    self.last_backup_successful = True
                    logger.info(f'Updated {count} files. Uploaded {humanize.naturalsize(data_size, binary=True)}')
                    self.total_uploaded += data_size
                except Exception as e:
                    logger.info(f'Error during GDrive upload: {e}')

            self.next_run_time = datetime.now() + self.frequency
            await self._sleep_until(self.next_run_time)
