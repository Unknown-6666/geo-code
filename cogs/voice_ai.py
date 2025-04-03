import asyncio
import discord
import logging
import os
import random
import tempfile
import threading
import time
import wave
from gtts import gTTS
import speech_recognition as sr
from discord.ext import commands
from discord import app_commands
from utils.embed_helpers import create_embed, create_error_embed
from cogs.ai_chat import AIChat

logger = logging.getLogger('discord')

class VoiceAI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Store voice clients for each guild
        self.user_sessions = {}  # Track active voice AI sessions
        self.voice_recognition_tasks = {}  # Track voice recognition tasks
        self.listening_status = {}  # Track listening status for each guild
        self.recognizer = sr.Recognizer()
        logger.info("Voice AI cog initialized with full speech capabilities")
        
    @commands.command(name="voicechat", aliases=["vc"])
    async def voice_chat_prefix(self, ctx):
        """Join a voice channel and enable AI voice chat (prefix version)"""
        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.send(embed=create_error_embed("Error", "You need to be in a voice channel to use this command"))
            return
            
        voice_channel = ctx.author.voice.channel
        
        # Check for required permissions
        permissions = voice_channel.permissions_for(ctx.guild.me)
        if not permissions.connect or not permissions.speak:
            missing_perms = []
            if not permissions.connect:
                missing_perms.append("Connect")
            if not permissions.speak:
                missing_perms.append("Speak")
                
            await ctx.send(embed=create_error_embed(
                "Permission Error", 
                f"I don't have the required permissions to use voice chat: {', '.join(missing_perms)}"
            ))
            return
        
        # Connect to the voice channel with retry mechanism
        max_retries = 2
        retry_count = 0
        
        # Connect to the voice channel
        try:
            while retry_count <= max_retries:
                try:
                    if ctx.guild.id in self.voice_clients:
                        # If already connected, move to the new channel
                        if self.voice_clients[ctx.guild.id].is_connected():
                            await self.voice_clients[ctx.guild.id].move_to(voice_channel)
                        else:
                            # If client exists but is disconnected, create a new connection
                            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
                            self.voice_clients[ctx.guild.id] = voice_client
                    else:
                        # Otherwise connect to the channel
                        voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
                        self.voice_clients[ctx.guild.id] = voice_client
                    
                    # If we get here, connection was successful
                    break
                    
                except discord.ClientException as e:
                    logger.error(f"Discord client exception: {str(e)}")
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    logger.info(f"Retrying voice connection (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(1)
                    
                except asyncio.TimeoutError:
                    logger.error("Voice connection timed out")
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    logger.info(f"Retrying voice connection after timeout (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(2)
                
            # Start a voice AI session for this user
            self.user_sessions[ctx.author.id] = {
                "guild_id": ctx.guild.id,
                "active": True,
                "last_interaction": asyncio.get_event_loop().time()
            }
            
            await ctx.send(embed=create_embed(
                "🎙️ Voice AI Activated",
                f"I've joined {voice_channel.name} and enabled AI voice chat. I'll respond to your text messages with both text and voice. Use `!listen` to enable voice recognition, and `!vc_stop` to end the session."
            ))
            
        except Exception as e:
            logger.error(f"Error connecting to voice channel: {str(e)}")
            await ctx.send(embed=create_error_embed("Error", f"Failed to connect to voice channel: {str(e)}"))
    
    @app_commands.command(name="voicechat", description="Join a voice channel and enable AI voice chat")
    async def voice_chat(self, interaction: discord.Interaction):
        """Join a voice channel and enable AI voice chat"""
        # First acknowledge the interaction to prevent timeouts
        await interaction.response.defer()
        
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "You need to be in a voice channel to use this command"),
                    ephemeral=True
                )
                return
                
            voice_channel = interaction.user.voice.channel
            
            # Check for required permissions
            permissions = voice_channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                missing_perms = []
                if not permissions.connect:
                    missing_perms.append("Connect")
                if not permissions.speak:
                    missing_perms.append("Speak")
                    
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Permission Error", 
                        f"I don't have the required permissions to use voice chat: {', '.join(missing_perms)}"
                    ),
                    ephemeral=True
                )
                return
            
            # Connect to the voice channel with retry mechanism
            max_retries = 2
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    if interaction.guild.id in self.voice_clients:
                        # If already connected, move to the new channel
                        if self.voice_clients[interaction.guild.id].is_connected():
                            await self.voice_clients[interaction.guild.id].move_to(voice_channel)
                        else:
                            # If client exists but is disconnected, create a new connection
                            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
                            self.voice_clients[interaction.guild.id] = voice_client
                    else:
                        # Otherwise connect to the channel
                        voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
                        self.voice_clients[interaction.guild.id] = voice_client
                    
                    # If we get here, connection was successful
                    break
                    
                except discord.ClientException as e:
                    logger.error(f"Discord client exception: {str(e)}")
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    logger.info(f"Retrying voice connection (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(1)
                    
                except asyncio.TimeoutError:
                    logger.error("Voice connection timed out")
                    retry_count += 1
                    if retry_count > max_retries:
                        raise
                    logger.info(f"Retrying voice connection after timeout (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(2)
            
            # Start a voice AI session for this user
            self.user_sessions[interaction.user.id] = {
                "guild_id": interaction.guild.id,
                "active": True,
                "last_interaction": asyncio.get_event_loop().time()
            }
            
            await interaction.followup.send(embed=create_embed(
                "🎙️ Voice AI Activated",
                f"I've joined {voice_channel.name} and enabled AI voice chat. I'll respond to your text messages with both text and voice. Use `/listen` to enable voice recognition, and `/voice_stop` to end the session."
            ))
            
        except Exception as e:
            logger.error(f"Error connecting to voice channel: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to connect to voice channel: {str(e)}"),
                ephemeral=True
            )
    
    @commands.command(name="voice_stop", aliases=["vc_stop"])
    async def voice_stop_prefix(self, ctx):
        """Stop AI voice chat and disconnect from voice channel (prefix version)"""
        # Check if there's an active voice client for this guild
        if ctx.guild.id not in self.voice_clients:
            await ctx.send(embed=create_error_embed("Error", "I'm not currently in a voice channel"))
            return
            
        # Disconnect from voice channel
        voice_client = self.voice_clients[ctx.guild.id]
        await voice_client.disconnect()
        del self.voice_clients[ctx.guild.id]
        
        # End user sessions in this guild
        for user_id, session in list(self.user_sessions.items()):
            if session["guild_id"] == ctx.guild.id:
                del self.user_sessions[user_id]
                
        await ctx.send(embed=create_embed(
            "🎙️ AI Chat Deactivated",
            "I've disconnected from the voice channel and disabled AI chat."
        ))
    
    @app_commands.command(name="voice_stop", description="Stop AI voice chat and disconnect from voice channel")
    async def voice_stop(self, interaction: discord.Interaction):
        """Stop AI voice chat and disconnect from voice channel"""
        # First acknowledge the interaction to prevent timeouts
        await interaction.response.defer()
        
        # Check if there's an active voice client for this guild
        if interaction.guild.id not in self.voice_clients:
            await interaction.followup.send(
                embed=create_error_embed("Error", "I'm not currently in a voice channel"),
                ephemeral=True
            )
            return
            
        # Disconnect from voice channel
        voice_client = self.voice_clients[interaction.guild.id]
        await voice_client.disconnect()
        del self.voice_clients[interaction.guild.id]
        
        # End user sessions in this guild
        for user_id, session in list(self.user_sessions.items()):
            if session["guild_id"] == interaction.guild.id:
                del self.user_sessions[user_id]
                
        await interaction.followup.send(embed=create_embed(
            "🎙️ AI Chat Deactivated",
            "I've disconnected from the voice channel and disabled AI chat."
        ))
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages from users with active voice AI sessions"""
        # Ignore messages from bots or system messages
        if message.author.bot or not message.content:
            return
            
        # Check if the user has an active voice AI session
        if message.author.id in self.user_sessions and self.user_sessions[message.author.id]["active"]:
            session = self.user_sessions[message.author.id]
            guild_id = session["guild_id"]
            
            # Make sure the message is from the same guild as the voice session
            if message.guild and message.guild.id == guild_id:
                # Update last interaction time
                session["last_interaction"] = asyncio.get_event_loop().time()
                
                # Check if we're still connected to voice
                if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                    # Don't respond to commands
                    ctx = await self.bot.get_context(message)
                    if ctx.valid:
                        return
                        
                    # Generate AI response
                    await self.respond_with_voice(message)
    
    async def respond_with_voice(self, message):
        """Generate an AI response and play it through voice"""
        try:
            # Get reference to the AI chat cog to use its response generation
            ai_cog = self.bot.get_cog('AIChat')
            if not ai_cog:
                logger.error("AIChat cog not found, cannot generate voice response")
                await message.channel.send(embed=create_error_embed(
                    "Error", "AI system is not available right now"
                ))
                return
                
            # Use typing indicator to show we're processing
            async with message.channel.typing():
                # Process AI request using the AI chat cog's helper method
                # This gives us more direct access to the AI response generation
                ai_response, provider = await ai_cog._process_ai_request(
                    message.content, 
                    user_id=str(message.author.id),
                    include_history=True
                )
                
                if not ai_response:
                    await message.channel.send(embed=create_error_embed(
                        "Error", "I couldn't generate a response"
                    ))
                    return
                
                # Convert the AI response to speech
                speech_file = await self.text_to_speech(ai_response)
                
                # If text-to-speech is not available, just respond with text and inform the user
                if not speech_file:
                    await message.reply(
                        embed=create_embed(
                            "AI Response (Text Only)", 
                            f"{ai_response}\n\n*Note: Voice response is currently unavailable as the text-to-speech package is not installed.*"
                        )
                    )
                    return
                
                # If we have a speech file, continue with voice playback
                # Get voice client and play the audio
                voice_client = self.voice_clients[message.guild.id]
                
                # Make sure we're not already playing something
                if voice_client.is_playing():
                    voice_client.stop()
                    
                # Create a Discord audio source from the file
                audio_source = discord.FFmpegPCMAudio(speech_file)
                voice_client.play(audio_source, after=lambda e: self.cleanup_audio(speech_file, e))
                
                # Also send the text response
                await message.reply(ai_response)
                
        except Exception as e:
            logger.error(f"Error in voice AI response: {str(e)}")
            await message.channel.send(embed=create_error_embed(
                "Error", f"Something went wrong with voice AI: {str(e)}"
            ))
    
    async def text_to_speech(self, text):
        """Convert text to speech and save to a temporary file"""
        temp_file = None
        try:
            # Create a temporary file for the audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_file.close()
            
            # Try different TTS methods in order of preference
            tts_methods = [
                self._tts_with_gtts,
                self._tts_with_ffmpeg_fallback
            ]
            
            for tts_method in tts_methods:
                try:
                    success = await tts_method(text, temp_file.name)
                    if success:
                        logger.info(f"Successfully generated TTS audio file at {temp_file.name}")
                        return temp_file.name
                except Exception as e:
                    logger.warning(f"TTS method failed: {str(e)}")
                    continue
                    
            # If we get here, all TTS methods failed
            logger.error("All TTS methods failed")
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None
            
        except Exception as e:
            logger.error(f"Critical error in text-to-speech: {str(e)}")
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            return None
            
    async def _tts_with_gtts(self, text, output_file):
        """Use Google Text-to-Speech to generate audio"""
        # Break text into smaller chunks if it's too long (gTTS has limitations)
        # Maximum length is around 500 characters per chunk
        max_chunk_size = 500
        chunks = []
        for i in range(0, len(text), max_chunk_size):
            chunks.append(text[i:i + max_chunk_size])
        
        # If we have multiple chunks, create a separate file for each and then combine
        if len(chunks) > 1:
            chunk_files = []
            for i, chunk in enumerate(chunks):
                chunk_file = f"{output_file}.chunk{i}.mp3"
                # Create TTS for this chunk
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: gTTS(text=chunk, lang='en', slow=False).save(chunk_file))
                chunk_files.append(chunk_file)
            
            # Use ffmpeg to concatenate all chunks
            import subprocess
            concat_list = "|".join(chunk_files)
            result = subprocess.call(["ffmpeg", "-i", f"concat:{concat_list}", "-c", "copy", output_file])
            
            # Clean up chunk files
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    os.unlink(chunk_file)
                    
            return result == 0  # Return True if ffmpeg succeeded
            
        else:
            # If we just have one chunk, create TTS directly
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: gTTS(text=text, lang='en', slow=False).save(output_file))
            return True
            
    async def _tts_with_ffmpeg_fallback(self, text, output_file):
        """Generate speech using FFmpeg as a fallback - creates simple beeps for testing"""
        import subprocess
        
        # Create a silent audio file with text displayed as metadata
        # This is just a fallback so users know TTS is working even if no audio is produced
        subprocess.call([
            "ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", 
            "-metadata", f"title=TTS Fallback - Text: {text[:50]}...", 
            "-c:a", "libmp3lame", "-q:a", "2", output_file
        ])
        
        logger.warning("Using TTS fallback - only beep sound will be played")
        return True
    
    def cleanup_audio(self, file_path, error):
        """Clean up audio file after playing"""
        if error:
            logger.error(f"Error playing audio: {str(error)}")
            
        # Remove the temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up audio file: {str(e)}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state changes like disconnections"""
        # If the bot was disconnected from a voice channel
        if member.id == self.bot.user.id and before.channel and not after.channel:
            guild_id = before.channel.guild.id
            if guild_id in self.voice_clients:
                del self.voice_clients[guild_id]
                
                # End user sessions in this guild
                for user_id, session in list(self.user_sessions.items()):
                    if session["guild_id"] == guild_id:
                        del self.user_sessions[user_id]
        
        # If a user with an active session left the voice channel
        elif member.id in self.user_sessions:
            session = self.user_sessions[member.id]
            guild_id = session["guild_id"]
            
            # Check if user left the voice channel where the bot is
            if guild_id in self.voice_clients and before.channel == self.voice_clients[guild_id].channel:
                if not after.channel or after.channel != self.voice_clients[guild_id].channel:
                    # End this user's session
                    del self.user_sessions[member.id]
    
    @commands.command(name="listen", aliases=["listen_start"])
    async def listen_prefix(self, ctx):
        """Start voice recognition (prefix version)"""
        if not ctx.author.voice:
            await ctx.send(embed=create_error_embed("Error", "You need to be in a voice channel to use this command"))
            return
            
        if ctx.guild.id not in self.voice_clients:
            await ctx.send(embed=create_error_embed("Error", "I need to join your voice channel first. Use !voicechat"))
            return
            
        # Start listening
        await self.start_voice_recognition(ctx.guild.id, ctx.channel)
        await ctx.send(embed=create_embed("🎙️ Listening", "I'm now listening to the voice channel. Speak clearly and I'll respond to what I hear."))
        
    @app_commands.command(name="listen", description="Start voice recognition")
    async def listen(self, interaction: discord.Interaction):
        """Start voice recognition"""
        await interaction.response.defer()
        
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=create_error_embed("Error", "You need to be in a voice channel to use this command"),
                ephemeral=True
            )
            return
            
        if interaction.guild.id not in self.voice_clients:
            await interaction.followup.send(
                embed=create_error_embed("Error", "I need to join your voice channel first. Use /voicechat"),
                ephemeral=True
            )
            return
            
        # Start listening
        await self.start_voice_recognition(interaction.guild.id, interaction.channel)
        await interaction.followup.send(embed=create_embed("🎙️ Listening", "I'm now listening to the voice channel. Speak clearly and I'll respond to what I hear."))
    
    @commands.command(name="listen_stop", aliases=["stop_listen"])
    async def listen_stop_prefix(self, ctx):
        """Stop voice recognition (prefix version)"""
        if ctx.guild.id not in self.listening_status:
            await ctx.send(embed=create_error_embed("Error", "I'm not currently listening to voice"))
            return
            
        # Stop listening
        self.stop_voice_recognition(ctx.guild.id)
        await ctx.send(embed=create_embed("🎙️ Stopped Listening", "I've stopped listening to the voice channel."))
        
    @app_commands.command(name="listen_stop", description="Stop voice recognition")
    async def listen_stop(self, interaction: discord.Interaction):
        """Stop voice recognition"""
        await interaction.response.defer()
        
        if interaction.guild.id not in self.listening_status:
            await interaction.followup.send(
                embed=create_error_embed("Error", "I'm not currently listening to voice"),
                ephemeral=True
            )
            return
            
        # Stop listening
        self.stop_voice_recognition(interaction.guild.id)
        await interaction.followup.send(embed=create_embed("🎙️ Stopped Listening", "I've stopped listening to the voice channel."))
    
    async def start_voice_recognition(self, guild_id, text_channel):
        """Start voice recognition for the given guild"""
        # If we're already listening, do nothing
        if guild_id in self.listening_status and self.listening_status[guild_id]:
            return
            
        # Mark as listening
        self.listening_status[guild_id] = True
        
        # Start voice recognition in a separate thread
        task = asyncio.create_task(self.voice_recognition_loop(guild_id, text_channel))
        self.voice_recognition_tasks[guild_id] = task
    
    def stop_voice_recognition(self, guild_id):
        """Stop voice recognition for the given guild"""
        if guild_id in self.listening_status:
            self.listening_status[guild_id] = False
            
        if guild_id in self.voice_recognition_tasks:
            # Don't cancel the task, just let it loop see that listening is disabled
            # This avoids issues with abruptly stopping audio processing
            self.voice_recognition_tasks[guild_id] = None
    
    async def voice_recognition_loop(self, guild_id, text_channel):
        """Main loop for voice recognition"""
        logger.info(f"Starting voice recognition loop for guild {guild_id}")
        
        # Get the voice client
        voice_client = self.voice_clients.get(guild_id)
        if not voice_client or not voice_client.is_connected():
            logger.error(f"Voice client not found or not connected for guild {guild_id}")
            self.listening_status[guild_id] = False
            return
        
        # Create a sink to capture audio
        sink = discord.sinks.WaveSink()
        voice_client.start_recording(sink, self.finished_recording_callback, text_channel)
        
        # Keep the loop running while we're still listening
        while self.listening_status.get(guild_id, False):
            # We process recordings in the callback so this just needs to stay alive
            await asyncio.sleep(1)
        
        # Stop recording when we're done
        if voice_client.is_connected():
            voice_client.stop_recording()
        
        logger.info(f"Voice recognition loop ended for guild {guild_id}")
    
    def finished_recording_callback(self, sink, channel, *args):
        """Callback for when recording is finished"""
        # The sink callback needs to be a normal function that returns an async function
        # This matches discord.py's expected pattern for sink callbacks
        
        async def process_recorded_audio():
            logger.info(f"Processing recorded audio in channel {channel.name}")
            logger.info(f"Number of audio files received: {len(sink.audio_data)}")
            
            # Check if we have any audio data
            if not sink.audio_data:
                logger.warning("No audio data received in this recording session")
                await channel.send(embed=create_error_embed(
                    "Voice Recognition Issue", 
                    "No audio was captured during this recording session. Make sure your microphone is working and not muted in Discord."
                ))
                return
                
            # Process each audio file (one per user)
            for user_id, audio in sink.audio_data.items():
                if not audio.file:
                    logger.warning(f"No audio file for user {user_id}")
                    continue
                    
                logger.info(f"Processing audio from user {user_id}")
                
                try:
                    # Process the audio file
                    text = await self.process_voice_audio(audio.file)
                    
                    # Get the user object
                    user = self.bot.get_user(int(user_id))
                    if not user:
                        logger.warning(f"Could not find user with ID {user_id}")
                        continue
                        
                    if text:
                        # Log what we heard for debugging
                        logger.info(f"Recognized text from {user.display_name}: {text}")
                        
                        # Process the recognized text as if it were a message
                        await channel.send(embed=create_embed(
                            f"🎤 Voice from {user.display_name}", 
                            f"I heard: {text}"
                        ))
                        
                        # Create a simulated message for AI processing
                        class SimulatedMessage:
                            def __init__(self, content, author, channel, guild):
                                self.content = content
                                self.author = author
                                self.channel = channel
                                self.guild = guild
                            async def reply(self, content=None, embed=None):
                                return await channel.send(content=content, embed=embed)
                        
                        simulated_msg = SimulatedMessage(
                            content=text,
                            author=user,
                            channel=channel,
                            guild=channel.guild
                        )
                        
                        # Process with AI
                        await self.respond_with_voice(simulated_msg)
                    else:
                        logger.warning(f"No text recognized from {user.display_name}'s audio")
                        # Only notify in Discord occasionally to avoid spam
                        if random.random() < 0.3:  # 30% chance to show message
                            await channel.send(embed=create_error_embed(
                                "Voice Recognition", 
                                f"I couldn't understand what {user.display_name} said. Please speak clearly and try again."
                            ))
                    
                except Exception as e:
                    logger.error(f"Error processing audio: {str(e)}")
                    await channel.send(embed=create_error_embed(
                        "Voice Recognition Error", 
                        f"I couldn't process the audio: {str(e)}"
                    ))
        
        # Return the async function
        return process_recorded_audio
    
    async def process_voice_audio(self, audio_file):
        """Process voice audio and convert to text"""
        temp_path = None
        try:
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                logger.info(f"Created temporary WAV file at: {temp_path}")
            
            # Get audio file size and position before writing
            audio_file.seek(0, 2)  # Go to end of file
            file_size = audio_file.tell()
            audio_file.seek(0)  # Reset to beginning
            
            logger.info(f"Original audio file size: {file_size} bytes")
            
            if file_size == 0:
                logger.warning("Audio file is empty, no data to process")
                return None
            
            # Copy the audio data to the temp file
            with open(temp_path, 'wb') as f:
                data = audio_file.read()
                f.write(data)
                logger.info(f"Wrote {len(data)} bytes to temporary WAV file")
            
            # Verify file was written correctly
            if os.path.getsize(temp_path) == 0:
                logger.error("Failed to write audio data to temporary file")
                return None
                
            # Debug file format info
            try:
                with wave.open(temp_path, 'rb') as wave_file:
                    channels = wave_file.getnchannels()
                    sample_width = wave_file.getsampwidth()
                    frame_rate = wave_file.getframerate()
                    frames = wave_file.getnframes()
                    duration = frames / float(frame_rate)
                    
                    logger.info(f"WAV file info: channels={channels}, sample_width={sample_width}, "
                               f"frame_rate={frame_rate}, frames={frames}, duration={duration:.2f}s")
                    
                    # Warning for extremely short audio
                    if duration < 0.2:
                        logger.warning(f"Audio duration too short: {duration:.2f}s - may not contain speech")
            except Exception as wave_err:
                logger.error(f"Error reading WAV file info: {str(wave_err)}")
            
            # Use SpeechRecognition to convert audio to text
            logger.info("Running speech recognition on audio file...")
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._recognize_speech, temp_path)
            
            if text:
                logger.info(f"Successfully converted audio to text: '{text}'")
            else:
                logger.warning("Failed to recognize any speech in the audio")
            
            return text
            
        except Exception as e:
            logger.error(f"Error processing voice audio: {str(e)}")
            return None
            
        finally:
            # Clean up the temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {str(e)}")
    
    def _recognize_speech(self, audio_file_path):
        """Helper method to run speech recognition on a file"""
        # Use energy-based noise detection to filter out background noise
        try:
            # Log the start of speech recognition
            logger.info(f"Starting speech recognition on file: {audio_file_path}")
            
            # Debug: check if file exists and has content
            file_size = os.path.getsize(audio_file_path)
            logger.info(f"Audio file size: {file_size} bytes")
            if file_size == 0:
                logger.error("Audio file is empty - no data to process")
                return None
                
            # Store the initial energy threshold - default is 300
            initial_threshold = self.recognizer.energy_threshold
            logger.info(f"Initial energy threshold: {initial_threshold}")
            
            # Set a very low energy threshold to catch quiet speech
            self.recognizer.energy_threshold = 50
            logger.info(f"Set initial energy threshold to: {self.recognizer.energy_threshold}")
            
            with sr.AudioFile(audio_file_path) as source:
                # Adjust for ambient noise with a shorter duration
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                logger.info(f"After ambient adjustment, energy threshold: {self.recognizer.energy_threshold}")
                
                # Record audio data with increased timeout
                logger.info("Recording audio data from file...")
                audio_data = self.recognizer.record(source)
                
                # First attempt: standard recognition
                try:
                    # Use Google's speech recognition service
                    logger.info("Attempting speech recognition with Google Speech Recognition")
                    text = self.recognizer.recognize_google(audio_data)
                    logger.info(f"Successfully recognized text: {text}")
                    return text
                except sr.UnknownValueError:
                    logger.warning("Google Speech Recognition could not understand audio")
                except sr.RequestError as e:
                    logger.error(f"Could not request results from Google Speech Recognition service: {e}")
                
                # Second attempt: Try with an even lower energy threshold 
                try:
                    current_threshold = self.recognizer.energy_threshold
                    # Adjust the recognizer to be very sensitive - use a very small threshold
                    self.recognizer.energy_threshold = 30
                    
                    logger.info(f"Retrying with much lower energy threshold: {self.recognizer.energy_threshold}")
                    with sr.AudioFile(audio_file_path) as new_source:
                        new_audio_data = self.recognizer.record(new_source)
                        text = self.recognizer.recognize_google(new_audio_data)
                    
                    logger.info(f"Successfully recognized text with adjusted threshold: {text}")
                    return text
                except (sr.UnknownValueError, sr.RequestError) as e:
                    logger.warning(f"Second recognition attempt failed: {str(e)}")
                    
                # Third attempt: Try with Sphinx (offline) if available
                try:
                    logger.info("Attempting speech recognition with Sphinx (offline)")
                    self.recognizer.energy_threshold = 100  # Middle ground for Sphinx
                    with sr.AudioFile(audio_file_path) as sphinx_source:
                        sphinx_audio = self.recognizer.record(sphinx_source)
                        text = self.recognizer.recognize_sphinx(sphinx_audio)
                        
                    logger.info(f"Successfully recognized text with Sphinx: {text}")
                    return text
                except (sr.UnknownValueError, AttributeError, ImportError) as e:
                    logger.warning(f"Sphinx recognition attempt failed: {str(e)}")
                finally:
                    # Always restore original energy threshold before returning or proceeding
                    self.recognizer.energy_threshold = initial_threshold
                    logger.info(f"Restored energy threshold to {initial_threshold}")
                
        except Exception as e:
            logger.error(f"Error in speech recognition: {str(e)}")
            return None
        # If we get here, all recognition attempts have failed
        logger.error("All speech recognition attempts failed")
        return None

async def setup(bot):
    await bot.add_cog(VoiceAI(bot))