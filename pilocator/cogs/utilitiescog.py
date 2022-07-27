#  Copyright (c) 2019-2022 ThatRedKite and contributors
#  Copyright (c) 2022 diminDDL
#  License: MIT License

import discord
from discord.ext import commands
import psutil
from datetime import datetime
import si_prefix


class UtilityCommands(commands.Cog, name="utility commands"):
    """
    Utility commands for the bot. These commands are basically informational commands.
    """
    def __init__(self, bot: commands.Bot):
        self.dirname = bot.dirname
        self.redis = bot.redis
        self.bot = bot

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(pass_context=True, aliases=["uptime", "load"])
    async def status(self, ctx):
        """
        Displays the status of the bot.
        """
        process = psutil.Process(self.bot.pid)
        mem = process.memory_info()[0]
        redismem = (await self.redis.info())["used_memory"]

        cpu = psutil.cpu_percent(interval=None)
        ping = round(self.bot.latency * 1000, 1)
        uptime = str(datetime.now() - self.bot.starttime).split(".")[0]
        total_users = sum([users.member_count for users in self.bot.guilds])
        guilds = len(self.bot.guilds)

        embed = discord.Embed()
        embed.add_field(name="System status",
                        value=f"""RAM usage: **{si_prefix.si_format(mem + redismem)}B**
                                CPU usage: **{cpu} %**
                                uptime: **{uptime}**
                                ping: **{ping} ms**""")

        embed.add_field(name="Bot stats",
                        value=f"""guilds: **{guilds}**
                                extensions loaded: **{len(self.bot.extensions)}**
                                total users: **{total_users}**
                                bot version: **{self.bot.version}**
                                """, inline=False)

        embed.set_thumbnail(url=str(self.bot.user.avatar.url))

        if not self.bot.debugmode:
            if cpu >= 90.0:
                embed.color = 0xbb1e10
                embed.set_footer(text="Warning: CPU usage over 90%")
            else:
                embed.color = 0x00b51a
        else:
            embed.color = 0x47243c
        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx):
        """This sends you an invite for the bot if you want to add it to one of your servers."""
        await ctx.author.send(
            f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=412317247552&scope=bot%20applications.commands"
        )


def setup(bot):
    bot.add_cog(UtilityCommands(bot))
