#  Copyright (c) 2022 diminDDL
#  License: MIT License

import discord
import datetime
import requests
import feedparser
from urllib.parse import urlparse, parse_qs
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

async def is_allowed_filter(filter: str):
    allowedRegions = ["AT", "BE", "CA", "CH", "CN", "DE", "ES", "FR", "IT", "JP", "NL", "PL", "PT", "SE", "UK", "US", "ZA"]
    allowedWendors = ["adafruit", "berrybase", "botland", "chicagodist", "coolcomp", "digikeyus", "electrokit", "elektor", "elektronica", "farnell", "kubii", "mauserpt", "mchobby", "melopero", "newark", "okdonl", "okdouk", "okdous", "pi3g", "pimoroni", "pishopca", "pishopch", "pishopus", "pishopza", "rapid", "raspberrystore", "rasppishop", "reichelt", "sbcomp", "seeedstudio", "semaf", "sparkfun", "switchjp", "thepihut", "tiendatec", "vilros", "welectron"]
    allowedDevices = ["CM3", "CM4", "PI3", "PI4", "PIZERO"]
    for region in allowedRegions:
        if filter == region:
            return True
    for vendor in allowedWendors:
        if filter == vendor:
            return True
    for device in allowedDevices:
        if filter == device:
            return True
    return False

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

        #self.control.pop(0)    # remove after testing

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
            await ctx.send(f"Last update: <t:{int(datetime.datetime.timestamp(self.lastUpdate))}:T>, {pretty_date(time=self.lastUpdate)}")
        else:
            await ctx.send("No update yet")

    @commands.check(can_change_settings)
    @commands.command()
    async def setup(self, ctx, channel: discord.TextChannel, role: discord.Role, filter=''):
        """
        This command is used to setup the channel to post the updates and the role to ping when there is a new update.
        Allows a filter to be set while being set up. The format can be obtained at the bottom of this page: https://rpilocator.com/about.cfm
        Examples: `-setup #channel @role` - sends all updates and pings the role.
        `-setup #channel @role https://rpilocator.com/feed/?country=DE,NL,PL&cat=CM4,PI3,PIZERO` - sends only updates from Germany, Netherlands and Poland for CM4, PI3 and PI ZERO devices, and pings the role.
        """
        # check seeings and permissions
        if not await can_change_settings(ctx):
            return

        if not await check_permissions(ctx, channel, role):
            return
        
        # parse the filter
        if len(filter) > 0:
            print(filter)
            url = urlparse(filter)
            if(url.netloc != "rpilocator.com"):
                await ctx.send("The filter is not from rpilocator.com")
                return
            try:
                countries = parse_qs(url.query)['country'][0].split(',')
            except:
                countries = None
            try:
                vendors = parse_qs(url.query)['vendor'][0].split(',')
            except:
                vendors = None
            try:
                devices = parse_qs(url.query)['cat'][0].split(',')
            except:
                devices = None
            if countries != None:
                for country in countries:
                    if not await is_allowed_filter(country):
                        await ctx.send("Invalid country filter")
                        return
            if vendors != None:
                for vendor in vendors:
                    if not await is_allowed_filter(vendor):
                        await ctx.send("Invalid vendor filter")
                        return
            if devices != None:
                for device in devices:
                    if not await is_allowed_filter(device):
                        await ctx.send("Invalid device filter")
                        return

            filerDict = {'countries': countries, 'vendors': vendors, 'devices': devices}
            print(url)
            print(filerDict)

        print(channel)
        print(role)

    def cog_unload(self):
        self.listen.cancel()

    def formatEmbed(self, message, time):
        if(self.updateFailed):
            self.updateFailed = False
            embed = discord.Embed(title="Last update failed", description=f"failed at: {self.lastFail.strftime('%d/%m/%Y %H:%M:%S')}", color=0xff0000)
            return embed
        embed = discord.Embed(title=message.title, description=message.link, color=0xe91e63, timestamp=time)
        #embed.set_footer(text=f'{time.strftime("%d/%m/%Y %H:%M:%S")}')
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
