#  Copyright (c) 2022 diminDDL
#  License: MIT License

import discord
import datetime
import requests
import feedparser
from discord.ext import commands, tasks


class Locate(commands.Cog, name="piLocate"):
    """
    This cog is used to get the latest news from rpilocator.com
    """
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.FEED_URL = 'https://rpilocator.com/feed/'
        self.USER_AGENT = 'DiscordBot'
        self.control = []
        f = feedparser.parse(self.FEED_URL, agent=self.USER_AGENT)
        if f.entries:
            for entries in f.entries:
                self.control.append(entries.id)
        self.lastUpdate = None
        self.lastFail = None
        self.updateFailed = False
        self.listen.start()

    @commands.command(aliases=["lastupdate", "lu", "last", "update"])
    async def getLastUpdate(self, ctx):
        await ctx.send(f"Last update: {self.lastUpdate.strftime('%d/%m/%Y %H:%M:%S')}")

    def cog_unload(self):
        self.listen.cancel()

    def formatEmbed(self, message, time):
        if(self.updateFailed):
            self.updateFailed = False
            embed = discord.Embed(title="Last update failed", description=f"failed at: {self.lastFail.strftime('%d/%m/%Y %H:%M:%S')}", color=0xff0000)
            return embed
        embed = discord.Embed(title=message.title, description=message.link, color=0xe91e63)
        embed.set_footer(text=f'{time.strftime("%d/%m/%Y %H:%M:%S")}')
        return embed

    async def getUpdateChannel(self, guild):
        # TODO implement this
        # for now we use a hardcoded channel
        return 1000740663882682499

    async def getGuildList(self):
        # TODO implement this
        # for now we use a hardcoded guild
        return [759419755253465188]

    @tasks.loop(seconds=59.0)
    async def listen(self):
        try:
            f = feedparser.parse(self.FEED_URL, agent=self.USER_AGENT)

            for entries in f.entries:
                if entries.id not in self.control:
                
                    embed = self.formatEmbed(entries, self.lastUpdate)

                    for guild in self.getGuildList():
                        channel = await self.bot.fetch_channel(self.getUpdateChannel(guild))
                        await channel.send(embed=embed)

                    self.control.append(entries.id)
            self.lastUpdate = datetime.datetime.now()
        except:
            self.updateFailed = True
            self.lastFail = datetime.datetime.now()
            return

def setup(bot):
    bot.add_cog(Locate(bot))
