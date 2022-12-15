"""Interact with the channel sleep timer"""
from argparse import ArgumentParser, Namespace
from datetime import datetime
import logging

import humanize
import isodate
from discord.ext.commands import Context
from isodate import ISO8601Error

from modron.db import ModronState
from modron.interact import InteractionModule

_description = '''Interact with the reminder timer'''

logger = logging.getLogger(__name__)


def _add_delay(team_id: int, time: str) -> str:
    """Update Modron reminder state

    Args:
        team_id (int): Name of the team to adjust
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

    def __init__(self):
        super().__init__('reminder', 'View or snooze the reminder timer', _description)

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

    async def interact(self, args: Namespace, context: Context):
        if args.reminder_command is None or args.reminder_command == 'status':
            # Get the reminder time as a time
            state = ModronState.load()
            reminder_time = state.reminder_time[context.guild.id]
            reply = f'Next check for reminder: <t:{int(reminder_time.timestamp())}>'  # Format as a
        elif args.reminder_command == 'break':
            reply = _add_delay(context.guild.id, args.time)
        else:
            raise ValueError('Support for {args.reminder_command} has not been implemented (blame Logan)')

        # Send reply back to user
        await context.reply(reply)
