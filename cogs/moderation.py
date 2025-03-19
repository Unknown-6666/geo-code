import discord
import logging
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    @app_commands.default_permissions(kick_members=True)
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
            await user.kick(reason=f"Kicked by {interaction.user}: {reason}")
            logger.info(f"User {user} was kicked by {interaction.user} for reason: {reason}")

            embed = create_embed(
                "👢 User Kicked",
                f"{user.mention} has been kicked from the server.\nReason: {reason or 'No reason provided'}",
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

    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_days="Number of days of messages to delete (0-7)"
    )
    @app_commands.default_permissions(ban_members=True)
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

    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for the unban"
    )
    @app_commands.default_permissions(ban_members=True)
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

    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    @app_commands.default_permissions(moderate_members=True)
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

async def setup(bot):
    await bot.add_cog(Moderation(bot))
