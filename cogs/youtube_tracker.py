import discord
import logging
import os
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_CHANNELS
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

class YouTubeTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.announcement_channel_id = None
        self.last_video_ids = {channel: None for channel in YOUTUBE_CHANNELS}
        self.youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        self.check_new_videos.start()
        logger.info(f"YouTube tracker initialized for channels: {YOUTUBE_CHANNELS}")

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
                    embed=create_error_embed("Error", "I don't have permission to send messages in that channel."),
                    ephemeral=True
                )
                return

            self.announcement_channel_id = channel.id
            logger.info(f"Set announcement channel to {channel.id} in guild {interaction.guild.id}")

            embed = create_embed(
                "✅ YouTube Announcements Setup",
                f"Successfully set {channel.mention} as the announcement channel.\nI'll post notifications here when new videos are uploaded to the tracked channels.",
                color=0x43B581
            )
            # Add tracked channels to the confirmation message
            tracked_channels_str = "\n".join([f"• `{channel_id}`" for channel_id in YOUTUBE_CHANNELS])
            embed.add_field(name="Tracked Channels", value=tracked_channels_str)
            embed.add_field(name="Check Interval", value="Once per day")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error setting announcement channel: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while setting up the announcement channel."),
                ephemeral=True
            )

    @tasks.loop(hours=24)
    async def check_new_videos(self):
        """Check for new videos from configured channels"""
        if not self.announcement_channel_id:
            return

        try:
            for channel_id in YOUTUBE_CHANNELS:
                # Fetch latest video from each channel
                request = self.youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    order="date",
                    maxResults=1,
                    type="video"
                )
                response = request.execute()
                logger.debug(f"Checking for new videos on channel {channel_id}")

                if not response['items']:
                    logger.debug(f"No videos found for channel {channel_id}")
                    continue

                latest_video = response['items'][0]
                video_id = latest_video['id']['videoId']

                # If this is a new video we haven't announced yet
                if video_id != self.last_video_ids[channel_id]:
                    self.last_video_ids[channel_id] = video_id
                    video_title = latest_video['snippet']['title']
                    channel_title = latest_video['snippet']['channelTitle']

                    logger.info(f"New video found: {video_title} from {channel_title}")

                    embed = create_embed(
                        "🎥 New Video Posted!",
                        f"**{channel_title}** has uploaded a new video:\n{video_title}",
                        color=0x7289DA
                    )
                    embed.url = f"https://youtube.com/watch?v={video_id}"
                    embed.set_thumbnail(url=latest_video['snippet']['thumbnails']['high']['url'])
                    embed.add_field(name="Channel", value=channel_title)
                    embed.add_field(name="Published", value=datetime.strptime(
                        latest_video['snippet']['publishedAt'],
                        '%Y-%m-%dT%H:%M:%SZ'
                    ).strftime('%Y-%m-%d %H:%M UTC'))

                    # Send to all guilds that have configured an announcement channel
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
        logger.info("YouTube video checker is ready to start")

async def setup(bot):
    await bot.add_cog(YouTubeTracker(bot))