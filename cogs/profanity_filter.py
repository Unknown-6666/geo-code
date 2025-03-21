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
            except Exception as e:
                logger.error(f"Error loading profanity filter config: {str(e)}")
                # Initialize with empty defaults
                self.blocked_words = []
                self.filter_enabled = {}
                self.warning_count = {}
        else:
            logger.info("No profanity filter config found, creating new one")
            self.save_config()  # Create initial empty config

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
        
        # Skip check if filter is disabled for this guild
        if not self.filter_enabled.get(guild_id, False):
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
            return
            
        # Reset the warning count
        if user_id in self.warning_count[guild_id]:
            self.warning_count[guild_id][user_id] = 0
            self.save_config()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages for profanity"""
        # Ignore messages from bots, including our own
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
            
        # Check if message contains filtered words
        if self.is_filtered_word(message.content, message.guild.id):
            logger.info(f"Filtered message from {message.author.name} in {message.guild.name}: {message.content}")
            
            try:
                # Delete the message
                await message.delete()
                
                # Add warning and get count
                warning_count = self.add_warning(message.author.id, message.guild.id)
                
                # Send warning DM to user
                try:
                    await message.author.send(
                        f"⚠️ Your message in **{message.guild.name}** was removed for containing inappropriate language. "
                        f"This is warning #{warning_count}."
                    )
                except discord.Forbidden:
                    # Can't send DMs to this user
                    logger.info(f"Could not send DM to {message.author.name}")
                    
                # If warning count exceeds threshold, take action
                if warning_count >= 3:
                    # Try to timeout for 10 minutes
                    try:
                        # 600 seconds = 10 minutes
                        await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=600), 
                                                reason="Automatic timeout for repeated use of inappropriate language")
                        logger.info(f"User {message.author.name} timed out for 10 minutes due to repeated profanity")
                    except discord.Forbidden:
                        logger.warning(f"No permission to timeout {message.author.name}")
                    except Exception as e:
                        logger.error(f"Error timing out user: {str(e)}")
                        
                    # Notify a log channel if available
                    try:
                        # Look for a channel named "mod-logs" or "logs"
                        log_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                        if not log_channel:
                            log_channel = discord.utils.get(message.guild.text_channels, name="logs")
                            
                        if log_channel:
                            embed = discord.Embed(
                                title="User Timed Out",
                                description=f"User {message.author.mention} has been timed out for 10 minutes.",
                                color=discord.Color.red()
                            )
                            embed.add_field(name="Reason", value="Repeated use of inappropriate language")
                            embed.add_field(name="Warning Count", value=str(warning_count))
                            embed.set_footer(text=f"User ID: {message.author.id}")
                            
                            await log_channel.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Error sending to log channel: {str(e)}")
                        
            except discord.Forbidden:
                logger.warning(f"No permission to delete message from {message.author.name}")
            except Exception as e:
                logger.error(f"Error processing filtered message: {str(e)}")

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
        count = self.get_warning_count(user.id, ctx.guild.id)
        
        await ctx.send(f"{user.mention} has {count} profanity warning(s).")
    
    @app_commands.command(name="checkwarnings", description="Check warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def check_user_warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Check how many profanity warnings a user has"""
        # Check if user has appropriate permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
            
        # Get warning count
        count = self.get_warning_count(user.id, interaction.guild.id)
        
        await interaction.response.send_message(f"{user.mention} has {count} profanity warning(s).", ephemeral=True)

    @commands.command(name="filterstatus")
    async def check_filter_status_prefix(self, ctx):
        """Check if the profanity filter is enabled for this server (prefix command)"""
        # Convert guild ID to string for JSON compatibility
        guild_id = str(ctx.guild.id)
        
        # Get status
        status = "enabled" if self.filter_enabled.get(guild_id, False) else "disabled"
        
        await ctx.send(f"The profanity filter is currently {status} for this server.")
        
    @app_commands.command(name="filterstatus", description="Check if the profanity filter is enabled")
    async def check_filter_status(self, interaction: discord.Interaction):
        """Check if the profanity filter is enabled for this server"""
        # Convert guild ID to string for JSON compatibility
        guild_id = str(interaction.guild.id)
        
        # Get status
        status = "enabled" if self.filter_enabled.get(guild_id, False) else "disabled"
        
        await interaction.response.send_message(f"The profanity filter is currently {status} for this server.", ephemeral=True)

async def setup(bot):
    # Create an instance of the cog
    await bot.add_cog(ProfanityFilter(bot))
    logger.info("Profanity filter cog loaded")