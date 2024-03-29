"""Definition of the bot"""

from datetime import timedelta
import logging

from discord.ext.commands import Bot
from discord import utils

from modron.config import config
from modron.db import ModronState
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
from modron.utils import get_version

logger = logging.getLogger(__name__)


class ModronClient(Bot):
    """Client used to connect to Discord"""

    testing: bool = False

    async def on_ready(self):
        """Start the services when the bot is ready"""
        logger.info(f'Logged on as {self.user}')

        # If testing, do nothing
        if self.testing:
            return

        # Determine if this is a new version
        my_version = get_version()
        state = ModronState().load()
        was_updated = False
        if state.library_version != my_version:
            logger.info(f'Library has been updated since last boot. New version: {my_version}')
            was_updated = True
            state.library_version = my_version
            state.save()

        # Launch the services for each time
        for team_id, team_config in config.team_options.items():
            guild = self.get_guild(team_id)

            # Start the reminder thread
            if team_config.reminders:
                reminder = ReminderService(guild, team_config.reminder_channel,
                                           team_config.watch_channels)
                self.loop.create_task(reminder.run())
                logger.info(f'Launched reminder service for {team_config.name}')
            else:
                logger.info(f'No reminders for {team_config.name}')

            # Start the backup thread
            if len(team_config.backup_channels) > 0:
                backup = BackupService(guild,
                                       backup_dir=config.backup_dir,
                                       frequency=timedelta(days=1),
                                       channels=team_config.backup_channels)
                self.loop.create_task(backup.run())
                logger.info(f'Launched backup service for {team_config.name}')
            else:
                logger.info(f'No backup for {team_config.name}')

            # Make a hello message, if we're not in testing mode
            ooc_channel = utils.get(guild.channels, name=team_config.ooc_channel)
            if was_updated:
                await ooc_channel.send('I have been leveled up. My summoner knows my new powers')
            else:
                await ooc_channel.send('I have been re-summoned. Your incense was appreciated. 🤖')

        logger.info('Successfully started Modron.')

    async def on_disconnect(self):
        logger.warning('Disconnected from Discord service')

    async def on_connect(self):
        logger.info('Connected to Discord service')
