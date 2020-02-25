import os
import logging
from datetime import datetime, timedelta

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

# Watch the cha
client.display_reminders_on_channel(channel_to_monitor, threshold_stall_time)
