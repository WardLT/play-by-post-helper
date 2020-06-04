import os
import sys
import json
import logging
from functools import partial
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import requests
from flask import Flask, request
from slackeventsapi import SlackEventAdapter

from modron.config import get_config
from modron.events import status_check
from modron.interact import assemble_parser, handle_slash_command, SlashCommandPayload, \
    DiceRollInteraction, ReminderModule, NPCGenerator
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
from modron.slack import BotClient

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s',
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
OAUTH_ACCESS_TOKENS = os.environ.get('OAUTH_ACCESS_TOKENS', None)
if OAUTH_ACCESS_TOKENS is None:
    raise ValueError('Cannot find Auth token')
SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
if SIGNING_SECRET is None:
    raise ValueError('Cannot find signing secret')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
if CLIENT_SECRET is None:
    raise ValueError('Cannot find client secret')
CLIENT_ID = os.environ.get('CLIENT_ID')
if CLIENT_ID is None:
    raise ValueError('Cannot find the client ID')

# Make the Flask app
app = Flask('modron')

# Make the Slack client and Events adapter
clients = {}
for token in OAUTH_ACCESS_TOKENS.split(":"):
    client = BotClient(token=token)
    clients[client.team_id] = client
event_adapter = SlackEventAdapter(SIGNING_SECRET, "/slack/events", app)
logger.info('Finished initializing clients')

# Check that we have configurations for each team
authed_teams = set(clients.keys())
missing_config = authed_teams.difference(config.team_options.keys())
if len(missing_config) > 0:
    raise ValueError(f'Missing configuration data for {len(missing_config)} teams: {", ".join(missing_config)}')

# Make the services
reminder_threads = {}
for team_id, team_config in config.team_options.items():
    client = clients[team_id]

    # Start the reminder thread
    if team_config.reminder_channel is not None:
        reminder = ReminderService(clients[team_id], team_config.reminder_channel,
                                   team_config.watch_channels)
        reminder.start()
        reminder_threads[team_id] = reminder

    # Start the backup thread
    backup = BackupService(client, frequency=timedelta(days=1), channel_regex=team_config.backup_channels)
    backup.start()

# Generate the slash command responder
modules = [
    DiceRollInteraction(clients),
    ReminderModule(clients, reminder_threads),
    NPCGenerator(clients)
]
modron_cmd_parser = assemble_parser(modules)


@app.route('/modron', methods=('POST',))
def modron_slash_cmd():
    payload = SlashCommandPayload(**request.form.to_dict())
    return handle_slash_command(payload, parser=modron_cmd_parser)


@app.route('/oauth', methods=('GET',))
def slack_auth():
    # Get the request code from the user
    code = request.args.get('code', None)
    logger.info('Received an authorization code. About to exchange it for a token')

    # Query Slack to get the token
    res = requests.post(
        url="https://slack.com/api/oauth.v2.access",
        data={
            'code': code,
            'client_secret': CLIENT_SECRET,
            'client_id': CLIENT_ID,
            'redirect_uri': request.base_url
        }
    )
    with open('received-tokens.json', 'w') as fp:
        json.dump(res.json(), fp)


# Register the events
event_adapter.on('message', f=partial(status_check, clients=clients, start_time=start_time))

if __name__ == "__main__":
    # Start the Slack Events API
    app.run(port=3152, host='0.0.0.0', debug=False)
