import discord
import logging
import asyncio
import yt_dlp
import os
import signal
import psutil
from discord import app_commands
from discord.ext import commands
from typing import Literal
from utils.embed_helpers import create_embed, create_error_embed
from collections import deque

logger = logging.getLogger('discord')

# Configure yt-dlp with more reliable options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,  # Enable output to troubleshoot
    'no_warnings': False,  # Show warnings for debugging
    'default_search': 'ytsearch',  # Use YouTube search by default
    'source_address': '0.0.0.0',
    # Support for SoundCloud and other platforms
    'extractors': 'youtube',  # Simplified to just youtube for now
    'extractor_args': {
        'youtube': {
            'skip': ['dash', 'hls'],  # Skip problematic formats
        },
    },
    'verbose': True,  # Enable verbose output for debugging
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Unknown title')
        self.url = data.get('url', '')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.platform = data.get('extractor', 'Unknown')
        
        # Keep track of the ffmpeg process for proper cleanup
        self._ffmpeg_process = None
        if hasattr(source, '_process'):
            self._ffmpeg_process = source._process
            logger.info(f"Tracking ffmpeg process for {self.title}")
        
    @classmethod
    async def search(cls, query, *, loop=None, stream=True):
        """Search for a song and return the first result"""
        loop = loop or asyncio.get_event_loop()
        try:
            # Determine if this is a direct URL or a search query
            is_url = query.startswith(('http://', 'https://', 'www.', 'spotify:', 'soundcloud:'))
            
            if is_url:
                logger.info(f"Processing direct URL: {query}")
                search_query = query
            else:
                # Detect platform hints in the query (e.g., "soundcloud: artist name")
                if query.lower().startswith('soundcloud:'):
                    platform = 'scsearch'
                    search_query = query[11:].strip()  # Remove "soundcloud: " prefix
                    logger.info(f"Searching SoundCloud for: {search_query}")
                elif query.lower().startswith('spotify:'):
                    # For Spotify, we'll still use the direct URL handling
                    platform = ''
                    search_query = query
                    logger.info(f"Processing Spotify URL: {search_query}")
                else:
                    # Default to YouTube search
                    platform = 'ytsearch'
                    search_query = query
                    logger.info(f"Searching YouTube for: {search_query}")
                
                # Add platform prefix for search if not a direct URL and not already specified
                if not is_url and platform:
                    search_query = f"{platform}:{search_query}"
                    
            logger.info(f"Final search query: {search_query}")
            
            # Use yt-dlp to extract info
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=not stream))
            
            # If we got a playlist or search results, take the first item
            if 'entries' in data:
                logger.info(f"Found {len(data['entries'])} results, using first match")
                data = data['entries'][0]
                
            return data
            
        except Exception as e:
            logger.error(f"Error searching for query '{query}': {str(e)}")
            raise

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        try:
            logger.info(f"Attempting to extract info from URL: {url}")
            
            # Use search function to handle both URLs and search queries
            data = await cls.search(url, loop=loop, stream=stream)
            logger.debug(f"Successfully extracted info: {data.get('title', 'Unknown title')}")

            # Verify we have a URL to play
            if 'url' not in data:
                logger.error(f"No playable URL found in data for: {data.get('title', 'Unknown title')}")
                if 'webpage_url' in data:
                    logger.info(f"Retrying extraction with webpage_url: {data['webpage_url']}")
                    # Try one more time with the webpage_url
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(data['webpage_url'], download=not stream))
                    if 'entries' in data:
                        data = data['entries'][0]
                else:
                    raise ValueError("No playable URL found and no webpage_url to retry")
                
            # Check again if we have a valid URL
            if 'url' not in data:
                raise ValueError(f"Could not find a playable URL for {data.get('title', 'Unknown')}")
                
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            logger.info(f"Creating audio source for: {data.get('title', 'Unknown title')} from {data.get('extractor', 'Unknown source')}")
            try:
                # More targeted FFmpeg process cleanup
                import psutil
                import signal
                current_pid = os.getpid()
                parent = psutil.Process(current_pid)
                
                # Only kill child FFmpeg processes of the current process
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        if 'ffmpeg' in child.name().lower():
                            logger.info(f"Terminating FFmpeg process {child.pid}")
                            child.terminate()
                            child.wait(timeout=2)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try:
                            os.kill(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                
                # Wait briefly for cleanup
                await asyncio.sleep(0.5)
                
                # Use more reliable ffmpeg options with lower bitrate and explicit format
                ffmpeg_options = {
                    'options': '-vn -b:a 64k -bufsize 64k -ar 48000 -ac 2 -f s16le -loglevel warning',
                    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin -analyzeduration 0'
                }
                
                audio_source = discord.FFmpegPCMAudio(filename, **ffmpeg_options)
                logger.info(f"Created FFmpeg audio source for: {data.get('title', 'Unknown')}")
                
                # Return the audio source transformer with lower initial volume
                return cls(audio_source, data=data, volume=0.3)
            except Exception as audio_error:
                logger.error(f"Error creating FFmpeg audio source: {str(audio_error)}")
                try:
                    # Try with simplified options if first attempt fails
                    simplified_options = {
                        'options': '-vn',
                        'before_options': '-reconnect 1 -reconnect_streamed 1'
                    }
                    logger.info("Retrying with simplified FFmpeg options")
                    # Verify the filename is valid
                    if not filename or not isinstance(filename, str):
                        logger.error(f"Invalid filename: {filename}")
                        raise ValueError(f"Invalid URL for FFmpeg: {filename}")
                    
                    # Create the audio source with simplified options
                    logger.info(f"Creating FFmpeg with URL: {filename[:50]}... (truncated)")
                    audio_source = discord.FFmpegPCMAudio(filename, **simplified_options)
                    logger.info(f"Successfully created audio source with simplified options")
                    return cls(audio_source, data=data)
                except Exception as retry_error:
                    logger.error(f"Second attempt at creating audio source failed: {str(retry_error)}")
                    raise
        except Exception as e:
            logger.error(f"Error extracting info from URL {url}: {str(e)}")
            # Include more detailed error info
            if hasattr(e, "__dict__"):
                for key, value in e.__dict__.items():
                    logger.error(f"Error detail - {key}: {value}")
            raise

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Guild ID -> Queue
        self.now_playing = {}  # Guild ID -> Current song
        self._volume = {}  # Guild ID -> Volume level
        logger.info("Music cog initialized")

    def get_queue(self, guild_id):
        """Get or create queue for a guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
            self._volume[guild_id] = 0.5  # Default volume: 50%
        return self.queues[guild_id]

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        """Join the user's voice channel"""
        if not interaction.user.voice:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You must be in a voice channel to use this command."),
                ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        # Defer the response immediately
        await interaction.response.defer()

        try:
            # Attempt to reconnect if there's an existing but disconnected voice client
            if voice_client:
                if not voice_client.is_connected():
                    logger.info(f"Voice client exists but is disconnected, cleaning up")
                    await voice_client.disconnect(force=True)
                    voice_client = None
                elif voice_client.channel == channel:
                    await interaction.followup.send("I'm already in your voice channel!", ephemeral=True)
                    return
            
            # Connect or move to the specified channel
            if voice_client:
                await voice_client.move_to(channel)
            else:
                # Use explicit timeout for connection
                try:
                    voice_client = await channel.connect(timeout=10.0, reconnect=True)
                except asyncio.TimeoutError:
                    logger.error(f"Timed out connecting to voice channel {channel.id}")
                    await interaction.followup.send(
                        embed=create_error_embed("Connection Error", "Timed out connecting to voice channel. Please try again or use a different channel."),
                        ephemeral=True
                    )
                    return

            # Verify connection was successful
            if voice_client and voice_client.is_connected():
                logger.info(f"Successfully joined voice channel {channel.id} in guild {interaction.guild_id}")
                try:
                    await interaction.response.send_message(
                        embed=create_embed("🎵 Joined Voice", f"Connected to {channel.mention}")
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        embed=create_embed("🎵 Joined Voice", f"Connected to {channel.mention}")
                    )
            else:
                logger.error(f"Failed to connect to voice channel {channel.id}")
                try:
                    await interaction.response.send_message(
                        embed=create_error_embed("Connection Error", "Could not establish voice connection. This may be due to network restrictions or Discord limitations."),
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    await interaction.followup.send(
                        embed=create_error_embed("Connection Error", "Could not establish voice connection. This may be due to network restrictions or Discord limitations."),
                        ephemeral=True
                    )
        except Exception as e:
            logger.error(f"Error joining voice channel: {str(e)}")
            try:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", f"Failed to join voice channel: {str(e)}"),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_error_embed("Error", f"Failed to join voice channel: {str(e)}"),
                    ephemeral=True
                )

    @app_commands.command(name="play", description="Play a song from YouTube, SoundCloud, or Spotify")
    @app_commands.describe(query="URL or search query (prepend with 'soundcloud:' or 'spotify:' to search specific platforms)")
    async def play(self, interaction: discord.Interaction, *, query: str):
        """Play music from various sources including YouTube, SoundCloud, and Spotify
        
        Examples:
        - /play despacito (searches YouTube)
        - /play soundcloud: electronic music (searches SoundCloud)
        - /play https://www.youtube.com/watch?v=dQw4w9WgXcQ (direct YouTube URL)
        - /play https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT (Spotify URL)
        - /play https://soundcloud.com/artist/song-name (SoundCloud URL)
        """
        try:
            if not interaction.user.voice:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=create_error_embed("Error", "You must be in a voice channel to use this command."),
                        ephemeral=True
                    )
                return

            # Defer only if we haven't responded yet
            if not interaction.response.is_done():
                await interaction.response.defer()
                
        except Exception as e:
            logger.error(f"Error checking voice state: {str(e)}")
            return

        logger.info(f"Processing play command for query: {query}")

        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                try:
                    # Use explicit timeout for connection
                    voice_client = await interaction.user.voice.channel.connect(timeout=10.0, reconnect=True)
                except asyncio.TimeoutError:
                    logger.error(f"Timed out connecting to voice channel in /play command")
                    await interaction.followup.send(
                        embed=create_error_embed("Connection Error", "Timed out connecting to voice channel. Please try again or use the /join command first."),
                        ephemeral=True
                    )
                    return
                except Exception as connect_error:
                    logger.error(f"Error connecting to voice channel in /play command: {str(connect_error)}")
                    await interaction.followup.send(
                        embed=create_error_embed("Connection Error", f"Could not connect to voice channel: {str(connect_error)}"),
                        ephemeral=True
                    )
                    return
                    
            # Verify we have a valid voice connection
            if not voice_client or not voice_client.is_connected():
                logger.error("Voice client failed to connect properly in /play command")
                await interaction.followup.send(
                    embed=create_error_embed("Connection Error", "Could not establish a stable voice connection. Please try again or use a different voice channel."),
                    ephemeral=True
                )
                return

            queue = self.get_queue(interaction.guild_id)

            # Use our new search method to handle the query
            try:
                data = await YTDLSource.search(query, loop=self.bot.loop)
                logger.info(f"Successfully found music: {data['title']} from {data.get('extractor', 'unknown source')}")
            except Exception as e:
                logger.error(f"Error searching for query '{query}': {str(e)}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Could not find the requested song. Please check your query and try again."),
                    ephemeral=True
                )
                return

            # Get source info for display
            source_type = data.get('extractor', 'Unknown')
            if 'youtube' in source_type.lower():
                platform_emoji = "▶️ YouTube"
            elif 'soundcloud' in source_type.lower():
                platform_emoji = "☁️ SoundCloud"
            elif 'spotify' in source_type.lower():
                platform_emoji = "🎧 Spotify"
            else:
                platform_emoji = "🎵 Music"

            # Add to queue - store the original query if it's a URL, otherwise store the specific resource URL
            if query.startswith(('http://', 'https://', 'www.', 'spotify:', 'soundcloud:')):
                queue.append(query)
            else:
                # For search queries, store the actual URL we found
                queue.append(data['webpage_url'])
                
            logger.info(f"Added song to queue: {data['title']} from {source_type}")

            if not voice_client.is_playing():
                # If nothing is playing, start playing
                await self.play_next(interaction.guild, voice_client)
                await interaction.followup.send(
                    embed=create_embed(f"{platform_emoji} Now Playing", f"[{data['title']}]({data['webpage_url']})")
                )
            else:
                # Add to queue
                await interaction.followup.send(
                    embed=create_embed(f"{platform_emoji} Added to Queue", f"[{data['title']}]({data['webpage_url']})")
                )

        except Exception as e:
            logger.error(f"Error playing music: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"An error occurred while trying to play the song: {str(e)}"),
                ephemeral=True
            )

    async def play_next(self, guild, voice_client):
        """Play the next song in the queue"""
        queue = self.get_queue(guild.id)

        # Clean up any existing player more carefully
        if voice_client and voice_client.source:
            try:
                # Only attempt to kill if the attribute exists
                if hasattr(voice_client.source, '_player') and voice_client.source._player:
                    logger.info(f"Safely terminating previous ffmpeg process")
                    voice_client.source._player.kill()
            except Exception as e:
                logger.error(f"Error cleaning up previous player: {str(e)}")
            
            # Safely stop the current playing audio
            try:
                voice_client.stop()
            except Exception as e:
                logger.error(f"Error stopping voice client: {str(e)}")

        if not queue:
            self.now_playing[guild.id] = None
            return
            
        if not voice_client or not voice_client.is_connected():
            logger.warning(f"Voice client disconnected for guild {guild.id}, clearing queue")
            queue.clear()
            self.now_playing[guild.id] = None
            return

        try:
            # Take the next song from the queue
            url = queue.popleft()
            logger.info(f"Attempting to play next song from URL: {url}")
            
            try:
                # Create a brief delay to ensure previous ffmpeg processes are cleaned up
                await asyncio.sleep(0.5)
                
                # Create the audio source
                player = await YTDLSource.from_url(url, loop=self.bot.loop)
                player.volume = self._volume.get(guild.id, 0.5)
                
                self.now_playing[guild.id] = player
                logger.info(f"Playing next song in guild {guild.id}: {player.title}")
                
                # Define callback with better error handling
                def after_callback(e):
                    if e:
                        logger.error(f"Error in play_next callback: {str(e)}")
                    # Use a try-except block here to prevent potential crashes
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.play_next(guild, voice_client), self.bot.loop
                        )
                    except Exception as callback_error:
                        logger.error(f"Failed to schedule next song: {str(callback_error)}")
                
                # Check if the voice client is still connected before playing
                if voice_client and voice_client.is_connected():
                    # Add extra logging for debugging
                    logger.info(f"Starting playback of {player.title}")
                    voice_client.play(player, after=after_callback)
                else:
                    logger.warning(f"Voice client disconnected before playing in guild {guild.id}")
                    self.now_playing[guild.id] = None
                    queue.clear()
            except Exception as e:
                logger.error(f"Error getting audio source: {str(e)}")
                # Add detailed error info
                if hasattr(e, "__dict__"):
                    for key, value in e.__dict__.items():
                        logger.error(f"Error detail - {key}: {value}")
                # Try to play the next song in the queue
                asyncio.create_task(self.play_next(guild, voice_client))
                
        except Exception as e:
            logger.error(f"Error in play_next: {str(e)}")
            # Try to safely clear up and disconnect if there's a major error
            try:
                self.now_playing[guild.id] = None
                if voice_client and voice_client.is_connected():
                    voice_client.stop()
            except:
                pass

    @app_commands.command(name="stop", description="Stop playing and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        """Stop playing and clear the queue"""
        voice_client = interaction.guild.voice_client
        if not voice_client:
            try:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "I'm not playing anything right now."),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "I'm not playing anything right now."),
                    ephemeral=True
                )
            return

        queue = self.get_queue(interaction.guild_id)
        queue.clear()
        voice_client.stop()
        logger.info(f"Stopped playback and cleared queue in guild {interaction.guild_id}")

        try:
            await interaction.response.send_message(
                embed=create_embed("⏹️ Stopped", "Music playback stopped and queue cleared.")
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                embed=create_embed("⏹️ Stopped", "Music playback stopped and queue cleared.")
            )

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        """Skip the current song"""
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            try:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "Nothing is playing right now."),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Nothing is playing right now."),
                    ephemeral=True
                )
            return

        voice_client.stop()  # This will trigger play_next automatically
        logger.info(f"Skipped song in guild {interaction.guild_id}")
        try:
            await interaction.response.send_message(
                embed=create_embed("⏭️ Skipped", "Skipped the current song.")
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                embed=create_embed("⏭️ Skipped", "Skipped the current song.")
            )

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current queue"""
        queue = self.get_queue(interaction.guild_id)

        if not queue and not self.now_playing.get(interaction.guild_id):
            try:
                await interaction.response.send_message(
                    embed=create_embed("📋 Queue", "The queue is empty and nothing is playing.")
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_embed("📋 Queue", "The queue is empty and nothing is playing.")
                )
            return

        # Using defer as this might take a moment to process all queue items
        try:
            await interaction.response.defer()
        except discord.errors.InteractionResponded:
            # Already responded, continue with followup messages
            pass
            
        embed = create_embed("📋 Queue", "")

        # Add now playing
        current = self.now_playing.get(interaction.guild_id)
        if current:
            # Get platform icon
            platform = current.platform
            if 'youtube' in platform.lower():
                platform_icon = "▶️"
            elif 'soundcloud' in platform.lower():
                platform_icon = "☁️"
            elif 'spotify' in platform.lower():
                platform_icon = "🎧"
            else:
                platform_icon = "🎵"
                
            embed.add_field(
                name=f"{platform_icon} Now Playing",
                value=f"[{current.title}]({current.webpage_url or current.url})",
                inline=False
            )

        # Add queue items
        if queue:
            # Get info for first 5 items
            queue_list = []
            
            for i, url in enumerate(list(queue)[:5], 1):
                try:
                    # Use our search method for better handling
                    data = await YTDLSource.search(url, loop=self.bot.loop)
                    
                    # Get platform icon
                    source_type = data.get('extractor', 'Unknown')
                    if 'youtube' in source_type.lower():
                        platform_icon = "▶️"
                    elif 'soundcloud' in source_type.lower():
                        platform_icon = "☁️"
                    elif 'spotify' in source_type.lower():
                        platform_icon = "🎧"
                    else:
                        platform_icon = "🎵"
                        
                    queue_list.append(f"{i}. {platform_icon} [{data['title']}]({data['webpage_url']})")
                except Exception as e:
                    logger.error(f"Error fetching queue item info: {str(e)}")
                    queue_list.append(f"{i}. 🎵 [Unable to fetch title]({url})")

            embed.add_field(
                name="Up Next",
                value="\n".join(queue_list) + (f"\n\n...and {len(queue) - 5} more" if len(queue) > 5 else ""),
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="volume", description="Set the volume (0-100)")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set the volume"""
        if not 0 <= volume <= 100:
            try:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "Volume must be between 0 and 100."),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Volume must be between 0 and 100."),
                    ephemeral=True
                )
            return

        self._volume[interaction.guild_id] = volume / 100

        # Adjust volume of currently playing song
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.source:
            voice_client.source.volume = volume / 100

        logger.info(f"Set volume to {volume}% in guild {interaction.guild_id}")
        try:
            await interaction.response.send_message(
                embed=create_embed("🔊 Volume", f"Set volume to {volume}%")
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                embed=create_embed("🔊 Volume", f"Set volume to {volume}%")
            )

    @app_commands.command(name="search", description="Search for music from different platforms")
    @app_commands.describe(
        query="What to search for",
        platform="Which platform to search on (default: YouTube)"
    )
    async def search(
        self, 
        interaction: discord.Interaction, 
        query: str, 
        platform: Literal["youtube", "soundcloud"] = "youtube"
    ):
        """Search for music and display the results
        
        Examples:
        - /search query:despacito platform:youtube
        - /search query:electronic music platform:soundcloud
        """
        await interaction.response.defer()  # This might take a while
        logger.info(f"Searching for '{query}' on {platform}")
        
        # Prepare search query with platform prefix
        if platform == "soundcloud":
            search_query = f"scsearch5:{query}"  # Get top 5 SoundCloud results
            platform_name = "SoundCloud"
            platform_emoji = "☁️"
        else:  # Default to YouTube
            search_query = f"ytsearch5:{query}"  # Get top 5 YouTube results
            platform_name = "YouTube"
            platform_emoji = "▶️"
            
        try:
            # Get search results directly from ytdl
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_query, download=False))
            
            if not data or 'entries' not in data or len(data['entries']) == 0:
                await interaction.followup.send(
                    embed=create_error_embed("No Results", f"No results found for '{query}' on {platform_name}."),
                    ephemeral=True
                )
                return
                
            # Create embed with results
            embed = create_embed(
                f"{platform_emoji} {platform_name} Search Results", 
                f"Search results for: **{query}**\nUse `/play` with the number or URL to play a song."
            )
            
            for i, entry in enumerate(data['entries'], 1):
                if not entry:
                    continue  # Skip empty entries
                    
                title = entry.get('title', 'Unknown title')
                url = entry.get('webpage_url', '')
                duration = entry.get('duration')
                uploader = entry.get('uploader', 'Unknown uploader')
                
                # Format duration if available
                duration_str = ""
                if duration:
                    minutes, seconds = divmod(int(duration), 60)
                    hours, minutes = divmod(minutes, 60)
                    if hours > 0:
                        duration_str = f" • {hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_str = f" • {minutes}:{seconds:02d}"
                
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"By: {uploader}{duration_str}\n[Link]({url})",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error searching for music: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"An error occurred while searching: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        voice_client = interaction.guild.voice_client
        if not voice_client:
            try:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "I'm not in a voice channel."),
                    ephemeral=True
                )
            except discord.errors.InteractionResponded:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "I'm not in a voice channel."),
                    ephemeral=True
                )
            return

        await voice_client.disconnect()
        # Clear guild data
        self.queues.pop(interaction.guild_id, None)
        self.now_playing.pop(interaction.guild_id, None)
        logger.info(f"Left voice channel in guild {interaction.guild_id}")

        try:
            await interaction.response.send_message(
                embed=create_embed("👋 Left Voice", "Disconnected from voice channel.")
            )
        except discord.errors.InteractionResponded:
            await interaction.followup.send(
                embed=create_embed("👋 Left Voice", "Disconnected from voice channel.")
            )

async def setup(bot):
    logger.info("Setting up Music cog")
    await bot.add_cog(Music(bot))
    logger.info("Music cog is ready")