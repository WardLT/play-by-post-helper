"""General utilities for working with the Slack client"""
from datetime import timedelta, datetime
from functools import lru_cache
from time import sleep
from typing import Optional
import logging

import humanize
from slack import WebClient
from slack.web.slack_response import SlackResponse


logger = logging.getLogger(__name__)


class BotClient(WebClient):
    """Utility class for a Bot user

    Is a superclass of WebClient, so you can use it like a normal WebClient.
    and also use a few utility operations used often by my Bot.

    The utility operations are all designed to use channel names as arguments.
    The channel ids are stored in an LRU cache to prevent unnecessary calls to
    the Slack API.
    """

    def __init__(
            self,
            token=None,
            timeout=30,
    ):
        super().__init__(token, timeout=timeout)
        self._my_id = None

    @property
    def my_id(self) -> str:
        """Get the ID of the bot user"""
        if self._my_id is None:
            self._my_id = self.auth_test()['user_id']
            logger.info(f'Queried Slack to get my ID: {self._my_id}')
        return self._my_id

    @lru_cache(maxsize=128)
    def get_channel_id(self, channel_name: str) -> str:
        """Get the channel ID associated with a certain name"""
        channels = self.channels_list()
        channel_id = None
        for c in channels['channels']:
            if c['name'] == channel_name:
                channel_id = c['id']
        logger.info(f'Found {channel_name} channel as channel id: {channel_id}')
        return channel_id

    def add_self_to_channel(self, channel_name: str) -> Optional[SlackResponse]:
        """Adds the bot user to a certain channel

        Args:
            channel_name (str): Channel to be added to
        Returns:
             (dict) Reply from server on request to add
        """
        logger.info(f'Adding myself to the channel: {channel_name}')
        return self.channels_join(name=channel_name)

    def display_reminders_on_channel(self, channel_name: str,
                                     allowed_stall_time: timedelta = timedelta(days=1)):
        """Display reminders on a channel

        This operation runs on an infinite loop and might be best
        run from a separate thread.

        Args:
            channel_name (str): Name of the channel to be monitored
            allowed_stall_time (timedelta): Time without a message before the reminder is sent
        """
        # Get the channel ID
        channel_id = self.get_channel_id(channel_name)

        # Make sure I am in the channel to be watched
        self.add_self_to_channel(channel_name)

        # Main loop: Wait for messages
        while True:
            # Query the channel information
            channel_info = self.channels_info(channel=channel_id)['channel']

            # Get the last message time
            last_time = channel_info['latest']['ts']
            last_time = datetime.utcfromtimestamp(float(last_time))
            stall_time = datetime.utcnow() - last_time
            logger.info(f'Last message was {last_time.isoformat()}, {stall_time} ago')

            # Check if we are past the stall time
            if stall_time > allowed_stall_time:
                logger.info(f'Channel has been stalled for {allowed_stall_time - stall_time} too long')

                # Check if the bot was the last one to send a message
                #  If not, then send a reminder to the channel
                last_poster = channel_info['latest']['user']
                if last_poster == self.my_id:
                    logger.info('Last poster was me, doing nothing')
                else:
                    logger.info('Last poster was not me. Sending an @channel reminder')
                    self.chat_postMessage(
                        channel=channel_id,
                        text=f'<!channel> Last message was {humanize.naturaltime(stall_time)}.'
                             f' Who\'s up? Let\'s play some D&D!',
                        mrkdwn=True
                    )

                # Sleep for the timeout length
                logger.info(f'Sleeping for {stall_time}')
                sleep(stall_time.total_seconds())
            else:
                # If we are not past the stall time, wait for the remaining time
                remaining_time = allowed_stall_time - stall_time
                logger.info(f'There is another {remaining_time} before a reminder will be sent')
                sleep(remaining_time.total_seconds())
