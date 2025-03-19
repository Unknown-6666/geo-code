import discord
import logging
import os
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger('discord')

class YouTubeTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = None
        self.announcement_channel_id = None
        self.last_video_id = None
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        self.check_new_videos.start()

    def cog_unload(self):
        self.check_new_videos.cancel()

    @commands.command(name="setyoutube")
    @commands.has_permissions(administrator=True)
    async def set_youtube_channel(self, ctx, channel_id: str, announcement_channel: discord.TextChannel = None):
        """Legacy command to set YouTube channel tracking"""
        await self._setup_youtube_tracking(ctx, channel_id, announcement_channel)

    @app_commands.command(
        name="setyoutube",
        description="Set up YouTube channel tracking and announcement channel"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_youtube_channel_slash(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        announcement_channel: discord.TextChannel = None
    ):
        """Slash command to set YouTube channel tracking"""
        await self._setup_youtube_tracking(interaction, channel_id, announcement_channel)

    async def _setup_youtube_tracking(self, ctx_or_interaction, channel_id: str, announcement_channel: discord.TextChannel = None):
        """Helper method to set up YouTube tracking"""
        try:
            # Verify the channel exists
            request = self.youtube.channels().list(
                part="snippet",
                id=channel_id
            )
            response = request.execute()

            if not response['items']:
                error_message = "❌ Invalid YouTube channel ID. Please check and try again."
                if isinstance(ctx_or_interaction, discord.Interaction):
                    await ctx_or_interaction.response.send_message(error_message)
                else:
                    await ctx_or_interaction.send(error_message)
                return

            self.channel_id = channel_id
            self.announcement_channel_id = (
                announcement_channel.id if announcement_channel
                else ctx_or_interaction.channel_id if isinstance(ctx_or_interaction, discord.Interaction)
                else ctx_or_interaction.channel.id
            )

            # Create embed for confirmation
            embed = discord.Embed(
                title="✅ YouTube Tracking Setup",
                description=f"Successfully set up tracking for channel ID: {channel_id}",
                color=0x43B581
            )
            embed.add_field(
                name="Announcements Channel",
                value=ctx_or_interaction.guild.get_channel(self.announcement_channel_id).mention
            )

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(embed=embed)
            else:
                await ctx_or_interaction.send(embed=embed)

            logger.info(f"YouTube tracking set up for channel {channel_id} in guild {ctx_or_interaction.guild.id}")

        except Exception as e:
            error_message = "❌ An error occurred while setting up YouTube tracking. Please try again later."
            logger.error(f"Error setting up YouTube tracking: {str(e)}")

            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.response.send_message(error_message)
            else:
                await ctx_or_interaction.send(error_message)

    @tasks.loop(hours=24)
    async def check_new_videos(self):
        """Check for new videos every 24 hours"""
        try:
            if not self.channel_id:
                return

            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                order="date",
                maxResults=1,
                type="video"
            )
            response = request.execute()

            if not response['items']:
                return

            latest_video = response['items'][0]
            video_id = latest_video['id']['videoId']

            if video_id != self.last_video_id:
                self.last_video_id = video_id
                video_title = latest_video['snippet']['title']

                embed = discord.Embed(
                    title="🎥 New Video Posted!",
                    description=video_title,
                    color=0x7289DA,
                    url=f"https://youtube.com/watch?v={video_id}"
                )
                embed.set_thumbnail(url=latest_video['snippet']['thumbnails']['high']['url'])

                for guild in self.bot.guilds:
                    if hasattr(self, 'announcement_channel_id'):
                        channel = guild.get_channel(self.announcement_channel_id)
                        if channel:
                            await channel.send(embed=embed)
                            logger.info(f"Sent new video announcement to guild {guild.id}")

        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error checking for new videos: {str(e)}")

    @check_new_videos.before_loop
    async def before_check_videos(self):
        """Wait for the bot to be ready before starting the task"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(YouTubeTracker(bot))