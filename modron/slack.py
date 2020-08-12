"""General utilities for working with the Slack client"""
import asyncio
from datetime import datetime
from functools import lru_cache
from threading import Lock
from typing import Optional, List, Tuple, Union
import logging
import re

from slack import WebClient
from slack.web.slack_response import SlackResponse

logger = logging.getLogger(__name__)
_api_lock = Lock()


class BotClient(WebClient):
    """Utility class for a Bot user

    Is a superclass of WebClient, so you can use it like a normal WebClient.
    and also use a few utility operations used often by my Bot.

    Many utility operations are all designed to use channel names as arguments.
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

        # Get the team name
        info = self.auth_test()
        self.team_id = info['team_id']
        self.team_name = info['team']
        self.my_id = info['user_id']
        logger.info(f'Created a client for {self.team_name} ({self.team_id}). User id {self.my_id}')

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

    def conversation_is_channel(self, channel_id: str) -> bool:
        """Determine if a conversation is a channel and not an IM/Group/private channel/etc

        Public channels begin with C, group IMs with a G, and direct messages with a D

        Args:
            channel_id: ID of channel to assess
        Returns:
            Whether it is a channel
        """
        return channel_id.startswith('C')

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

    def get_last_activity(self, channel_name: str) -> Tuple[datetime, bool]:
        """Determine the most recent time a message was sent in a channel

        Args:
            channel_name (str): Name of the channel to assess
        Returns:
            - (datetime) Time when the most recent message was sent
            - (bool) Whether Modron was the last message sender
        """
        # Query the channel information
        channel_id = self.get_channel_id(channel_name)
        channel_info = self.channels_info(channel=channel_id)['channel']

        # Get the last message time
        last_time = float(channel_info['latest']['ts'])
        last_time = datetime.fromtimestamp(last_time)
        stall_time = datetime.now() - last_time
        logger.info(f'Last message was in {channel_name} was {last_time.isoformat()}, {stall_time} ago')

        # Determine if Modron posted last
        last_was_me = channel_info['latest'].get('user', None) == self.my_id

        return last_time, last_was_me

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

    def api_call(
        self, *args, **kwargs
    ) -> Union[asyncio.Future, SlackResponse]:
        with _api_lock:
            return super().api_call(*args, **kwargs)
