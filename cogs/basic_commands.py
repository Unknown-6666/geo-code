import discord
import logging
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from config import COLORS
from utils.permissions import PermissionChecks

logger = logging.getLogger('discord')

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Legacy ping command"""
        await self._show_ping(ctx)

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping_slash(self, interaction: discord.Interaction):
        """Slash command version of ping"""
        latency = round(self.bot.latency * 1000)
        logger.info(f'Ping command used. Latency: {latency}ms')
        embed = create_embed("Pong! 🏓", f"Latency: {latency}ms")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="help")
    async def help(self, ctx):
        """Legacy help command"""
        await self._show_help(ctx)

    @app_commands.command(name="help", description="Display help information about the bot")
    async def help_slash(self, interaction: discord.Interaction):
        """Slash command version of help"""
        embed = discord.Embed(
            title="Bot Help",
            description="Here are all available commands:",
            color=COLORS["PRIMARY"]
        )

        embed.add_field(
            name="Basic Commands",
            value="""
            `/ping` - Check bot's latency
            `/help` - Show this help message
            `/info` - Get server information
            """,
            inline=False
        )

        embed.add_field(
            name="Member Commands",
            value="""
            `/userinfo [user]` - Get information about a user
            """,
            inline=False
        )

        embed.add_field(
            name="YouTube Commands",
            value="""
            `/setyoutube <channel_id> [#announcement-channel]` - Set up YouTube video tracking
            """,
            inline=False
        )

        embed.set_footer(text="Use / to access slash commands")
        await interaction.response.send_message(embed=embed)

    @commands.command(name="info")
    async def info(self, ctx):
        """Legacy server info command"""
        await self._show_server_info(ctx)

    @app_commands.command(name="info", description="Display server information")
    async def info_slash(self, interaction: discord.Interaction):
        """Slash command version of server info"""
        guild = interaction.guild
        embed = create_embed(
            f"{guild.name} Server Information",
            f"Created on {guild.created_at.strftime('%B %d, %Y')}"
        )
        embed.add_field(name="Server Owner", value=guild.owner, inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Channel Count", value=len(guild.channels), inline=True)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed)

    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        """Legacy user info command"""
        await self._show_user_info(ctx, member)

    @app_commands.command(name="userinfo", description="Display information about a user")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        """Slash command version of user info"""
        member = member or interaction.user
        embed = create_embed(
            f"User Information - {member.name}",
            f"Account created on {member.created_at.strftime('%B %d, %Y')}"
        )
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Roles", value=len(member.roles), inline=True)

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        await interaction.response.send_message(embed=embed)

    async def _show_ping(self, ctx):
        """Helper method for ping command"""
        latency = round(self.bot.latency * 1000)
        logger.info(f'Ping command used. Latency: {latency}ms')
        embed = create_embed("Pong! 🏓", f"Latency: {latency}ms")
        await ctx.send(embed=embed)

    async def _show_help(self, ctx):
        """Helper method for help command"""
        embed = discord.Embed(
            title="Bot Help",
            description="Here are all available commands:",
            color=COLORS["PRIMARY"]
        )

        embed.add_field(
            name="Basic Commands",
            value="""
            `!ping` - Check bot's latency
            `!help` - Show this help message
            `!info` - Get server information
            `/ping` - Check bot's latency
            `/help` - Show this help message
            `/info` - Get server information
            """,
            inline=False
        )

        embed.add_field(
            name="Member Commands",
            value="""
            `!userinfo [@user]` - Get information about a user
            `/userinfo [user]` - Get information about a user
            """,
            inline=False
        )

        embed.add_field(
            name="YouTube Commands",
            value="""
            `!setyoutube <channel_id> [#announcement-channel]` - Set up YouTube video tracking
            `/setyoutube <channel_id> [#announcement-channel]` - Set up YouTube video tracking
            """,
            inline=False
        )

        embed.set_footer(text="Use ! prefix or / for commands")
        await ctx.send(embed=embed)

    async def _show_server_info(self, ctx):
        """Helper method for server info command"""
        guild = ctx.guild
        embed = create_embed(
            f"{guild.name} Server Information",
            f"Created on {guild.created_at.strftime('%B %d, %Y')}"
        )
        embed.add_field(name="Server Owner", value=guild.owner, inline=True)
        embed.add_field(name="Member Count", value=guild.member_count, inline=True)
        embed.add_field(name="Channel Count", value=len(guild.channels), inline=True)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await ctx.send(embed=embed)

    async def _show_user_info(self, ctx, member):
        """Helper method for user info command"""
        member = member or ctx.author
        embed = create_embed(
            f"User Information - {member.name}",
            f"Account created on {member.created_at.strftime('%B %d, %Y')}"
        )
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Roles", value=len(member.roles), inline=True)

        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        logger.error(f'Command error in {ctx.guild}: {str(error)}')

        if isinstance(error, commands.MissingPermissions):
            embed = create_error_embed("Error", "You don't have permission to use this command.")
            logger.warning(f'User {ctx.author} attempted to use command without permission')
        elif isinstance(error, commands.MemberNotFound):
            embed = create_error_embed("Error", "Member not found.")
            logger.warning(f'Member not found error for command {ctx.command}')
        else:
            embed = create_error_embed("Error", str(error))
            logger.error(f'Unexpected error in command {ctx.command}: {str(error)}')

        await ctx.send(embed=embed)

    @commands.command(name="sync")
    @PermissionChecks.is_owner()
    async def sync_commands(self, ctx):
        """Sync slash commands across all servers (Bot Owner Only)"""
        try:
            logger.info("Starting global slash command sync")
            synced = await self.bot.tree.sync()
            embed = create_embed(
                "🔄 Commands Synced",
                f"Successfully synced {len(synced)} commands globally!",
                color=COLORS["PRIMARY"]
            )
            await ctx.send(embed=embed)
            logger.info(f"Successfully synced {len(synced)} commands globally")
        except Exception as e:
            logger.error(f"Error syncing commands: {str(e)}")
            embed = create_error_embed("Error", "Failed to sync commands. Check logs for details.")
            await ctx.send(embed=embed)

    @commands.command(name="sync_guild")
    @PermissionChecks.is_owner()
    async def sync_guild_commands(self, ctx):
        """Sync slash commands for the current server only (Bot Owner Only)"""
        try:
            logger.info(f"Starting slash command sync for guild {ctx.guild.id}")
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            embed = create_embed(
                "🔄 Commands Synced",
                f"Successfully synced {len(synced)} commands in this server!",
                color=COLORS["PRIMARY"]
            )
            await ctx.send(embed=embed)
            logger.info(f"Successfully synced {len(synced)} commands in guild {ctx.guild.id}")
        except Exception as e:
            logger.error(f"Error syncing guild commands: {str(e)}")
            embed = create_error_embed("Error", "Failed to sync commands. Check logs for details.")
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(BasicCommands(bot))