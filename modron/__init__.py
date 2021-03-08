import os
import sys
import json
import logging
from urllib.parse import quote_plus, urlparse
from functools import partial
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import humanize
import requests
from flask import Flask, request
from slackeventsapi import SlackEventAdapter

from modron.config import get_config
from modron.events import status_check
from modron.interact import assemble_parser, handle_slash_command, SlashCommandPayload
from modron.interact.dice_roll import DiceRollInteraction
from modron.interact.reminder import ReminderModule
from modron.interact.npc import NPCGenerator
from modron.interact.character import CharacterSheet
from modron.services.backup import BackupService
from modron.services.reminder import ReminderService
from modron.slack import BotClient


def create_app(test_config=None):
    """Create the flask app"""

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
    OAUTH_ACCESS_TOKENS = os.environ.get('OAUTH_ACCESS_TOKENS')
    SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
    CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
    CLIENT_ID = os.environ.get('CLIENT_ID')

    # Make the Flask app
    app = Flask('modron', template_folder='./views/templates', static_folder="./views/static")
    app.jinja_env.filters['quote_plus'] = quote_plus
    app.secret_key = CLIENT_SECRET

    def get_netloc(url):
        p = urlparse(url)
        return f'{p.scheme}://{p.netloc}'
    app.jinja_env.filters['get_netloc'] = get_netloc
    app.jinja_env.filters['humanize_td'] = humanize.naturaldelta
    app.jinja_env.filters['humanize_size'] = humanize.naturalsize

    # Store some details about the runtime configuration
    app.config['start_time'] = start_time
    app.config['team_config'] = config
    app.config['CLIENT_SECRET'] = CLIENT_SECRET
    app.config['CLIENT_ID'] = CLIENT_ID

    # Register the views
    from .views import status, auth, players
    app.register_blueprint(status.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(players.bp)

    # Store the clients
    clients = {}
    app.config['clients'] = clients

    # Make the Slack client and Events adapter
    if OAUTH_ACCESS_TOKENS is None:
        logger.warning('OAUTH_ACCESS_TOKENS was unset. Skipping all Slack-related functionality')
        return app

    for token in OAUTH_ACCESS_TOKENS.split(":"):
        client = BotClient(token=token)
        client.team_info()
        clients[client.team_id] = client
    event_adapter = SlackEventAdapter(SIGNING_SECRET, "/slack/events", app)
    logger.info(f'Finished initializing {len(clients)} Slack clients')

    # Check that we have configurations for each team
    authed_teams = set(clients.keys())
    missing_config = authed_teams.difference(config.team_options.keys())
    if len(missing_config) > 0:
        raise ValueError(f'Missing configuration data for {len(missing_config)} teams: {", ".join(missing_config)}')

    # Make the services
    app.config['services'] = {'reminder': {}, 'backup': {}}
    reminder_threads = {}
    for team_id, team_config in config.team_options.items():
        if team_id not in clients:
            logging.warning(f'Missing OAuth Token for {team_id}')
            continue
        client = clients[team_id]

        # Start the reminder thread
        if team_config.reminders:
            reminder = ReminderService(clients[team_id], team_config.reminder_channel,
                                       team_config.watch_channels)
            reminder.start()
            reminder_threads[team_id] = reminder
            app.config['services']['reminder'][team_config.name] = reminder
        else:
            logger.info(f'No reminders for {team_config.name}')

        # Start the backup thread
        if team_config.backup_channels is not None:
            backup = BackupService(client, frequency=timedelta(days=1), channel_regex=team_config.backup_channels)
            backup.start()
            app.config['services']['backup'][team_config.name] = backup
        else:
            logger.info(f'No backup for {team_config.name}')

    # Generate the slash command responder
    modules = [
        DiceRollInteraction(clients),
        ReminderModule(clients, reminder_threads),
        NPCGenerator(clients),
        CharacterSheet(clients)
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
        return "Success!"

    # Register the events
    event_adapter.on('message', f=partial(status_check, clients=clients, start_time=start_time))

    return app
