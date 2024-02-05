# Installation

Installing Modron requires:

1. [Installing the Computational Environment](#where-to-install-and-run-modron)
2. [Registering the Bot with Discord](#creating-the-discord-app)
3. [Configuring the Server](#launching-modron-for-first-time)
4. [Adding Character Sheets](#adding-character-sheets)

## Where to Install and Run Modron

Modron is designed to run as a persistent service and will need to be running
whenever you are using Discord to play an RPG.
The resource requirements for Modron are minimal and can easily run on
a second generation Raspberry Pi (512 MB RAM, 700 MHz ARM processor)
or an Amazon `t2.nano`.

### Installing Python Requirements

Modron has limited Python requirements, which we describe with Anaconda.
Install the environment using conda with the command:

```bash
conda env create --file environment.yml --force
```

or by [creating a virtual environment with venv](https://docs.python.org/3/library/venv.html).

The NPC generator requires the [`wkhtmltopdf` command line tool](https://wkhtmltopdf.org/index.html) to be installed.

## Creating the Discord App

> I'm hosting the app on a tiny server under my couch, so you'll have to create your own!

The more complicated step is to create the Discord App itself.

Follow the instructions on ["Getting Started"](https://discord.com/developers/docs/getting-started) to
create the application and its security token.
Place the token as the `BOT_TOKEN` variable in [start-service.sh](../start-service.sh).

> Do not share that token with anyone!

The next step is to add Modron to your server.
As noted in the quick start, you will need to go to the "OAuth2" page
and generate a URL that gives your bot the following scope permissions:

- identify
- guilds
- messages.read
- bot

The "bot" scope will open a menu and give your bot the following permissions:

- "Change Nicknames" and "Manage Nicknames" for our yet-to-be implemented multi-character feature
- "Read Messages/View Channels" to be able to gather messages
- "Send Messages," "Create Public, Private Threads," and "Send Messages in Threads" to communicate via text
- "Attach Files" for the NPC generator
- "Read Message History" for backup
- "Mention Everyone" for alerts
- "Add Reactions," which is unused but potentially fun

That will give you a URL that points to discord.com. 
Open it and follow the instructions to add Modron to your party!

## Launching Modron for First Time

> You may want to [learn YAML first](https://learnxinyminutes.com/docs/yaml/)

Once you've added Modron to your Discord, you'll need to tell it a few things about your service.
All will be part of the [`modron_config.yml`](../modron_config.yml) file,
which follows the format defined in [`config.yml`](../modron/config.py).
A few first steps are to:

1. Enable [Developer Mode](https://www.howtogeek.com/714348/how-to-enable-or-disable-developer-mode-on-discord/)
   on your app, which will display numeric IDs of channels/guilds/etc in the app.   
2. Create a new section in the `team_options` section with the ID for your "server."
   Give that server a name as the `name` field of the server.
3. Provide the name of the channel you will use to talk to Modron in `ooc_channel`.


Your initial YAML file will look like.
   
```yaml
team_options:
  <server id>:
    name: <server name>
    ooc_channel: <channel name>
```

This is the minimum information required to run Modron, though you may want to add more (see next section).

When ready, start Modron by calling `./start-server.sh`.

## Customizing Modron

Add new features to Modron by setting the appropriate options in [`modron_config.yml`](../modron_config.yml)
then restarting the service.

### Reminders

Modron can send reminders to the players after stalls for more than a set time.

Enable the feature by:

1. Set `reminders` to ``True`` for your channel
2. Set `reminder_channel` the name of the channel in which to message players
3. Define a list of channels to watch as a list named `watch_channels`
4. If desired, change the `allowed_stall_time` before reminders are sent.

An example:

```yaml
team_options:
  <server id>:
    name: <server name>
    ooc_channel: <channel name>
    reminders: True
    reminder_channel: ic_all
    watch_channels:
       - ic_all
       - player1_gm 
```

### Backing up to Google Drive

Modron automatically downloads channel activity and, if proper credentials are acquired,
upload them to Google Drive.
Add a list of the channels to back up as a set for  `backup_channels` to control which channels are downloaded.

If you would like backup to Google drive, create a Google API project
and activate the Google Drive API for that project
following [Google's documentation](https://developers.google.com/drive/api/v3/enable-drive-api).
Once complete, download the credentials to `creds/grive` and run `get-gdrive-creds` to
get credentials for your user account.
The `token.pickle` file produced by your application contains the credentials needed by
Modron to access Google Drive on your behalf.
Then, change the `backup_folder` configuration to point to a folder in your Google Drive.
Folder IDs are available from the URL: `https://drive.google.com/drive/u/0/folders/<folder id>`

### Adding Character Sheets

Character sheets for Modron are stored in a YAML format on your server.
See [`Adrianna`](../characters/kaluth/adrianna.yml) as an example.

Add your own characters by first creating a subdirectory in `characters` using the name of your 
campaign and then add characters following the schema described in [`characters.py`](../modron/characters.py).
