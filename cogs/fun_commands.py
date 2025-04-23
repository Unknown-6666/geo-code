import discord
import logging
import random
import os
import asyncio
import time
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from typing import Optional
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import PermissionChecks, is_mod, is_admin, is_bot_owner
from config import JOG_ALLOWED_USER_ID

# List of funny fake ban reasons
FAKE_BAN_REASONS = [
    "using light mode at 3 AM",
    "putting pineapple on pizza",
    "using Comic Sans in a professional document",
    "calling HTML a programming language",
    "using spaces instead of tabs",
    "using tabs instead of spaces",
    "leaving the shopping cart in the parking spot",
    "saying 'um' too many times",
    "not returning the shopping cart",
    "taking too long to decide at a drive-thru",
    "talking during movies",
    "replying with 'k'",
    "using all lowercase on formal emails",
    "eating cereal with water",
    "double-dipping chips",
    "calling gif as 'jif'",
    "calling gif as 'gif' instead of 'jif'",
    "singing karaoke really badly",
    "not sharing snacks",
    "being sus",
    "taking 5 business days to reply to text messages",
    "having an anime profile picture",
    "making bad puns repeatedly",
    "using the wrong 'your' in a sentence",
    "posting cringe",
    "drinking milk with ice cubes",
    "paying only in pennies",
    "being a morning person",
    "liking Nickelback",
    "wearing socks with sandals",
    "clapping when the plane lands",
    "using auto-tune in karaoke",
    "quoting vines/TikToks in normal conversation",
    "not knowing the difference between there, their, and they're",
    "writing in all caps",
    "sending multiple messages when one would do",
    "hoarding the aux cord at parties",
    "talking about NFTs at dinner",
    "making too many dad jokes",
    "microwaving fish in the office",
    "reply all to company-wide emails",
    "taking up two parking spaces",
    "forgetting to mute during Zoom calls",
    "eating loudly during voice chat",
    "excessive use of emojis",
    "not using dark mode",
    "saying 'literally' literally all the time",
    "eating a Kit Kat without breaking it apart first",
    "biting ice cream instead of licking it",
    "leaving the microwave with 1 second left",
    "wearing non-prescription glasses",
    "leaving voicemails in 2023",
    "eating pizza with a fork and knife",
    "playing music on public transport without headphones",
    "doing TikTok dances in public",
    "claiming to be 'fluent' after using Duolingo for 5 days",
    "sending 'we need to talk' messages without context",
    "saying 'I'm not like other girls/guys'"
]

logger = logging.getLogger('discord')

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Log the initialization with the specific allowed user ID
        logger.info(f"Fun commands cog initialized. Jog command restricted to bot owner and user ID: {JOG_ALLOWED_USER_ID}")

    # Custom check function for jog command
    def is_jog_allowed():
        async def predicate(ctx):
            # Allow bot owner using our custom is_bot_owner function for consistency
            # This will use the same BOT_OWNER_IDS list as all other commands
            if is_bot_owner(ctx.author.id):
                logger.info(f"Jog command allowed for owner: {ctx.author.name} (ID: {ctx.author.id})")
                return True
                
            # Allow specified user ID
            if JOG_ALLOWED_USER_ID and ctx.author.id == int(JOG_ALLOWED_USER_ID):
                logger.info(f"Jog command allowed for authorized user: {ctx.author.name} (ID: {ctx.author.id})")
                return True
                
            # Deny everyone else - just log the denial but don't send a message here
            # to avoid duplicate messages (the command error handler will send one)
            logger.warning(f"Jog command access denied for {ctx.author.name} (ID: {ctx.author.id})")
            # We'll let the command error handler send the appropriate message
            return False
        return commands.check(predicate)

    @commands.command(name="jog")
    @is_jog_allowed()
    async def jog_prefix(self, ctx):
        """Timeout everyone in the server for 60 seconds (prefix command)"""
        # Check if the bot has permissions to timeout members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to timeout members."))
            return
            
        # Confirm the action before proceeding
        confirmation_msg = await ctx.send(embed=create_embed(
            "⚠️ Confirm Server Jog",
            "This will timeout everyone in the server for 60 seconds. Are you sure you want to proceed?",
            color=0xFFCC00
        ))
        
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id
            
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "❌":
                await confirmation_msg.delete()
                await ctx.send(embed=create_embed("Canceled", "Server jog canceled."))
                return
                
        except TimeoutError:
            await confirmation_msg.delete()
            await ctx.send(embed=create_embed("Canceled", "Server jog timed out."))
            return
            
        # Get all members in the server
        members = ctx.guild.members
        timeout_duration = timedelta(seconds=60)  # 60 seconds timeout
        
        # Create a status message to update
        status_msg = await ctx.send(embed=create_embed(
            "🏃‍♂️ Server Jog in Progress",
            f"Starting to timeout members (0/{len(members)})",
            color=0x3498DB
        ))
        
        # Counter for successful timeouts
        successful_timeouts = 0
        failed_timeouts = 0
        
        # Exclude the command invoker and the bot from timeouts
        excluded_ids = [ctx.author.id, self.bot.user.id]
        
        # Also exclude members with higher roles than the bot
        for member in members:
            if member.id in excluded_ids:
                continue
                
            # Skip if member has a higher role than the bot or has admin permissions
            if member.top_role >= ctx.guild.me.top_role or member.guild_permissions.administrator:
                continue
                
            try:
                await member.timeout(timeout_duration, reason=f"Server-wide jog initiated by {ctx.author}")
                successful_timeouts += 1
                
                # Add a small delay to avoid hitting Discord rate limits
                if successful_timeouts % 5 == 0:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error timing out member {member.name}: {str(e)}")
                failed_timeouts += 1
                
            # Only update status at certain milestones to prevent rate limiting
            if successful_timeouts in [1, 10, 25, 50, 100, 200, 500] or successful_timeouts % 100 == 0:
                try:
                    # Use a new message instead of editing to avoid Discord's rate limits
                    await ctx.send(embed=create_embed(
                        "🏃‍♂️ Server Jog Progress Update",
                        f"Timed out {successful_timeouts} members so far...",
                        color=0x3498DB
                    ))
                except Exception as edit_error:
                    # If we can't send a new message, just log it and continue
                    logger.error(f"Error sending status update: {str(edit_error)}")
                
        # Final report
        await status_msg.edit(embed=create_embed(
            "🏃‍♂️ Server Jog Complete",
            f"Everyone is running for 60 seconds!\n\n"
            f"Successfully timed out: {successful_timeouts} members\n"
            f"Failed to timeout: {failed_timeouts} members\n\n"
            "All timeouts will automatically expire after 60 seconds.",
            color=0x2ECC71
        ))
        
        logger.info(f"Server jog completed in {ctx.guild.name} by {ctx.author.name}. Success: {successful_timeouts}, Failed: {failed_timeouts}")

    # Custom check for slash command version
    async def slash_is_jog_allowed(interaction: discord.Interaction):
        # Allow bot owner using our custom is_bot_owner function for consistency
        # This will use the same BOT_OWNER_IDS list as all other commands
        if is_bot_owner(interaction.user.id):
            logger.info(f"Jog slash command allowed for owner: {interaction.user.name} (ID: {interaction.user.id})")
            return True
            
        # Allow specified user ID
        if JOG_ALLOWED_USER_ID and interaction.user.id == int(JOG_ALLOWED_USER_ID):
            logger.info(f"Jog slash command allowed for authorized user: {interaction.user.name} (ID: {interaction.user.id})")
            return True
            
        # Deny everyone else - for app_commands we need to send the error message here
        # since app_commands don't have the same error handling as regular commands
        logger.warning(f"Jog slash command access denied for {interaction.user.name} (ID: {interaction.user.id})")
        await interaction.response.send_message(
            embed=create_error_embed("Access Denied", "You don't have permission to use this command."),
            ephemeral=True
        )
        return False

    @app_commands.command(name="jog", description="Timeout everyone in the server for 60 seconds")
    @app_commands.check(slash_is_jog_allowed)
    async def jog(self, interaction: discord.Interaction):
        """Timeout everyone in the server for 60 seconds (slash command)"""
        # Check if the bot has permissions to timeout members
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to timeout members."),
                ephemeral=True
            )
            return
            
        # Create confirm/cancel buttons
        confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Confirm", custom_id="confirm")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", custom_id="cancel")
        
        view = discord.ui.View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        # Send confirmation message with buttons
        await interaction.response.send_message(
            embed=create_embed(
                "⚠️ Confirm Server Jog",
                "This will timeout everyone in the server for 60 seconds. Are you sure you want to proceed?",
                color=0xFFCC00
            ),
            view=view
        )
        
        # Define button callbacks
        async def confirm_callback(button_interaction):
            # Check if the interaction user is the same as the original command user
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("You didn't initiate this command.", ephemeral=True)
                return
                
            # Disable buttons to prevent multiple clicks
            for item in view.children:
                item.disabled = True
                
            await button_interaction.response.edit_message(view=view)
            
            # Get all members in the server
            members = interaction.guild.members
            timeout_duration = timedelta(seconds=60)  # 60 seconds timeout
            
            # Create a status message
            status_msg = await button_interaction.followup.send(
                embed=create_embed(
                    "🏃‍♂️ Server Jog in Progress",
                    f"Starting to timeout members (0/{len(members)})",
                    color=0x3498DB
                )
            )
            
            # Counter for successful timeouts
            successful_timeouts = 0
            failed_timeouts = 0
            
            # Exclude the command invoker and the bot from timeouts
            excluded_ids = [interaction.user.id, self.bot.user.id]
            
            # Also exclude members with higher roles than the bot
            for member in members:
                if member.id in excluded_ids:
                    continue
                    
                # Skip if member has a higher role than the bot or has admin permissions
                if member.top_role >= interaction.guild.me.top_role or member.guild_permissions.administrator:
                    continue
                    
                try:
                    await member.timeout(timeout_duration, reason=f"Server-wide jog initiated by {interaction.user}")
                    successful_timeouts += 1
                    
                    # Add a small delay to avoid hitting Discord rate limits
                    if successful_timeouts % 5 == 0:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.error(f"Error timing out member {member.name}: {str(e)}")
                    failed_timeouts += 1
                    
                # Only update status at specific milestones to prevent rate limiting
                if successful_timeouts in [1, 10, 25, 50, 100, 200, 500] or successful_timeouts % 100 == 0:
                    try:
                        # Send a new message instead of editing to avoid Discord's rate limits
                        await button_interaction.followup.send(embed=create_embed(
                            "🏃‍♂️ Server Jog Progress Update",
                            f"Timed out {successful_timeouts} members so far...",
                            color=0x3498DB
                        ))
                    except Exception as send_error:
                        # If we can't send a new message, just log it and continue
                        logger.error(f"Error sending status update: {str(send_error)}")
                    
            # Final report
            await status_msg.edit(embed=create_embed(
                "🏃‍♂️ Server Jog Complete",
                f"Everyone is running for 60 seconds!\n\n"
                f"Successfully timed out: {successful_timeouts} members\n"
                f"Failed to timeout: {failed_timeouts} members\n\n"
                "All timeouts will automatically expire after 60 seconds.",
                color=0x2ECC71
            ))
            
            logger.info(f"Server jog completed in {interaction.guild.name} by {interaction.user.name}. Success: {successful_timeouts}, Failed: {failed_timeouts}")
        
        async def cancel_callback(button_interaction):
            # Check if the interaction user is the same as the original command user
            if button_interaction.user.id != interaction.user.id:
                await button_interaction.response.send_message("You didn't initiate this command.", ephemeral=True)
                return
                
            # Disable buttons to prevent multiple clicks
            for item in view.children:
                item.disabled = True
                
            await button_interaction.response.edit_message(view=view)
            await button_interaction.followup.send(embed=create_embed("Canceled", "Server jog canceled."))
        
        # Attach callbacks to buttons
        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback
        
    @commands.command(name="setjoguser")
    @commands.is_owner()
    async def set_jog_user(self, ctx, user_id: int = None):
        """Set a specific user who can use the jog command (Bot Owner Only)"""
        from config import JOG_ALLOWED_USER_ID
        
        if user_id is None:
            # Display current allowed user
            if JOG_ALLOWED_USER_ID:
                user = self.bot.get_user(JOG_ALLOWED_USER_ID)
                user_name = user.name if user else f"Unknown User ({JOG_ALLOWED_USER_ID})"
                await ctx.send(embed=create_embed(
                    "Jog Command Access",
                    f"The jog command is currently accessible by you and: {user_name} (ID: {JOG_ALLOWED_USER_ID})",
                    color=0x3498DB
                ))
            else:
                await ctx.send(embed=create_embed(
                    "Jog Command Access",
                    "The jog command is currently only accessible by you (the bot owner).",
                    color=0x3498DB
                ))
            return
            
        # Try to find the user
        user = self.bot.get_user(user_id)
        if user:
            # Set environment variable and update config
            os.environ["JOG_ALLOWED_USER_ID"] = str(user_id)
            # Update config module (this will be reset on bot restart)
            import config
            config.JOG_ALLOWED_USER_ID = user_id
            await ctx.send(embed=create_embed(
                "Jog User Set",
                f"User {user.name} (ID: {user_id}) can now use the jog command along with you.",
                color=0x2ECC71
            ))
            logger.info(f"Bot owner {ctx.author.name} set jog command access for user {user.name} (ID: {user_id})")
        else:
            await ctx.send(embed=create_error_embed(
                "User Not Found",
                f"Could not find user with ID: {user_id}. Make sure the ID is correct and the user shares a server with the bot."
            ))
    
    @app_commands.command(name="setjoguser", description="Set a specific user who can use the jog command")
    @app_commands.describe(user_id="The Discord user ID of the person who should have jog command access")
    async def set_jog_user_slash(self, interaction: discord.Interaction, user_id: str = None):
        """Set a specific user who can use the jog command (Bot Owner Only)"""
        # Check if user is the bot owner using our custom is_bot_owner function for consistency
        if not is_bot_owner(interaction.user.id):
            logger.warning(f"SetJogUser command denied for non-owner: {interaction.user.name} (ID: {interaction.user.id})")
            await interaction.response.send_message(
                embed=create_error_embed("Access Denied", "Only the bot owner can use this command."),
                ephemeral=True
            )
            return
            
        from config import JOG_ALLOWED_USER_ID
        
        if user_id is None:
            # Display current allowed user
            if JOG_ALLOWED_USER_ID:
                user = self.bot.get_user(JOG_ALLOWED_USER_ID)
                user_name = user.name if user else f"Unknown User ({JOG_ALLOWED_USER_ID})"
                await interaction.response.send_message(embed=create_embed(
                    "Jog Command Access",
                    f"The jog command is currently accessible by you and: {user_name} (ID: {JOG_ALLOWED_USER_ID})",
                    color=0x3498DB
                ))
            else:
                await interaction.response.send_message(embed=create_embed(
                    "Jog Command Access",
                    "The jog command is currently only accessible by you (the bot owner).",
                    color=0x3498DB
                ))
            return
            
        # Convert string ID to int
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid ID", "Please provide a valid numeric user ID."),
                ephemeral=True
            )
            return
            
        # Try to find the user
        user = self.bot.get_user(user_id_int)
        if user:
            # Set environment variable
            os.environ["JOG_ALLOWED_USER_ID"] = str(user_id_int)
            # Update config module (this will be reset on bot restart)
            import config
            config.JOG_ALLOWED_USER_ID = user_id_int
            await interaction.response.send_message(embed=create_embed(
                "Jog User Set",
                f"User {user.name} (ID: {user_id_int}) can now use the jog command along with you.",
                color=0x2ECC71
            ))
            logger.info(f"Bot owner {interaction.user.name} set jog command access for user {user.name} (ID: {user_id_int})")
        else:
            await interaction.response.send_message(embed=create_error_embed(
                "User Not Found",
                f"Could not find user with ID: {user_id_int}. Make sure the ID is correct and the user shares a server with the bot."
            ))
            
    # Spam command - owner only
    @commands.command(name="spam")
    @commands.is_owner()  # Only bot owner can use this
    async def spam_prefix(self, ctx, count: int, *, message: str):
        """
        Make the bot spam a message multiple times (prefix command)
        Usage: !spam [count] [message]
        Example: !spam 5 Hello everyone!
        """
        # Validate the count to prevent abuse
        if count <= 0:
            await ctx.send(embed=create_error_embed("Invalid Count", "The count must be a positive number."))
            return
            
        if count > 50:
            # Confirm the action if it's a large number
            confirmation_msg = await ctx.send(embed=create_embed(
                "⚠️ Confirm Message Spam",
                f"You're about to send {count} messages. This is a lot and might be considered spam by Discord. Are you sure?",
                color=0xFFCC00
            ))
            
            await confirmation_msg.add_reaction("✅")
            await confirmation_msg.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id
                
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == "❌":
                    await confirmation_msg.delete()
                    await ctx.send(embed=create_embed("Canceled", "Message spam canceled."))
                    return
                    
            except:
                await confirmation_msg.delete()
                await ctx.send(embed=create_embed("Canceled", "Message spam request timed out."))
                return
        
        # Create a status message to update
        status_msg = await ctx.send(embed=create_embed(
            "🔄 Spam in Progress",
            f"Starting to send {count} messages...",
            color=0x3498DB
        ))
        
        # Track if we should keep sending
        keep_spamming = True
        
        # Function to handle stopping the spam if needed
        async def stop_spam_on_reaction():
            nonlocal keep_spamming
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "🛑" and reaction.message.id == status_msg.id
                
            await status_msg.add_reaction("🛑")  # Stop sign reaction
            
            try:
                # Wait for the stop reaction
                await self.bot.wait_for('reaction_add', timeout=count * 1.5, check=check)
                keep_spamming = False
                await status_msg.edit(embed=create_embed(
                    "Spam Canceled",
                    "Stopped sending messages as requested.",
                    color=0xE74C3C
                ))
            except asyncio.TimeoutError:
                # Timeout just means they didn't click stop
                pass
                
        # Start the reaction listener in the background
        stop_task = asyncio.create_task(stop_spam_on_reaction())
        
        # Send the messages
        sent_count = 0
        for i in range(count):
            if not keep_spamming:
                break  # Stop if the user requested to stop
                
            try:
                await ctx.send(message)
                sent_count += 1
                
                # Update the status every 5 messages
                if sent_count % 5 == 0:
                    await status_msg.edit(embed=create_embed(
                        "🔄 Spam in Progress",
                        f"Sent {sent_count}/{count} messages so far...",
                        color=0x3498DB
                    ))
                
                # Add delays to avoid rate limits
                if i % 5 == 4:  # Every 5 messages
                    await asyncio.sleep(1.5)
                else:
                    await asyncio.sleep(0.5)  # Small delay between individual messages
                    
            except Exception as e:
                logger.error(f"Error sending spam message: {str(e)}")
                # If we encounter an error, stop spamming
                await status_msg.edit(embed=create_error_embed(
                    "Error",
                    f"An error occurred after sending {sent_count} messages: {str(e)}"
                ))
                break
        
        # Cancel the reaction listener if it's still running
        if not stop_task.done():
            stop_task.cancel()
            
        # Final report (only if not already edited due to cancel or error)
        if keep_spamming:
            await status_msg.edit(embed=create_embed(
                "✅ Spam Complete",
                f"Successfully sent {sent_count} messages.",
                color=0x2ECC71
            ))
            
        logger.info(f"Spam command completed by {ctx.author.name}. Sent {sent_count}/{count} messages.")
    
    # Slash command version of spam
    @app_commands.command(name="spam", description="Make the bot spam a message multiple times (Owner only)")
    @app_commands.describe(
        count="How many times to send the message",
        message="The message to spam"
    )
    async def spam_slash(self, interaction: discord.Interaction, count: int, message: str):
        """Make the bot spam a message multiple times (slash command)"""
        # Check if user is bot owner
        if not is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=create_error_embed("Access Denied", "Only the bot owner can use this command."),
                ephemeral=True
            )
            return
            
        # Validate the count to prevent abuse
        if count <= 0:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid Count", "The count must be a positive number."),
                ephemeral=True
            )
            return
            
        # The actual spam execution function
        async def execute_spam(response_interaction):
            # Create a status message
            status_msg = await response_interaction.followup.send(
                embed=create_embed(
                    "🔄 Spam in Progress",
                    f"Starting to send {count} messages...",
                    color=0x3498DB
                )
            )
            
            # Create a stop button
            stop_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Stop Spamming", custom_id="stop")
            stop_view = discord.ui.View()
            stop_view.add_item(stop_button)
            
            # Track if we should keep sending
            keep_spamming = True
            
            # Update the status message with a stop button
            await status_msg.edit(view=stop_view)
            
            # Define stop button callback
            async def stop_callback(stop_interaction):
                nonlocal keep_spamming
                # Check if it's the same user
                if stop_interaction.user.id != interaction.user.id:
                    await stop_interaction.response.send_message("You didn't initiate this command.", ephemeral=True)
                    return
                    
                keep_spamming = False
                stop_button.disabled = True
                await stop_interaction.response.edit_message(
                    embed=create_embed(
                        "Spam Canceled",
                        "Stopped sending messages as requested.",
                        color=0xE74C3C
                    ),
                    view=stop_view
                )
                
            # Attach callback
            stop_button.callback = stop_callback
            
            # Send the messages
            sent_count = 0
            channel = interaction.channel
            
            for i in range(count):
                if not keep_spamming:
                    break  # Stop if the user requested to stop
                    
                try:
                    await channel.send(message)
                    sent_count += 1
                    
                    # Update the status every 5 messages or at the end
                    if sent_count % 5 == 0 or sent_count == count:
                        await status_msg.edit(
                            embed=create_embed(
                                "🔄 Spam in Progress",
                                f"Sent {sent_count}/{count} messages so far...",
                                color=0x3498DB
                            )
                        )
                    
                    # Add delays to avoid rate limits
                    if i % 5 == 4:  # Every 5 messages
                        await asyncio.sleep(1.5)
                    else:
                        await asyncio.sleep(0.5)  # Small delay between individual messages
                        
                except Exception as e:
                    logger.error(f"Error sending spam message: {str(e)}")
                    # If we encounter an error, stop spamming
                    stop_button.disabled = True
                    await status_msg.edit(
                        embed=create_error_embed(
                            "Error",
                            f"An error occurred after sending {sent_count} messages: {str(e)}"
                        ),
                        view=stop_view
                    )
                    break
            
            # Final report (only if not already edited due to cancel or error)
            if keep_spamming:
                stop_button.disabled = True
                await status_msg.edit(
                    embed=create_embed(
                        "✅ Spam Complete",
                        f"Successfully sent {sent_count} messages.",
                        color=0x2ECC71
                    ),
                    view=stop_view
                )
                
            logger.info(f"Spam command completed by {interaction.user.name}. Sent {sent_count}/{count} messages.")
            
        if count > 50:
            # For large spam counts, create confirm/cancel buttons
            confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Confirm", custom_id="confirm")
            cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", custom_id="cancel")
            
            view = discord.ui.View()
            view.add_item(confirm_button)
            view.add_item(cancel_button)
            
            # Send confirmation message with buttons
            await interaction.response.send_message(
                embed=create_embed(
                    "⚠️ Confirm Message Spam",
                    f"You're about to send {count} messages. This is a lot and might be considered spam by Discord. Are you sure?",
                    color=0xFFCC00
                ),
                view=view
            )
            
            # Define button callbacks
            async def confirm_callback(button_interaction):
                # Check if it's the same user
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("You didn't initiate this command.", ephemeral=True)
                    return
                    
                # Disable buttons to prevent multiple clicks
                for item in view.children:
                    item.disabled = True
                    
                await button_interaction.response.edit_message(view=view)
                await execute_spam(button_interaction)
            
            async def cancel_callback(button_interaction):
                # Check if it's the same user
                if button_interaction.user.id != interaction.user.id:
                    await button_interaction.response.send_message("You didn't initiate this command.", ephemeral=True)
                    return
                    
                # Disable buttons to prevent multiple clicks
                for item in view.children:
                    item.disabled = True
                    
                await button_interaction.response.edit_message(view=view)
                await button_interaction.followup.send(embed=create_embed("Canceled", "Message spam canceled."))
            
            # Attach callbacks to buttons
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
        else:
            # For small counts, no confirmation needed
            await interaction.response.defer()
            await execute_spam(interaction)

    # Fake ban command - prefix version
    @commands.command(name="fakeban")
    async def fakeban_prefix(self, ctx, member: discord.Member = None, *, reason: str = None):
        """
        Pretend to ban a user for a funny reason (doesn't actually ban anyone)
        Usage: !fakeban @user [optional reason]
        """
        # If no member is mentioned, inform the user
        if member is None:
            await ctx.send(embed=create_error_embed(
                "Missing User",
                "You need to mention a user to fake ban. Example: !fakeban @user"
            ))
            return
            
        # If the mentioned member is the bot, respond with humor
        if member.id == self.bot.user.id:
            await ctx.send(embed=create_embed(
                "Nice Try",
                "You can't ban me, I'm too powerful! ⚡",
                color=0xE74C3C
            ))
            return
            
        # Generate a random reason if none is provided
        if reason is None:
            reason = random.choice(FAKE_BAN_REASONS)
        
        # Create fake ban message
        ban_embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**{member.name}** has been banned from the server!",
            color=0xE74C3C
        )
        ban_embed.add_field(name="Reason", value=reason, inline=False)
        ban_embed.add_field(name="Banned By", value=ctx.author.mention, inline=True)
        ban_embed.add_field(name="Duration", value="Forever (or until they apologize)", inline=True)
        ban_embed.set_thumbnail(url=member.display_avatar.url if hasattr(member, 'display_avatar') else member.avatar.url)
        ban_embed.set_footer(text="Just kidding! This is a fake ban. No users were harmed in the making of this joke.")
        
        # Send the initial ban message
        ban_msg = await ctx.send(embed=ban_embed)
        
        # Wait a moment for comedic effect, then reveal it's fake
        await asyncio.sleep(3)
        
        reveal_embed = discord.Embed(
            title="😄 Just Kidding!",
            description=f"**{member.name}** wasn't actually banned. It was just a prank!",
            color=0x2ECC71
        )
        reveal_embed.set_footer(text="This was a fake ban. No moderation actions were taken.")
        
        await ctx.send(embed=reveal_embed)
        logger.info(f"Fake ban command used by {ctx.author.name} on {member.name} for reason: {reason}")
    
    # Fake ban command - slash version
    @app_commands.command(name="fakeban", description="Pretend to ban a user (doesn't actually ban anyone)")
    @app_commands.describe(
        user="The user to fake ban",
        reason="The reason for the fake ban (optional, will use a random funny reason if not provided)"
    )
    async def fakeban_slash(self, interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = None):
        """Pretend to ban a user for a funny reason (slash command)"""
        # If the mentioned member is the bot, respond with humor
        if user.id == self.bot.user.id:
            await interaction.response.send_message(embed=create_embed(
                "Nice Try",
                "You can't ban me, I'm too powerful! ⚡",
                color=0xE74C3C
            ))
            return
            
        # Generate a random reason if none is provided
        if reason is None:
            reason = random.choice(FAKE_BAN_REASONS)
        
        # Create fake ban message
        ban_embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**{user.name}** has been banned from the server!",
            color=0xE74C3C
        )
        ban_embed.add_field(name="Reason", value=reason, inline=False)
        ban_embed.add_field(name="Banned By", value=interaction.user.mention, inline=True)
        ban_embed.add_field(name="Duration", value="Forever (or until they apologize)", inline=True)
        ban_embed.set_thumbnail(url=user.display_avatar.url if hasattr(user, 'display_avatar') else user.avatar.url)
        ban_embed.set_footer(text="This ban hammer is getting a workout today...")
        
        # Send the initial ban message
        await interaction.response.send_message(embed=ban_embed)
        
        # Wait a moment for comedic effect, then reveal it's fake
        await asyncio.sleep(3)
        
        # Create the reveal message
        reveal_embed = discord.Embed(
            title="😄 Just Kidding!",
            description=f"**{user.name}** wasn't actually banned. It was just a prank!",
            color=0x2ECC71
        )
        reveal_embed.set_footer(text="This was a fake ban. No moderation actions were taken.")
        
        # Send the reveal message
        await interaction.followup.send(embed=reveal_embed)
        logger.info(f"Fake ban slash command used by {interaction.user.name} on {user.name} for reason: {reason}")
    
    # Another fun variation - UNO reverse card - prefix version
    @commands.command(name="unoreverse")
    async def uno_reverse_prefix(self, ctx, member: discord.Member = None):
        """
        Send an UNO reverse card to someone who tried to use a command on you
        Usage: !unoreverse @user
        """
        # If no member is mentioned, use a default message
        if member is None:
            uno_embed = discord.Embed(
                title="⏪ UNO Reverse Card ⏪",
                description=f"{ctx.author.mention} plays an UNO reverse card!",
                color=0xFF5733
            )
            uno_embed.set_image(url="https://i.imgur.com/yXEiYQ4.png")  # UNO reverse card image
            await ctx.send(embed=uno_embed)
            return
            
        # If a member is mentioned, direct it at them
        uno_embed = discord.Embed(
            title="⏪ UNO Reverse Card ⏪",
            description=f"{ctx.author.mention} plays an UNO reverse card on {member.mention}!",
            color=0xFF5733
        )
        uno_embed.set_image(url="https://i.imgur.com/yXEiYQ4.png")  # UNO reverse card image
        
        await ctx.send(embed=uno_embed)
        logger.info(f"UNO reverse card command used by {ctx.author.name} on {member.name if member else 'no one'}")
    
    # UNO reverse card - slash version
    @app_commands.command(name="unoreverse", description="Play an UNO reverse card on someone")
    @app_commands.describe(user="The user to reverse (optional)")
    async def uno_reverse_slash(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Send an UNO reverse card (slash command)"""
        # If no user is specified, use a default message
        if user is None:
            uno_embed = discord.Embed(
                title="⏪ UNO Reverse Card ⏪",
                description=f"{interaction.user.mention} plays an UNO reverse card!",
                color=0xFF5733
            )
            uno_embed.set_image(url="https://i.imgur.com/yXEiYQ4.png")  # UNO reverse card image
            await interaction.response.send_message(embed=uno_embed)
            return
            
        # If a user is specified, direct it at them
        uno_embed = discord.Embed(
            title="⏪ UNO Reverse Card ⏪",
            description=f"{interaction.user.mention} plays an UNO reverse card on {user.mention}!",
            color=0xFF5733
        )
        uno_embed.set_image(url="https://i.imgur.com/yXEiYQ4.png")  # UNO reverse card image
        
        await interaction.response.send_message(embed=uno_embed)
        logger.info(f"UNO reverse slash command used by {interaction.user.name} on {user.name if user else 'no one'}")
        
async def setup(bot):
    await bot.add_cog(FunCommands(bot))