import os
import slack
import logging
import humanize
from time import sleep
from datetime import datetime, timedelta

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
client = slack.WebClient(token=OAUTH_ACCESS_TOKEN)
logger.info('Created web client')

# Get my ID
my_id = client.auth_test()['user_id']
logger.info(f'Bot user ID: {my_id}')

# Find the "#ic_all" channel
channels = client.channels_list()
channel_id = None
for c in channels['channels']:
    if c['name'] == channel_to_monitor:
        channel_id = c['id']
logger.info(f'Found {channel_to_monitor} channel as channel id: {channel_id}')

# Make sure I am in the channel
channel_info = client.channels_info(channel=channel_id)['channel']
if my_id not in channel_info['members']:
    logger.info('Adding myself to the channel')
    result = client.channels_join(name=channel_to_monitor)

# Main loop: Waiting
while True:
    # Query the channel information
    channel_info = client.channels_info(channel=channel_id)['channel']

    # Get the last message time
    last_time = channel_info['latest']['ts']
    last_time = datetime.utcfromtimestamp(float(last_time))
    stall_time = datetime.utcnow() - last_time
    logger.info(f'Last message was {last_time.isoformat()}, {stall_time} ago')

    # Check if we are past the stall time
    if stall_time > threshold_stall_time:
        logger.info(f'Channel has been stalled for {stall_time - threshold_stall_time} too long')

        # Check if the bot was the last one to send a message
        #  If not, then send a reminder to the channel
        last_poster = channel_info['latest']['user']
        if last_poster == my_id:
            logger.info('Last poster was me, doing nothing')
        else:
            logger.info('Last poster was not me. Sending an @channel reminder')
            client.chat_postMessage(
                channel=channel_id,
                text=f'<!channel> Last message was {humanize.naturaltime(stall_time)}.'
                     f' Who\'s up? Let\'s play some D&D!',
                mrkdwn=True
            )

        # Sleep for the timeout length
        logger.info(f'Sleeping for {threshold_stall_time}')
        sleep(threshold_stall_time.total_seconds())

    else:
        # If we are not past the stall time, wait for the remaining time
        remaining_time = threshold_stall_time - stall_time
        logger.info(f'There is another {remaining_time} before a reminder will be sent')
        sleep(remaining_time.total_seconds())
