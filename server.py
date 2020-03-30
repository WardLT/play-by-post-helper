import os
import sys
import logging
from functools import partial
from threading import Thread
from datetime import timedelta, datetime
from logging.handlers import RotatingFileHandler

from slackeventsapi import SlackEventAdapter

from modron.events import status_check
from modron.slack import BotClient

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[RotatingFileHandler('modron.log', mode='a',
                                                  maxBytes=1024 * 1024 * 2,
                                                  backupCount=1),
                              logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Record the start time, used for status information
start_time = datetime.now()

# Configuration details
reminder_channel = "ic_all"
watch_channel_regex = r"ic_(?!mezu_gm)"
threshold_stall_time = timedelta(days=1)

# Get the secure tokens
OAUTH_ACCESS_TOKEN = os.environ.get('OAUTH_ACCESS_TOKEN', None)
if OAUTH_ACCESS_TOKEN is None:
    raise ValueError('Cannot find Auth token')
SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET')
if SIGNING_SECRET is None:
    raise ValueError('Cannot find signing secret')

# Make the Slack client and Events adapter
client = BotClient(token=OAUTH_ACCESS_TOKEN)
event_adapter = SlackEventAdapter(SIGNING_SECRET)
logger.info('Created web client')

# Get the channels to watch
watch_channels = client.match_channels(watch_channel_regex)

# Watch the channel as a daemon thread
reminder_thread = Thread(target=client.display_reminders_on_channel, name=f'watch_for_stalls',
                         args=(reminder_channel, watch_channels, threshold_stall_time),
                         daemon=True)
reminder_thread.start()

# Register the events
event_adapter.on('message', f=partial(status_check, client=client, start_time=start_time))

# Start the Slack Events API
event_adapter.start(port=3152, debug=True)
