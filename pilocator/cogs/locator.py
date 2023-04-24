#  Copyright (c) 2022 diminDDL
#  License: MIT License

from re import T
import discord
import datetime
import requests
import feedparser
import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor
from time import sleep
from io import BytesIO
from urllib.parse import urlparse, parse_qs
from time import mktime
from discord.ext import commands, tasks, bridge
from pilocator.backend.util import pretty_date
from pilocator.backend.util import can_change_settings


allowedRegions = ["AU", "AT", "BE", "CA", "CH", "CN", "DE", "DK", "ES", "FR", "IT", "MX", "JP", "NL", "PL", "PT", "SE", "UK", "US", "ZA"]
allowedVendors = ["adafruit", "berrybase", "botland", "chicagodist", "coolcomp", "digikeyus", "electrokit", "elektor", "elektronica", "farnell", "kubii", "mauserpt", "mchobby", "melopero", "newark", "okdonl", "okdouk", "okdous", "pi3g", "pimoroni", "pishopca", "pishopch", "pishopus", "pishopza", "rapid", "raspberrystore", "rasppishop", "reichelt", "sbcomp", "seeedstudio", "semaf", "sparkfun", "switchjp", "thepihut", "tiendatec", "vilros", "welectron"]
allowedDevices = ["CM3", "CM4", "PI3", "PI4", "PIZERO", "PIZERO2"]


async def is_allowed_filter(filter: str):
    for region in allowedRegions:
        if filter == region:
            return True
    for vendor in allowedVendors:
        if filter == vendor:
            return True
    for device in allowedDevices:
        if filter == device:
            return True
    return False


async def check_permissions(ctx, channel: discord.TextChannel, role: discord.Role):
    if not channel.permissions_for(ctx.me).send_messages:
        await ctx.respond("I don't have permission to send messages in that channel.")
        return False
    elif not channel.permissions_for(ctx.me).embed_links:
        await ctx.respond("I don't have permission to embed links in that channel.")
        return False
    elif not role.mention:
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
        self.pp = ProcessPoolExecutor(max_workers=1)    
        self.sep = asyncio.Semaphore(2)
        self.ll = asyncio.get_event_loop()
        print("initialized bot and redis")
        self.FEED_URL = 'https://rpilocator.com/feed/'
        self.USER_AGENT = 'DiscordBot'
        self.control = []
        print("Getting feed...")
        success = False
        while not success:
            try:
                resp = requests.get(self.FEED_URL, timeout=20.0)
                # convert the above into aiohttp
                success = True
            except requests.ReadTimeout:
                print(f"Timeout when reading RSS {self.FEED_URL} will wait a minute and try again")
                sleep(60)
            
        content = BytesIO(resp.content)
        f = feedparser.parse(content)
        print("Got feed")
        if f.entries:
            for entries in f.entries:
                self.control.append(entries.id)
        print("locator cog loaded")

        # self.control.pop(0)    # remove after testing
        # self.control.pop(1)    # remove after testing

        self.lastUpdate = None
        self.lastFail = None
        self.updateFailed = False
        self.listen.start()
        if self.bot.debugmode:
            print("Cog loaded: Locate loaded")
            print("Control list: " + str(self.control)) 

    async def get_feed(self, FEED_URL):
        async with self.sep:
            try:
                # for some reason it never runs the function if you use an actual executor, so this is a temporary workaround
                resp = await asyncio.wait_for(self.ll.run_in_executor(executor=None, func=functools.partial(requests.get, FEED_URL, timeout=60.0)), timeout=30.0)
            except asyncio.TimeoutError:
                print("Getting feed timed out")
                return None
            content = BytesIO(resp.content)
            f = feedparser.parse(content)
        return f

    @commands.command(aliases=["test"])
    async def sendTest(self, ctx, channel: discord.TextChannel):
        """
        Sends a test message to the specified channel
        """
        for channelInt in await self.getUpdateChannelList(ctx.guild):
            if channelInt == channel.id:
                role = ctx.guild.get_role(int(await self.redis.hget(f"notification_settings:{ctx.guild.id}:{channelInt}", 'role')))
                await channel.send(f"Test message {role.mention}")
                return

    @bridge.bridge_command(aliases=["lastupdate", "lu", "last", "update"])
    async def lastcheck(self, ctx: bridge.BridgeContext):
        """
        This command is used to get the time of the last update from rpilocator.com
        """
        if self.lastUpdate is not None:
            await ctx.respond(f"Last update: <t:{int(datetime.datetime.timestamp(self.lastUpdate))}:T>, {pretty_date(time=self.lastUpdate)}")
        else:
            await ctx.respond("No update yet")

    @commands.check(can_change_settings)
    @bridge.bridge_command()
    async def setup(self, ctx: bridge.BridgeContext, channel: discord.TextChannel, role: discord.Role, filter=''):
        """
        Used to setup the channel to post the updates and the role to ping when there is a new update.
        """
        # Allows a filter to be set while being set up. The format can be obtained at the bottom of this page: https://rpilocator.com/about.cfm
        # Examples: `-setup #channel @role` - sends all updates and pings the role.
        # -setup #channel @role https://rpilocator.com/feed/?country=DE,NL,PL&cat=CM4,PI3,PIZERO` - sends only updates from Germany, Netherlands and Poland for CM4, PI3 and PI ZERO devices, and pings the role.

        # check seeings and permissions
        if not await can_change_settings(ctx):
            return

        if not await check_permissions(ctx, channel, role):
            return
        
        # parse the filter
        if len(filter) > 0:
            url = urlparse(filter)
            if (url.netloc != "rpilocator.com"):
                await ctx.send("The filter is not from rpilocator.com")
                return
            try:
                countries = parse_qs(url.query)['country'][0]
            except:
                countries = 0
            try:
                vendors = parse_qs(url.query)['vendor'][0]
            except:
                vendors = 0
            try:
                devices = parse_qs(url.query)['cat'][0]
            except:
                devices = 0
            if countries != 0:
                for country in countries.split(','):
                    if not await is_allowed_filter(country):
                        await ctx.send("Invalid country filter")
                        return
            if vendors != 0:
                for vendor in vendors.split(','):
                    if not await is_allowed_filter(vendor):
                        await ctx.send("Invalid vendor filter")
                        return
            if devices != 0:
                for device in devices.split(','):
                    if not await is_allowed_filter(device):
                        await ctx.send("Invalid device filter")
                        return
            if countries != 0 and vendors != 0:
                await ctx.send("You can't use both country and vendor filters")
                return
        else:
            countries = 0
            vendors = 0
            devices = 0
        # Write data to DB
        key = f"notification_settings:{ctx.guild.id}:{channel.id}"
        setdict = {
            'role': role.id,
            'countries': countries,
            'vendors': vendors,
            'devices': devices
        }
        await self.redis.hmset(key, setdict)
        await ctx.respond(f"The notification channel {channel.mention} is set up and {role.mention} will be pinged when there is a new update. Use `-unset <channel>` to remove the notification settings.")

    @commands.check(can_change_settings)
    @bridge.bridge_command()
    async def unset(self, ctx: bridge.BridgeContext, channel: discord.TextChannel):
        """
        This command is used to remove the notification settings for a channel.
        """
        # check seeings and permissions
        if not await can_change_settings(ctx):
            return

        # Delete the DB entry
        key = f"notification_settings:{ctx.guild.id}:{channel.id}"
        try:
            await self.redis.delete(key)
            await ctx.respond(f"The notifications for channel {channel.mention} have been disabled.")
        except:
            await ctx.respond(f"The notifications for channel {channel.mention} does not exist.")

    @commands.check(can_change_settings)
    @bridge.bridge_command()
    async def list(self, ctx: bridge.BridgeContext):
        """
        This command is used to list all the notification settings for the server.
        """

        # check seeings and permissions
        if not await can_change_settings(ctx):
            return

        # Get the DB entries
        key_list = [key async for key in self.redis.scan_iter(match=f"notification_settings:{ctx.guild.id}:*")]
        if len(key_list) == 0:
            await ctx.respond("No notification settings found.")
            return
        message = "List of notification settings:\n"
        for key in key_list:
            data = await self.redis.hgetall(key)
            channel = self.bot.get_channel(int(key.split(':')[-1]))
            role = ctx.guild.get_role(int(data['role']))
            countries = data['countries']
            vendors = data['vendors']
            devices = data['devices']
            message = message + f"Channel: {channel.mention}, Role: {role.mention}, Countries: {countries if countries != '0' else 'all'}, Vendors: {vendors if vendors != '0' else 'all'}, Devices: {devices if devices != '0' else 'all'}\n"
        await ctx.respond(message)

    def cog_unload(self):
        self.listen.cancel()

    def formatEmbed(self, message, time):
        if (self.updateFailed):
            self.updateFailed = False
            embed = discord.Embed(title="Last update failed", description=f"failed at: {self.lastFail.strftime('%d/%m/%Y %H:%M:%S')}", color=0xff0000)
            return embed
        embed = discord.Embed(title=message.title, description=message.link, color=0xe91e63, timestamp=time)
        return embed

    async def getUpdateChannelList(self, guild):
        channel_list = []
        key_list = [key async for key in self.redis.scan_iter(match=f"notification_settings:{guild.id}:*")]
        for key in key_list:
            channel = int(key.split(':')[-1])
            if channel not in channel_list:
                channel_list.append(channel)
        return channel_list

    async def getGuildList(self):
        guildList = []
        key_list = [key async for key in self.redis.scan_iter(match=f"notification_settings:*")]
        for n in key_list:
            try:
                guild = await self.bot.fetch_guild(int(n.split(':')[1]))
            except:
                continue
            if guild not in guildList:
                guildList.append(guild)
        return guildList

    async def checkFilter(self, message, guild, channel):
        deviceLookUpTable = {
            allowedDevices[0]: "CM3",       # CM3
            allowedDevices[1]: "CM4",       # CM4
            allowedDevices[2]: "RPi 3",     # PI3
            allowedDevices[3]: "RPi 4",     # PI4
            allowedDevices[4]: "Pi Zero",   # PI ZERO
            allowedDevices[5]: "Pi Zero 2", # PI ZERO 2 W
        }
        key = f"notification_settings:{guild.id}:{channel.id}"
        data = await self.redis.hgetall(key)
        countries = data['countries']
        vendors = data['vendors']
        devices = data['devices']

        if countries == '0' and vendors == '0' and devices == '0':
            return True
        
        countryFlag = False
        vendorFlag = False
        deviceFlag = False

        link = message.link
        title = message.title
        if countries != '0':
            for country in countries.split(','):
                if country in title:
                    countryFlag = True
        elif vendors == '0':
            countryFlag = True
        if vendors != '0':
            for vendor in vendors.split(','):
                if vendor.lower() in link.lower():
                    vendorFlag = True
        elif countries == '0':
            vendorFlag = True
        if devices != '0':
            for device in devices.split(','):
                if deviceLookUpTable[device].lower() in title.lower():
                    deviceFlag = True
        else:
            deviceFlag = True
        
        return (countryFlag or vendorFlag) and deviceFlag

    @tasks.loop(seconds=59.0)
    async def listen(self):
        try:
            f = await self.get_feed(self.FEED_URL)
            if f is None:
                return
            self.lastUpdate = datetime.datetime.now()
            for entries in f.entries:
                if entries.id not in self.control:
                    
                    fail = self.updateFailed
                    embed = self.formatEmbed(entries, datetime.datetime.fromtimestamp(mktime(entries.published_parsed)))

                    for guild in await self.getGuildList():
                        for channelInt in await self.getUpdateChannelList(guild):
                            # if we had a fail, we want to send the message to continue sending to the rest of the channels
                            try:
                                channel = await self.bot.fetch_channel(channelInt)
                                role = guild.get_role(int(await self.redis.hget(f"notification_settings:{guild.id}:{channelInt}", 'role')))
                                if (await self.checkFilter(entries, guild, channel)):
                                    await channel.send(embed=embed)
                                    if not fail:
                                        await channel.send(f"{role.mention}")
                                    if self.bot.debugmode:
                                        print(f"Sent notification to {channel.name}-({channel.id}) in {guild.name}-({guild.id}) for {entries.title}")
                            except:
                                continue

                    self.control.append(entries.id)
        except Exception as e:
            self.updateFailed = True
            self.lastFail = datetime.datetime.now()
            print("failed: " + str(e))
            return


def setup(bot):
    bot.add_cog(Locate(bot))
