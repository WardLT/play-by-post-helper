"""Interact with the channel sleep timer"""
from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
import logging

import humanize
from pytimeparse.timeparse import timeparse
from discord.ext.commands import Context

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
    # Parse the time period
    duration = parse_delay(time)

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
        return f'Reminders are already paused until {humanize.naturaldate(state.reminder_time[team_id])}'


def parse_delay(time: str) -> timedelta:
    """Parse an ISO8061 time length

    Args:
        time: Amount of time to wait by
    Returns:
        Time delta
    Raises:
        (ValueError) If user gives bad time
    """

    seconds = timeparse(time, granularity='minutes')
    if seconds is None:
        raise ValueError(f'Cannot parse snooze time \"{time}\".')
    return timedelta(seconds=seconds)


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
        subparser.add_argument('time', help='How long to delay the reminder for', type=str, nargs="+")

    async def interact(self, args: Namespace, context: Context):
        guild_id = context.guild.id
        if args.reminder_command is None or args.reminder_command == 'status':
            # Get the reminder time as a time
            state = ModronState.load()
            reminder_time = state.reminder_time[guild_id]
            reply = f'Next check for reminder: <t:{int(reminder_time.timestamp())}>'  # Format as a time

            # Display the last message
            if guild_id in state.last_message is not None:
                last_message = state.last_message[guild_id]
                reply += (f"\n\nLast message was from {last_message.sender}"
                          f" in #{last_message.channel}"
                          f" <t:{int(last_message.last_time.timestamp())}:R>")
        elif args.reminder_command == 'break':
            delay_time = " ".join(args.time)
            reply = _add_delay(guild_id, delay_time)
        else:
            raise ValueError('Support for {args.reminder_command} has not been implemented (blame Logan)')

        # Reply to user
        await context.reply(reply)
