import discord
import logging
import random
import os
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import PermissionChecks, is_mod, is_admin, is_bot_owner
from config import JOG_ALLOWED_USER_ID

logger = logging.getLogger('discord')

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Log the initialization with the specific allowed user ID
        logger.info(f"Fun commands cog initialized. Jog command restricted to bot owner and user ID: {JOG_ALLOWED_USER_ID}")

    # Custom check function for jog command
    def is_jog_allowed():
        async def predicate(ctx):
            # Allow bot owner
            if await ctx.bot.is_owner(ctx.author):
                return True
            # Allow specified user ID
            if JOG_ALLOWED_USER_ID and ctx.author.id == JOG_ALLOWED_USER_ID:
                return True
            # Deny everyone else
            await ctx.send(embed=create_error_embed("Access Denied", "You don't have permission to use this command."))
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
                
                # Update status every 5 members
                if successful_timeouts % 5 == 0:
                    await status_msg.edit(embed=create_embed(
                        "🏃‍♂️ Server Jog in Progress",
                        f"Timing out members ({successful_timeouts}/{len(members)})",
                        color=0x3498DB
                    ))
                    
            except Exception as e:
                logger.error(f"Error timing out member {member.name}: {str(e)}")
                failed_timeouts += 1
                
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
        # Allow bot owner
        app_info = await interaction.client.application_info()
        if interaction.user.id == app_info.owner.id:
            return True
        # Allow specified user ID
        if JOG_ALLOWED_USER_ID and interaction.user.id == JOG_ALLOWED_USER_ID:
            return True
        # Deny everyone else
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
                    
                    # Update status every 5 members
                    if successful_timeouts % 5 == 0:
                        await status_msg.edit(embed=create_embed(
                            "🏃‍♂️ Server Jog in Progress",
                            f"Timing out members ({successful_timeouts}/{len(members)})",
                            color=0x3498DB
                        ))
                        
                except Exception as e:
                    logger.error(f"Error timing out member {member.name}: {str(e)}")
                    failed_timeouts += 1
                    
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
        # Check if user is the bot owner
        app_info = await interaction.client.application_info()
        if interaction.user.id != app_info.owner.id:
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

async def setup(bot):
    await bot.add_cog(FunCommands(bot))