"""Services related to reminding players when it is their turn"""
from datetime import datetime
from math import inf
import logging

import humanize

from modron.config import get_config
from modron.db import ModronState
from modron.services import BaseService
from modron.slack import BotClient

logger = logging.getLogger(__name__)


config = get_config()


class ReminderService(BaseService):
    """Thread that issues a reminder to players if play stalls"""

    def __init__(self, client: BotClient, reminder_channel, watch_channel_regex, max_sleep_time: float = inf):
        """
        Args:
            client: Authenticated BotClient
            reminder_channel: Channel on which to post reminders
            watch_channel_regex: Pattern to match channels to watch for activity
            max_sleep_time: Longest time the thread is allowed to sleep for
        """
        short_name = config.team_options[client.team_id].name
        super().__init__(client, max_sleep_time, name=f'reminder_{short_name}')
        self._reminder_channel = reminder_channel
        self._watch_channels = client.match_channels(watch_channel_regex)

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
            allowed_stall_time = config.team_options[self._client.team_id].allowed_stall_time
            reminder_time = last_time + allowed_stall_time

            # If it is after any previous reminder time, replace that reminder time
            team_reminder_time = state.reminder_time.get(self._client.team_id, None)
            if team_reminder_time is None or reminder_time > team_reminder_time:
                logger.info(f'Moving up the next reminder time to: {reminder_time}')
                state.reminder_time[self._client.team_id] = reminder_time
                state.save()
            else:
                logger.info(f'Activity-based reminder would be sooner '
                            f'than user-specified reminder: {state.reminder_time}. Not updating reminder time')
                reminder_time = state.reminder_time[self._client.team_id]

            # Check if we are past the stall time
            if datetime.now() > reminder_time:
                logger.info(f'Channel has been stalled for {stall_time - allowed_stall_time} too long')

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
                wake_time = datetime.utcnow() + allowed_stall_time
                logger.info(f'Sleeping until {wake_time}')
                self._sleep_until(wake_time)
            else:
                # If we are not past the stall time, wait for the remaining time
                logger.info(f'Reminder will be sent at {reminder_time}')
                self._sleep_until(reminder_time)
