"""Command for a user to remind themselves about a message"""

import asyncio
import logging
from argparse import ArgumentParser, Namespace
from asyncio import Task
from datetime import timedelta, datetime
from typing import Optional

from discord import TextChannel, utils, User, AllowedMentions
from discord.ext.commands import Context

from modron.config import config
from modron.interact import InteractionModule
from modron.interact.reminder import parse_delay

logger = logging.getLogger(__name__)


class FollowupModule(InteractionModule):
    """Simple module for users leaving themselves reminders to respond later"""

    def __init__(self):
        """
        Args:
            bot: Bot, which we'll use to map user to reminder channel
        """
        super().__init__('rem', 'Remind self about a message later',
                         'Have Modron remind you to reply to a message later')

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

        # Determine where to remind the user
        team_options = config.team_options[context.guild.id]
        reply_channel = context.channel
        if context.author.id in team_options.private_channels:
            reply_channel = utils.get(context.guild.channels, name=team_options.private_channels[context.author.id])
        logger.info(f'Watching for reminders on {context.channel.name}, reminding user on {reply_channel.name}')

        # Set up a timer to reply when that occurs
        task = asyncio.create_task(
            self.reply_if_needed(duration, context.author, context.channel, reply_channel)
        )
        logger.info('Submitted a reminder to run as a co-routine')

        return task

    async def reply_if_needed(self,
                              sleep_time: timedelta,
                              user: User,
                              watch_channel: TextChannel,
                              reply_channel: TextChannel) -> bool:
        """Send a reminder if the user did not reply within

        Args:
            sleep_time: How long until we check
            user: User who made this request
            watch_channel: Channel to watch if a reminder is needed
            reply_channel: Text channel in which to reply
        """
        # Wait until the sleep is over
        start_time = datetime.utcnow()
        await asyncio.sleep(sleep_time.total_seconds())
        logger.info(f'Awake and looking for messages from {user.display_name} after {start_time}')

        # See what the latest message from this user is
        any_from_user = False
        async for message in watch_channel.history(after=start_time):
            if message.author == user:
                logger.info(f'Found a message from user: {message.content[:32]}')
                any_from_user = True
                break
        if any_from_user:
            print(any_from_user)
            logger.info('The user already responded, so we don\'t need to remind them')
            return False

        # Otherwise, message them
        await reply_channel.send(
            f"<@{user.id}>, you asked me to remind you to reply to a message in <#{watch_channel.id}>",
            delete_after=10 * 60,
            allowed_mentions=AllowedMentions(users=[user])
        )
        return True
