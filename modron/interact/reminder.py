"""Interact with the channel sleep timer"""
from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone, timedelta
from threading import Thread
import logging

import humanize
import isodate
import requests
from isodate import ISO8601Error

from modron.db import ModronState
from modron.interact import InteractionModule, SlashCommandPayload
from modron.slack import BotClient
from modron import config

_description = '''Interact with the reminder timer'''

logger = logging.getLogger(__name__)


def start_reminder_thread(client: BotClient):
    """Launch a reminder thread and store it in the global context"""
    watch_channels = client.match_channels(config.WATCH_CHANNELS)
    config.REMINDER_THREAD = Thread(target=client.display_reminders_on_channel, name=f'reminder_thread',
                                    args=(config.REMINDER_CHANNEL, watch_channels), daemon=True)
    config.REMINDER_THREAD.start()


def _add_delay(time: str) -> str:
    """Update Modron reminder state

    Args:
        time (str): How long to snooze for
    Returns:
        (str) A reply to give to the user about the status
    """
    # Parse the duration
    try:
        duration = isodate.parse_duration(time)
    except ISO8601Error:
        logger.info(f'Parsing failed for: {time}')
        return f'Cannot parse snooze time \"{time}\". Use ISO 8601 spec: P[n]Y[n]M[n]DT[n]H[n]M[n]S'

    # Compute the new reminder time
    logger.info(f'Request to snooze for {duration}')
    new_time = datetime.now() + duration

    # Update, if needed
    state = ModronState.load()
    if new_time > state.reminder_time:
        # Update the reminder time
        logger.info(f'Updating reminder time from {state.reminder_time} to {new_time}')
        state.reminder_time = new_time
        state.save()

        # Reply to user
        return f'Paused reminders until at least {humanize.naturaldate(new_time)}'
    else:
        logger.info('No update')
        return f'Reminders are already paused until {humanize.naturaldate(state.reminder_time)}'


class ReminderModule(InteractionModule):
    """Interact with the reminder timer"""

    def __init__(self, client: BotClient):
        super().__init__(client, 'reminder', 'View or snooze the reminder timer', _description)

    def register_argparse(self, parser: ArgumentParser):
        # Prepare to add subparsers
        subparsers = parser.add_subparsers(title='available commands',
                                           description='Different ways to interact with reminder process',
                                           dest='reminder_command')

        # Subcommand for checking status
        subparsers.add_parser('status', help='Print the status for the reminder thread')

        # Subcommand for snoozing the reminder
        subparser = subparsers.add_parser('break', help='Delay the reminder thread for a certain time')
        subparser.add_argument('time', help='How long to delay the reminder for. ISO 8601 format', type=str)

    def interact(self, args: Namespace, payload: SlashCommandPayload):
        if args.reminder_command == 'status':
            reply = self._generate_status(payload)
        elif args.reminder_command == 'break':
            reply = _add_delay(args.time)
        else:
            reply = f'*ERROR*: Support for {args.reminder_command} has not been implemented (blame Logan)'

        # Send reply back to user
        requests.post(payload.response_url, json={
            'text': reply, 'mkdwn': True,
            'response_type': 'in_channel',
        })

    def _generate_status(self, payload: SlashCommandPayload) -> str:
        """Generate a status message for the reminder threads

        Args:
            payload (SlashCommandPayload): Command payload
        Returns:
            (str) Status message
        """

        # Get the user's time zone
        user_info = self.client.users_info(user=payload.user_id)
        user_tz = timezone(timedelta(seconds=user_info['user']['tz_offset']),
                           name=user_info['user']['tz_label'])

        # Get the reminder time
        state = ModronState.load()
        reminder_time = state.reminder_time.astimezone(user_tz)
        reply = f'Next check for reminder: {humanize.naturaldate(reminder_time)} ' \
                f'{reminder_time.strftime("%I:%M %p %Z")}\n'

        # Append thread status
        if config.REMINDER_THREAD is None:
            reply += 'No reminder thread detected'
        else:
            reply += f'Thread status: {"Alive" if config.REMINDER_THREAD.is_alive() else "*Dead*"}'
        return reply
