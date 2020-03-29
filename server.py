import os
import logging
from threading import Thread
from datetime import timedelta

from modron.slack import BotClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration details
reminder_channel = "ooc_discussion"
watch_channel_regex = r"ic_(?!mezu_gm)"
threshold_stall_time = timedelta(days=1)

# Look for configuration information
OAUTH_ACCESS_TOKEN = os.environ.get('OAUTH_ACCESS_TOKEN', None)
if OAUTH_ACCESS_TOKEN is None:
    raise ValueError('Cannot find Auth token')

# Make the Slack client
client = BotClient(token=OAUTH_ACCESS_TOKEN)
logger.info('Created web client')

# Get the channels to watch
watch_channels = client.match_channels(watch_channel_regex)

# Watch the channel as a daemon thread
reminder_thread = Thread(target=client.display_reminders_on_channel, name=f'watch_for_stalls',
                         args=(reminder_channel, watch_channels, threshold_stall_time),
                         daemon=False)
reminder_thread.start()
