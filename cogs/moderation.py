import discord
import logging
import asyncio
import re
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
        logger.info("Moderation cog initialized")

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
    async def clear_prefix(self, ctx, amount: int, user: discord.Member = None):
        """Clear messages from the channel (prefix command)
        Usage: !clear amount [@user]"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to delete messages."))
            return
            
        # Limit amount to 1-100
        amount = max(1, min(100, amount))
        
        try:
            def check_message(message):
                return user is None or message.author == user
                
            deleted = await ctx.channel.purge(
                limit=amount + 1,  # +1 to include the command message
                check=check_message
            )
            
            # Remove 1 from count if user is None (command message counted)
            actual_count = len(deleted) - 1 if user is None else len(deleted)
            
            user_text = f" from {user.mention}" if user else ""
            embed = create_embed(
                "🗑️ Messages Cleared",
                f"Deleted {actual_count} messages{user_text}.",
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
            await ctx.send(embed=create_error_embed("Error", "I don't have permission to delete messages."))
        except Exception as e:
            logger.error(f"Error clearing messages: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", "An error occurred while trying to clear messages."))
    
    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.check(PermissionChecks.slash_is_mod())
    async def clear(self, interaction: discord.Interaction, amount: int, user: discord.Member = None):
        """Clear messages from the channel"""
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I don't have permission to delete messages."),
                ephemeral=True
            )
            return

        # Limit amount to 1-100
        amount = max(1, min(100, amount))

        try:
            await interaction.response.defer(ephemeral=True)

            def check_message(message):
                return user is None or message.author == user

            deleted = await interaction.channel.purge(
                limit=amount,
                check=check_message,
                before=interaction.created_at
            )

            user_text = f" from {user.mention}" if user else ""
            embed = create_embed(
                "🗑️ Messages Cleared",
                f"Deleted {len(deleted)} messages{user_text}.",
                color=0x43B581
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                embed=create_error_embed("Error", "I don't have permission to delete messages."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error clearing messages: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while trying to clear messages."),
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
            
        # Check if the command user has permission to use it on the target
        if not ctx.author.guild_permissions.administrator:
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
            
        # Check if the command user has permission to use it on the target
        if not interaction.user.guild_permissions.administrator:
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

async def setup(bot):
    await bot.add_cog(Moderation(bot))