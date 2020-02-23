# Play-by-Post Helper

The Play-by-Post Helper (PbPHelper) is a Slack bot that assists playing Role Playing Games (RPGs) with Slack.

The helper is designed to be a simple Slack Bot for performing tasks including:

- Messaging the channel to remind people if play has stalled

## Installation

The package has limited requirements on the Python end. 
Install the environment using conda with the command:

```bash
conda env create --file environment.yml --force
```

The more complicated step is to create the Slack App itself.
The [tutorial on the GitHub page for the Python API](https://github.com/slackapi/python-slackclient/tree/master/tutorial)
is very good!
Follow the directions from the first section to create the app,
 give it the required permissions,
 and access the AccessToken.

The app requires at least the following Bot Token Scopes (refer back to the [tutorial](https://github.com/slackapi/python-slackclient/blob/master/tutorial/01-creating-the-slack-app.md#give-your-app-permissions)):
- `app_mentions:read`: Asking the bot to keep track of things
- `channels:history`: Allowing the bot to read the channel history
- `channels:join`: Allow bot to add itself to channels
- `channels:read`: Allows bot to figure out which channels it need add itself to
- `chat:write`: Send chat messages as its own personality
- `im:write`: Send messages to people on private channels
- `mpim:write`: Send messages to groups of people

_Note_: Some of the features alluded to by these permissions have not been implemented yet.
 
You will need to store the access token as an environment variable named ``OAUTH_ACCESS_TOKEN``
for the bot to use it. 
My preferred method is to store it as an environment variable. 
