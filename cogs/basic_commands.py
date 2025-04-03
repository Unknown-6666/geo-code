import discord
import logging
import asyncio
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from config import COLORS
from utils.permissions import PermissionChecks, is_bot_owner

logger = logging.getLogger('discord')

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("Basic commands cog initialized")

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
            description="Here are all available slash commands:",
            color=COLORS["PRIMARY"]
        )

        # Basic Commands
        embed.add_field(
            name="Basic Commands",
            value="""
            `/ping` - Check bot's latency
            `/help` - Show this help message
            `/info` - Get server information
            `/userinfo [user]` - Get information about a user
            """,
            inline=False
        )

        # Admin Commands
        if is_bot_owner(interaction.user.id):
            embed.add_field(
                name="Admin Commands",
                value="""
                `/clear_commands` - Clear all slash commands (Bot Owner Only)
                """,
                inline=False
            )
        
        # AI Chat Commands
        embed.add_field(
            name="AI Chat Commands",
            value="""
            `/ask [question]` - Ask the AI a one-time question
            `/chat [message]` - Have a casual conversation with the AI (with memory)
            `/clear_chat_history` - Clear your conversation history with the AI
            `/show_chat_history` - Show your recent conversation history with the AI
            """,
            inline=False
        )

        # Economy Commands
        embed.add_field(
            name="Economy Commands",
            value="""
            `/balance` - Check your wallet and bank balance
            `/daily` - Collect daily rewards
            `/work` - Work to earn coins
            `/deposit [amount]` - Deposit money into your bank
            `/withdraw [amount]` - Withdraw money from your bank
            `/coinflip [amount] [choice]` - Gamble coins on a coin flip
            `/slots [amount]` - Play the slot machine
            `/shop` - View available items in the shop
            `/buy [item_name]` - Buy an item from the shop
            `/inventory` - View your inventory
            """,
            inline=False
        )

        # YouTube Commands
        embed.add_field(
            name="YouTube Commands",
            value="""
            `/setannouncement` - Set up YouTube video tracking channel
            """,
            inline=False
        )

        # Music Commands
        embed.add_field(
            name="Music Commands",
            value="""
            `/play [query]` - Play a song from YouTube
            `/pause` - Pause the current song
            `/resume` - Resume the paused song
            `/skip` - Skip to the next song
            `/queue` - Show the current music queue
            `/stop` - Stop playing and clear queue
            `/now_playing` - Show the current song
            `/volume [0-100]` - Set volume
            `/join` - Join voice channel
            `/leave` - Leave voice channel
            """,
            inline=False
        )
        
        # Moderation Commands
        embed.add_field(
            name="Moderation Commands",
            value="""
            `/kick [user] [reason]` - Kick a member from the server
            `/ban [user] [reason]` - Ban a member from the server
            `/unban [username#tag]` - Unban a member from the server
            `/mute [user] [duration] [reason]` - Mute a member
            `/unmute [user]` - Unmute a member
            `/clear [amount]` - Clear messages from a channel
            `/slowmode [seconds]` - Set slowmode in a channel
            """,
            inline=False
        )
        
        # Meme Commands
        embed.add_field(
            name="Meme Commands",
            value="""
            `/meme` - Get a random meme
            `/memedump [count]` - Get multiple random memes at once
            """,
            inline=False
        )

        embed.set_footer(text="Use / for slash commands or !help to see prefix commands")
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
        embed.add_field(name="Role Count", value=len(guild.roles), inline=True)
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Verification Level", value=guild.verification_level, inline=True)

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
        roles = [role.mention for role in member.roles[1:]]  # Exclude @everyone

        embed = create_embed(
            f"User Information - {member.name}",
            f"Account created on {member.created_at.strftime('%B %d, %Y')}"
        )
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%B %d, %Y"), inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="User ID", value=member.id, inline=True)
        embed.add_field(name="Roles", value=" ".join(roles) if roles else "No roles", inline=False)

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
            description="Here are all available commands (prefix version):",
            color=COLORS["PRIMARY"]
        )

        # Basic Commands
        embed.add_field(
            name="Basic Commands",
            value="""
            `!ping` - Check bot's latency
            `!help` - Show this help message
            `!info` - Get server information
            `!userinfo [@user]` - Get information about a user
            """,
            inline=False
        )
        
        # Admin Commands (for bot owners)
        embed.add_field(
            name="Admin Commands",
            value="""
            `!sync` - Sync slash commands across all servers (Bot Owner Only)
            `!sync_guild` - Sync slash commands for the current server only (Bot Owner Only)
            `!clear_commands` - Clear all slash commands from all servers (Bot Owner Only)
            """,
            inline=False
        )
        
        # AI Chat Commands
        embed.add_field(
            name="AI Chat Commands",
            value="""
            `!ask [question]` - Ask the AI a one-time question
            `!chat [message]` - Have a casual conversation with the AI (with memory)
            `!clear_history` - Clear your conversation history with the AI
            `!history` - Show your recent conversation history with the AI
            """,
            inline=False
        )
        
        # Economy Commands
        embed.add_field(
            name="Economy Commands",
            value="""
            `!balance` - Check your wallet and bank balance
            `!daily` - Collect daily rewards
            `!work` - Work to earn coins
            `!deposit [amount]` - Deposit money into your bank
            `!withdraw [amount]` - Withdraw money from your bank
            `!shop` - View available items in the shop
            `!buy [item_name]` - Buy an item from the shop
            `!inventory` - View your inventory
            """,
            inline=False
        )
        
        # Music Commands
        embed.add_field(
            name="Music Commands",
            value="""
            `!play [query]` - Play a song from YouTube
            `!pause` - Pause the current song
            `!resume` - Resume the paused song
            `!skip` - Skip to the next song
            `!queue` - Show the current music queue
            `!stop` - Stop playing and clear the queue
            `!leave` - Disconnect the bot from voice channel
            `!volume [1-100]` - Adjust the volume
            `!now` - Show the currently playing song
            """,
            inline=False
        )
        
        # Moderation Commands
        embed.add_field(
            name="Moderation Commands",
            value="""
            `!kick [@user] [reason]` - Kick a member from the server
            `!ban [@user] [reason]` - Ban a member from the server
            `!unban [user#1234]` - Unban a member from the server
            `!mute [@user] [duration] [reason]` - Mute a member
            `!unmute [@user]` - Unmute a member
            `!clear [amount]` - Clear a number of messages from a channel
            `!slowmode [seconds]` - Set slowmode in a channel
            """,
            inline=False
        )
        
        # Meme Commands
        embed.add_field(
            name="Meme Commands",
            value="""
            `!meme` - Get a random meme
            `!memedump [count]` - Get multiple random memes at once
            """,
            inline=False
        )

        embed.set_footer(text="Type '!help' to see this message again or use / for slash commands")
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
        # Just log errors - let the individual commands handle their own error responses
        logger.error(f'Command error in {ctx.guild}: {str(error)}')

        # Log specific common errors with appropriate level
        if isinstance(error, commands.MissingPermissions):
            logger.warning(f'User {ctx.author} attempted to use command without permission')
        elif isinstance(error, commands.MemberNotFound):
            logger.warning(f'Member not found error for command {ctx.command}')
        else:
            logger.error(f'Unexpected error in command {ctx.command}: {str(error)}')

    @commands.command(name="sync")
    @PermissionChecks.is_owner()
    async def sync_commands(self, ctx):
        """Sync slash commands across all servers (Bot Owner Only)"""
        # Create a message ID to track this specific command execution
        command_id = f"{ctx.message.id}-{ctx.author.id}"
        
        try:
            # Store message reference to avoid duplicate messages
            message = await ctx.send("Starting global slash command sync... Please wait.")
            logger.info(f"Starting global slash command sync (ID: {command_id})")
            
            # First clear existing commands
            logger.info(f"Clearing existing commands (ID: {command_id})")
            try:
                await self.bot.http.request(
                    discord.http.Route("PUT", "/applications/{application_id}/commands", 
                                    application_id=self.bot.application_id), 
                    json=[]
                )
                logger.info(f"Commands cleared successfully (ID: {command_id})")
            except Exception as e:
                logger.error(f"Error clearing commands: {str(e)} (ID: {command_id})")
                # Continue to sync even if clear fails
            
            # Now sync the command tree
            synced = await self.bot.tree.sync()
            
            if len(synced) > 0:
                embed = create_embed(
                    "🔄 Commands Synced",
                    f"Successfully synced {len(synced)} commands globally!\nYou can now use the updated slash commands in all servers.",
                    color=COLORS["PRIMARY"]
                )
                logger.info(f"Successfully synced {len(synced)} commands globally (ID: {command_id})")
            else:
                embed = create_embed(
                    "⚠️ Command Sync Issue",
                    "No commands were registered. This might indicate a problem with command registration in the cogs.",
                    color=COLORS["WARNING"]
                )
                logger.warning(f"Command sync returned 0 commands - possible issue with command registration (ID: {command_id})")
            
            # Edit the original message instead of sending a new one
            await message.edit(content=None, embed=embed)
            
        except Exception as e:
            logger.error(f"Error syncing commands: {str(e)} (ID: {command_id})")
            embed = create_error_embed("Error", f"Failed to sync commands: {str(e)}")
            try:
                # Try to respond in the original channel
                await ctx.send(embed=embed)
            except:
                # If that fails, try to DM the owner
                try:
                    await ctx.author.send(embed=embed)
                except:
                    # If everything fails, just log the error
                    logger.error(f"Couldn't send error message to {ctx.author} (ID: {command_id})")

    @commands.command(name="sync_guild")
    @PermissionChecks.is_owner()
    async def sync_guild_commands(self, ctx):
        """Sync slash commands for the current server only (Bot Owner Only)"""
        # Create a message ID to track this specific command execution
        command_id = f"{ctx.message.id}-{ctx.author.id}"
        
        try:
            # Store message reference to avoid duplicate messages
            message = await ctx.send("Starting server slash command sync... Please wait.")
            logger.info(f"Starting slash command sync for guild {ctx.guild.id} (ID: {command_id})")
            
            # Copy global commands to this guild and sync
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            
            if len(synced) > 0:
                embed = create_embed(
                    "🔄 Commands Synced",
                    f"Successfully synced {len(synced)} commands in this server!\nYou can now use the updated slash commands here.",
                    color=COLORS["PRIMARY"]
                )
                logger.info(f"Successfully synced {len(synced)} commands in guild {ctx.guild.id} (ID: {command_id})")
            else:
                embed = create_embed(
                    "⚠️ Command Sync Issue",
                    "No commands were registered in this server. This might indicate a problem with command registration.",
                    color=COLORS["WARNING"]
                )
                logger.warning(f"Guild command sync returned 0 commands for guild {ctx.guild.id} (ID: {command_id})")
            
            # Edit the original message instead of sending a new one
            await message.edit(content=None, embed=embed)
            
        except Exception as e:
            logger.error(f"Error syncing guild commands: {str(e)} (ID: {command_id})")
            embed = create_error_embed("Error", f"Failed to sync commands: {str(e)}")
            try:
                # Try to respond in the original channel
                await ctx.send(embed=embed)
            except:
                # If that fails, try to DM the owner
                try:
                    await ctx.author.send(embed=embed)
                except:
                    # If everything fails, just log the error
                    logger.error(f"Couldn't send error message to {ctx.author} (ID: {command_id})")

    @commands.command(name="clear_commands")
    @PermissionChecks.is_owner()
    async def clear_commands_prefix(self, ctx):
        """Clear all slash commands from all servers (Bot Owner Only)"""
        try:
            confirmation_embed = create_embed(
                "⚠️ Confirmation Required", 
                "Are you sure you want to clear all slash commands from all servers? This will remove all slash commands until a new sync is performed. Reply with `yes` to confirm or `no` to cancel.",
                color=COLORS["WARNING"]
            )
            await ctx.send(embed=confirmation_embed)
            
            # Wait for user confirmation
            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.lower() in ['yes', 'no']
                
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                if msg.content.lower() == 'no':
                    await ctx.send(embed=create_embed("Cancelled", "Command clearing has been cancelled.", color=COLORS["PRIMARY"]))
                    return
                    
            except asyncio.TimeoutError:
                await ctx.send(embed=create_embed("Timed Out", "You didn't respond in time. Command clearing has been cancelled.", color=COLORS["WARNING"]))
                return
            
            # User confirmed, proceed with clearing commands
            logger.warning(f"Command clearing initiated by {ctx.author} (ID: {ctx.author.id})")
            await ctx.send("Clearing all commands... Please wait.")
            
            # Clear all application commands globally
            await self.bot.tree.sync()
            self.bot.tree.clear_commands(guild=None)
            await self.bot.tree.sync()
            
            # Log success
            logger.warning(f"All global commands cleared by {ctx.author} (ID: {ctx.author.id})")
            
            # Create success embed
            embed = create_embed(
                "🧹 Commands Cleared",
                "Successfully cleared all slash commands from all servers. Use `!sync_commands` to restore them when needed.",
                color=COLORS["PRIMARY"]
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error clearing commands: {str(e)}")
            embed = create_error_embed("Error", f"Failed to clear commands: {str(e)}")
            await ctx.send(embed=embed)

    @app_commands.command(name="clear_commands", description="Clear all slash commands from all servers (Bot Owner Only)")
    async def clear_commands_slash(self, interaction: discord.Interaction):
        """Clear all slash commands from all servers (Bot Owner Only)"""
        # Check if user is the bot owner
        if not is_bot_owner(interaction.user.id):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
            
        try:
            # Send confirmation
            confirmation_embed = create_embed(
                "⚠️ Confirmation Required", 
                "Are you sure you want to clear all slash commands from all servers? This will remove all slash commands until a new sync is performed.",
                color=COLORS["WARNING"]
            )
            
            # Create confirm and cancel buttons
            confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger)
            cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
            
            view = discord.ui.View()
            view.add_item(confirm_button)
            view.add_item(cancel_button)
            
            # Define callbacks for buttons
            async def confirm_callback(btn_interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
                    return
                
                # Disable buttons to prevent further interaction
                confirm_button.disabled = True
                cancel_button.disabled = True
                await btn_interaction.response.edit_message(view=view)
                
                # Clear all application commands globally
                logger.warning(f"Command clearing initiated by {interaction.user} (ID: {interaction.user.id})")
                
                # Clear all application commands globally
                await self.bot.tree.sync()
                self.bot.tree.clear_commands(guild=None)
                await self.bot.tree.sync()
                
                # Log success
                logger.warning(f"All global commands cleared by {interaction.user} (ID: {interaction.user.id})")
                
                # Create success embed
                success_embed = create_embed(
                    "🧹 Commands Cleared",
                    "Successfully cleared all slash commands from all servers. Use `/sync_commands` to restore them when needed.",
                    color=COLORS["PRIMARY"]
                )
                
                await btn_interaction.followup.send(embed=success_embed)
                
            async def cancel_callback(btn_interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("You cannot interact with this confirmation.", ephemeral=True)
                    return
                    
                # Disable buttons to prevent further interaction
                confirm_button.disabled = True
                cancel_button.disabled = True
                await btn_interaction.response.edit_message(view=view)
                
                cancel_embed = create_embed("Cancelled", "Command clearing has been cancelled.", color=COLORS["PRIMARY"])
                await btn_interaction.followup.send(embed=cancel_embed)
            
            # Assign callbacks to buttons
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            
            # Send the message with buttons
            await interaction.response.send_message(embed=confirmation_embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error clearing commands: {str(e)}")
            embed = create_error_embed("Error", f"Failed to clear commands: {str(e)}")
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(BasicCommands(bot))