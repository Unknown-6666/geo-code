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

    @app_commands.command(name="clear", description="Clear messages from the channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user"
    )
    @app_commands.default_permissions(manage_messages=True)
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

    @app_commands.command(name="slowmode", description="Set the slowmode delay for this channel")
    @app_commands.describe(
        delay="Delay in seconds (0 to disable, max 21600)",
        reason="Reason for changing slowmode"
    )
    @app_commands.default_permissions(manage_channels=True)
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

    @app_commands.command(name="serverinfo", description="Show information about the server")
    @app_commands.default_permissions(moderate_members=True)
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

    @app_commands.command(name="announce", description="Send an announcement to a channel")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        message="The announcement message"
    )
    @app_commands.default_permissions(manage_messages=True)
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

    @app_commands.command(name="embedannounce", description="Send an embed announcement")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        title="The title of the announcement",
        description="The content of the announcement",
        color="The color of the embed (optional, hex code like #FF0000)"
    )
    @app_commands.default_permissions(manage_messages=True)
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

async def setup(bot):
    await bot.add_cog(Moderation(bot))