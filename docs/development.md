# Development Guide

Modron is a multithreaded Python application launched from the command line using [`modron`](../modron/app.py).

## Main Thread: Discord

The main thread of the application is a Discord Bot built on [discord.py](https://discordpy.readthedocs.io/en/stable/intro.html).

Calling `modron` on the command line:

1. Reads configuration details for each Discord "guild" from the `modron_config.yml` file
1. Reads a security token from an environment variable
1. Starts services for each guild
1. Registers commands used in all guilds
1. Opens a websocket connection with Discord

## Persistent Services

Persistent services perform tasks on a scheduled basis, such as backing up chat history. 

Each thread is based on [BaseService](../modron/services/__init__.py) class,
which contains utility operations for pausing the thread on regular intervals.

<!--- todo (wardlt): Make the threads read configuration *entirely* from config or
*entirely* from the __init__.py. Having half/half seems confusing -->

## Discord Commands

We discord.py's [Command](https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html) 
to implement commands written using [Python's argparse](https://docs.python.org/3/library/argparse.html) with Discord.

Each command is built by subclassing the [`InteractionModule`](../modron/interact/base.py).
Implementations of this class provide a `register_argparse` that configures
an argument parser to read the user's command and an `interact` function 
that acts on the command given the parsed arguments and the Discord command payload. 

The parser relies on a subclassed version of the Python's
`ArgumentParser` that raises a special exception type holding the exception 
string rather than printing the parser help to `stderr` and
then calling `exit()`.
See [`_argparse.py`](../modron/interact/_argparse.py) for details.
