# Play-by-Post Helper

[![CI](https://github.com/WardLT/play-by-post-helper/actions/workflows/python-app.yml/badge.svg)](https://github.com/WardLT/play-by-post-helper/actions/workflows/python-app.yml)
[![Coverage Status](https://coveralls.io/repos/github/WardLT/play-by-post-helper/badge.svg?branch=master)](https://coveralls.io/github/WardLT/play-by-post-helper?branch=master)

The Play-by-Post Helper (Modron) is a Discord bot that assists playing Role Playing Games (RPGs) on Discord.
Modron can do common tasks for D&D and other TTRPG games, including:

- Messaging the channel to remind people if play has stalled
- Performing rolls according to D&D 5e rules
- Keeping track of character ability and health

## Setting Up Modron

Modron is a Python-based web server that you will need to install and then register with Discord.
The [installation guide](./docs/installation.md) describes how to install it for your Guild.

## Using Modron

Modron is a collection of Discord slash commands and persistent services. 
We briefly introduce them here and refer you to the [user guide](./docs/user-guide.md)
for the full documentation. 

### Rolling Dice

![rolling_dice](docs/img/roll-command.png)

Modron supports the D&D 5e rules for dice rolling, such as advantage and re-rolling ones.
A few examples include:

   - `$roll 1d20+5`: Rolling a single D20
   - `$roll 4d6 -1`: Roll 4d6 and re-roll any dice that are 1 on the first roll

### Tracking HP and Character Sheets

![HP Tracking](./docs/img/manage-hp.png)

Modron can look up values from a character sheet for each player and change its HP over time.

### Channel Reminders

![reminder](docs/img/reminder.png) 

Modron will issue reminders if play stalls for more than a configurable amount.
