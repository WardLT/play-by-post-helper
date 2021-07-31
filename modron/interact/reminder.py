"""Interact with the channel sleep timer"""
from argparse import ArgumentParser, Namespace
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional, Dict

import humanize
import isodate
import requests
from isodate import ISO8601Error

from modron.db import ModronState
from modron.interact import InteractionModule, SlashCommandPayload
from modron.services.reminder import ReminderService

_description = '''Interact with the reminder timer'''

logger = logging.getLogger(__name__)


def _add_delay(team_id: str, time: str) -> str:
    """Update Modron reminder state

    Args:
        team_id (str): Name of the team to adjust
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
    if new_time > state.reminder_time[team_id]:
        # Update the reminder time
        logger.info(f'Updating reminder time from {state.reminder_time[team_id]} to {new_time}')
        state.reminder_time[team_id] = new_time
        state.save()

        # Reply to user
        return f'Paused reminders until at least {humanize.naturaldate(new_time)}'
    else:
        logger.info('No update')
        return f'Reminders are already paused until {humanize.naturaldate(state.reminder_time)}'


class ReminderModule(InteractionModule):
    """Interact with the reminder timer"""

    def __init__(self, clients, reminder_thread: Optional[Dict[str, ReminderService]] = None):
        """
        Args:
            clients: Authenticated BotClients
            reminder_thread: Pointer to the reminder service
        """
        super().__init__(clients, 'reminder', 'View or snooze the reminder timer', _description)
        if reminder_thread is None:
            reminder_thread = dict()
        self.reminder_threads = reminder_thread

    def register_argparse(self, parser: ArgumentParser):
        # Prepare to add subparsers
        subparsers = parser.add_subparsers(title='available commands',
                                           description='Different ways to interact with reminder process',
                                           dest='reminder_command')

        # Subcommand for checking status
        subparsers.add_parser('status', help='Print the status for the reminder thread')

        # Subcommand for snoozing the reminder
        subparser = subparsers.add_parser('break', help='Delay the reminder thread for a certain time')
        subparser.add_argument('time', help='How long to delay the reminder for. ISO 8601 format (ex: P3d)', type=str)

    def interact(self, args: Namespace, context: SlashCommandPayload):
        if args.reminder_command is None or args.reminder_command == 'status':
            reply = self._generate_status(context)
        elif args.reminder_command == 'break':
            reply = _add_delay(context.team_id, args.time)
        else:
            reply = f'*ERROR*: Support for {args.reminder_command} has not been implemented (blame Logan)'

        # Send reply back to user
        requests.post(context.response_url, json={
            'text': reply, 'mkdwn': True
        })

    def _generate_status(self, payload: SlashCommandPayload) -> str:
        """Generate a status message for the reminder threads

        Args:
            payload (SlashCommandPayload): Command payload
        Returns:
            (str) Status message
        """

        # Get the user's time zone
        user_info = self.clients[payload.team_id].users_info(user=payload.user_id)
        user_tz = timezone(timedelta(seconds=user_info['user']['tz_offset']),
                           name=user_info['user']['tz_label'])

        # Get the reminder time
        state = ModronState.load()
        reminder_time = state.reminder_time[payload.team_id].astimezone(user_tz)
        reply = f'Next check for reminder: {reminder_time.strftime("%a %b %d, %I:%M %p")}\n'

        # Append thread status
        thread = self.reminder_threads.get(payload.team_id, None)
        if thread is None:
            reply += 'No reminder thread detected'
        else:
            reply += f'Thread status: {"Alive" if thread.is_alive() else "*Dead*"}'
        return reply
