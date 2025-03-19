import discord
import logging
import asyncio
import yt_dlp
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from collections import deque

logger = logging.getLogger('discord')

# Configure yt-dlp
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
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
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
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
            logger.debug(f"Successfully extracted info for URL: {url}")

            if 'entries' in data:
                # Take first item from a playlist
                data = data['entries'][0]

            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            logger.error(f"Error extracting info from URL {url}: {str(e)}")
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

        try:
            if voice_client:
                if voice_client.channel == channel:
                    await interaction.response.send_message("I'm already in your voice channel!", ephemeral=True)
                    return
                await voice_client.move_to(channel)
            else:
                await channel.connect()

            logger.info(f"Joined voice channel {channel.id} in guild {interaction.guild_id}")
            await interaction.response.send_message(
                embed=create_embed("🎵 Joined Voice", f"Connected to {channel.mention}")
            )
        except Exception as e:
            logger.error(f"Error joining voice channel: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Failed to join voice channel."),
                ephemeral=True
            )

    @app_commands.command(name="play", description="Play a song from YouTube")
    @app_commands.describe(query="YouTube URL or search query")
    async def play(self, interaction: discord.Interaction, *, query: str):
        """Play a song from YouTube"""
        if not interaction.user.voice:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "You must be in a voice channel to use this command."),
                ephemeral=True
            )
            return

        await interaction.response.defer()  # This might take a while
        logger.info(f"Processing play command for query: {query}")

        try:
            voice_client = interaction.guild.voice_client
            if not voice_client:
                voice_client = await interaction.user.voice.channel.connect()

            queue = self.get_queue(interaction.guild_id)

            # Extract info first to get title for queue message
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))

            if 'entries' in data:
                data = data['entries'][0]

            # Add to queue
            queue.append(query)
            logger.info(f"Added song to queue: {data['title']}")

            if not voice_client.is_playing():
                # If nothing is playing, start playing
                await self.play_next(interaction.guild, voice_client)
                await interaction.followup.send(
                    embed=create_embed("🎵 Now Playing", f"[{data['title']}]({data['webpage_url']})")
                )
            else:
                # Add to queue
                await interaction.followup.send(
                    embed=create_embed("📋 Added to Queue", f"[{data['title']}]({data['webpage_url']})")
                )

        except Exception as e:
            logger.error(f"Error playing music: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while trying to play the song."),
                ephemeral=True
            )

    async def play_next(self, guild, voice_client):
        """Play the next song in the queue"""
        queue = self.get_queue(guild.id)

        if not queue:
            self.now_playing[guild.id] = None
            return

        try:
            url = queue.popleft()
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            player.volume = self._volume.get(guild.id, 0.5)

            self.now_playing[guild.id] = player
            logger.info(f"Playing next song in guild {guild.id}: {player.title}")

            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(guild, voice_client), self.bot.loop
            ))
        except Exception as e:
            logger.error(f"Error in play_next: {str(e)}")

    @app_commands.command(name="stop", description="Stop playing and clear the queue")
    async def stop(self, interaction: discord.Interaction):
        """Stop playing and clear the queue"""
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I'm not playing anything right now."),
                ephemeral=True
            )
            return

        queue = self.get_queue(interaction.guild_id)
        queue.clear()
        voice_client.stop()
        logger.info(f"Stopped playback and cleared queue in guild {interaction.guild_id}")

        await interaction.response.send_message(
            embed=create_embed("⏹️ Stopped", "Music playback stopped and queue cleared.")
        )

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        """Skip the current song"""
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_playing():
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Nothing is playing right now."),
                ephemeral=True
            )
            return

        voice_client.stop()  # This will trigger play_next automatically
        logger.info(f"Skipped song in guild {interaction.guild_id}")
        await interaction.response.send_message(
            embed=create_embed("⏭️ Skipped", "Skipped the current song.")
        )

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        """Display the current queue"""
        queue = self.get_queue(interaction.guild_id)

        if not queue and not self.now_playing.get(interaction.guild_id):
            await interaction.response.send_message(
                embed=create_embed("📋 Queue", "The queue is empty and nothing is playing.")
            )
            return

        embed = create_embed("📋 Queue", "")

        # Add now playing
        current = self.now_playing.get(interaction.guild_id)
        if current:
            embed.add_field(
                name="Now Playing",
                value=f"[{current.title}]({current.url})",
                inline=False
            )

        # Add queue items
        if queue:
            # Get info for first 5 items
            queue_list = []
            for i, url in enumerate(list(queue)[:5], 1):
                try:
                    info = ytdl.extract_info(url, download=False)
                    queue_list.append(f"{i}. [{info['title']}]({info['webpage_url']})")
                except:
                    queue_list.append(f"{i}. [Unable to fetch title]({url})")

            embed.add_field(
                name="Up Next",
                value="\n".join(queue_list) + (f"\n\n...and {len(queue) - 5} more" if len(queue) > 5 else ""),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Set the volume (0-100)")
    @app_commands.describe(volume="Volume level (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set the volume"""
        if not 0 <= volume <= 100:
            await interaction.response.send_message(
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
        await interaction.response.send_message(
            embed=create_embed("🔊 Volume", f"Set volume to {volume}%")
        )

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Leave the voice channel"""
        voice_client = interaction.guild.voice_client
        if not voice_client:
            await interaction.response.send_message(
                embed=create_error_embed("Error", "I'm not in a voice channel."),
                ephemeral=True
            )
            return

        await voice_client.disconnect()
        # Clear guild data
        self.queues.pop(interaction.guild_id, None)
        self.now_playing.pop(interaction.guild_id, None)
        logger.info(f"Left voice channel in guild {interaction.guild_id}")

        await interaction.response.send_message(
            embed=create_embed("👋 Left Voice", "Disconnected from voice channel.")
        )

async def setup(bot):
    logger.info("Setting up Music cog")
    await bot.add_cog(Music(bot))
    logger.info("Music cog is ready")