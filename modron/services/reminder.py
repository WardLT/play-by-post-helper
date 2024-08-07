"""Services related to reminding players when it is their turn"""
from typing import List, Optional
from datetime import datetime, timedelta
from math import inf
import logging

import humanize
from discord import Guild, TextChannel, AllowedMentions, CategoryChannel, Message
from discord import utils

from modron.config import config
from modron.db import ModronState, LastMessage
from modron.discord import get_last_activity
from modron.services import BaseService

logger = logging.getLogger(__name__)


class ReminderService(BaseService):
    """Thread that issues a reminder to players if play stalls"""

    def __init__(self,
                 guild: Guild,
                 reminder_channel: str,
                 channels_to_watch: List[str],
                 max_sleep_time: float = inf):
        """
        Args:
            guild: Authenticated BotClient
            reminder_channel: Name of channel on which to post reminders
            channels_to_watch: IDs of the channels, which could include category channels, channels to watch
            max_sleep_time: Longest time the thread is allowed to sleep for
        """
        short_name = config.team_options[guild.id].name
        super().__init__(guild, max_sleep_time, name=f'reminder_{short_name}')
        self.reminder_channel: TextChannel = utils.get(self._guild.channels, name=reminder_channel)
        self.channels_to_watch = channels_to_watch
        self.allowed_stall_time = config.team_options[guild.id].allowed_stall_time

        # Status attributes
        self.active_channel = None
        self.last_message: Optional[Message] = None
        self.time_last_activity = datetime.now()
        self.last_channel_poll = datetime.now()
        self.watched_channels: List[TextChannel] = []

    @property
    def is_expired(self) -> bool:
        """Whether the played has stalled for the specified amount of time"""
        return datetime.now() > self.team_reminder_time

    @property
    def stall_time(self) -> timedelta:
        """How long play has been stalled, at most"""
        return datetime.now() - self.time_last_activity

    @property
    def since_last_poll(self) -> timedelta:
        """How long since we have polled for new messages"""
        return datetime.now() - self.last_channel_poll

    @property
    def time_until_reminder(self) -> timedelta:
        """How long until a reminder"""
        return self.team_reminder_time - datetime.now()

    @property
    def team_reminder_time(self):
        state = ModronState.load()
        return state.reminder_time.get(self._guild.id, None)

    async def run(self) -> None:
        """Display reminders if the play-by-post stalls.

        Modron will post reminders on a certain channel if no messages
        are posted on any of the watched channels after a certain
        allowed stall time.

        This operation runs on an infinite loop and might
        be best run from a separate thread.
        """
        while True:
            wake_time = await self.perform_reminder_check()
            await self._sleep_until(wake_time)

    async def perform_reminder_check(self) -> datetime:
        """Check for whether a reminder needs to be given and, if so, do it.

        Also updates the status attributes of this object and the
        overall state stored in ModronState yaml file.

        Returns:
            (datetime) Time to check for the next reminder
        """
        # Determine the last activity
        last_time = await self.assess_last_activity()
        stall_time = datetime.now() - last_time
        logger.info(f'Most recent post was {stall_time} ago in {self.active_channel} '
                    f'by {self.last_message.author.name}')
        self.last_channel_poll = datetime.now()

        # Determine when we would issue a reminder based on activity
        state = ModronState.load()
        reminder_time = last_time + self.allowed_stall_time

        # Update the lass message in the state
        state.last_message[self._guild.id] = LastMessage.from_discord(self.last_message)

        # If it is after any previous reminder time, replace that reminder time
        team_reminder_time = state.reminder_time.get(self._guild.id, None)
        if team_reminder_time is None or reminder_time > team_reminder_time:
            logger.info(f'Moving up the next reminder time to: {reminder_time}')
            state.reminder_time[self._guild.id] = reminder_time
        else:
            logger.info(f'Activity-based reminder would be sooner '
                        f'than user-specified reminder: {team_reminder_time}. Not updating reminder time')
            reminder_time = state.reminder_time[self._guild.id]
        state.save()

        # Check if we are past the stall time
        now = datetime.now()
        if now > reminder_time:
            logger.info(f'Channel has been stalled for {stall_time - self.allowed_stall_time} too long')

            # Check if the last message was me giving a reminder message
            active_poster_was_me = (self.last_message is not None and
                                    self.last_message.author == self._guild.me)

            # Check if we're in the middle of an off time
            wake_time, sleep_time = config.team_options[self._guild.id].reminder_window
            if now.time() > sleep_time or now.time() < wake_time:
                # If so, sleep until
                wake_datetime = now.replace(hour=wake_time.hour, minute=wake_time.minute)
                if wake_datetime < now:
                    wake_datetime += timedelta(days=1)

                logger.info(f'It is a bad time to remind anyone. Sleeping until {wake_datetime.time()}')
                return wake_datetime + timedelta(seconds=1)

            # If not, send a reminder
            if active_poster_was_me:
                logger.info('Last poster was me. Upping the ante')
                await self.reminder_channel.send(
                    content=f'@everyone, another reminder! It\'s been since {humanize.naturaltime(stall_time)}'
                            f' that we played some D&D!',
                    allowed_mentions=AllowedMentions.all()
                )
            else:
                logger.info('Last poster was not me. Sending an @channel reminder')
                await self.reminder_channel.send(
                    content=f'@everyone Last message was {humanize.naturaltime(stall_time)}.'
                            f' Who\'s up? Let\'s play some D&D!',
                    allowed_mentions=AllowedMentions.all()
                )

            # Sleep for the timeout length
            wake_time = datetime.now() + self.allowed_stall_time
        else:
            # If we are not past the stall time, wait for the remaining time
            wake_time = reminder_time
        return wake_time + timedelta(seconds=1)

    async def assess_last_activity(self) -> datetime:
        """Get the last activity on the watched channels

        Updates the results in:
            ``self.last_updated_time`` - Time of the last activity on watched channels
            ``self.active_channel`` - Last active channel
            ``self.last_message`` - Last message sent on any watched channel
            ``self.watch_channels`` - The list of channels being watched

        Returns:
            Time of the latest activity
        """

        # Get the channels to watch
        self.watched_channels = []
        for name in self.channels_to_watch:
            watch_channel = utils.get(self._guild.channels, name=name)
            if isinstance(watch_channel, TextChannel):
                self.watched_channels.append(watch_channel)
            elif isinstance(watch_channel, CategoryChannel):
                self.watched_channels.extend(watch_channel.text_channels)
            else:
                raise ValueError(f'Unrecognized type of channel: {type(watch_channel)}')
        logger.info(f'Watching {len(self.watched_channels)} channels for activity')

        # Warn user if the bot does not write a channel watched for stalling
        if self.reminder_channel not in self.watched_channels:
            logger.warning('Bot will write reminders to a channel not being watched for stalling, which '
                           'means it will issue reminders even if no other activity has occurred since the '
                           'previous reminder.')

        # Check every channel
        tasks = [await get_last_activity(c) for c in self.watched_channels]
        last_times, last_messages = zip(*tasks)

        # Get the most recent activity and info on most recent channel
        last_time = max(last_times)
        self.time_last_activity = last_time
        active_channel_ind = last_times.index(last_time)
        self.last_message = last_messages[active_channel_ind]
        self.active_channel = self.watched_channels[active_channel_ind]
        return last_time
