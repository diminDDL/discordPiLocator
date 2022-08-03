#  Copyright (c) 2019-2022 ThatRedKite and contributors
#  Copyright (c) 2022 diminDDL
#  License: MIT License

import discord
import aioredis
from discord.ext import commands, tasks
from discord.ext.commands.errors import CommandInvokeError
from pilocator.backend.util import errormsg


class ListenerCog(commands.Cog):
    """
    The perfect place to put random listeners in.
    """
    def __init__(self, bot):
        self.dirname = bot.dirname
        self.bot: discord.Client = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: CommandInvokeError):
        match type(error):
            case commands.CommandOnCooldown:
                await errormsg(ctx, f"Sorry, but this command is on cooldown! Please wait {int(error.retry_after)} seconds.")
            case commands.CommandInvokeError:
                if self.bot.debugmode:
                    await errormsg(ctx, repr(error))
                raise error
            case commands.CheckFailure:
                await errormsg(ctx, "A check has failed! This command might be disabled on the server or you lack permission")
            case commands.MissingPermissions:
                await errormsg(ctx, "Sorry, but you don't have the permissions to do this")
            case commands.NotOwner:
                await errormsg(ctx, "Only the bot owner can do this! Contact them if needed.")
            case commands.ChannelNotFound:
                await errormsg(ctx, "The channel you specified was not found!")
            case commands.RoleNotFound:
                await errormsg(ctx, "The role you specified was not found!")

    @commands.Cog.listener()
    async def on_ready(self):
        print("\nbot successfully started!")
        await self.bot.change_presence(
            activity=discord.Activity(name="-help", type=1),
            status=discord.Status.online,
        )

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, ex):
        raise ex


def setup(bot):
    bot.add_cog(ListenerCog(bot))
