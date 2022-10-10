#  Copyright (c) 2019-2022 ThatRedKite and contributors

from discord.ext import commands


class SudoCommands(commands.Cog, name="administrative commands"):
    """
    This cog contains commands that are used to manage the bot. These commands are only available to the bot owner.
    """
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.dirname = bot.dirname
        self.redis = self.bot.redis

    @commands.is_owner()
    @commands.command()
    async def kill(self, ctx):
        """Kills the bot :("""

        # close the aiohttp session
        await self.bot.aiohttp_session.close()

        # close the discord session
        await self.bot.close()

    @commands.is_owner()
    @commands.command(aliases=["reload", "reboot", "r"])
    async def restart(self, ctx):
        """Reloads all cogs"""
        # this will currently break all image commands
        extensions = list(self.bot.extensions.keys())
        for extension in extensions:
            try:
                self.bot.reload_extension(extension)
                print(f"Reloaded {extension}")
            except Exception as exc:
                raise exc
        await ctx.send(f"All cogs reloaded.")
        print("\n")

    @commands.is_owner()
    @commands.command()
    async def debug(self, ctx):
        """produces more verbose error messages"""
        self.bot.debugmode = not self.bot.debugmode
        await ctx.message.delete()

    @commands.is_owner()
    @commands.command()
    async def echo(self, ctx, *, message: str):
        """pretend to be the bot"""
        await ctx.message.delete()
        await ctx.send(message)

    @commands.is_owner()
    @commands.command()
    async def broadcast(self, ctx, *, message: str):
        """send a message to all guilds the bot is in"""
        for guild in self.bot.guilds:
            try:
                msg = message
                if "\locatorRole/" in msg:
                    # find the pilocator role for the current guild in the redis database
                    key_list = [key async for key in self.redis.scan_iter(match=f"notification_settings:{guild.id}:*")]
                    roles = ""
                    for key in key_list:
                        data = await self.redis.hgetall(key)
                        role = guild.get_role(int(data['role']))
                        if f"{role.mention}" not in roles:
                            roles += f"{role.mention} "
                    msg = msg.replace("\locatorRole/", roles)
                await guild.system_channel.send(msg)
            except Exception:
                print(f"Could not send message to {guild.name}")

def setup(bot):
    bot.add_cog(SudoCommands(bot))
