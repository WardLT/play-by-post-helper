# Development Guide

Modron runs as a multi-threaded application that is launched by `server.py`.
We explain Modron by describing each of the types of threads:
what they do, how are they launched, and how they are built.

## Persistent Services

Persistent services perform tasks on a scheduled basis, such
as backing up chat history. 
The threads are all launched at the beginning of `server.py` with 
a single thread being responsible for the processes associated with a single
 
The threads are based on [BaseService](../modron/services/__init__.py) class,
which contains utility operations for pausing the thread on regular intervals.
The `server.py` script is responsible for configuring the threads appropriately.

<!--- todo (wardlt): Make the threads read configuration *entirely* from config or
*entirely* from the __init__.py. Having half/half seems confusing -->

## Slash Commands

The `/modron` slash commands provide in-chat interaction for Modron.
Slack [slash commands](https://api.slack.com/interactivity/slash-commands)
are received by Modron using a single HTTP endpoint `/modron` which 
routes the command to a single Python function for responding to the command, 
which is registered to Flask in `server.py`.

The [`handle_slash_command`](../modron/interact/__init__.py) function parses
the input command, launches a thread to handle the more detailed processing, 
and immediately returns a ["response received"](https://api.slack.com/interactivity/slash-commands#best_practices)
back to Slack.
The immediate response helps ensure that Slack receives a response in under their
required latency of 3000ms. 
The interactions for each of the modules can then reply on a slower timescale
using the response URL provided in the Slack command payload.

The subcommands for the `/modron` slash command are built using 
different subclasses of [`InteractionModule`](../modron/interact/base.py).
Implementations of this class provide a `register_argparse` that configure
a argument parser to read the user's command and an `interact` function 
that perform the desired command given the the parsed arguments and
the Slash command payload. 
The `server.py` launch script instantiates these modules with
the Slack authentication client(s) and uses their `register_argparse`
functions to create the "master parser" used by `handle_slash_command`.

Most of the slash command functionalities are based upon 
Python's [`argparse`](https://docs.python.org/3.8/library/argparse.html) module.
Modron has a custom "HelpFormatter" which renders the help strings or error
messages into Slack's markdown format.
The parser also relies on a subclassed version of the base
`ArgumentParser` that raises a special exception type holding the exception 
string rather than printing the parser help to `stderr` and
then calling `exit()`.
See [`_argparse.py`](../modron/interact/_argparse.py) for details.

## Other Interactions

There are a few other, special-purpose interactions.

### Team Registration OAuth Endpoint

The `oauth` endpoint receives authorization codes and exchanges them
for OAuth tokens.
The tokens are saved to disk as `received-tokens.json`, which
includes the `auth_token` needed to add a new team to the Slack.
(See [installation instructions](installation.md#launching-modron-for-first-time)
for more details.)

### Status Checker

We use Slack's events API to provide a simple status-check in.
It is registered using Slack's event API classes in `server.py`.
