"""Interact with the channel sleep timer"""
from argparse import ArgumentParser, Namespace
from asyncio import Task
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
import logging

import humanize
from pytimeparse.timeparse import timeparse
from discord import User, TextChannel, Guild, AllowedMentions
from discord.ext.commands import Context
from discord import utils

from modron.config import config
from modron.bot import ModronClient
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
        return f'Reminders are already paused until {humanize.naturaldate(state.reminder_time)}'


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
        subparser.add_argument('time', help='How long to delay the reminder for', type=str)

    async def interact(self, args: Namespace, context: Context):
        if args.reminder_command is None or args.reminder_command == 'status':
            # Get the reminder time as a time
            state = ModronState.load()
            reminder_time = state.reminder_time[context.guild.id]
            reply = f'Next check for reminder: <t:{int(reminder_time.timestamp())}>'  # Format as a time

            # Display the last message
            if state.last_message is not None:
                reply += f"\n\nLast message was from {state.last_message.sender} in #{state.last_message.channel}" \
                         f" <t:{int(state.last_message.last_time.timestamp())}:R>"
        elif args.reminder_command == 'break':
            reply = _add_delay(context.guild.id, args.time)
        else:
            raise ValueError('Support for {args.reminder_command} has not been implemented (blame Logan)')

        # Reply to user
        await context.reply(reply)


class FollowupModule(InteractionModule):
    """Simple module for users leaving themselves reminders to respond later"""

    def __init__(self, bot: ModronClient):
        """
        Args:
            bot: Bot, which we'll use to map user to reminder channel
        """
        super().__init__('rem', 'Remind self about a message later',
                         'Have Modron remind you to reply to a message later')

        # Map user to channel object
        self.user_map: Dict[str, Dict[str, TextChannel]] = {}  # guild_id -> user_id -> TextChannel
        for guild_id, guild_options in config.team_options.items():
            self.user_map[guild_id] = {}
            guild: Guild = bot.get_guild(guild_id)
            for user_id, channel_name in guild_options.private_channels.items():
                channel = utils.get(guild.channels, name=channel_name)
                self.user_map[guild_id][user_id] = channel

    def register_argparse(self, parser: ArgumentParser):
        parser.add_argument('time', nargs='?', default='3 hours',
                            help='How long to wait for a message (default: 3 hours)')

    async def interact(self, args: Namespace, context: Context) -> Optional[Task]:
        # Get the pause time
        try:
            duration = parse_delay(args.time)
        except ValueError as error:
            await context.reply(str(error))
            return

        # Set up a timer to reply when that occurs
        task = asyncio.create_task(
            self.reply_if_needed(duration, context.author, context.channel)
        )
        logger.info('Submitted a reminder to run as a co-routine')
        return task

    async def reply_if_needed(self, sleep_time: timedelta, user: User, channel: TextChannel) -> bool:
        """Send a reminder if the user did not reply within

        Args:
            sleep_time: How long until we check
            user: User who made this request
            channel: Text channel in which to reply
        """
        # Wait until the sleep is over
        start_time = datetime.utcnow()
        await asyncio.sleep(sleep_time.total_seconds())
        logger.info(f'Awake and looking for messages from {user.display_name} after {start_time}')

        # See what the latest message from this user is
        any_from_user = False
        async for message in channel.history(after=start_time):
            if message.author == user:
                logger.info(f'Found a message from user: {message.content[:32]}')
                any_from_user = True
                break
        if any_from_user:
            print(any_from_user)
            logger.info('The user already responded, so we don\'t need to remind them')
            return False

        # Determine where to remind the user
        channel = self.user_map[channel.guild.id].get(user.id, channel)
        logger.info(f'Reminding user on back on {channel.name}')

        # Otherwise, message them
        await channel.send(
            f"<@{user.id}>, you asked me to remind you to reply to a message in <#{channel.id}>",
            delete_after=10 * 60,
            allowed_mentions=AllowedMentions(users=[user])
        )
        return True
