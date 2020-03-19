import os
import logging
from threading import Thread
from datetime import timedelta

from modron.slack import BotClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration details
channel_to_monitor = "ic_all"
threshold_stall_time = timedelta(days=1)

# Look for configuration information
OAUTH_ACCESS_TOKEN = os.environ.get('OAUTH_ACCESS_TOKEN', None)
if OAUTH_ACCESS_TOKEN is None:
    raise ValueError('Cannot find Auth token')

# Make the Slack client
client = BotClient(token=OAUTH_ACCESS_TOKEN)
logger.info('Created web client')

# Watch the channel as a daemon thread
reminder_thread = Thread(target=client.display_reminders_on_channel, name=f'reminder_on_{channel_to_monitor}',
                         args=(channel_to_monitor, threshold_stall_time),
                         daemon=True)
reminder_thread.start()
