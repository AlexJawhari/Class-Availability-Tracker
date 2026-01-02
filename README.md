# Class Availability Tracker

A cloud-hosted service that watches UTD coursebook sections and notifies subscribed users when seats open.

## Overview

Measurement of class availability is done by a background runner that scrapes the UTD Coursebook site.
Users interact with the system via a Discord bot to track or untrack specific classes.

## Features

-   **Discord Integration**: Slash commands (`/track`, `/untrack`, `/list`) to manage subscriptions.
-   **Smart Notifications**: Background runner checks for changes and DMs users immediately when a spot opens.

## Usage

1.  Add the bot to your server or DM it.
2.  Use `/track CS 4349 006` to start watching a class.
3.  Receive a DM when the class opens!
