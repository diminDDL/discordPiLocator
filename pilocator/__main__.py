#  Copyright (c) 2019-2022 ThatRedKite and contributors
#  Copyright (c) 2022 diminDDL
#  License: MIT License

import os
from abc import ABC
from datetime import datetime
from pathlib import Path

import aiohttp
import psutil
import discord
import json
from discord.ext import commands, bridge

__name__ = "pilocator"
__version__ = "1.0"
__author__ = "diminDDL and ThatRedKite"

enabled_ext = [
    "pilocator.cogs.sudocog",
    "pilocator.cogs.locator",
    "pilocator.cogs.help",
]

tempdir = "/tmp/pilocator/"
datadir = "/app/data"
dirname = "/app/pilocator"

# this is a pretty dumb way of doing things, but it works
intents = discord.Intents.all()

# check if the init_settings.json file exists and if not, create it
if not Path(os.path.join(datadir, "init_settings.json")).exists():
    print("No init_settings.json file found. Creating one now.")
    settings_dict_empty = {
        "discord token": "",
        "prefix": "+",
    }
    # write the dict as json to the init_settings.json file with the json library
    with open(os.path.join(datadir, "init_settings.json"), "w") as f:
        # dump the dict as json to the file with an indent of 4 and support for utf-8
        json.dump(settings_dict_empty, f, indent=4, ensure_ascii=False)
    # make the user 1000 the owner of the file, so they can edit it
    os.chown(os.path.join(datadir, "init_settings.json"), 1000, 1000)

    # exit the program
    exit(1)

# load the init_settings.json file with the json library
with open(os.path.join(datadir, "init_settings.json"), "r") as f:
    try:
        settings_dict = json.load(f)
        # get the discord token, the tenor api key, and the prefix from the dict
        discord_token = settings_dict["discord token"]
        prefix = settings_dict["prefix"]

    except json.decoder.JSONDecodeError:
        print("init_settings.json is not valid json. Please fix it.")
        exit(1)


# define the bot class
class pilocator(bridge.Bot, ABC):
    def __init__(self, command_prefix, dirname, help_command=None, description=None, **options):
        super().__init__(command_prefix, help_command=help_command, description=description, **options)
        # ---static values---
        self.prefix = command_prefix
        # paths
        self.dirname = dirname
        self.datadir = "/app/data/"
        self.tempdir = "/tmp/"

        # info
        self.version = __version__
        self.starttime = datetime.now()
        self.pid = os.getpid()
        self.process = psutil.Process(os.getpid())

        # ---dynamic values---

        # settings
        self.debugmode = False
        # sessions
        self.aiohttp_session = None  # give the aiohttp session an initial value
        self.loop.run_until_complete(self.aiohttp_start())

        # bot status info
        self.cpu_usage = 0
        self.command_invokes_hour = 0
        self.command_invokes_total = 0

    async def aiohttp_start(self):
        self.aiohttp_session = aiohttp.ClientSession()


# create the bot instance
print(f"Starting pilocator v {__version__} ...")
bot = pilocator(prefix, dirname, intents=intents)
print(f"Loading {len(enabled_ext)} extensions: \n")

# load the cogs aka extensions
for ext in enabled_ext:
    try:
        print(f"   loading {ext}")
        bot.load_extension(ext)
    except Exception as exc:
        print(f"error loading {ext}")
        raise exc

# try to start the bot with the token from the init_settings.json file catch any login errors
try:
    bot.run(discord_token)
except discord.LoginFailure:
    print("Login failed. Check your token. If you don't have a token, get one from https://discordapp.com/developers/applications/me")
    exit(1)


