import discord
import logging
import os
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_CHANNELS

logger = logging.getLogger('discord')

class YouTubeTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announcement_channel_id = None
        self.last_video_ids = {channel: None for channel in YOUTUBE_CHANNELS}
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        self.check_new_videos.start()

    def cog_unload(self):
        self.check_new_videos.cancel()

    @app_commands.command(
        name="setannouncement",
        description="Set the channel for YouTube video announcements"
    )
    @app_commands.default_permissions(administrator=True)
    async def set_announcement_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the announcement channel for YouTube notifications"""
        try:
            if not channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(
                    "I don't have permission to send messages in that channel.",
                    ephemeral=True
                )
                return

            self.announcement_channel_id = channel.id

            embed = discord.Embed(
                title="✅ YouTube Announcements Setup",
                description=f"Successfully set {channel.mention} as the announcement channel.",
                color=0x43B581
            )
            await interaction.response.send_message(embed=embed)

            logger.info(f"YouTube announcement channel set to {channel.id} in guild {interaction.guild.id}")

        except Exception as e:
            logger.error(f"Error setting announcement channel: {str(e)}")
            await interaction.response.send_message(
                "An error occurred while setting up the announcement channel.",
                ephemeral=True
            )

    @tasks.loop(minutes=5)  # Check every 5 minutes instead of 24 hours
    async def check_new_videos(self):
        """Check for new videos from configured channels"""
        if not self.announcement_channel_id:
            return

        try:
            for channel_id in YOUTUBE_CHANNELS:
                request = self.youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    order="date",
                    maxResults=1,
                    type="video"
                )
                response = request.execute()

                if not response['items']:
                    continue

                latest_video = response['items'][0]
                video_id = latest_video['id']['videoId']

                if video_id != self.last_video_ids[channel_id]:
                    self.last_video_ids[channel_id] = video_id
                    video_title = latest_video['snippet']['title']
                    channel_title = latest_video['snippet']['channelTitle']

                    embed = discord.Embed(
                        title="🎥 New Video Posted!",
                        description=f"**{channel_title}** has uploaded a new video:\n{video_title}",
                        color=0x7289DA,
                        url=f"https://youtube.com/watch?v={video_id}"
                    )
                    embed.set_thumbnail(url=latest_video['snippet']['thumbnails']['high']['url'])

                    for guild in self.bot.guilds:
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