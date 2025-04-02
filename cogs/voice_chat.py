"""
Voice chat cog for Discord bot with Vertex AI TTS support
"""
import discord
import logging
import os
import tempfile
import asyncio
import aiohttp
import json
from discord.ext import commands
from discord import app_commands
from utils.embed_helpers import create_embed, create_error_embed
from utils.google_credentials import setup_google_credentials

# Configure logging
logger = logging.getLogger('discord')

# Get Vertex AI settings from environment variables
PROJECT_ID = os.environ.get("VERTEX_AI_PROJECT_ID", "discord-bot-ai-455519")
LOCATION = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
TTS_API_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/text-bison:predict"

class VoiceChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Store voice clients by guild ID
        
        # Setup Google credentials
        credentials_setup = setup_google_credentials()
        if credentials_setup:
            logger.info("Voice Chat cog initialized with Google Cloud credentials")
        else:
            logger.warning("Voice Chat cog initialized without Google Cloud credentials")

    @app_commands.command(name="joinvc", description="Join a voice channel")
    async def join_vc(self, interaction: discord.Interaction):
        """Join the user's current voice channel"""
        try:
            # Check if user is in a voice channel
            if not interaction.user.voice:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "You need to be in a voice channel first!"),
                    ephemeral=True
                )
                return

            voice_channel = interaction.user.voice.channel
            guild_id = interaction.guild_id
            
            # Check if already connected to a voice channel in this guild
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                await interaction.response.send_message(
                    embed=create_embed("Already Connected", "I'm already in a voice channel. Use /leavevc first to disconnect.", color=0xFFA500),
                    ephemeral=True
                )
                return
            
            # Connect to the voice channel
            voice_client = await voice_channel.connect()
            self.voice_clients[guild_id] = voice_client
            
            await interaction.response.send_message(
                embed=create_embed("Connected", f"Joined voice channel: {voice_channel.name}", color=0x00FF00),
                ephemeral=True
            )
            logger.info(f"Joined voice channel {voice_channel.name} in guild {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error joining voice channel: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"Failed to join voice channel: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="leavevc", description="Leave the voice channel")
    async def leave_vc(self, interaction: discord.Interaction):
        """Leave the current voice channel"""
        try:
            guild_id = interaction.guild_id
            
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                await self.voice_clients[guild_id].disconnect()
                del self.voice_clients[guild_id]
                await interaction.response.send_message(
                    embed=create_embed("Disconnected", "Left the voice channel", color=0xFF5733),
                    ephemeral=True
                )
                logger.info(f"Left voice channel in guild {interaction.guild.name}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Not Connected", "I'm not in a voice channel!"),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error leaving voice channel: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"Failed to leave voice channel: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="speak", description="Make the bot speak in the voice channel")
    @app_commands.describe(text="Text for the bot to speak")
    async def speak(self, interaction: discord.Interaction, *, text: str):
        """Speak text using Vertex AI TTS in the voice channel"""
        try:
            await interaction.response.defer()
            
            guild_id = interaction.guild_id
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                await interaction.followup.send(
                    embed=create_error_embed("Not Connected", "I need to join a voice channel first! Use /joinvc"),
                    ephemeral=True
                )
                return
                
            voice_client = self.voice_clients[guild_id]
            
            # Generate TTS audio using Vertex AI
            audio_content = await self.generate_speech(text)
            
            if not audio_content:
                await interaction.followup.send(
                    embed=create_error_embed("TTS Error", "Failed to generate speech"),
                    ephemeral=True
                )
                return
                
            # Save audio content to temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_path = temp_file.name
                
            # Stop any currently playing audio
            if voice_client.is_playing():
                voice_client.stop()
                
            # Play the audio file
            voice_client.play(
                discord.FFmpegPCMAudio(temp_path), 
                after=lambda e: self.cleanup_temp_file(temp_path, e)
            )
            
            await interaction.followup.send(
                embed=create_embed("Speaking", f"Speaking: {text[:100]}{'...' if len(text) > 100 else ''}", color=0x00FFFF)
            )
            logger.info(f"Speaking TTS message in {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error in speak command: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to speak: {str(e)}"),
                ephemeral=True
            )

    async def generate_speech(self, text):
        """Generate speech using Google Cloud Text-to-Speech API"""
        try:
            # Import here to avoid errors if the library isn't installed
            from google.cloud import texttospeech
            
            # Create text-to-speech client
            client = texttospeech.TextToSpeechClient()
            
            # Set up the voice parameters
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Note: Voice names are available here:
            # https://cloud.google.com/text-to-speech/docs/voices
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-J",  # High quality male voice
                ssml_gender=texttospeech.SsmlVoiceGender.MALE
            )
            
            # Select the audio file format
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,  # Normal speaking rate
                pitch=0.0,  # Default pitch
                volume_gain_db=0.0,  # Default volume
                sample_rate_hertz=24000  # High quality audio
            )
            
            # Generate the TTS response
            response = client.synthesize_speech(
                input=synthesis_input, 
                voice=voice, 
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except ImportError:
            logger.error("Google Cloud Text-to-Speech library not installed")
            await self.fallback_tts(text)
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            return None
    
    async def fallback_tts(self, text):
        """Fallback TTS using public API if Google Cloud TTS fails"""
        try:
            # Use Google Translate TTS as fallback (not recommended for production)
            url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={text}&tl=en"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
            return None
        except Exception as e:
            logger.error(f"Error using fallback TTS: {str(e)}")
            return None
            
    def cleanup_temp_file(self, file_path, error):
        """Clean up temporary audio file after playback"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
            if error:
                logger.error(f"Error during playback: {error}")
        except Exception as e:
            logger.error(f"Error cleaning up temp file: {str(e)}")

    @app_commands.command(name="speakai", description="Get AI response and speak it in voice channel")
    @app_commands.describe(question="Question or prompt for the AI")
    async def speak_ai(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and have it respond in voice"""
        try:
            await interaction.response.defer()
            
            guild_id = interaction.guild_id
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                await interaction.followup.send(
                    embed=create_error_embed("Not Connected", "I need to join a voice channel first! Use /joinvc"),
                    ephemeral=True
                )
                return
            
            # Find the AI Chat cog to use its AI response functionality
            ai_cog = self.bot.get_cog("AIChat")
            if not ai_cog:
                await interaction.followup.send(
                    embed=create_error_embed("Error", "AI Chat functionality is not available"),
                    ephemeral=True
                )
                return
                
            # Get AI response using the existing AI logic
            logger.info(f"Getting AI response for voice: {question}")
            system_prompt = "Keep responses concise and conversational, suitable for speaking aloud."
            
            # Use the existing get_google_ai_response method from AI cog if available
            if hasattr(ai_cog, 'get_google_ai_response'):
                response = await ai_cog.get_google_ai_response(question, system_prompt)
            else:
                # Fallback to direct AI response
                await interaction.followup.send(
                    embed=create_error_embed("AI Error", "AI response generation method not available"),
                    ephemeral=True
                )
                return
            
            if not response:
                await interaction.followup.send(
                    embed=create_error_embed("AI Error", "Couldn't generate an AI response"),
                    ephemeral=True
                )
                return
                
            # Generate TTS for the AI response
            voice_client = self.voice_clients[guild_id]
            audio_content = await self.generate_speech(response)
            
            if not audio_content:
                await interaction.followup.send(
                    embed=create_error_embed("TTS Error", "Failed to generate speech for AI response"),
                    ephemeral=True
                )
                return
                
            # Stop any currently playing audio
            if voice_client.is_playing():
                voice_client.stop()
                
            # Save and play audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file.write(audio_content)
                temp_path = temp_file.name
                
            voice_client.play(
                discord.FFmpegPCMAudio(temp_path), 
                after=lambda e: self.cleanup_temp_file(temp_path, e)
            )
            
            # Show the text response too
            embed = create_embed(
                f"🤖 AI Voice Response",
                response,
                color=0x7289DA
            )
            embed.add_field(name="Your Question", value=question)
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Speaking AI response in {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error in speak_ai command: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to get or speak AI response: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(
        name="voicestyle", 
        description="Change the bot's voice style"
    )
    @app_commands.choices(voice=[
        app_commands.Choice(name="Male (Default)", value="en-US-Neural2-J"),
        app_commands.Choice(name="Female", value="en-US-Neural2-F"),
        app_commands.Choice(name="Male (Deep)", value="en-US-Neural2-D"),
        app_commands.Choice(name="Female (Soft)", value="en-US-Wavenet-F"),
        app_commands.Choice(name="British Male", value="en-GB-Neural2-B"),
        app_commands.Choice(name="British Female", value="en-GB-Neural2-C")
    ])
    async def voice_style(self, interaction: discord.Interaction, voice: str):
        """Change the bot's voice style"""
        try:
            # Create a file to store the voice preference
            voice_config_path = f"voice_config_{interaction.guild_id}.json"
            
            config = {
                "voice_name": voice
            }
            
            with open(voice_config_path, 'w') as f:
                json.dump(config, f)
                
            await interaction.response.send_message(
                embed=create_embed("Voice Updated", f"Bot voice style changed to: {voice}", color=0x00FF00),
                ephemeral=True
            )
            logger.info(f"Changed voice style to {voice} in guild {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error changing voice style: {str(e)}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", f"Failed to change voice style: {str(e)}"),
                ephemeral=True
            )

async def setup(bot):
    logger.info("Setting up Voice Chat cog")
    await bot.add_cog(VoiceChat(bot))