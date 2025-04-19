import discord
import logging
import re
import json
import os
import datetime
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger('discord')

class ProfanityFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blocked_words = []
        self.filter_enabled = {}  # Per guild setting
        self.warning_count = {}  # Track warnings per user
        self.config_file = "data/profanity_config.json"
        self.load_config()

    def load_config(self):
        """Load blocked words and settings from config file"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.blocked_words = config.get('blocked_words', [])
                    self.filter_enabled = config.get('filter_enabled', {})
                    self.warning_count = config.get('warning_count', {})
                    logger.info(f"Loaded profanity filter config with {len(self.blocked_words)} blocked words")
                    
                    # Add logging for current filter settings
                    enabled_count = sum(1 for val in self.filter_enabled.values() if val == True)
                    disabled_count = sum(1 for val in self.filter_enabled.values() if val == False)
                    logger.info(f"Filter status: {enabled_count} servers explicitly enabled, {disabled_count} servers explicitly disabled")
            except Exception as e:
                logger.error(f"Error loading profanity filter config: {str(e)}")
                # Initialize with empty defaults
                self.blocked_words = []
                self.filter_enabled = {}
                self.warning_count = {}
        else:
            logger.info("No profanity filter config found, creating new one")
            self.save_config()  # Create initial empty config
            
        # Pre-initialize filter enabled status for all current servers if not set
        if self.bot.is_ready():
            for guild in self.bot.guilds:
                guild_id = str(guild.id)
                if guild_id not in self.filter_enabled:
                    # Default to True (enabled) for all servers that don't have a setting
                    logger.info(f"Setting default filter status (enabled) for guild: {guild.name} ({guild_id})")
                    self.filter_enabled[guild_id] = True
            
            # Save any changes we made
            self.save_config()

    def save_config(self):
        """Save current configuration to file"""
        try:
            config = {
                'blocked_words': self.blocked_words,
                'filter_enabled': self.filter_enabled,
                'warning_count': self.warning_count
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Saved profanity filter configuration")
        except Exception as e:
            logger.error(f"Error saving profanity filter config: {str(e)}")

    def is_filtered_word(self, content, guild_id):
        """Check if message contains filtered words"""
        # Convert guild_id to string for JSON compatibility
        guild_id = str(guild_id)
        
        # Skip check if filter is explicitly disabled for this guild (default to enabled)
        # The filter is enabled by default for all servers unless explicitly disabled
        if guild_id in self.filter_enabled and self.filter_enabled[guild_id] == False:
            logger.info(f"Filter explicitly disabled for guild {guild_id}")
            return False

        # No words to filter
        if not self.blocked_words:
            return False

        # Create regex pattern for whole word matching with word boundaries
        content = content.lower()
        for word in self.blocked_words:
            # Use word boundaries to match whole words only
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            if re.search(pattern, content):
                return True
        return False

    def get_warning_count(self, user_id, guild_id):
        """Get warning count for a user in a guild"""
        # Convert IDs to strings for JSON compatibility
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Initialize the guild dict if it doesn't exist
        if guild_id not in self.warning_count:
            self.warning_count[guild_id] = {}
            
        # Return the warning count or 0 if not found
        return self.warning_count[guild_id].get(user_id, 0)

    def add_warning(self, user_id, guild_id):
        """Add a warning to a user's count"""
        # Convert IDs to strings for JSON compatibility
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Initialize the guild dict if it doesn't exist
        if guild_id not in self.warning_count:
            self.warning_count[guild_id] = {}
            
        # Get current count and increment
        current = self.warning_count[guild_id].get(user_id, 0)
        self.warning_count[guild_id][user_id] = current + 1
        self.save_config()
        
        return self.warning_count[guild_id][user_id]

    def reset_warnings(self, user_id, guild_id):
        """Reset warnings for a user"""
        # Convert IDs to strings for JSON compatibility
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Initialize the guild dict if it doesn't exist
        if guild_id not in self.warning_count:
            self.warning_count[guild_id] = {}
            logger.info(f"No warnings to reset for guild ID {guild_id} - guild not in warning registry")
            return
            
        # Reset the warning count
        previous_warnings = self.warning_count[guild_id].get(user_id, 0)
        if user_id in self.warning_count[guild_id]:
            self.warning_count[guild_id][user_id] = 0
            self.save_config()
            logger.info(f"Reset warnings for user ID {user_id} in guild ID {guild_id} from {previous_warnings} to 0")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages for profanity"""
        # Always log incoming messages for debugging
        logger.info(f"Message received from {message.author.name}: {message.content}")
        
        # Ignore messages from bots, including our own
        if message.author.bot:
            logger.info("Message ignored - from bot")
            return
            
        # Ignore DMs
        if not message.guild:
            logger.info("Message ignored - from DM")
            return
        
        # Debug log - before filter check
        guild_id = str(message.guild.id)
        filter_status = "disabled" if guild_id in self.filter_enabled and self.filter_enabled[guild_id] == False else "enabled"
        logger.info(f"Filter status for guild {message.guild.name} ({guild_id}): {filter_status}")
        logger.info(f"Number of blocked words: {len(self.blocked_words)}")
            
        # Check if message contains filtered words
        if self.is_filtered_word(message.content, message.guild.id):
            logger.info(f"MATCH FOUND - Filtered message from {message.author.name} in {message.guild.name}: {message.content}")
            
            try:
                # Delete the message
                await message.delete()
                logger.info(f"Message deleted successfully")
                
                # Add warning and get count
                warning_count = self.add_warning(message.author.id, message.guild.id)
                logger.info(f"Warning added: user {message.author.name} ({message.author.id}) now has {warning_count} warnings in server '{message.guild.name}'")
                
                # Send warning DM to user
                try:
                    await message.author.send(
                        f"⚠️ Your message in **{message.guild.name}** was removed for containing inappropriate language. "
                        f"This is warning #{warning_count}."
                    )
                    logger.info(f"Warning DM sent to {message.author.name}")
                except discord.Forbidden:
                    # Can't send DMs to this user
                    logger.info(f"Could not send DM to {message.author.name} - forbidden")
                except Exception as e:
                    logger.error(f"Error sending DM: {str(e)}")
                    
                # If warning count exceeds threshold, take action
                if warning_count >= 3:
                    # Use the !prisoner command instead of timeout
                    try:
                        # The warning threshold is 3 warnings, but we'll continue trying if we get more
                        logger.info(f"Trying to jail user with {warning_count} warnings for mentioning Kendrick Lamar")
                        
                        # Get the proper member object
                        member = message.author
                        
                        # Execute the !prisoner command to jail the user
                        reason = "Automatic jail for mentioning Kendrick Lamar"
                        
                        # Create a context that simulates a moderator using the command
                        # We'll use the bot itself as the command invoker
                        ctx = await self.bot.get_context(message)
                        ctx.author = message.guild.me
                        
                        # Get the prisoner command from moderation cog
                        prisoner_cmd = self.bot.get_command("prisoner")
                        if prisoner_cmd:
                            await prisoner_cmd(ctx, member, reason=reason)
                            logger.info(f"User {message.author.name} ({message.author.id}) jailed for mentioning Kendrick Lamar in server '{message.guild.name}'")
                        else:
                            logger.error("Could not find 'prisoner' command. Make sure the moderation cog is loaded.")
                            # Try to find a log channel and send a message
                            try:
                                log_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                                if not log_channel:
                                    log_channel = discord.utils.get(message.guild.text_channels, name="logs")
                                    
                                if log_channel:
                                    await log_channel.send(f"⚠️ Could not jail {message.author.mention} because the prisoner command is not available.")
                            except:
                                pass
                            return
                        
                        # Initialize variables for notification
                        dm_sent = False
                        embed = discord.Embed(
                            title="User Jailed",
                            description=f"User {message.author.mention} has been jailed for mentioning Kendrick Lamar.",
                            color=discord.Color.dark_red()
                        )
                        embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                        embed.add_field(name="Server", value=message.guild.name, inline=True)
                        embed.add_field(name="Reason", value="Mentioning Kendrick Lamar", inline=False)
                        embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
                        embed.set_footer(text=f"Triggered: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                        
                        # Notify the user via DM that they've been jailed
                        try:
                            await message.author.send(
                                f"🛑 You have been jailed in **{message.guild.name}** for mentioning Kendrick Lamar. All your server roles have been removed."
                            )
                            dm_sent = True
                            logger.info(f"Jail notification DM sent to {message.author.name}")
                        except Exception as e:
                            logger.warning(f"Could not send jail DM to {message.author.name}: {str(e)}")
                            # We'll still log to the channel, so not a critical error
                            
                    except discord.Forbidden as e:
                        logger.warning(f"FORBIDDEN: No permission to jail {message.author.name} ({message.author.id}) in server '{message.guild.name}': {str(e)}")
                    except AttributeError as e:
                        logger.error(f"Attribute error when jailing user: {str(e)}")
                        # For older discord.py versions or other issues, we'll skip this
                        logger.warning(f"Server '{message.guild.name}' might have issues with the prisoner command")
                    except Exception as e:
                        logger.error(f"Error jailing user: {str(e)}")
                        
                    # Notify a log channel if available
                    try:
                        # Look for a channel named "mod-logs" or "logs"
                        log_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                        if not log_channel:
                            log_channel = discord.utils.get(message.guild.text_channels, name="logs")
                            
                        if log_channel:
                            # Create a new embed for the log in case the previous one wasn't defined
                            log_embed = discord.Embed(
                                title="User Jailed",
                                description=f"User {message.author.mention} has been jailed for mentioning Kendrick Lamar.",
                                color=discord.Color.dark_red()
                            )
                            log_embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                            log_embed.add_field(name="Server", value=message.guild.name, inline=True)
                            log_embed.add_field(name="Reason", value="Mentioning Kendrick Lamar", inline=False)
                            log_embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
                            log_embed.set_footer(text=f"Triggered: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                            
                            # Add note about DM status to the log
                            # dm_sent might not be defined if there was an early error
                            dm_status = "User was notified via DM" if locals().get('dm_sent', False) else "Could not send DM to user"
                            log_embed.add_field(name="DM Status", value=dm_status, inline=False)
                                
                            await log_channel.send(embed=log_embed)
                            logger.info(f"Notification sent to log channel in server '{message.guild.name}'")
                        else:
                            logger.info(f"No log channel found in server")
                    except Exception as e:
                        logger.error(f"Error sending to log channel: {str(e)}")
                        
            except discord.Forbidden:
                logger.warning(f"PERMISSION ERROR - No permission to delete message from {message.author.name}")
            except Exception as e:
                logger.error(f"GENERAL ERROR - Error processing filtered message: {str(e)}")
        else:
            # Debug - why didn't we match?
            logger.info(f"No filtered words found in message")

    @commands.command(name="addfilter")
    @commands.has_permissions(manage_messages=True)
    async def add_filtered_word_prefix(self, ctx, word: str):
        """Add a word to the profanity filter (prefix command)"""
        # Convert to lowercase for case-insensitive filtering
        word = word.lower()
        
        # Check if word already exists
        if word in self.blocked_words:
            await ctx.send(f"The word '{word}' is already in the filter.")
            return
            
        # Add word to filter
        self.blocked_words.append(word)
        self.save_config()
        
        await ctx.send(f"Added '{word}' to the profanity filter.")
        logger.info(f"User {ctx.author.name} added '{word}' to profanity filter")
            
    @app_commands.command(name="addfilter", description="Add a word to the profanity filter")
    @app_commands.default_permissions(manage_messages=True)
    async def add_filtered_word(self, interaction: discord.Interaction, word: str):
        """Add a word to the profanity filter"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Convert to lowercase for case-insensitive filtering
        word = word.lower()
        
        # Check if word already exists
        if word in self.blocked_words:
            await interaction.response.send_message(f"The word '{word}' is already in the filter.", ephemeral=True)
            return
            
        # Add word to filter
        self.blocked_words.append(word)
        self.save_config()
        
        await interaction.response.send_message(f"Added '{word}' to the profanity filter.", ephemeral=True)
        logger.info(f"User {interaction.user.name} added '{word}' to profanity filter")

    @commands.command(name="removefilter")
    @commands.has_permissions(manage_messages=True)
    async def remove_filtered_word_prefix(self, ctx, word: str):
        """Remove a word from the profanity filter (prefix command)"""
        # Convert to lowercase for case-insensitive matching
        word = word.lower()
        
        # Check if word exists
        if word not in self.blocked_words:
            await ctx.send(f"The word '{word}' is not in the filter.")
            return
            
        # Remove word from filter
        self.blocked_words.remove(word)
        self.save_config()
        
        await ctx.send(f"Removed '{word}' from the profanity filter.")
        logger.info(f"User {ctx.author.name} removed '{word}' from profanity filter")
    
    @app_commands.command(name="removefilter", description="Remove a word from the profanity filter")
    @app_commands.default_permissions(manage_messages=True)
    async def remove_filtered_word(self, interaction: discord.Interaction, word: str):
        """Remove a word from the profanity filter"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Convert to lowercase for case-insensitive matching
        word = word.lower()
        
        # Check if word exists
        if word not in self.blocked_words:
            await interaction.response.send_message(f"The word '{word}' is not in the filter.", ephemeral=True)
            return
            
        # Remove word from filter
        self.blocked_words.remove(word)
        self.save_config()
        
        await interaction.response.send_message(f"Removed '{word}' from the profanity filter.", ephemeral=True)
        logger.info(f"User {interaction.user.name} removed '{word}' from profanity filter")

    @commands.command(name="listfilters")
    @commands.has_permissions(manage_messages=True)
    async def list_filtered_words_prefix(self, ctx):
        """List all words in the profanity filter (prefix command)"""
        # No words in filter
        if not self.blocked_words:
            await ctx.send("There are no words in the profanity filter.")
            return
            
        # Format the list of words
        word_list = ", ".join([f"`{word}`" for word in sorted(self.blocked_words)])
        
        # Send list privately
        await ctx.send(f"**Filtered Words:**\n{word_list}")
        
    @app_commands.command(name="listfilters", description="List all filtered words")
    @app_commands.default_permissions(manage_messages=True)
    async def list_filtered_words(self, interaction: discord.Interaction):
        """List all words in the profanity filter"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # No words in filter
        if not self.blocked_words:
            await interaction.response.send_message("There are no words in the profanity filter.", ephemeral=True)
            return
            
        # Format the list of words
        word_list = ", ".join([f"`{word}`" for word in sorted(self.blocked_words)])
        
        # Send list privately
        await interaction.response.send_message(f"**Filtered Words:**\n{word_list}", ephemeral=True)

    @commands.command(name="togglefilter")
    @commands.has_permissions(manage_messages=True)
    async def toggle_filter_prefix(self, ctx, enabled: bool):
        """Enable or disable the profanity filter (prefix command)
        Usage: !togglefilter True/False"""
        # Convert guild ID to string for JSON compatibility
        guild_id = str(ctx.guild.id)
        
        # Update setting
        self.filter_enabled[guild_id] = enabled
        self.save_config()
        
        status = "enabled" if enabled else "disabled"
        await ctx.send(f"Profanity filter {status} for this server.")
        logger.info(f"User {ctx.author.name} {status} profanity filter for {ctx.guild.name}")
    
    @app_commands.command(name="togglefilter", description="Enable or disable the profanity filter")
    @app_commands.default_permissions(manage_messages=True)
    async def toggle_filter(self, interaction: discord.Interaction, enabled: bool):
        """Enable or disable the profanity filter for this server"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Convert guild ID to string for JSON compatibility
        guild_id = str(interaction.guild.id)
        
        # Update setting
        self.filter_enabled[guild_id] = enabled
        self.save_config()
        
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(f"Profanity filter {status} for this server.", ephemeral=False)
        logger.info(f"User {interaction.user.name} {status} profanity filter for {interaction.guild.name}")

    @commands.command(name="resetwarnings")
    @commands.has_permissions(manage_messages=True)
    async def reset_user_warnings_prefix(self, ctx, user: discord.Member):
        """Reset profanity warnings for a specific user (prefix command)"""
        # Reset warnings
        self.reset_warnings(user.id, ctx.guild.id)
        
        await ctx.send(f"Reset profanity warnings for {user.mention}.")
        logger.info(f"User {ctx.author.name} reset warnings for {user.name} in {ctx.guild.name}")
    
    @app_commands.command(name="resetwarnings", description="Reset warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def reset_user_warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Reset profanity warnings for a specific user"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Reset warnings
        self.reset_warnings(user.id, interaction.guild.id)
        
        await interaction.response.send_message(f"Reset profanity warnings for {user.mention}.", ephemeral=False)
        logger.info(f"User {interaction.user.name} reset warnings for {user.name} in {interaction.guild.name}")

    @commands.command(name="checkwarnings")
    @commands.has_permissions(manage_messages=True)
    async def check_user_warnings_prefix(self, ctx, user: discord.Member):
        """Check how many profanity warnings a user has (prefix command)"""
        # Get warning count
        guild_id = str(ctx.guild.id)
        user_id = str(user.id)
        server_name = ctx.guild.name
        
        if guild_id not in self.warning_count:
            await ctx.send(f"No warnings have been issued in server '{server_name}'.")
            return
            
        if user_id not in self.warning_count[guild_id]:
            await ctx.send(f"User **{user.display_name}** has no warnings in server '{server_name}'.")
            return
            
        count = self.warning_count[guild_id][user_id]
        
        await ctx.send(f"User **{user.display_name}** has {count} profanity warning(s) in server '{server_name}'.")
    
    @app_commands.command(name="checkwarnings", description="Check warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def check_user_warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Check how many profanity warnings a user has"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Get warning count and server details
        guild_id = str(interaction.guild_id)
        user_id = str(user.id)
        server_name = interaction.guild.name
        
        if guild_id not in self.warning_count:
            await interaction.response.send_message(f"No warnings have been issued in server '{server_name}'.", ephemeral=True)
            return
            
        if user_id not in self.warning_count[guild_id]:
            await interaction.response.send_message(f"User **{user.display_name}** has no warnings in server '{server_name}'.", ephemeral=True)
            return
            
        count = self.warning_count[guild_id][user_id]
        
        await interaction.response.send_message(
            f"User **{user.display_name}** has {count} profanity warning(s) in server '{server_name}'.", 
            ephemeral=True
        )

    @commands.command(name="filterstatus")
    async def check_filter_status_prefix(self, ctx):
        """Check if the profanity filter is enabled for this server (prefix command)"""
        # Convert guild ID to string for JSON compatibility
        guild_id = str(ctx.guild.id)
        
        # Get status - now defaulting to enabled if not explicitly set to False
        status = "disabled" if guild_id in self.filter_enabled and self.filter_enabled[guild_id] == False else "enabled"
        
        await ctx.send(f"The profanity filter is currently {status} for this server.")
        
    @app_commands.command(name="filterstatus", description="Check if the profanity filter is enabled")
    async def check_filter_status(self, interaction: discord.Interaction):
        """Check if the profanity filter is enabled for this server"""
        # Convert guild ID to string for JSON compatibility
        guild_id = str(interaction.guild.id)
        
        # Get status - now defaulting to enabled if not explicitly set to False
        status = "disabled" if guild_id in self.filter_enabled and self.filter_enabled[guild_id] == False else "enabled"
        
        await interaction.response.send_message(f"The profanity filter is currently {status} for this server.", ephemeral=True)

    @commands.command(name="listwarnings")
    @commands.has_permissions(manage_messages=True)
    async def list_warnings_prefix(self, ctx):
        """List all users with warnings in this server (prefix command)"""
        guild_id = str(ctx.guild.id)
        server_name = ctx.guild.name
        
        if guild_id not in self.warning_count or not self.warning_count[guild_id]:
            await ctx.send(f"No warnings have been issued in server '{server_name}'.")
            return
            
        # Create a list of users with warnings
        warning_list = []
        for user_id, count in self.warning_count[guild_id].items():
            if count > 0:  # Only include users with active warnings
                # Try to resolve user
                try:
                    member = await ctx.guild.fetch_member(int(user_id))
                    user_name = member.display_name if member else f"Unknown User ({user_id})"
                except:
                    user_name = f"Unknown User ({user_id})"
                    
                warning_list.append(f"**{user_name}** - {count} warning(s)")
        
        if not warning_list:
            await ctx.send(f"No active warnings in server '{server_name}'.")
            return
            
        # Create embed for better formatting
        embed = discord.Embed(
            title=f"Warning List for {server_name}",
            description="Users with active warnings:",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Users", value="\n".join(warning_list))
        embed.set_footer(text=f"Total Users with Warnings: {len(warning_list)} | Server ID: {guild_id}")
        embed.timestamp = datetime.datetime.utcnow()
        
        await ctx.send(embed=embed)
        
    @app_commands.command(name="listwarnings", description="List all users with warnings")
    @app_commands.default_permissions(manage_messages=True)
    async def list_warnings(self, interaction: discord.Interaction):
        """List all users with warnings in this server"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        guild_id = str(interaction.guild_id)
        server_name = interaction.guild.name
        
        if guild_id not in self.warning_count or not self.warning_count[guild_id]:
            await interaction.response.send_message(f"No warnings have been issued in server '{server_name}'.", ephemeral=True)
            return
            
        # Create a list of users with warnings
        warning_list = []
        for user_id, count in self.warning_count[guild_id].items():
            if count > 0:  # Only include users with active warnings
                # Try to resolve user
                try:
                    member = await interaction.guild.fetch_member(int(user_id))
                    user_name = member.display_name if member else f"Unknown User ({user_id})"
                except:
                    user_name = f"Unknown User ({user_id})"
                    
                warning_list.append(f"**{user_name}** - {count} warning(s)")
        
        if not warning_list:
            await interaction.response.send_message(f"No active warnings in server '{server_name}'.", ephemeral=True)
            return
            
        # Create embed for better formatting
        embed = discord.Embed(
            title=f"Warning List for {server_name}",
            description="Users with active warnings:",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Users", value="\n".join(warning_list))
        embed.set_footer(text=f"Total Users with Warnings: {len(warning_list)} | Server ID: {guild_id}")
        embed.timestamp = datetime.datetime.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    # Create an instance of the cog
    await bot.add_cog(ProfanityFilter(bot))
    logger.info("Profanity filter cog loaded")