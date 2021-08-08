"""Services related to backing up channels"""
import asyncio
from glob import glob
import pickle as pkl
import json
import os
from hashlib import md5
from pathlib import Path
from datetime import datetime, timedelta
from math import inf, isclose
import logging
from time import sleep
from typing import List, Dict, Optional, Tuple

import humanize
from discord import Guild, TextChannel, Message, User, CategoryChannel
from googleapiclient.channel import Channel
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaFileUpload

from modron.discord import get_last_activity, match_channels_to_regex
from modron.services import BaseService
from modron.config import get_config

config = get_config()
logger = logging.getLogger(__name__)


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
            # Drop the team column and convert ts to a float
            msg = dict(msg)
            if 'team' in msg:
                msg.pop('team')

            # Write it out
            print(json.dumps(msg), file=fp)


class BackupService(BaseService):
    """Download and write messages from certain channels to disk

    Messages are written in a special "backup directory" which contains the channels
    being backed up as separate json-ld files.
    """

    def __init__(self, guild: Guild, backup_dir: Optional[str] = None, frequency: timedelta = timedelta(days=1),
                 channels: List[int] = (), max_sleep_time: float = inf):
        """

        Args:
            guild: Connection to the guild
            backup_dir: Directory to store the
            channels: List of channels or categories to back up
            max_sleep_time: Longest time to sleep before
        """
        short_name = config.team_options[guild.id].name
        super().__init__(guild, max_sleep_time, name=f'backup_{short_name}')
        self.frequency = frequency
        self.backup_dir = backup_dir
        self.channels = channels

        # Create a Google-drive page, if credentials are available
        cred_path = config.get_gdrive_credentials_path()
        if os.path.isfile(cred_path):
            with open(cred_path, 'rb') as fp:
                self._creds = pkl.load(fp)
            logger.info('Loaded Google Drive credentials')
        else:
            logger.info('No Google Drive conventions available')

        # Store status information
        self.last_backup_date = datetime.now()
        self.last_backup_successful = True
        self.total_uploaded = 0
        self.next_run_time = datetime.now()
        self.gdrive_backup_folder = None
        if self._creds is not None:
            gdc = self.get_gdrive_client()
            self.gdrive_backup_folder = self._get_folder_id(gdc, short_name)

    @property
    def since_last_backup(self) -> timedelta:
        """Time since the last backup"""
        return datetime.now() - self.last_backup_date

    @property
    def backup_url(self) -> Optional[str]:
        """URL for the backup folder"""
        if self.gdrive_backup_folder is None:
            return None
        return f'https://drive.google.com/drive/folders/{self.gdrive_backup_folder}'

    @property
    def until_next_backup(self) -> timedelta:
        """Time until the next backup"""
        return self.next_run_time - datetime.now()

    def get_gdrive_client(self) -> Resource:
        """Build the GDrive client with stored credentials"""
        return build('drive', 'v3', credentials=self._creds)

    async def backup_messages(self, channel: TextChannel) -> int:
        """Backup all messages from a certain channel

        Args:
            channel: Link to the channel to back up
        Returns:
            (int) Number of messages written
        """
        logger.info(f'Starting to backup {channel}')

        # Get the time of the last message
        output_path = os.path.join(self.backup_dir, f'{channel}.json')
        logger.info(f'Backup path: {output_path}')
        if not os.path.isfile(output_path):
            start_time = 0
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        else:
            # Get the last line of the file
            start_time = 0
            with open(output_path) as fp:
                for line in fp:
                    msg = json.loads(line)
                    start_time = max(start_time, float(msg["timestamp"]))
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
        assert self._creds is not None, "Google Drive credentials are unavailable"
        gdrive_service = self.get_gdrive_client()

        # Make sure the target folder exists
        output = gdrive_service.files().get(fileId=config.gdrive_backup_folder).execute()
        assert output.get('mimeType', None) == 'application/vnd.google-apps.folder'
        logger.info(f'Ready to upload to \"{output["name"]}\" ({config.gdrive_backup_folder})')

        # List out all of the files to be backed-up
        files = glob(os.path.join(self.backup_dir, '**', '*.json'), recursive=True)
        folders = set(Path(p).parent.name for p in files)
        logger.info(f'Found {len(files)} files to upload in {len(folders)} folders')

        # Make the folders for each of the Slacks
        folder_ids = dict(
            (f, self._get_folder_id(gdrive_service, f)) for f in folders
        )

        # Upload the documents
        updated_count = 0
        uploaded_size = 0
        for file in files:
            was_updated, file_size = self._upload_file(gdrive_service, file, folder_ids)
            if was_updated:
                updated_count += 1
                uploaded_size += file_size
        return updated_count, uploaded_size

    def _upload_file(self, gdrive_service: Resource, file: str, folder_ids: Dict[str, str]) -> Tuple[bool, int]:
        """Upload a file if it has changed

        Args:
            gdrive_service: Authenticated GDrive client
            file (str): Path to the file to be uploaded
            folder_ids (dict): Map of the workspace name to folder ids
        Returns:
            - (bool) Whether the file was updated
            - (int) Amount of data uploaded
        """
        # Get the appropriate folder
        file_path = Path(file)
        folder_name = file_path.parent.name
        folder_id = folder_ids[folder_name]

        # See if the file already exists
        # Lookup the folder
        result = gdrive_service.files().list(
            q=f"name = '{file_path.name}' and '{folder_id}' in parents and trashed = false",
            pageSize=2, fields='files/id,files/md5Checksum,files/size'
        ).execute()
        hits = result.get('files', [])

        # Determine whether to upload the file
        if len(hits) > 1:
            raise ValueError('>1 file with this name in the backup directory')
        elif len(hits) == 1:
            # Otherwise, udate a new copy
            file_id = hits[0].get('id')
            logger.info(f'Matched existing file {file_id} to {file}')

            # Check if the file's md5 has has changed
            my_hash = md5()
            with open(file_path, 'rb') as fp:
                buff = fp.read(4096)
                while len(buff) > 0:
                    my_hash.update(buff)
                    buff = fp.read(4096)
            if my_hash.hexdigest() == hits[0].get('md5Checksum'):
                logger.info('MD5 checksum is unchanged. Skipping upload')
                return False, 0

            # Update the file
            file_metadata = {'name': file_path.name}
            media = MediaFileUpload(file, mimetype='application/ld+json')
            result = gdrive_service.files().update(
                fileId=file_id, body=file_metadata, media_body=media, fields='id,size').execute()
            logger.info(f'Uploaded {file} to {result.get("id")}')
            return True, int(result.get('size'))
        else:
            # Upload the file
            file_metadata = {'name': file_path.name,
                             'parents': [folder_id]}
            media = MediaFileUpload(file, mimetype='application/ld+json')
            result = gdrive_service.files().create(body=file_metadata,
                                                   media_body=media,
                                                   fields='id,size').execute()
            logger.info(f'Uploaded {file} to {result.get("id")}')
            return True, int(result.get('size'))

    def _get_folder_id(self, gdrive_service: Resource, name: str) -> str:
        """Get ID for the folder to hold logs for a certain Slack

        Args:
            gdrive_service (Resource): Authenticated GDrive client
            name (str): Name of the folder
        Returns:
            (str) ID of the folder
        """

        # Lookup the folder
        result = gdrive_service.files().list(
            q=f"name = '{name}' and '{config.gdrive_backup_folder}' in parents and trashed = false",
            pageSize=2
        ).execute()
        hits = result.get('files', [])

        # Operate!
        if len(hits) > 1:
            raise ValueError('>1 folder with this name in the backup directory')
        elif len(hits) == 1:
            output = hits[0].get('id')
            logger.info(f'Matched existing folder {output} to {name}')
        else:
            file_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [config.gdrive_backup_folder]
            }
            result = gdrive_service.files().create(
                body=file_metadata
            ).execute()
            output = result.get('id')
            logger.info(f'Created new folder {output} for {name}')
        return output

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
