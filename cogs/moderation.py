import discord
import json
import logging
import asyncio
import os
import re
import config
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import PermissionChecks, is_mod, is_admin, is_bot_owner

logger = logging.getLogger('discord')

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recent_actions = {}  # Store recent moderation actions for potential undoing
        # Default to 0, will be configurable via commands
        self.prisoner_role_id = 1260428877080035338  # Placeholder for prisoner role ID
        # Try to load from config file if it exists
        self.config_file = 'data/prisoner_role.json'
        self._load_prisoner_role_config()
        logger.info("Moderation cog initialized")
        
    def _load_prisoner_role_config(self):
        """Load prisoner role configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.prisoner_role_id = config.get('prisoner_role_id', 0)
                    logger.info(f"Loaded prisoner role ID: {self.prisoner_role_id}")
        except Exception as e:
            logger.error(f"Failed to load prisoner role config: {e}")
            
    def _save_prisoner_role_config(self):
        """Save prisoner role configuration to file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump({'prisoner_role_id': self.prisoner_role_id}, f)
                logger.info(f"Saved prisoner role ID: {self.prisoner_role_id}")
        except Exception as e:
            logger.error(f"Failed to save prisoner role config: {e}")

    @commands.command(name="kick")
    @commands.check_any(commands.has_permissions(kick_members=True), PermissionChecks.is_mod())
    async def kick_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Kick a user from the server (prefix command)"""
        # Check if the bot can kick members
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to kick members."))
            return
            
        # Check if the user is trying to kick themselves
        if user == ctx.author:
            await ctx.send(embed=create_error_embed("Error", "You cannot kick yourself."))
            return
            
        # Check if the user is trying to kick someone with a higher role
        if user.top_role >= ctx.author.top_role:
            await ctx.send(embed=create_error_embed("Error", "You cannot kick someone with a higher or equal role."))
            return
            
        try:
            # Store kicked user info for potential undoing
            user_info = {
                "user_id": user.id,
                "user_name": str(user),
                "kicked_by": ctx.author.id,
                "kicked_at": discord.utils.utcnow(),
                "reason": reason
            }
            self.recent_actions[f"kick_{ctx.guild.id}"] = user_info
            
            await user.kick(reason=f"Kicked by {ctx.author}: {reason}")
            logger.info(f"User {user} was kicked by {ctx.author} for reason: {reason}")
            
            embed = create_embed(
                "👢 User Kicked",
                f"{user.mention} has been kicked from the server.\nReason: {reason or 'No reason provided'}\n\nYou can use the `!undokick` command to invite this user back.",
                color=0xF04747
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to kick this user."))
        except Exception as e:
            logger.error(f"Error kicking user: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to kick the user."))
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    @app_commands.default_permissions(kick_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Kick a user from the server"""
        # Check if the bot can kick members
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to kick members."),
                ephemeral=True
            )
            return

        # Check if the user is trying to kick themselves
        if user == interaction.user:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot kick yourself."),
                ephemeral=True
            )
            return

        # Check if the user is trying to kick someone with a higher role
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot kick someone with a higher or equal role."),
                ephemeral=True
            )
            return

        try:
            # Store kicked user info for potential undoing
            user_info = {
                "user_id": user.id,
                "user_name": str(user),
                "kicked_by": interaction.user.id,
                "kicked_at": discord.utils.utcnow(),
                "reason": reason
            }
            self.recent_actions[f"kick_{interaction.guild.id}"] = user_info
            
            await user.kick(reason=f"Kicked by {interaction.user}: {reason}")
            logger.info(f"User {user} was kicked by {interaction.user} for reason: {reason}")

            embed = create_embed(
                "👢 User Kicked",
                f"{user.mention} has been kicked from the server.\nReason: {reason or 'No reason provided'}\n\nYou can use the `/undokick` command to invite this user back.",
                color=0xF04747
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to kick this user."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error kicking user: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to kick the user."),
                ephemeral=True
            )

    @commands.command(name="ban")
    @commands.check_any(commands.has_permissions(ban_members=True), PermissionChecks.is_mod())
    async def ban_prefix(self, ctx, user: discord.Member, delete_days: int = 1, *, reason: str = None):
        """Ban a user from the server (prefix command)
        Usage: !ban @user [delete_days] [reason]"""
        # Check if the bot can ban members
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to ban members."))
            return
            
        # Check if the user is trying to ban themselves
        if user == ctx.author:
            await ctx.send(embed=create_error_embed("Error", "You cannot ban yourself."))
            return
            
        # Check if the user is trying to ban someone with a higher role
        if user.top_role >= ctx.author.top_role:
            await ctx.send(embed=create_error_embed("Error", "You cannot ban someone with a higher or equal role."))
            return
            
        # Validate delete_days
        delete_days = max(0, min(7, delete_days))  # Clamp between 0 and 7
            
        try:
            await user.ban(reason=f"Banned by {ctx.author}: {reason}", delete_message_days=delete_days)
            logger.info(f"User {user} was banned by {ctx.author} for reason: {reason}")
            
            embed = create_embed(
                "🔨 User Banned",
                f"{user.mention} has been banned from the server.\nReason: {reason or 'No reason provided'}",
                color=0xF04747
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to ban this user."))
        except Exception as e:
            logger.error(f"Error banning user: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to ban the user."))
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_days="Number of days of messages to delete (0-7)"
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = None, delete_days: int = 1):
        """Ban a user from the server"""
        # Check if the bot can ban members
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to ban members."),
                ephemeral=True
            )
            return

        # Check if the user is trying to ban themselves
        if user == interaction.user:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot ban yourself."),
                ephemeral=True
            )
            return

        # Check if the user is trying to ban someone with a higher role
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot ban someone with a higher or equal role."),
                ephemeral=True
            )
            return

        # Validate delete_days
        delete_days = max(0, min(7, delete_days))  # Clamp between 0 and 7

        try:
            await user.ban(reason=f"Banned by {interaction.user}: {reason}", delete_message_days=delete_days)
            logger.info(f"User {user} was banned by {interaction.user} for reason: {reason}")

            embed = create_embed(
                "🔨 User Banned",
                f"{user.mention} has been banned from the server.\nReason: {reason or 'No reason provided'}",
                color=0xF04747
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to ban this user."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error banning user: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to ban the user."),
                ephemeral=True
            )

    @commands.command(name="unban")
    @commands.check_any(commands.has_permissions(ban_members=True), PermissionChecks.is_mod()) 
    async def unban_prefix(self, ctx, user_id: str, *, reason: str = None):
        """Unban a user from the server (prefix command)
        Usage: !unban user_id [reason]"""
        try:
            # Convert user_id to integer
            user_id = int(user_id)
            banned_users = await ctx.guild.bans()
            
            user_to_unban = None
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    user_to_unban = ban_entry.user
                    break
                    
            if user_to_unban is None:
                await ctx.send(embed=create_error_embed("Error", "This user is not banned."))
                return
                
            await ctx.guild.unban(user_to_unban, reason=f"Unbanned by {ctx.author}: {reason}")
            logger.info(f"User {user_to_unban} was unbanned by {ctx.author} for reason: {reason}")
            
            embed = create_embed(
                "🔓 User Unbanned",
                f"{user_to_unban.mention} has been unbanned from the server.\nReason: {reason or 'No reason provided'}",
                color=0x43B581
            )
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send(embed=create_error_embed("Error", "Invalid user ID provided."))
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to unban users."))
        except Exception as e:
            logger.error(f"Error unbanning user: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to unban the user."))
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for the unban"
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        """Unban a user from the server"""
        try:
            # Convert user_id to integer
            user_id = int(user_id)
            banned_users = await interaction.guild.bans()

            user_to_unban = None
            for ban_entry in banned_users:
                if ban_entry.user.id == user_id:
                    user_to_unban = ban_entry.user
                    break

            if user_to_unban is None:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "This user is not banned."),
                    ephemeral=True
                )
                return

            await interaction.guild.unban(user_to_unban, reason=f"Unbanned by {interaction.user}: {reason}")
            logger.info(f"User {user_to_unban} was unbanned by {interaction.user} for reason: {reason}")

            embed = create_embed(
                "🔓 User Unbanned",
                f"{user_to_unban.mention} has been unbanned from the server.\nReason: {reason or 'No reason provided'}",
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed)

        except ValueError:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Invalid user ID provided."),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to unban users."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error unbanning user: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to unban the user."),
                ephemeral=True
            )

    @commands.command(name="timeout")
    @commands.check_any(commands.has_permissions(moderate_members=True), commands.is_owner())
    async def timeout_prefix(self, ctx, user: discord.Member, duration: int, *, reason: str = None):
        """Timeout (mute) a user for a specified duration (prefix command)"""
        # Check if the bot can timeout members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to timeout members."))
            return
            
        # Check if the user is trying to timeout themselves
        if user == ctx.author:
            await ctx.send(embed=create_error_embed("Error", "You cannot timeout yourself."))
            return
            
        # Check if the user is trying to timeout someone with a higher role
        if user.top_role >= ctx.author.top_role:
            await ctx.send(embed=create_error_embed("Error", "You cannot timeout someone with a higher or equal role."))
            return
            
        try:
            # Convert duration to timedelta (max 28 days)
            duration = min(duration, 40320)  # 40320 minutes = 28 days
            timeout_duration = timedelta(minutes=duration)
            
            await user.timeout(timeout_duration, reason=f"Timed out by {ctx.author}: {reason}")
            logger.info(f"User {user} was timed out by {ctx.author} for {duration} minutes. Reason: {reason}")
            
            embed = create_embed(
                "🔇 User Timed Out",
                f"{user.mention} has been timed out for {duration} minutes.\nReason: {reason or 'No reason provided'}",
                color=0xF04747
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to timeout this user."))
        except Exception as e:
            logger.error(f"Error timing out user: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to timeout the user."))
    
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = None):
        """Timeout (mute) a user for a specified duration"""
        # Check if the bot can timeout members
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to timeout members."),
                ephemeral=True
            )
            return

        # Check if the user is trying to timeout themselves
        if user == interaction.user:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot timeout yourself."),
                ephemeral=True
            )
            return

        # Check if the user is trying to timeout someone with a higher role
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot timeout someone with a higher or equal role."),
                ephemeral=True
            )
            return

        try:
            # Convert duration to timedelta (max 28 days)
            duration = min(duration, 40320)  # 40320 minutes = 28 days
            timeout_duration = timedelta(minutes=duration)

            await user.timeout(timeout_duration, reason=f"Timed out by {interaction.user}: {reason}")
            logger.info(f"User {user} was timed out by {interaction.user} for {duration} minutes. Reason: {reason}")

            embed = create_embed(
                "🔇 User Timed Out",
                f"{user.mention} has been timed out for {duration} minutes.\nReason: {reason or 'No reason provided'}",
                color=0xF04747
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to timeout this user."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error timing out user: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to timeout the user."),
                ephemeral=True
            )

    @commands.command(name="undokick")
    @commands.check_any(commands.has_permissions(kick_members=True), PermissionChecks.is_mod())
    async def undokick_prefix(self, ctx, *, reason: str = None):
        """Invite back the last kicked user (prefix command)"""
        # Check if the bot can create invites
        if not ctx.guild.me.guild_permissions.create_instant_invite:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to create invites."))
            return
            
        # Check if there's a record of a recently kicked user
        kick_key = f"kick_{ctx.guild.id}"
        if kick_key not in self.recent_actions:
            await ctx.send(embed=create_error_embed("Error", "I don't have any record of recently kicked users."))
            return
            
        user_info = self.recent_actions[kick_key]
        
        # Don't allow undoing kicks by other moderators unless you're an admin
        if user_info["kicked_by"] != ctx.author.id and not is_admin(ctx.author) and not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed(
                "Error", 
                "You cannot undo kicks performed by other moderators unless you're an admin."
            ))
            return
            
        try:
            # Create an invite
            invite = await ctx.channel.create_invite(
                max_age=86400,  # 24 hours in seconds
                max_uses=1,     # One-time use
                reason=f"Undo kick for {user_info['user_name']} by {ctx.author}"
            )
            
            embed = create_embed(
                "🔄 Kick Undone",
                f"An invite has been created for {user_info['user_name']} to rejoin the server.\n\n"
                f"**Invite Link:** {invite.url}\n"
                f"This invite will expire in 24 hours and can only be used once.\n\n"
                f"**Original Kick Reason:** {user_info['reason'] or 'No reason provided'}\n"
                f"**Undo Reason:** {reason or 'No reason provided'}",
                color=0x43B581
            )
            await ctx.send(embed=embed)
            
            # Remove the record to prevent duplicate undos
            del self.recent_actions[kick_key]
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to create invites."))
        except Exception as e:
            logger.error(f"Error undoing kick: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to undo the kick."))
    
    @app_commands.command(name="undokick", description="Invite back the last kicked user")
    @app_commands.describe(
        reason="Reason for undoing the kick"
    )
    @app_commands.default_permissions(kick_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def undokick(self, interaction: discord.Interaction, reason: str = None):
        """Invite back the last kicked user"""
        # Check if the bot can create invites
        if not interaction.guild.me.guild_permissions.create_instant_invite:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to create invites."),
                ephemeral=True
            )
            return
            
        # Check if there's a record of a recently kicked user
        kick_key = f"kick_{interaction.guild.id}"
        if kick_key not in self.recent_actions:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have any record of recently kicked users."),
                ephemeral=True
            )
            return
            
        user_info = self.recent_actions[kick_key]
        
        # Don't allow undoing kicks by other moderators unless you're an admin
        if user_info["kicked_by"] != interaction.user.id and not is_admin(interaction.user) and not is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error", 
                    "You cannot undo kicks performed by other moderators unless you're an admin."
                ),
                ephemeral=True
            )
            return
            
        try:
            # Create an invite
            invite = await interaction.channel.create_invite(
                max_age=86400,  # 24 hours in seconds
                max_uses=1,     # One-time use
                reason=f"Undo kick for {user_info['user_name']} by {interaction.user}"
            )
            
            embed = create_embed(
                "🔄 Kick Undone",
                f"An invite has been created for {user_info['user_name']} to rejoin the server.\n\n"
                f"**Invite Link:** {invite.url}\n"
                f"This invite will expire in 24 hours and can only be used once.\n\n"
                f"**Original Kick Reason:** {user_info['reason'] or 'No reason provided'}\n"
                f"**Undo Reason:** {reason or 'No reason provided'}",
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed)
            
            # Remove the record to prevent duplicate undos
            del self.recent_actions[kick_key]
            
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to create invites."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error undoing kick: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to undo the kick."),
                ephemeral=True
            )
    
    @commands.command(name="untimeout")
    @commands.check_any(commands.has_permissions(moderate_members=True), PermissionChecks.is_mod())
    async def untimeout_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Remove timeout from a user (prefix command)"""
        # Check if the bot can moderate members
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage timeouts."))
            return
            
        # Check if the user is trying to untimeout themselves
        if user == ctx.author:
            await ctx.send(embed=create_error_embed("Error", "You don't need to remove a timeout from yourself."))
            return
            
        # Check if the user is trying to untimeout someone with a higher role
        if user.top_role >= ctx.author.top_role and not is_bot_owner(ctx.author.id):
            await ctx.send(embed=create_error_embed("Error", "You cannot remove a timeout from someone with a higher or equal role."))
            return
            
        try:
            # Remove timeout by setting duration to None
            await user.timeout(None, reason=f"Timeout removed by {ctx.author}: {reason}")
            logger.info(f"Timeout removed from user {user} by {ctx.author}. Reason: {reason}")
            
            embed = create_embed(
                "🔊 Timeout Removed",
                f"Timeout has been removed from {user.mention}.\nReason: {reason or 'No reason provided'}",
                color=0x43B581
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to remove timeouts from this user."))
        except Exception as e:
            logger.error(f"Error removing timeout: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to remove the timeout."))
    
    @app_commands.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.describe(
        user="The user to remove timeout from",
        reason="Reason for removing the timeout"
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def untimeout(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Remove timeout from a user"""
        # Check if the bot can moderate members
        if not interaction.guild.me.guild_permissions.moderate_members:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to manage timeouts."),
                ephemeral=True
            )
            return

        # Check if the user is trying to untimeout themselves
        if user == interaction.user:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You don't need to remove a timeout from yourself."),
                ephemeral=True
            )
            return

        # Check if the user is trying to untimeout someone with a higher role
        if user.top_role >= interaction.user.top_role and not is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You cannot remove a timeout from someone with a higher or equal role."),
                ephemeral=True
            )
            return

        try:
            # Remove timeout by setting duration to None
            await user.timeout(None, reason=f"Timeout removed by {interaction.user}: {reason}")
            logger.info(f"Timeout removed from user {user} by {interaction.user}. Reason: {reason}")

            embed = create_embed(
                "🔊 Timeout Removed",
                f"Timeout has been removed from {user.mention}.\nReason: {reason or 'No reason provided'}",
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to remove timeouts from this user."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error removing timeout: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to remove the timeout."),
                ephemeral=True
            )
    
    @commands.command(name="clear")
    @commands.check_any(commands.has_permissions(manage_messages=True), PermissionChecks.is_mod())
    async def clear_prefix(self, ctx, *args):
        """Clear messages from the channel (prefix command)
        Usage: !clear amount [@user] or !clear @user amount or !clear all"""
        # Prevent processing of commands from DMs
        if not ctx.guild:
            return
            
        # Check for permissions first
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to delete messages."), delete_after=10)
            return
        
        # Handle flexible parameter ordering
        amount = None
        user = None
        all_messages = False
        
        if len(args) == 0:
            await ctx.send(embed=create_error_embed("Error", "Please provide the number of messages to delete or 'all' to clear the entire channel."), delete_after=10)
            return
        
        # Check if the first argument is 'all'
        if args[0].lower() == 'all':
            all_messages = True
            
            # Check if there's a user mentioned after 'all'
            if len(args) > 1:
                for arg in args[1:]:
                    # Check if argument is a member mention
                    if isinstance(arg, str) and (arg.startswith('<@') or arg.startswith('<@!')):
                        try:
                            # Extract user ID from mention
                            user_id = ''.join(filter(str.isdigit, arg))
                            user = ctx.guild.get_member(int(user_id))
                            if not user:
                                await ctx.send(embed=create_error_embed("Error", f"Member not found from mention: {arg}"), delete_after=10)
                                return
                            break
                        except (ValueError, AttributeError):
                            await ctx.send(embed=create_error_embed("Error", f"Invalid user mention: {arg}"), delete_after=10)
                            return
                    # Check if argument is a numeric user ID
                    elif isinstance(arg, str) and arg.isdigit() and len(arg) > 8:  # User IDs are typically at least 17 digits
                        try:
                            user_id = int(arg)
                            user = ctx.guild.get_member(user_id)
                            if not user:
                                await ctx.send(embed=create_error_embed("Error", f"Member not found with ID: {arg}"), delete_after=10)
                                return
                            break
                        except (ValueError, AttributeError):
                            await ctx.send(embed=create_error_embed("Error", f"Invalid user ID: {arg}"), delete_after=10)
                            return
            
            # Customize confirmation message based on whether a user was mentioned
            if user:
                confirmation_message = f"You are about to delete **ALL** messages from **{user.display_name}** in this channel. This action cannot be undone."
            else:
                confirmation_message = "You are about to delete **ALL** messages in this channel. This action cannot be undone."
                
            # Show a confirmation before proceeding with deletion
            confirmation_embed = create_embed(
                "⚠️ Confirm Clear All",
                confirmation_message + "\n\nReply with `yes` within 30 seconds to confirm, or `no` to cancel.",
                color=0xFFCC00
            )
            confirm_msg = await ctx.send(embed=confirmation_embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']
            
            try:
                reply = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                # Clean up the confirmation messages
                try:
                    await confirm_msg.delete()
                    await reply.delete()
                except:
                    pass
                
                if reply.content.lower() != 'yes':
                    await ctx.send(embed=create_embed("Operation Cancelled", "Clear all operation has been cancelled.", color=0x43B581), delete_after=10)
                    return
                    
            except asyncio.TimeoutError:
                # If the user doesn't respond in time
                try:
                    await confirm_msg.delete()
                except:
                    pass
                    
                await ctx.send(embed=create_error_embed("Operation Cancelled", "Clear all operation has been cancelled due to timeout."), delete_after=10)
                return
                
        else:
            # Process regular clear command arguments
            for arg in args:
                # Check if argument is a member mention
                if isinstance(arg, str) and (arg.startswith('<@') or arg.startswith('<@!')):
                    try:
                        # Extract user ID from mention
                        user_id = ''.join(filter(str.isdigit, arg))
                        user = ctx.guild.get_member(int(user_id))
                        if not user:
                            await ctx.send(embed=create_error_embed("Error", f"Member not found from mention: {arg}"), delete_after=10)
                            return
                    except (ValueError, AttributeError):
                        await ctx.send(embed=create_error_embed("Error", f"Invalid user mention: {arg}"), delete_after=10)
                        return
                # Check if argument is a numeric user ID
                elif isinstance(arg, str) and arg.isdigit() and len(arg) > 8:  # User IDs are typically at least 17 digits
                    try:
                        user_id = int(arg)
                        user = ctx.guild.get_member(user_id)
                        if not user:
                            await ctx.send(embed=create_error_embed("Error", f"Member not found with ID: {arg}"), delete_after=10)
                            return
                    except (ValueError, AttributeError):
                        await ctx.send(embed=create_error_embed("Error", f"Invalid user ID: {arg}"), delete_after=10)
                        return
                # Try to parse as amount
                else:
                    try:
                        amount = int(arg)
                    except (ValueError, TypeError):
                        # Check if this might be a username instead of an amount
                        if isinstance(arg, str):
                            potential_user = None
                            for member in ctx.guild.members:
                                if arg.lower() in member.name.lower() or (member.nick and arg.lower() in member.nick.lower()):
                                    potential_user = member
                                    break
                            
                            if potential_user:
                                user = potential_user
                            else:
                                await ctx.send(embed=create_error_embed("Error", f"Invalid amount: {arg}. Please provide a valid number."), delete_after=10)
                                return
                        else:
                            await ctx.send(embed=create_error_embed("Error", "Please provide a valid number of messages to delete."), delete_after=10)
                            return
            
            # If amount is still None, there was no valid number provided
            if amount is None:
                await ctx.send(embed=create_error_embed("Error", "Please provide a valid number of messages to delete."), delete_after=10)
                return
                
            # Limit amount to 1-100
            amount = max(1, min(100, amount))
        
        # Attempt to delete the original command message
        try:
            await ctx.message.delete()
        except:
            pass
        
        try:
            total_deleted = 0
            
            if all_messages:
                # Handle "clear all" which will delete all messages in the channel in batches
                # Customize progress message based on whether we're deleting all messages or just from a specific user
                if user:
                    progress_message = f"Deleting all messages from **{user.display_name}** in this channel. This may take some time..."
                else:
                    progress_message = "Deleting all messages in this channel. This may take some time..."
                
                # Show a "working" message that will be updated with progress
                progress_embed = create_embed(
                    "🗑️ Clearing Channel",
                    progress_message,
                    color=0x43B581
                )
                progress_msg = await ctx.send(embed=progress_embed)
                
                # Delete messages in batches of 100 (Discord API limitation)
                batch_size = 100
                while True:
                    def check_message(message):
                        # Don't delete the progress message and filter by user if specified
                        if message.id == progress_msg.id:
                            return False
                        if user:
                            return message.author.id == user.id
                        return True
                        
                    # Get messages in batches
                    deleted = await ctx.channel.purge(limit=batch_size, check=check_message)
                    total_deleted += len(deleted)
                    
                    # Update progress message every 500 messages
                    if total_deleted % 500 == 0 and deleted:
                        try:
                            await progress_msg.edit(embed=create_embed(
                                "🗑️ Clearing Channel",
                                f"Deleted {total_deleted} messages so far...",
                                color=0x43B581
                            ))
                        except:
                            # If the progress message was deleted, create a new one
                            progress_msg = await ctx.send(embed=create_embed(
                                "🗑️ Clearing Channel",
                                f"Deleted {total_deleted} messages so far...",
                                color=0x43B581
                            ))
                    
                    # If we deleted fewer messages than the batch size, we're done
                    if len(deleted) < batch_size:
                        break
                
                # Delete the progress message now that we're done
                try:
                    await progress_msg.delete()
                except:
                    pass
                
                # Send final confirmation
                if total_deleted > 0:
                    confirm_embed = create_embed(
                        "🗑️ Channel Cleared",
                        f"Successfully deleted {total_deleted} messages from this channel.",
                        color=0x43B581
                    )
                    confirm_message = await ctx.send(embed=confirm_embed)
                else:
                    confirm_embed = create_embed(
                        "🗑️ Channel Cleared",
                        "No messages were found to delete.",
                        color=0x43B581
                    )
                    confirm_message = await ctx.send(embed=confirm_embed)
                
                # Delete confirmation after 5 seconds
                await asyncio.sleep(5)
                try:
                    await confirm_message.delete()
                except:
                    pass
            else:
                # Regular purge for specific amount
                def check_message(message):
                    return user is None or message.author == user
                    
                deleted = await ctx.channel.purge(
                    limit=amount,  # No need for +1 since we already deleted the command message
                    check=check_message
                )
                
                # Count the deleted messages
                total_deleted = len(deleted)
            
            # Only if we actually deleted messages and haven't already sent a confirmation for "clear all"
            if total_deleted > 0 and not all_messages:
                user_text = f" from {user.mention}" if user else ""
                embed = create_embed(
                    "🗑️ Messages Cleared",
                    f"Deleted {total_deleted} messages{user_text}.",
                    color=0x43B581
                )
                confirm_message = await ctx.send(embed=embed)
                
                # Delete confirmation after 5 seconds
                await asyncio.sleep(5)
                try:
                    await confirm_message.delete()
                except:
                    pass
                
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to delete messages."), delete_after=10)
        except Exception as e:
            logger.error(f"Error clearing messages: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", f"An error occurred while trying to clear messages: {str(e)}"), delete_after=10)
    
    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100, or 'all' to clear the entire channel)",
        user="Only delete messages from this user"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def clear(self, interaction: discord.Interaction, amount: str, user: discord.Member = None):
        """Clear messages from the channel"""
        # Prevent processing if not in a guild
        if not interaction.guild:
            return
            
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to delete messages."),
                ephemeral=True
            )
            return

        all_messages = False
        delete_count = 0

        # Check if amount is "all"
        if amount.lower() == "all":
            all_messages = True
            
            # Customize confirmation message based on whether a user was specified
            if user:
                confirmation_message = f"You are about to delete **ALL** messages from **{user.display_name}** in this channel. This action cannot be undone."
            else:
                confirmation_message = "You are about to delete **ALL** messages in this channel. This action cannot be undone."
                
            # Confirm with a button UI
            confirm_embed = create_embed(
                "⚠️ Confirm Clear All",
                confirmation_message,
                color=0xFFCC00
            )
            
            # Create confirm/cancel buttons
            confirm_view = discord.ui.View(timeout=30)
            confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Confirm", custom_id="confirm")
            cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="Cancel", custom_id="cancel")
            
            async def confirm_callback(btn_interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("You cannot interact with this button.", ephemeral=True)
                    return
                    
                # User confirmed, proceed with deletion
                # Customize progress message based on whether we're deleting all messages or just from a specific user
                if user:
                    progress_message = f"Deleting all messages from **{user.display_name}** in this channel. This may take some time..."
                else:
                    progress_message = "Deleting all messages in this channel. This may take some time..."
                    
                await btn_interaction.response.edit_message(
                    embed=create_embed("Processing", progress_message, color=0x5865F2),
                    view=None
                )
                
                # Use defer to prevent timeouts during deletion process
                total_deleted = 0
                
                # Delete messages in batches of 100 (Discord API limitation)
                batch_size = 100
                progress_update_count = 0
                
                while True:
                    # Create a check function to filter messages
                    def check_message(message):
                        if user:
                            return message.author.id == user.id
                        return True
                        
                    # Get messages in batches
                    deleted = await interaction.channel.purge(limit=batch_size, check=check_message)
                    total_deleted += len(deleted)
                    progress_update_count += 1
                    
                    # Update progress message occasionally
                    if progress_update_count % 5 == 0 and deleted:
                        try:
                            await btn_interaction.edit_original_response(
                                embed=create_embed(
                                    "🗑️ Clearing Channel",
                                    f"Deleted {total_deleted} messages so far...",
                                    color=0x43B581
                                )
                            )
                        except:
                            pass
                    
                    # If we deleted fewer messages than the batch size, we're done
                    if len(deleted) < batch_size:
                        break
                
                # Send final confirmation with user information if a user was specified
                if user:
                    confirmation_message = f"Successfully deleted {total_deleted} messages from **{user.display_name}** in this channel."
                else:
                    confirmation_message = f"Successfully deleted {total_deleted} messages from this channel."
                    
                await btn_interaction.edit_original_response(
                    embed=create_embed(
                        "🗑️ Channel Cleared",
                        confirmation_message,
                        color=0x43B581
                    )
                )
                
            async def cancel_callback(btn_interaction):
                if btn_interaction.user.id != interaction.user.id:
                    await btn_interaction.response.send_message("You cannot interact with this button.", ephemeral=True)
                    return
                    
                # User cancelled
                await btn_interaction.response.edit_message(
                    embed=create_embed("Operation Cancelled", "Clear all operation has been cancelled.", color=0x43B581),
                    view=None
                )
            
            # Set the callbacks
            confirm_button.callback = confirm_callback
            cancel_button.callback = cancel_callback
            
            # Add buttons to view
            confirm_view.add_item(confirm_button)
            confirm_view.add_item(cancel_button)
            
            # Send the confirmation message
            await interaction.response.send_message(embed=confirm_embed, view=confirm_view)
            return
                
        else:
            # Try to convert to integer
            try:
                delete_count = int(amount)
                # Limit amount to 1-100
                delete_count = max(1, min(100, delete_count))
            except ValueError:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "Please provide a valid number of messages to delete or 'all' to clear the entire channel."),
                    ephemeral=True
                )
                return

            try:
                # Use defer to prevent timeouts during purge operations
                await interaction.response.defer(ephemeral=True)

                def check_message(message):
                    return user is None or message.author == user

                # Perform the purge operation
                deleted = await interaction.channel.purge(
                    limit=delete_count,
                    check=check_message,
                    before=interaction.created_at
                )

                # Only send a confirmation if messages were actually deleted
                actual_count = len(deleted)
                if actual_count > 0:
                    user_text = f" from {user.mention}" if user else ""
                    embed = create_embed(
                        "🗑️ Messages Cleared",
                        f"Deleted {actual_count} messages{user_text}.",
                        color=0x43B581
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(
                        embed=create_embed("No Messages", "No messages were found matching the criteria.", color=0x43B581),
                        ephemeral=True
                    )

            except discord.Forbidden:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "I don't have permission to delete messages."),
                    ephemeral=True
                )
            except Exception as e:
                logger.error(f"Error clearing messages: {str(e)}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"An error occurred while trying to clear messages: {str(e)}"),
                    ephemeral=True
                )

    @commands.command(name="slowmode")
    @commands.check_any(commands.has_permissions(manage_channels=True), PermissionChecks.is_mod())
    async def slowmode_prefix(self, ctx, delay: int, *, reason: str = None):
        """Set the slowmode delay for the channel (prefix command)
        Usage: !slowmode delay [reason]"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage channel settings."))
            return
            
        # Limit delay to 0-21600 (6 hours)
        delay = max(0, min(21600, delay))
        
        try:
            # Edit channel first
            await ctx.channel.edit(
                slowmode_delay=delay,
                reason=f"Slowmode changed by {ctx.author}: {reason}"
            )
            
            # Then respond
            if delay == 0:
                description = "Slowmode has been disabled."
            else:
                description = f"Slowmode set to {delay} seconds."
                if reason:
                    description += f"\nReason: {reason}"
                    
            embed = create_embed(
                "⏱️ Slowmode Updated",
                description,
                color=0x43B581
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to change slowmode."))
        except Exception as e:
            logger.error(f"Error setting slowmode: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to set slowmode."))
    
    @app_commands.command(name="slowmode", description="Set the slowmode delay for this channel")
    @app_commands.describe(
        delay="Delay in seconds (0 to disable, max 21600)",
        reason="Reason for changing slowmode"
    )
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def slowmode(self, interaction: discord.Interaction, delay: int, reason: str = None):
        """Set the slowmode delay for the channel"""
        if not interaction.channel.permissions_for(interaction.guild.me).manage_channels:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to manage channel settings."),
                ephemeral=True
            )
            return

        # Limit delay to 0-21600 (6 hours)
        delay = max(0, min(21600, delay))

        try:
            # Edit channel first
            await interaction.channel.edit(
                slowmode_delay=delay,
                reason=f"Slowmode changed by {interaction.user}: {reason}"
            )

            # Then respond to the interaction
            if delay == 0:
                description = "Slowmode has been disabled."
            else:
                description = f"Slowmode set to {delay} seconds."
                if reason:
                    description += f"\nReason: {reason}"

            embed = create_embed(
                "⏱️ Slowmode Updated",
                description,
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to change slowmode."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error setting slowmode: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while trying to set slowmode."),
                ephemeral=True
            )

    @commands.command(name="serverinfo")
    @commands.check_any(commands.has_permissions(manage_messages=True), PermissionChecks.is_mod())
    async def serverinfo_prefix(self, ctx):
        """Display server information (prefix command)"""
        guild = ctx.guild
        
        # Get role and channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)
        
        # Get member counts
        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
        bot_count = sum(1 for m in guild.members if m.bot)
        
        # Create embed
        embed = create_embed(
            f"ℹ️ Server Information - {guild.name}",
            "",
            color=0x43B581
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)
        
        embed.add_field(name="Members", value=f"Total: {total_members}\nOnline: {online_members}\nBots: {bot_count}", inline=True)
        embed.add_field(name="Channels", value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}", inline=True)
        embed.add_field(name="Roles", value=str(roles), inline=True)
        
        if guild.premium_subscription_count:
            embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
            embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
            
        await ctx.send(embed=embed)
    
    @commands.command(name="modhistory")
    @commands.check_any(commands.has_permissions(moderate_members=True), PermissionChecks.is_mod())
    async def modhistory_prefix(self, ctx):
        """View recent moderation actions that can be undone (prefix command)"""
        if not self.recent_actions:
            await ctx.send(embed=create_error_embed("No Actions", "There are no recent moderation actions that can be undone."))
            return
            
        # Create a nicely formatted embed with all recent actions
        embed = create_embed(
            "📜 Recent Moderation Actions",
            "Here are the recent moderation actions that can be undone:",
            color=0x5865F2
        )
        
        for key, action in self.recent_actions.items():
            if key.startswith("kick_"):
                guild_id = key.split("_")[1]
                guild = self.bot.get_guild(int(guild_id))
                guild_name = guild.name if guild else "Unknown Server"
                
                # Calculate time since action
                time_since = discord.utils.utcnow() - action["kicked_at"]
                minutes = int(time_since.total_seconds() / 60)
                time_str = f"{minutes} minutes ago" if minutes > 0 else "just now"
                
                # Get moderator who performed the action
                mod = ctx.guild.get_member(action["kicked_by"])
                mod_name = mod.display_name if mod else "Unknown Moderator"
                
                embed.add_field(
                    name=f"Kick in {guild_name}",
                    value=f"**User:** {action['user_name']}\n"
                          f"**Reason:** {action['reason'] or 'No reason provided'}\n"
                          f"**By:** {mod_name}\n"
                          f"**When:** {time_str}\n"
                          f"**Command to Undo:** `!undokick`",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @app_commands.command(name="modhistory", description="View recent moderation actions that can be undone")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def modhistory(self, interaction: discord.Interaction):
        """View recent moderation actions that can be undone"""
        if not self.recent_actions:
            await interaction.response.send_message(
                embed=create_error_embed("No Actions", "There are no recent moderation actions that can be undone."),
                ephemeral=True
            )
            return
            
        # Create a nicely formatted embed with all recent actions
        embed = create_embed(
            "📜 Recent Moderation Actions",
            "Here are the recent moderation actions that can be undone:",
            color=0x5865F2
        )
        
        for key, action in self.recent_actions.items():
            if key.startswith("kick_"):
                guild_id = key.split("_")[1]
                guild = self.bot.get_guild(int(guild_id))
                guild_name = guild.name if guild else "Unknown Server"
                
                # Calculate time since action
                time_since = discord.utils.utcnow() - action["kicked_at"]
                minutes = int(time_since.total_seconds() / 60)
                time_str = f"{minutes} minutes ago" if minutes > 0 else "just now"
                
                # Get moderator who performed the action
                mod = interaction.guild.get_member(action["kicked_by"])
                mod_name = mod.display_name if mod else "Unknown Moderator"
                
                embed.add_field(
                    name=f"Kick in {guild_name}",
                    value=f"**User:** {action['user_name']}\n"
                          f"**Reason:** {action['reason'] or 'No reason provided'}\n"
                          f"**By:** {mod_name}\n"
                          f"**When:** {time_str}\n"
                          f"**Command to Undo:** `/undokick`",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="serverinfo", description="Show information about the server")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def serverinfo(self, interaction: discord.Interaction):
        """Display server information"""
        guild = interaction.guild

        # Get role and channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles)

        # Get member counts
        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
        bot_count = sum(1 for m in guild.members if m.bot)

        # Create embed
        embed = create_embed(
            f"ℹ️ Server Information - {guild.name}",
            "",
            color=0x43B581
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=True)

        embed.add_field(name="Members", value=f"Total: {total_members}\nOnline: {online_members}\nBots: {bot_count}", inline=True)
        embed.add_field(name="Channels", value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}", inline=True)
        embed.add_field(name="Roles", value=str(roles), inline=True)

        if guild.premium_subscription_count:
            embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
            embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)

        await interaction.response.send_message(embed=embed)

    @commands.command(name="announce")
    @commands.check_any(commands.has_permissions(manage_messages=True), PermissionChecks.is_mod())
    async def announce_prefix(self, ctx, channel: discord.TextChannel, *, message: str):
        """Send an announcement to a channel (prefix command)
        Usage: !announce #channel Your announcement message"""
        try:
            # Check if bot has permission to send messages in the target channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send(embed=create_error_embed("Error", "I don't have permission to send messages in that channel."))
                return
                
            await channel.send(message)
            
            embed = create_embed(
                "📢 Announcement Sent",
                f"Successfully sent announcement to {channel.mention}",
                color=0x43B581
            )
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to send announcements."))
        except Exception as e:
            logger.error(f"Error sending announcement: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while sending the announcement."))
    
    @app_commands.command(name="announce", description="Send an announcement to a channel")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        message="The announcement message"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, *, message: str):
        """Send an announcement to a specified channel"""
        try:
            # Check if bot has permission to send messages in the target channel
            if not channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "I don't have permission to send messages in that channel."),
                    ephemeral=True
                )
                return

            await channel.send(message)

            embed = create_embed(
                "📢 Announcement Sent",
                f"Successfully sent announcement to {channel.mention}",
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to send announcements."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error sending announcement: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while sending the announcement."),
                ephemeral=True
            )

    @commands.command(name="embedannounce")
    @commands.check_any(commands.has_permissions(manage_messages=True), PermissionChecks.is_mod())
    async def embedannounce_prefix(self, ctx, channel: discord.TextChannel, title: str, *, content: str):
        """Send a formatted embed announcement (prefix command)
        Usage: !embedannounce #channel "Title" Content of the announcement
        
        Note: To specify a custom color, add --color=#HEX at the end
        Example: !embedannounce #channel "Welcome!" This is our server --color=#FF0000
        """
        try:
            # Check if bot has permission to send messages in the target channel
            if not channel.permissions_for(ctx.guild.me).send_messages:
                await ctx.send(embed=create_error_embed("Error", "I don't have permission to send messages in that channel."))
                return
            
            # Extract color from content if present
            color_match = re.search(r'--color=(#[0-9A-Fa-f]{6})\s*$', content)
            embed_color = 0x43B581  # Default green color
            
            if color_match:
                try:
                    color_hex = color_match.group(1).strip('#')  # Remove # if present
                    embed_color = int(color_hex, 16)
                    # Remove the color part from content
                    content = re.sub(r'--color=#[0-9A-Fa-f]{6}\s*$', '', content).strip()
                except ValueError:
                    await ctx.send(embed=create_error_embed("Error", "Invalid color format. Use hex code like #FF0000"))
                    return
            
            embed = create_embed(title, content, color=embed_color)
            embed.set_footer(text=f"Announcement by {ctx.author.name}")
            
            await channel.send(embed=embed)
            
            confirmation_embed = create_embed(
                "📢 Embed Announcement Sent",
                f"Successfully sent announcement to {channel.mention}",
                color=0x43B581
            )
            await ctx.send(embed=confirmation_embed)
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to send announcements."))
        except Exception as e:
            logger.error(f"Error sending embed announcement: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while sending the announcement."))
    
    @app_commands.command(name="embedannounce", description="Send an embed announcement")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        title="The title of the announcement",
        description="The content of the announcement",
        color="The color of the embed (optional, hex code like #FF0000)"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def embedannounce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        color: str = None
    ):
        """Send a formatted embed announcement"""
        try:
            # Check if bot has permission to send messages in the target channel
            if not channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "I don't have permission to send messages in that channel."),
                    ephemeral=True
                )
                return

            # Convert hex color to discord.Color
            embed_color = 0x43B581  # Default green color
            if color:
                try:
                    color = color.strip("#")  # Remove # if present
                    embed_color = int(color, 16)
                except ValueError:
                    await interaction.response.send_message(
                        embed=create_error_embed("Error", "Invalid color format. Use hex code like #FF0000"),
                        ephemeral=True
                    )
                    return

            embed = create_embed(title, description, color=embed_color)
            embed.set_footer(text=f"Announcement by {interaction.user.name}")

            await channel.send(embed=embed)

            confirmation_embed = create_embed(
                "📢 Embed Announcement Sent",
                f"Successfully sent announcement to {channel.mention}",
                color=0x43B581
            )
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to send announcements."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error sending embed announcement: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while sending the announcement."),
                ephemeral=True
            )

    @commands.command(name="noping")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def noping_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Make a user unpingable (prefix command)
        Usage: !noping @user [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Direct check for bot owner - bypasses ALL permissions
        if ctx.author.id in config.BOT_OWNER_IDS:
            logger.info(f"Bot owner {ctx.author.name} ({ctx.author.id}) bypassing permission checks for noping command")
            # Bot owner can make anyone unpingable - proceed directly
        # Check if the command user has permission to use it on the target
        elif not ctx.author.guild_permissions.administrator:
            # Allow moderators to noping regular users but not other mods or admins
            if user.guild_permissions.kick_members or user.guild_permissions.administrator:
                if user != ctx.author:  # Allow making yourself unpingable
                    await ctx.send(embed=create_error_embed("Error", "You cannot make a moderator or administrator unpingable unless you're an admin."))
                    return
                
        # Check if the user is the bot
        if user.id == self.bot.user.id:
            await ctx.send(embed=create_error_embed("Error", "I cannot make myself unpingable."))
            return

        # Look for an existing No Ping role or create one
        no_ping_role = discord.utils.get(ctx.guild.roles, name="No Ping")
        
        if not no_ping_role:
            try:
                # Create the No Ping role with mentionable set to False
                no_ping_role = await ctx.guild.create_role(
                    name="No Ping",
                    colour=discord.Colour.dark_gray(),
                    mentionable=False,
                    reason="Created for noping command"
                )
                logger.info(f"Created 'No Ping' role in server '{ctx.guild.name}'")
                
                # Move the role above the default role to ensure it takes effect
                positions = {
                    no_ping_role: 1  # Just above the default role
                }
                await ctx.guild.edit_role_positions(positions=positions)
                
            except discord.Forbidden:
                await ctx.send(embed=create_error_embed("Error", "I don't have permission to create roles."))
                return
            except discord.HTTPException as e:
                await ctx.send(embed=create_error_embed("Error", f"Failed to create role: {str(e)}"))
                return
                
        # Assign the No Ping role to the user
        try:
            await user.add_roles(no_ping_role, reason=f"Made unpingable by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="User Made Unpingable",
                description=f"{user.name} can no longer be pinged by regular members.",
                color=discord.Color.blue()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made unpingable by {ctx.author.name} in server '{ctx.guild.name}'")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to assign roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to assign role: {str(e)}"))
            
    @app_commands.command(name="noping", description="Make a user unpingable by regular members")
    @app_commands.default_permissions(manage_roles=True)
    async def noping_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Make a user unpingable by regular members"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Direct check for bot owner - bypasses ALL permissions
        if interaction.user.id in config.BOT_OWNER_IDS:
            logger.info(f"Bot owner {interaction.user.name} ({interaction.user.id}) bypassing permission checks for noping slash command")
            # Bot owner can make anyone unpingable - proceed directly
        # Check if the command user has permission to use it on the target
        elif not interaction.user.guild_permissions.administrator:
            # Allow moderators to noping regular users but not other mods or admins
            if user.guild_permissions.kick_members or user.guild_permissions.administrator:
                if user != interaction.user:  # Allow making yourself unpingable
                    await interaction.response.send_message("You cannot make a moderator or administrator unpingable unless you're an admin.", ephemeral=True)
                    return
                
        # Check if the user is the bot
        if user.id == self.bot.user.id:
            await interaction.response.send_message("I cannot make myself unpingable.", ephemeral=True)
            return

        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)

        # Look for an existing No Ping role or create one
        no_ping_role = discord.utils.get(interaction.guild.roles, name="No Ping")
        
        if not no_ping_role:
            try:
                # Create the No Ping role with mentionable set to False
                no_ping_role = await interaction.guild.create_role(
                    name="No Ping",
                    colour=discord.Colour.dark_gray(),
                    mentionable=False,
                    reason="Created for noping command"
                )
                logger.info(f"Created 'No Ping' role in server '{interaction.guild.name}'")
                
                # Move the role above the default role to ensure it takes effect
                positions = {
                    no_ping_role: 1  # Just above the default role
                }
                await interaction.guild.edit_role_positions(positions=positions)
                
            except discord.Forbidden:
                await interaction.followup.send("I don't have permission to create roles.")
                return
            except discord.HTTPException as e:
                await interaction.followup.send(f"Failed to create role: {str(e)}")
                return
                
        # Assign the No Ping role to the user
        try:
            await user.add_roles(no_ping_role, reason=f"Made unpingable by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="User Made Unpingable",
                description=f"{user.name} can no longer be pinged by regular members.",
                color=discord.Color.blue()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made unpingable by {interaction.user.name} in server '{interaction.guild.name}'")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to assign role: {str(e)}")

    @commands.command(name="allowping")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def allowping_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Make a user pingable again (prefix command)
        Usage: !allowping @user [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Direct check for bot owner - bypasses ALL permissions
        if ctx.author.id in config.BOT_OWNER_IDS:
            logger.info(f"Bot owner {ctx.author.name} ({ctx.author.id}) bypassing permission checks for allowping prefix command")
            # Bot owner can make anyone pingable - proceed directly

        # Find the No Ping role
        no_ping_role = discord.utils.get(ctx.guild.roles, name="No Ping")
        
        if not no_ping_role:
            await ctx.send(embed=create_error_embed("Error", "The No Ping role doesn't exist in this server."))
            return
            
        # Check if the user has the No Ping role
        if no_ping_role not in user.roles:
            await ctx.send(embed=create_error_embed("Error", f"{user.name} is not currently unpingable."))
            return
            
        # Remove the No Ping role
        try:
            await user.remove_roles(no_ping_role, reason=f"Made pingable again by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="User Can Be Pinged Again",
                description=f"{user.name} can now be pinged by members again.",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made pingable again by {ctx.author.name} in server '{ctx.guild.name}'")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to remove roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to remove role: {str(e)}"))

    @app_commands.command(name="allowping", description="Make a user pingable again")
    @app_commands.default_permissions(manage_roles=True)
    async def allowping_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Make a user pingable again"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Direct check for bot owner - bypasses ALL permissions
        if interaction.user.id in config.BOT_OWNER_IDS:
            logger.info(f"Bot owner {interaction.user.name} ({interaction.user.id}) bypassing permission checks for allowping slash command")
            # Bot owner can make anyone pingable - proceed directly

        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)

        # Find the No Ping role
        no_ping_role = discord.utils.get(interaction.guild.roles, name="No Ping")
        
        if not no_ping_role:
            await interaction.followup.send("The No Ping role doesn't exist in this server.")
            return
            
        # Check if the user has the No Ping role
        if no_ping_role not in user.roles:
            await interaction.followup.send(f"{user.name} is not currently unpingable.")
            return
            
        # Remove the No Ping role
        try:
            await user.remove_roles(no_ping_role, reason=f"Made pingable again by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="User Can Be Pinged Again",
                description=f"{user.name} can now be pinged by members again.",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made pingable again by {interaction.user.name} in server '{interaction.guild.name}'")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to remove roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to remove role: {str(e)}")

    @commands.command(name="prisoner")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def prisoner_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Assign the prisoner role to a user (prefix command)
        Usage: !prisoner @user [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Check if the prisoner role is configured
        if self.prisoner_role_id == 0:
            await ctx.send(embed=create_error_embed("Error", "The prisoner role ID has not been configured yet."))
            return
            
        # Get the prisoner role by ID
        prisoner_role = ctx.guild.get_role(self.prisoner_role_id)
        if not prisoner_role:
            await ctx.send(embed=create_error_embed("Error", "The prisoner role doesn't exist in this server."))
            return
            
        # Check if the user is trying to assign a role to a user with higher permissions
        if user.top_role >= ctx.author.top_role and ctx.author.id not in config.BOT_OWNER_IDS:
            await ctx.send(embed=create_error_embed("Error", "You cannot assign roles to users with higher or equal roles."))
            return
            
        # Check if the user already has the prisoner role
        if prisoner_role in user.roles:
            await ctx.send(embed=create_error_embed("Error", f"{user.name} is already a prisoner."))
            return
            
        # Store the user's current roles to remember them
        current_roles = [role for role in user.roles if role.id != user.guild.id]  # Exclude @everyone
        stored_roles = [role.id for role in current_roles]
        
        # Store the roles in recent_actions so they can be restored when unprisoned
        role_info = {
            "user_id": user.id,
            "roles": stored_roles,
            "imprisoned_by": ctx.author.id,
            "imprisoned_at": discord.utils.utcnow().isoformat()
        }
        self.recent_actions[f"prison_roles_{user.id}_{ctx.guild.id}"] = role_info
        
        # Remove all current roles and add prisoner role
        try:
            # First remove existing roles
            if current_roles:
                await user.remove_roles(*current_roles, reason=f"Roles removed for imprisonment by {ctx.author.name}")
            
            # Then add the prisoner role
            await user.add_roles(prisoner_role, reason=f"Made prisoner by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Try to move the user to the jail channel if they are in a voice channel
            jail_channel_id = 1356447400255819929  # ID of the jail channel
            jail_channel = ctx.guild.get_channel(jail_channel_id)
            
            moved_from = None
            if jail_channel and user.voice and user.voice.channel:
                moved_from = user.voice.channel.name
                try:
                    await user.move_to(jail_channel, reason=f"Moved to jail by {ctx.author.name}")
                    logger.info(f"Moved {user.name} from {moved_from} to jail channel")
                except Exception as e:
                    logger.error(f"Failed to move {user.name} to jail channel: {str(e)}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Prisoner Role Assigned",
                description=f"{user.mention} has been given the prisoner role and stripped of all other roles.",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            embed.add_field(name="Roles Removed", value=len(current_roles), inline=True)
            
            if moved_from:
                embed.add_field(name="Voice Channel", value=f"Moved from {moved_from} to jail", inline=True)
                
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made prisoner by {ctx.author.name} in server '{ctx.guild.name}'")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to assign roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to assign role: {str(e)}"))
            
    @app_commands.command(name="prisoner", description="Assign the prisoner role to a user")
    @app_commands.describe(
        user="The user to make a prisoner",
        reason="Reason for assigning the prisoner role"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def prisoner_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Assign the prisoner role to a user"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Check if the prisoner role is configured
        if self.prisoner_role_id == 0:
            await interaction.response.send_message("The prisoner role ID has not been configured yet.", ephemeral=True)
            return
            
        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)
        
        # Get the prisoner role by ID
        prisoner_role = interaction.guild.get_role(self.prisoner_role_id)
        if not prisoner_role:
            await interaction.followup.send("The prisoner role doesn't exist in this server.")
            return
            
        # Check if the user is trying to assign a role to a user with higher permissions
        if user.top_role >= interaction.user.top_role and interaction.user.id not in config.BOT_OWNER_IDS:
            await interaction.followup.send("You cannot assign roles to users with higher or equal roles.")
            return
            
        # Check if the user already has the prisoner role
        if prisoner_role in user.roles:
            await interaction.followup.send(f"{user.name} is already a prisoner.")
            return
            
        # Store the user's current roles to remember them
        current_roles = [role for role in user.roles if role.id != user.guild.id]  # Exclude @everyone
        stored_roles = [role.id for role in current_roles]
        
        # Store the roles in recent_actions so they can be restored when unprisoned
        role_info = {
            "user_id": user.id,
            "roles": stored_roles,
            "imprisoned_by": interaction.user.id,
            "imprisoned_at": discord.utils.utcnow().isoformat()
        }
        self.recent_actions[f"prison_roles_{user.id}_{interaction.guild.id}"] = role_info
        
        # Remove all current roles and add prisoner role
        try:
            # First remove existing roles
            if current_roles:
                await user.remove_roles(*current_roles, reason=f"Roles removed for imprisonment by {interaction.user.name}")
            
            # Then add the prisoner role
            await user.add_roles(prisoner_role, reason=f"Made prisoner by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Try to move the user to the jail channel if they are in a voice channel
            jail_channel_id = 1356447400255819929  # ID of the jail channel
            jail_channel = interaction.guild.get_channel(jail_channel_id)
            
            moved_from = None
            if jail_channel and user.voice and user.voice.channel:
                moved_from = user.voice.channel.name
                try:
                    await user.move_to(jail_channel, reason=f"Moved to jail by {interaction.user.name}")
                    logger.info(f"Moved {user.name} from {moved_from} to jail channel")
                except Exception as e:
                    logger.error(f"Failed to move {user.name} to jail channel: {str(e)}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Prisoner Role Assigned",
                description=f"{user.mention} has been given the prisoner role and stripped of all other roles.",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            embed.add_field(name="Roles Removed", value=len(current_roles), inline=True)
            
            if moved_from:
                embed.add_field(name="Voice Channel", value=f"Moved from {moved_from} to jail", inline=True)
                
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) made prisoner by {interaction.user.name} in server '{interaction.guild.name}'")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to assign role: {str(e)}")
            
    @commands.command(name="unprisoner")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def unprisoner_prefix(self, ctx, user: discord.Member, *, reason: str = None):
        """Remove the prisoner role from a user (prefix command)
        Usage: !unprisoner @user [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Check if the prisoner role is configured
        if self.prisoner_role_id == 0:
            await ctx.send(embed=create_error_embed("Error", "The prisoner role ID has not been configured yet."))
            return
            
        # Get the prisoner role by ID
        prisoner_role = ctx.guild.get_role(self.prisoner_role_id)
        if not prisoner_role:
            await ctx.send(embed=create_error_embed("Error", "The prisoner role doesn't exist in this server."))
            return
            
        # Check if the user has the prisoner role
        if prisoner_role not in user.roles:
            await ctx.send(embed=create_error_embed("Error", f"{user.name} is not currently a prisoner."))
            return
            
        # Remove the prisoner role and try to restore previous roles
        try:
            # First, remove the prisoner role
            await user.remove_roles(prisoner_role, reason=f"Removed from prisoner by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Check if we have stored roles for this user
            stored_data_key = f"prison_roles_{user.id}_{ctx.guild.id}"
            restored_roles_count = 0
            
            if stored_data_key in self.recent_actions:
                # Get the stored role IDs
                stored_role_info = self.recent_actions[stored_data_key]
                stored_role_ids = stored_role_info.get("roles", [])
                
                # Get the role objects to restore
                roles_to_restore = []
                for role_id in stored_role_ids:
                    role = ctx.guild.get_role(role_id)
                    if role and role.id != self.prisoner_role_id:
                        roles_to_restore.append(role)
                
                # Restore the roles if there are any
                if roles_to_restore:
                    await user.add_roles(*roles_to_restore, reason=f"Roles restored after being freed from prisoner by {ctx.author.name}")
                    restored_roles_count = len(roles_to_restore)
                    
                # Clean up the stored data
                del self.recent_actions[stored_data_key]
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Prisoner Status Removed",
                description=f"{user.mention} has been freed from prisoner status.",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            
            if restored_roles_count > 0:
                embed.add_field(name="Roles Restored", value=str(restored_roles_count), inline=True)
            
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) freed from prisoner by {ctx.author.name} in server '{ctx.guild.name}', restored {restored_roles_count} roles")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to remove roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to remove role: {str(e)}"))
            
    @app_commands.command(name="unprisoner", description="Remove the prisoner role from a user")
    @app_commands.describe(
        user="The user to free from prisoner status",
        reason="Reason for removing the prisoner role"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def unprisoner_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str = None):
        """Remove the prisoner role from a user"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Check if the prisoner role is configured
        if self.prisoner_role_id == 0:
            await interaction.response.send_message("The prisoner role ID has not been configured yet.", ephemeral=True)
            return
            
        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)
        
        # Get the prisoner role by ID
        prisoner_role = interaction.guild.get_role(self.prisoner_role_id)
        if not prisoner_role:
            await interaction.followup.send("The prisoner role doesn't exist in this server.")
            return
            
        # Check if the user has the prisoner role
        if prisoner_role not in user.roles:
            await interaction.followup.send(f"{user.name} is not currently a prisoner.")
            return
            
        # Remove the prisoner role and try to restore previous roles
        try:
            # First, remove the prisoner role
            await user.remove_roles(prisoner_role, reason=f"Removed from prisoner by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Check if we have stored roles for this user
            stored_data_key = f"prison_roles_{user.id}_{interaction.guild.id}"
            restored_roles_count = 0
            
            if stored_data_key in self.recent_actions:
                # Get the stored role IDs
                stored_role_info = self.recent_actions[stored_data_key]
                stored_role_ids = stored_role_info.get("roles", [])
                
                # Get the role objects to restore
                roles_to_restore = []
                for role_id in stored_role_ids:
                    role = interaction.guild.get_role(role_id)
                    if role and role.id != self.prisoner_role_id:
                        roles_to_restore.append(role)
                
                # Restore the roles if there are any
                if roles_to_restore:
                    await user.add_roles(*roles_to_restore, reason=f"Roles restored after being freed from prisoner by {interaction.user.name}")
                    restored_roles_count = len(roles_to_restore)
                    
                # Clean up the stored data
                del self.recent_actions[stored_data_key]
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Prisoner Status Removed",
                description=f"{user.mention} has been freed from prisoner status.",
                color=discord.Color.green()
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            
            if restored_roles_count > 0:
                embed.add_field(name="Roles Restored", value=str(restored_roles_count), inline=True)
            
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) freed from prisoner by {interaction.user.name} in server '{interaction.guild.name}', restored {restored_roles_count} roles")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to remove roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to remove role: {str(e)}")
            
    @commands.command(name="role")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def role_prefix(self, ctx, user: discord.Member, role: discord.Role, *, reason: str = None):
        """Assign a role to a user (prefix command)
        Usage: !role @user @role [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Check if the bot can assign the specific role (bot's highest role must be higher than the role to assign)
        if role >= ctx.guild.me.top_role:
            await ctx.send(embed=create_error_embed("Error", "I cannot assign a role that is higher than or equal to my highest role."))
            return
            
        # Check if the user is trying to assign a role that is higher than or equal to their highest role
        if role >= ctx.author.top_role and ctx.author.id not in config.BOT_OWNER_IDS:
            await ctx.send(embed=create_error_embed("Error", "You cannot assign a role that is higher than or equal to your highest role."))
            return
            
        # Check if the user already has the role
        if role in user.roles:
            await ctx.send(embed=create_error_embed("Error", f"{user.name} already has the {role.name} role."))
            return
            
        # Assign the role
        try:
            await user.add_roles(role, reason=f"Role assigned by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Role Assigned",
                description=f"{user.mention} has been given the {role.mention} role.",
                color=role.color
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) given role {role.name} by {ctx.author.name} in server '{ctx.guild.name}'")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to assign roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to assign role: {str(e)}"))
            
    @app_commands.command(name="role", description="Assign a role to a user")
    @app_commands.describe(
        user="The user to receive the role",
        role="The role to assign",
        reason="Reason for assigning the role"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def role_slash(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role, reason: str = None):
        """Assign a role to a user"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)
        
        # Check if the bot can assign the specific role (bot's highest role must be higher than the role to assign)
        if role >= interaction.guild.me.top_role:
            await interaction.followup.send("I cannot assign a role that is higher than or equal to my highest role.")
            return
            
        # Check if the user is trying to assign a role that is higher than or equal to their highest role
        if role >= interaction.user.top_role and interaction.user.id not in config.BOT_OWNER_IDS:
            await interaction.followup.send("You cannot assign a role that is higher than or equal to your highest role.")
            return
            
        # Check if the user already has the role
        if role in user.roles:
            await interaction.followup.send(f"{user.name} already has the {role.name} role.")
            return
            
        # Assign the role
        try:
            await user.add_roles(role, reason=f"Role assigned by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Role Assigned",
                description=f"{user.mention} has been given the {role.mention} role.",
                color=role.color
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"User {user.name} ({user.id}) given role {role.name} by {interaction.user.name} in server '{interaction.guild.name}'")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to assign roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to assign role: {str(e)}")
            
    @commands.command(name="takerole")
    @commands.check_any(commands.has_permissions(manage_roles=True), PermissionChecks.is_mod())
    async def takerole_prefix(self, ctx, user: discord.Member, role: discord.Role, *, reason: str = None):
        """Remove a role from a user (prefix command)
        Usage: !takerole @user @role [reason]"""
        # Check if the bot can manage roles
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to manage roles."))
            return
            
        # Check if the bot can remove the specific role (bot's highest role must be higher than the role to remove)
        if role >= ctx.guild.me.top_role:
            await ctx.send(embed=create_error_embed("Error", "I cannot remove a role that is higher than or equal to my highest role."))
            return
            
        # Check if the user is trying to remove a role that is higher than or equal to their highest role
        if role >= ctx.author.top_role and ctx.author.id not in config.BOT_OWNER_IDS:
            await ctx.send(embed=create_error_embed("Error", "You cannot remove a role that is higher than or equal to your highest role."))
            return
            
        # Check if the user has the role
        if role not in user.roles:
            await ctx.send(embed=create_error_embed("Error", f"{user.name} doesn't have the {role.name} role."))
            return
            
        # Remove the role
        try:
            await user.remove_roles(role, reason=f"Role removed by {ctx.author.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Role Removed",
                description=f"The {role.mention} role has been removed from {user.mention}.",
                color=role.color
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=ctx.author.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await ctx.send(embed=embed)
            logger.info(f"Role {role.name} removed from user {user.name} ({user.id}) by {ctx.author.name} in server '{ctx.guild.name}'")
            
        except discord.Forbidden:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to remove roles."))
        except discord.HTTPException as e:
            await ctx.send(embed=create_error_embed("Error", f"Failed to remove role: {str(e)}"))
            
    @app_commands.command(name="takerole", description="Remove a role from a user")
    @app_commands.describe(
        user="The user to remove the role from",
        role="The role to remove",
        reason="Reason for removing the role"
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def takerole_slash(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role, reason: str = None):
        """Remove a role from a user"""
        # Check if the user has appropriate permissions
        if not interaction.user.guild_permissions.manage_roles and not await PermissionChecks.is_mod().predicate(interaction):
            await interaction.response.send_message("You need 'Manage Roles' permission to use this command.", ephemeral=True)
            return
            
        # Check if the bot can manage roles
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("I don't have permission to manage roles.", ephemeral=True)
            return
            
        # Defer the response for potentially slow role operations
        await interaction.response.defer(ephemeral=False)
        
        # Check if the bot can remove the specific role (bot's highest role must be higher than the role to remove)
        if role >= interaction.guild.me.top_role:
            await interaction.followup.send("I cannot remove a role that is higher than or equal to my highest role.")
            return
            
        # Check if the user is trying to remove a role that is higher than or equal to their highest role
        if role >= interaction.user.top_role and interaction.user.id not in config.BOT_OWNER_IDS:
            await interaction.followup.send("You cannot remove a role that is higher than or equal to your highest role.")
            return
            
        # Check if the user has the role
        if role not in user.roles:
            await interaction.followup.send(f"{user.name} doesn't have the {role.name} role.")
            return
            
        # Remove the role
        try:
            await user.remove_roles(role, reason=f"Role removed by {interaction.user.name}: {reason or 'No reason provided'}")
            
            # Send confirmation
            embed = discord.Embed(
                title="📋 Role Removed",
                description=f"The {role.mention} role has been removed from {user.mention}.",
                color=role.color
            )
            embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.name, inline=True)
            if reason:
                embed.add_field(name="Reason", value=reason, inline=False)
                
            await interaction.followup.send(embed=embed)
            logger.info(f"Role {role.name} removed from user {user.name} ({user.id}) by {interaction.user.name} in server '{interaction.guild.name}'")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to remove roles.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to remove role: {str(e)}")
    
    @commands.command(name="setprisoner")
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    async def set_prisoner_role_prefix(self, ctx, role: discord.Role):
        """Set the prisoner role for the server (Admin only)
        Usage: !setprisoner @role"""
        try:
            old_id = self.prisoner_role_id
            self.prisoner_role_id = role.id
            self._save_prisoner_role_config()
            
            embed = discord.Embed(
                title="⚙️ Prisoner Role Updated",
                description=f"Prisoner role has been set to {role.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Previous Role ID", value=str(old_id) if old_id != 0 else "None", inline=True)
            embed.add_field(name="New Role ID", value=str(role.id), inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Prisoner role updated to {role.name} (ID: {role.id}) by {ctx.author}")
        except Exception as e:
            logger.error(f"Error setting prisoner role: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", f"Failed to set prisoner role: {str(e)}"))
    
    @app_commands.command(name="setprisoner", description="Set the prisoner role for the server")
    @app_commands.describe(role="The role to set as the prisoner role")
    @app_commands.default_permissions(administrator=True)
    @app_commands.check(PermissionChecks.slash_is_admin())
    async def set_prisoner_role_slash(self, interaction: discord.Interaction, role: discord.Role):
        """Set the prisoner role for the server (Admin only)"""
        try:
            old_id = self.prisoner_role_id
            self.prisoner_role_id = role.id
            self._save_prisoner_role_config()
            
            embed = discord.Embed(
                title="⚙️ Prisoner Role Updated",
                description=f"Prisoner role has been set to {role.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Previous Role ID", value=str(old_id) if old_id != 0 else "None", inline=True)
            embed.add_field(name="New Role ID", value=str(role.id), inline=True)
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Prisoner role updated to {role.name} (ID: {role.id}) by {interaction.user}")
        except Exception as e:
            logger.error(f"Error setting prisoner role: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"Failed to set prisoner role: {str(e)}"),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Moderation(bot))