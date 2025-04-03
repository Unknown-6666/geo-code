import asyncio
import discord
import logging
import os
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
        
        # Connect to the voice channel
        try:
            if ctx.guild.id in self.voice_clients:
                # If already connected, move to the new channel
                await self.voice_clients[ctx.guild.id].move_to(voice_channel)
            else:
                # Otherwise connect to the channel
                voice_client = await voice_channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
                
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
        
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=create_error_embed("Error", "You need to be in a voice channel to use this command"),
                ephemeral=True
            )
            return
            
        voice_channel = interaction.user.voice.channel
        
        # Connect to the voice channel
        try:
            if interaction.guild.id in self.voice_clients:
                # If already connected, move to the new channel
                await self.voice_clients[interaction.guild.id].move_to(voice_channel)
            else:
                # Otherwise connect to the channel
                voice_client = await voice_channel.connect()
                self.voice_clients[interaction.guild.id] = voice_client
                
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
        """Convert text to speech using gTTS and save to a temporary file"""
        try:
            # Create a temporary file for the audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_file.close()
            
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
                    chunk_file = f"{temp_file.name}.chunk{i}.mp3"
                    # Create TTS for this chunk
                    tts = gTTS(text=chunk, lang='en', slow=False)
                    tts.save(chunk_file)
                    chunk_files.append(chunk_file)
                
                # Use ffmpeg to concatenate all chunks
                import subprocess
                concat_list = "|".join(chunk_files)
                subprocess.call(["ffmpeg", "-i", f"concat:{concat_list}", "-c", "copy", temp_file.name])
                
                # Clean up chunk files
                for chunk_file in chunk_files:
                    os.unlink(chunk_file)
            else:
                # If we just have one chunk, create TTS directly
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(temp_file.name)
            
            logger.info(f"Generated TTS audio file at {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error in text-to-speech: {str(e)}")
            return None
    
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
    
    async def finished_recording_callback(self, sink, channel, *args):
        """Callback for when recording is finished"""
        # Process each audio file (one per user)
        for user_id, audio in sink.audio_data.items():
            if audio.file:
                try:
                    # Process the audio file
                    text = await self.process_voice_audio(audio.file)
                    if text:
                        # Create a message object to simulate a text message
                        user = self.bot.get_user(int(user_id))
                        if user:
                            # Process the recognized text as if it were a message
                            await channel.send(embed=create_embed(
                                f"🎤 Voice from {user.display_name}", 
                                f"I heard: {text}"
                            ))
                            
                            # Create a simulated message
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
                    
                except Exception as e:
                    logger.error(f"Error processing audio: {str(e)}")
    
    async def process_voice_audio(self, audio_file):
        """Process voice audio and convert to text"""
        try:
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Copy the audio data to the temp file
            with open(temp_path, 'wb') as f:
                audio_file.seek(0)
                f.write(audio_file.read())
            
            # Use SpeechRecognition to convert audio to text
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, self._recognize_speech, temp_path)
            
            # Clean up the temp file
            os.unlink(temp_path)
            
            return text
        except Exception as e:
            logger.error(f"Error processing voice audio: {str(e)}")
            return None
    
    def _recognize_speech(self, audio_file_path):
        """Helper method to run speech recognition on a file"""
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio_data)
                return text
        except sr.UnknownValueError:
            logger.warning("Speech Recognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Speech Recognition service: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in speech recognition: {str(e)}")
            return None

async def setup(bot):
    await bot.add_cog(VoiceAI(bot))