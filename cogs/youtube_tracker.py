import discord
import logging
import os
import json
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_CHANNELS
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import PermissionChecks

logger = logging.getLogger('discord')

class YouTubeTracker(commands.Cog):
    def __init__(self, bot):
        global YOUTUBE_CHANNELS
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
            embed.add_field(name="Tracked Channels", value=tracked_channels_str if tracked_channels_str else "No channels tracked yet")
            embed.add_field(name="Check Interval", value="Once per day")
            embed.add_field(name="Manual Check", value="Moderators can use `/forcecheck` command to check now", inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error setting announcement channel: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "An error occurred while setting up the announcement channel."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="forcecheck",
        description="Manually check for new YouTube videos (Mod only)"
    )
    @app_commands.default_permissions(manage_messages=True)  # Only moderators and above
    async def force_check_videos(self, interaction: discord.Interaction):
        """Manually trigger a check for new YouTube videos (Moderator only)"""
        if not self.announcement_channel_id:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Error", 
                    "No announcement channel has been set. Please use `/setannouncement` first."
                ),
                ephemeral=True
            )
            return
            
        # Respond immediately to prevent timeout
        await interaction.response.send_message(
            embed=create_embed(
                "🔍 Checking for Videos",
                "Manually checking for new videos from all tracked channels. Please wait...",
                color=0x7289DA
            )
        )
        
        # Track if we found any videos to provide feedback
        videos_found = False
        
        try:
            global YOUTUBE_CHANNELS
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
                logger.info(f"[Manual Check] Checking for videos on channel {channel_id}")
                
                if not response['items']:
                    logger.debug(f"No videos found for channel {channel_id}")
                    continue
                    
                latest_video = response['items'][0]
                video_id = latest_video['id']['videoId']
                video_title = latest_video['snippet']['title']
                channel_title = latest_video['snippet']['channelTitle']
                
                # Always announce during manual check
                # We'll store the ID to prevent automatic re-announcement
                self.last_video_ids[channel_id] = video_id
                
                videos_found = True
                logger.info(f"[Manual Check] Found video: {video_title} from {channel_title}")
                
                embed = create_embed(
                    "🎥 Latest YouTube Video",
                    f"**{channel_title}** video:\n{video_title}",
                    color=0x7289DA
                )
                embed.url = f"https://youtube.com/watch?v={video_id}"
                embed.set_thumbnail(url=latest_video['snippet']['thumbnails']['high']['url'])
                embed.add_field(name="Channel", value=channel_title)
                embed.add_field(name="Published", value=datetime.strptime(
                    latest_video['snippet']['publishedAt'],
                    '%Y-%m-%dT%H:%M:%SZ'
                ).strftime('%Y-%m-%d %H:%M UTC'))
                
                # Send announcement to channel
                channel = interaction.guild.get_channel(self.announcement_channel_id)
                if channel:
                    await channel.send(embed=embed)
                    logger.info(f"Sent manual video announcement to channel {channel.id}")
            
            # Update user on results
            if videos_found:
                await interaction.followup.send(
                    embed=create_embed(
                        "✅ Check Complete",
                        "Found and posted videos to the announcement channel.",
                        color=0x43B581
                    )
                )
            else:
                await interaction.followup.send(
                    embed=create_embed(
                        "ℹ️ No Videos Found",
                        "No videos were found from the tracked channels.",
                        color=0x99AAB5
                    )
                )
                
        except HttpError as e:
            logger.error(f"YouTube API error during manual check: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"YouTube API error: {str(e)}")
            )
        except Exception as e:
            logger.error(f"Error during manual video check: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"An error occurred: {str(e)}")
            )

    @tasks.loop(hours=24)
    async def check_new_videos(self):
        """Check for new videos from configured channels"""
        if not self.announcement_channel_id:
            return

        try:
            global YOUTUBE_CHANNELS
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
        
    @app_commands.command(
        name="listyoutubechannels",
        description="List all YouTube channels being tracked"
    )
    @app_commands.default_permissions(manage_messages=True)  # Only moderators and above
    async def list_youtube_channels(self, interaction: discord.Interaction):
        """List all YouTube channels that are being tracked"""
        global YOUTUBE_CHANNELS
        if not YOUTUBE_CHANNELS:
            await interaction.response.send_message(
                embed=create_embed(
                    "YouTube Channels",
                    "No YouTube channels are currently being tracked.",
                    color=0x99AAB5
                )
            )
            return
            
        # Fetch channel info for each ID
        embed = create_embed(
            "🎬 Tracked YouTube Channels",
            f"Currently tracking {len(YOUTUBE_CHANNELS)} YouTube channels:",
            color=0x7289DA
        )
        
        try:
            for i, channel_id in enumerate(YOUTUBE_CHANNELS):
                try:
                    # Get channel info
                    request = self.youtube.channels().list(
                        part="snippet",
                        id=channel_id
                    )
                    response = request.execute()
                    
                    if response['items']:
                        channel_title = response['items'][0]['snippet']['title']
                        embed.add_field(
                            name=f"{i+1}. {channel_title}",
                            value=f"ID: `{channel_id}`\nURL: https://youtube.com/channel/{channel_id}",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name=f"{i+1}. Unknown Channel",
                            value=f"ID: `{channel_id}`\nUnable to fetch channel info",
                            inline=False
                        )
                except Exception as e:
                    logger.error(f"Error fetching channel info for {channel_id}: {str(e)}")
                    embed.add_field(
                        name=f"{i+1}. Error",
                        value=f"ID: `{channel_id}`\nError fetching channel info: {str(e)}",
                        inline=False
                    )
                    
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing YouTube channels: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"An error occurred while listing channels: {str(e)}")
            )
            
    @commands.command(name="addyoutubechannel")
    @PermissionChecks.is_owner()
    async def add_youtube_channel_prefix(self, ctx, channel_id: str):
        """Add a YouTube channel to track (prefix command, bot owner only)"""
        # Call the implementation method
        result_embed = await self._add_youtube_channel(channel_id)
        await ctx.send(embed=result_embed)
        
    @app_commands.command(
        name="addyoutubechannel",
        description="Add a YouTube channel to the tracking list (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def add_youtube_channel(self, interaction: discord.Interaction, channel_id: str):
        """Add a YouTube channel to track (slash command, admin only)"""
        result_embed = await self._add_youtube_channel(channel_id)
        await interaction.response.send_message(embed=result_embed)
        
    async def _add_youtube_channel(self, channel_id: str):
        """Common implementation for adding a YouTube channel"""
        # Clean the channel ID (in case they provided a URL)
        if "youtube.com/channel/" in channel_id:
            channel_id = channel_id.split("youtube.com/channel/")[1].split("?")[0]
            
        # Validate the channel ID by trying to fetch its info
        try:
            request = self.youtube.channels().list(
                part="snippet",
                id=channel_id
            )
            response = request.execute()
            
            if not response['items']:
                return create_error_embed(
                    "Error",
                    f"No YouTube channel found with ID: `{channel_id}`"
                )
                
            channel_title = response['items'][0]['snippet']['title']
            
            # Check if already in the list
            global YOUTUBE_CHANNELS
            if channel_id in YOUTUBE_CHANNELS:
                return create_error_embed(
                    "Already Tracked",
                    f"Channel `{channel_title}` is already being tracked."
                )
                
            # Add to global YOUTUBE_CHANNELS list in memory
            YOUTUBE_CHANNELS.append(channel_id)
            
            # Add to last_video_ids dictionary
            self.last_video_ids[channel_id] = None
                
            # Create success embed
            embed = create_embed(
                "✅ Channel Added",
                f"Successfully added YouTube channel `{channel_title}` to tracking list.",
                color=0x43B581
            )
            embed.add_field(
                name="Channel ID",
                value=f"`{channel_id}`"
            )
            embed.add_field(
                name="Total Tracked",
                value=f"{len(YOUTUBE_CHANNELS)} channels"
            )
            
            logger.info(f"Added YouTube channel to tracking: {channel_title} ({channel_id})")
            return embed
            
        except HttpError as e:
            logger.error(f"YouTube API error adding channel: {str(e)}")
            return create_error_embed("API Error", f"YouTube API error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error adding YouTube channel: {str(e)}")
            return create_error_embed("Error", f"An error occurred: {str(e)}")

    @commands.command(name="removeyoutubechannel")
    @PermissionChecks.is_owner()
    async def remove_youtube_channel_prefix(self, ctx, channel_id: str):
        """Remove a YouTube channel from tracking (prefix command, bot owner only)"""
        result_embed = await self._remove_youtube_channel(channel_id)
        await ctx.send(embed=result_embed)
        
    @app_commands.command(
        name="removeyoutubechannel",
        description="Remove a YouTube channel from tracking (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def remove_youtube_channel(self, interaction: discord.Interaction, channel_id: str):
        """Remove a YouTube channel from tracking (slash command, admin only)"""
        result_embed = await self._remove_youtube_channel(channel_id)
        await interaction.response.send_message(embed=result_embed)
        
    async def _remove_youtube_channel(self, channel_id: str):
        """Common implementation for removing a YouTube channel"""
        # Clean the channel ID (in case they provided a URL)
        if "youtube.com/channel/" in channel_id:
            channel_id = channel_id.split("youtube.com/channel/")[1].split("?")[0]
            
        try:
            # Check if channel exists in our list
            global YOUTUBE_CHANNELS
            if channel_id not in YOUTUBE_CHANNELS:
                return create_error_embed(
                    "Not Found",
                    f"No YouTube channel with ID `{channel_id}` is being tracked."
                )
                
            # Try to get the channel name for better feedback
            channel_name = "Unknown"
            try:
                request = self.youtube.channels().list(
                    part="snippet",
                    id=channel_id
                )
                response = request.execute()
                
                if response['items']:
                    channel_name = response['items'][0]['snippet']['title']
            except:
                pass  # If we can't get the name, just use the ID
            
            # Remove from tracking list
            YOUTUBE_CHANNELS.remove(channel_id)
            
            # Remove from last_video_ids dictionary if present
            if channel_id in self.last_video_ids:
                del self.last_video_ids[channel_id]
            
            # Create success embed
            embed = create_embed(
                "✅ Channel Removed",
                f"Successfully removed YouTube channel `{channel_name}` from tracking list.",
                color=0x43B581
            )
            embed.add_field(
                name="Channel ID",
                value=f"`{channel_id}`"
            )
            embed.add_field(
                name="Total Tracked",
                value=f"{len(YOUTUBE_CHANNELS)} channels"
            )
            
            logger.info(f"Removed YouTube channel from tracking: {channel_name} ({channel_id})")
            return embed
            
        except Exception as e:
            logger.error(f"Error removing YouTube channel: {str(e)}")
            return create_error_embed("Error", f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(YouTubeTracker(bot))