# Play-by-Post Helper

[![Build Status](https://travis-ci.org/WardLT/play-by-post-helper.svg?branch=master)](https://travis-ci.org/WardLT/play-by-post-helper)
[![Coverage Status](https://coveralls.io/repos/github/WardLT/play-by-post-helper/badge.svg?branch=master)](https://coveralls.io/github/WardLT/play-by-post-helper?branch=master)

The Play-by-Post Helper (Modron) is a Slack bot that assists playing Role Playing Games (RPGs) with Slack.

The helper is designed to be a simple Slack Bot for performing tasks including:

- Messaging the channel to remind people if play has stalled
- Performing rolls according to D&D 5e rules
- Keeping track of character abilitiy and health

## Setting Up Modron

Modron is a Python-based web server that you will need to install and then register with Slack.
The [installation guide](./docs/installation.md) describes how to install 
and run the Python server, register the service with Slack and 
then configure it for your campaign.

## Using Modron

Modron is a collection of Slack slash commands and persistant services. 
We briefly introduce them here and refer you to the [user guide](./docs/user-guide.md)
for the full documentation. 

### Rolling Dice

![rolling_dice](docs/img/roll-command.png)

Modron supports all of the D&D 5e rules for dice rolling, such
as advantage and re-rolling ones.
Roll dice by calling `/modron roll`, `/mroll`, or just `/roll`.
A few examples include:

   - `/modron roll 1d20+5`: Rolling a single D20
   - `/modron roll 4d6 -1`: Roll 4d6 and re-roll any dice that are 1 on the first roll

### Channel Reminders

![reminder](docs/img/reminder.png) 

Modron will automatically watch the Slack and issue reminders if play stalls.
