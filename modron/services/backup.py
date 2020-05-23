"""Services related to backing up channels"""
import json
import os
from datetime import datetime, timedelta
from math import inf, isclose
import logging
from time import sleep
from typing import List, Dict

from modron.services import BaseService
from modron.slack import BotClient

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
            my_time = datetime.fromtimestamp(float(msg['ts'])).astimezone()
            msg['ts'] = (my_time - my_time.utcoffset()).timestamp()

            # Write it out
            print(json.dumps(msg), file=fp)


class BackupService(BaseService):
    """Download and write messages from certain channels to disk

    Messages are written in a special "backup directory" which contains the channels
    being backed up as separate json-ld files.
    """

    def __init__(self, client: BotClient, backup_dir: str, frequency: timedelta,
                 channel_regex: str = "*", max_sleep_time: float = inf):
        """

        Args:
            client: Authenticated client
            backup_dir: Directory to store the
            channel_regex: Regex which matches the channels to be backed up
            max_sleep_time: Longest time to sleep before
        """
        super().__init__(client, max_sleep_time)
        self.frequency = frequency
        self.backup_dir = backup_dir
        self.backup_channels = client.match_channels(channel_regex)

    def backup_messages(self, channel: str) -> int:
        """Backup all messages from a certain channel

        Args:
            channel: Name of channel to backup
        Returns:
            (int) Number of messages written
        """
        logger.info(f'Starting to backup {channel}')

        # Get the time of the last message
        output_path = os.path.join(self.backup_dir, f'{channel}.jsonld')
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
                    start_time = max(start_time, int(msg["ts"]))
        logger.info(f'Starting timestamp {start_time}, which is {datetime.utcfromtimestamp(start_time)}')

        # Pulling the most recent message
        last_time, _ = self._client.get_last_activity(channel)
        if isclose(last_time.timestamp(), start_time):
            logger.info(f'No new messages in {channel}')
            return 0

        # Get the ID of the channel to be backed up
        channel_id = self._client.get_channel_id(channel)

        # Make one query to the system
        n_msg = 0
        response = self._client.conversations_history(channel=channel_id, inclusive='false', oldest=start_time)
        _write_messages(response['messages'], output_path)
        n_msg += len(response['messages'])

        # Loop until we have all of the messages
        while response['has_more']:
            response = self._client.conversations_history(channel=channel_id, inclusive='false', oldest=start_time,
                                                          cursor=response['response_metadata']['next_cursor'])
            _write_messages(response['messages'], output_path)
            n_msg += len(response['messages'])
            sleep(60 / 50)  # Make sure we don't saturate the limits
        logger.info(f'Backed up {n_msg} messages from {channel}')
        return n_msg

    def backup_all_channels(self) -> Dict[str, int]:
        """Download messages for all channels

        Returns:
            (dict) Number of messages downloaded per channel
        """

        return dict((c, self.backup_messages(c)) for c in self.backup_channels)

    def run(self):
        # Make sure I am a member of all the channels I am backing up
        for channel in self.backup_channels:
            self._client.add_self_to_channel(channel)

        # Run the main loop
        logger.info('Starting backup thread')
        while True:
            result = self.backup_all_channels()
            logger.info(f'Backed up {sum(result.values())} messages in total. From: {", ".join(result.keys())}')
            wake_time = datetime.utcnow() + self.frequency
            logger.info(f'Sleeping until {wake_time.isoformat()}')
            self._sleep_until(wake_time)
