#  Copyright (c) 2022 diminDDL
#  License: MIT License

import discord
import datetime
import requests
import feedparser
from time import mktime
from discord.ext import commands, tasks
from pilocator.backend.util import pretty_date
from pilocator.backend.util import can_change_settings


async def check_permissions(ctx, channel: discord.TextChannel, role: discord.Role):
    if not channel.permissions_for(ctx.me).send_messages:
        await ctx.respond("I don't have permission to send messages in that channel.")
        return False
    elif not channel.permissions_for(ctx.me).embed_links:
        await ctx.respond("I don't have permission to embed links in that channel.")
        return False
    elif not channel.permissions_for(ctx.me).manage_messages:
        await ctx.respond("I don't have permission to manage messages in that channel.")
        return False
    elif not role.mentionable:
        await ctx.respond("I don't have permission to mention that role.")
        return False
    return True


class Locate(commands.Cog, name="piLocate"):
    """
    This cog is used to get the latest news from rpilocator.com
    """
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.redis = self.bot.redis
        self.FEED_URL = 'https://rpilocator.com/feed/'
        self.USER_AGENT = 'DiscordBot'
        self.control = []
        f = feedparser.parse(self.FEED_URL, agent=self.USER_AGENT)
        if f.entries:
            for entries in f.entries:
                self.control.append(entries.id)

        # self.control.pop(0)    # remove after testing

        self.lastUpdate = None
        self.lastFail = None
        self.updateFailed = False
        self.listen.start()

    @commands.command(aliases=["lastupdate", "lu", "last", "update"])
    async def lastcheck(self, ctx):
        """
        This command is used to get the time of the last update from rpilocator.com
        """
        if self.lastUpdate != None:
            await ctx.send(f"Last update (UTC): {self.lastUpdate.strftime('%d/%m/%Y %H:%M:%S')}, {pretty_date(time=self.lastUpdate)}")
        else:
            await ctx.send("No update yet")

    @commands.check(can_change_settings)
    @commands.command()
    async def setup(self, ctx, channel: discord.TextChannel, role: discord.Role):
        """
        This command is used to setup the channel to post the updates and the role to ping when there is a new update
        """
        if not await can_change_settings(ctx):
            return

        if not await check_permissions(ctx, channel, role):
            return
        
        print(channel)
        print(role)

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
            self.lastUpdate = datetime.datetime.now()
            for entries in f.entries:
                if entries.id not in self.control:
                    
                    embed = self.formatEmbed(entries, datetime.datetime.fromtimestamp(mktime(entries.published_parsed)))

                    for guild in await self.getGuildList():
                        chanelInt = await self.getUpdateChannel(guild)
                        channel = await self.bot.fetch_channel(chanelInt)
                        await channel.send(embed=embed)

                    self.control.append(entries.id)
        except Exception as e:
            self.updateFailed = True
            self.lastFail = datetime.datetime.now()
            print("failed: " + str(e))
            return

def setup(bot):
    bot.add_cog(Locate(bot))
