"""General utilities for working with the Slack client"""
from datetime import timedelta, datetime
from functools import lru_cache
from time import sleep
from typing import Optional, List, Tuple
import logging
import re

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
        channels = self.conversations_list()
        channel_id = None
        for c in channels['channels']:
            if c['name'] == channel_name:
                channel_id = c['id']
        logger.info(f'Found {channel_name} channel as channel id: {channel_id}')
        return channel_id

    @lru_cache(maxsize=128)
    def get_channel_name(self, channel_id: str) -> str:
        """Get the channel name given the id"""
        result = self.conversations_info(channel=channel_id)
        return result['channel']['name']

    @lru_cache(maxsize=128)
    def conversation_is_public_channel(self, channel_id: str) -> bool:
        """Determine if a conversation is a channel and not an IM/Group/private channel/etc"""

        result = self.conversations_info(channel=channel_id)
        return result['channel']['is_channel']

    def get_user_name(self, user_id: str) -> str:
        """Lookup a user name given their ID.

        Of the `available options <https://api.slack.com/types/user>`_,
        we use the display name, which is what is rendered in the client"""

        result = self.users_info(user=user_id)
        return result['user']['profile']['display_name']

    def add_self_to_channel(self, channel_name: str) -> Optional[SlackResponse]:
        """Adds the bot user to a certain channel

        Args:
            channel_name (str): Channel to be added to
        Returns:
             (dict) Reply from server on request to add
        """
        logger.info(f'Adding myself to the channel: {channel_name}')
        return self.channels_join(name=channel_name)

    def display_reminders_on_channel(self, reminder_channel: str, watch_channels: List[str],
                                     allowed_stall_time: timedelta = timedelta(days=1)):
        """Display reminders if the play-by-post stalls.

        Modron will post reminders on a certain channel if no messages
        are posted on any of the watched channels after a certain
        allowed stall time.

        This operation runs on an infinite loop and might be best
        run from a separate thread.

        Args:
            reminder_channel (str): Name of the channel on which to post reminders
            watch_channels (str): Names of the channels on which to watch for messages
            allowed_stall_time (timedelta): Time without a message before the reminder is sent
        """
        # Get the channel ID for the reminder channel
        reminder_channel_id = self.get_channel_id(reminder_channel)

        # Warn user if the bot does not write a channel watched for stalling
        if reminder_channel not in watch_channels:
            logger.warning(f'Bot will write reminders to a channel not being watched for stalling, which '
                           f'means it will issue reminders even if no other activity has occurred since the '
                           f'previous reminder.')

        # Make sure I am in the channels to be watched and reminder channel
        self.add_self_to_channel(reminder_channel)
        for channel in watch_channels:
            self.add_self_to_channel(channel)

        # Main loop: Wait for messages
        while True:
            # Check every channel
            stall_times, last_was_me = zip(*map(self.get_stall_time, watch_channels))

            # Get the minimum stall time and info on most recent channel
            stall_time = min(stall_times)
            active_channel_ind = stall_times.index(stall_time)
            active_channel = watch_channels[active_channel_ind]
            active_poster_was_me = last_was_me[active_channel_ind]
            logger.info(f'Most recent post was {stall_time} ago in {active_channel}')

            # Check if we are past the stall time
            if stall_time > allowed_stall_time:
                logger.info(f'Channel has been stalled for {stall_time - allowed_stall_time} too long')

                # Check if the bot was the last one to send a message
                #  If not, then send a reminder to the channel
                if active_poster_was_me:
                    logger.info('Last poster was me, doing nothing')
                else:
                    logger.info('Last poster was not me. Sending an @channel reminder')
                    self.chat_postMessage(
                        channel=reminder_channel_id,
                        text=f'<!channel> Last message was {humanize.naturaltime(stall_time)}.'
                             f' Who\'s up? Let\'s play some D&D!',
                        mrkdwn=True
                    )

                # Sleep for the timeout length
                logger.info(f'Sleeping for {stall_time}')
                sleep(allowed_stall_time.total_seconds())
            else:
                # If we are not past the stall time, wait for the remaining time
                remaining_time = allowed_stall_time - stall_time
                logger.info(f'There is another {remaining_time} before a reminder will be sent')
                sleep(remaining_time.total_seconds())

    def get_stall_time(self, channel_name: str) -> Tuple[timedelta, bool]:
        """Determine the time since a message was sent in a channel

        Args:
            channel_name (str): Name of the channel to assess
        Returns:
            - (timedelta) Time since the last message was sent
            - (bool) Whether Modron was the last message sender
        """
        # Query the channel information
        channel_id = self.get_channel_id(channel_name)
        channel_info = self.channels_info(channel=channel_id)['channel']

        # Get the last message time
        last_time = channel_info['latest']['ts']
        last_time = datetime.utcfromtimestamp(float(last_time))
        stall_time = datetime.utcnow() - last_time
        logger.info(f'Last message was in {channel_name} was {last_time.isoformat()}, {stall_time} ago')

        # Determine if Modron posted last
        last_was_me = channel_info['latest'].get('user', None) == self.my_id

        return stall_time, last_was_me

    def match_channels(self, regex: str) -> List[str]:
        """Get a list of all channels whose names match a certain pattern

        Args:
            regex (str): Pattern to match
        Returns:
            ([str]): List of the names of channels that match the pattern
        """

        # Get a list of all channels
        all_channels = self.conversations_list()["channels"]
        logger.info(f'Found {len(all_channels)} channels')

        # Apply filter
        patt = re.compile(regex)
        matched = []
        for channel in all_channels:
            name = channel["name"]
            if patt.match(name) is not None:
                matched.append(name)

        return matched
