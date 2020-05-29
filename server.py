import os
import sys
import logging
from functools import partial
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from flask import Flask, request
from slackeventsapi import SlackEventAdapter

from modron.config import get_config
from modron.events import status_check
from modron.interact import assemble_parser, handle_slash_command, SlashCommandPayload, all_modules, \
    DiceRollInteraction, ReminderModule, NPCGenerator
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
from modron.slack import BotClient

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[RotatingFileHandler('modron.log', mode='a',
                                                  maxBytes=1024 * 1024 * 2,
                                                  backupCount=1),
                              logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Load the system configuration
config = get_config()

# Record the start time, used for status information
start_time = datetime.now()

# Get the secure tokens
OAUTH_ACCESS_TOKEN = os.environ.get('OAUTH_ACCESS_TOKEN', None)
if OAUTH_ACCESS_TOKEN is None:
    raise ValueError('Cannot find Auth token')
SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
if SIGNING_SECRET is None:
    raise ValueError('Cannot find signing secret')

# Make the Flask app
app = Flask('modron')

# Make the Slack client and Events adapter
client = BotClient(token=OAUTH_ACCESS_TOKEN)
event_adapter = SlackEventAdapter(SIGNING_SECRET, "/slack/events", app)
logger.info('Created web client')

# Make the reminder thread
reminder = ReminderService(client)
reminder.start()

# Generate the slash command responder
modules = [
    DiceRollInteraction(client),
    ReminderModule(client, reminder),
    NPCGenerator(client)
]
modron_cmd_parser = assemble_parser(modules)

# Start the backup thread
backup = BackupService(client, config.backup_path, timedelta(days=1),
                       channel_regex=config.backup_channels)
backup.start()


@app.route('/modron', methods=('POST',))
def modron_slash_cmd():
    payload = SlashCommandPayload(**request.form.to_dict())
    return handle_slash_command(payload, parser=modron_cmd_parser)


# Register the events
event_adapter.on('message', f=partial(status_check, client=client, start_time=start_time))

if __name__ == "__main__":
    # Start the Slack Events API
    app.run(port=3152, host='0.0.0.0', debug=False)
