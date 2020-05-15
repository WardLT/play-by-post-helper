"""Persistent processes that perform pre-defined projects periodically"""
from datetime import datetime
from math import inf
from threading import Thread
from time import sleep
import logging

import humanize

from modron import config
from modron.db import ModronState
from modron.slack import BotClient


logger = logging.getLogger(__name__)


class ReminderService(Thread):
    """Thread that issues a reminder to players if play stalls"""

    def __init__(self, client: BotClient, reminder_channel: str = config.REMINDER_CHANNEL,
                 watch_channel_regex: str = config.WATCH_CHANNELS, daemon: bool = True,
                 max_sleep_time: float = inf):
        """
        Args:
            client: Authenticated BotClient
            reminder_channel: Channel on which to post reminders
            watch_channel_regex: Pattern to match channels to watch for activity
            daemon: Whether to launch as a daemon thread
            max_sleep_time: Longest time the thread is allowed to sleep for
        """
        super().__init__(daemon=daemon)
        self._client = client
        self._reminder_channel = reminder_channel
        self._watch_channels = client.match_channels(watch_channel_regex)
        self._max_sleep_time = max_sleep_time

        # Flag that tells the thread to throw an exception after it has waited for a certain amount of time
        self.stop = False

    def _sleep_until(self, wake_time: datetime):
        """Sleep until a certain time has been reached

        Args:
            wake_time (str): When for the sleep loop to end
        """

        while not self.stop:
            # Compute the amount of remaining time
            remaining_time = (wake_time - datetime.utcnow()).total_seconds()
            if remaining_time <= 0:
                return

            # Sleep for the maximum allowable time smaller
            #  than the amount of remaining time
            sleep_time = min(remaining_time, self._max_sleep_time)
            sleep(sleep_time)

        raise ValueError('User has requested this thread to halt')

    def run(self) -> None:
        """Display reminders if the play-by-post stalls.

        Modron will post reminders on a certain channel if no messages
        are posted on any of the watched channels after a certain
        allowed stall time.

        This operation runs on an infinite loop and might
        be best run from a separate thread.
        """
        # Get the channel ID for the reminder channel
        reminder_channel_id = self._client.get_channel_id(self._reminder_channel)

        # Warn user if the bot does not write a channel watched for stalling
        if self._reminder_channel not in self._watch_channels:
            logger.warning('Bot will write reminders to a channel not being watched for stalling, which '
                           'means it will issue reminders even if no other activity has occurred since the '
                           'previous reminder.')

        # Make sure I am in the channels to be watched and reminder channel
        self._client.add_self_to_channel(self._reminder_channel)
        for channel in self._watch_channels:
            self._client.add_self_to_channel(channel)

        # Main loop: Wait for messages
        while True:
            # Check every channel
            last_times, last_was_me = zip(*map(self._client.get_last_activity, self._watch_channels))

            # Get the most recent activity and info on most recent channel
            last_time = max(last_times)
            active_channel_ind = last_times.index(last_time)
            active_channel = self._watch_channels[active_channel_ind]
            active_poster_was_me = last_was_me[active_channel_ind]
            stall_time = datetime.utcnow() - last_time
            logger.info(f'Most recent post was {stall_time} ago in {active_channel}')

            # Determine when we would issue a reminder based on activity
            state = ModronState.load()
            reminder_time = last_time + state.allowed_stall_time

            # If it is after any previous reminder time, replace that reminder time
            if state.reminder_time is None or reminder_time > state.reminder_time:
                logger.info(f'Moving up the next reminder time to: {reminder_time}')
                state.reminder_time = reminder_time
                state.save()
            else:
                logger.info(f'Activity-based reminder would be sooner '
                            f'than user-specified reminder: {state.reminder_time}. Not updating reminder time')
                reminder_time = state.reminder_time

            # Check if we are past the stall time
            if datetime.now() > reminder_time:
                logger.info(f'Channel has been stalled for {stall_time - state.allowed_stall_time} too long')

                # Check if the bot was the last one to send a message
                #  If not, then send a reminder to the channel
                if active_poster_was_me:
                    logger.info('Last poster was me, doing nothing')
                else:
                    logger.info('Last poster was not me. Sending an @channel reminder')
                    self._client.chat_postMessage(
                        channel=reminder_channel_id,
                        text=f'<!channel> Last message was {humanize.naturaltime(stall_time)}.'
                             f' Who\'s up? Let\'s play some D&D!',
                        mrkdwn=True
                    )

                # Sleep for the timeout length
                wake_time = datetime.utcnow() + state.allowed_stall_time
                logger.info(f'Sleeping until {wake_time}')
                self._sleep_until(wake_time)
            else:
                # If we are not past the stall time, wait for the remaining time
                logger.info(f'Reminder will be sent at {reminder_time}')
                self._sleep_until(reminder_time)
