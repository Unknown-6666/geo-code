import discord
import logging
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from config import COLORS

logger = logging.getLogger('discord')

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check the bot's latency"""
        latency = round(self.bot.latency * 1000)
        logger.info(f'Ping command used. Latency: {latency}ms')
        embed = create_embed("Pong! 🏓", f"Latency: {latency}ms")
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def custom_help(self, ctx):
        """Display help information about the bot"""
        embed = discord.Embed(
            title="Bot Help",
            description="Here are all available commands:",
            color=COLORS["PRIMARY"]
        )
        
        # Basic Commands
        embed.add_field(
            name="Basic Commands",
            value="""
            `!ping` - Check bot's latency
            `!help` - Show this help message
            `!info` - Get server information
            """,
            inline=False
        )
        
        # Member Commands
        embed.add_field(
            name="Member Commands",
            value="""
            `!userinfo [@user]` - Get information about a user
            """,
            inline=False
        )
        
        embed.set_footer(text="Use ! prefix before each command")
        await ctx.send(embed=embed)

    @commands.command(name="info")
    async def server_info(self, ctx):
        """Display server information"""
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

    @commands.command(name="userinfo")
    async def user_info(self, ctx, member: discord.Member = None):
        """Display information about a user"""
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

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))