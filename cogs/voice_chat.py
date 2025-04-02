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

    async def _join_voice_channel(self, ctx, is_interaction=False):
        """Helper method for joining a voice channel"""
        try:
            # For prefix command: ctx is a commands.Context
            # For slash command: ctx is a discord.Interaction
            user = ctx.author if not is_interaction else ctx.user
            guild = ctx.guild
            guild_id = guild.id
            
            # Check if user is in a voice channel
            if not user.voice:
                message = create_error_embed("Error", "You need to be in a voice channel first!")
                if is_interaction:
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False

            voice_channel = user.voice.channel
            
            # Check if already connected to a voice channel in this guild
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                message = create_embed("Already Connected", "I'm already in a voice channel. Use /leavevc or !leavevc first to disconnect.", color=0xFFA500)
                if is_interaction:
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
            
            # Connect to the voice channel
            voice_client = await voice_channel.connect()
            self.voice_clients[guild_id] = voice_client
            
            message = create_embed("Connected", f"Joined voice channel: {voice_channel.name}", color=0x00FF00)
            if is_interaction:
                await ctx.response.send_message(embed=message, ephemeral=True)
            else:
                await ctx.send(embed=message)
                
            logger.info(f"Joined voice channel {voice_channel.name} in guild {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error joining voice channel: {str(e)}")
            message = create_error_embed("Error", f"Failed to join voice channel: {str(e)}")
            if is_interaction:
                if not ctx.response.is_done():
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.followup.send(embed=message, ephemeral=True)
            else:
                await ctx.send(embed=message)
            return False
            
    @commands.command(name="joinvc", aliases=["join"])
    async def join_vc_prefix(self, ctx):
        """Join the user's current voice channel (prefix command)"""
        await self._join_voice_channel(ctx, is_interaction=False)

    @app_commands.command(name="joinvc", description="Join a voice channel")
    async def join_vc(self, interaction: discord.Interaction):
        """Join the user's current voice channel (slash command)"""
        await self._join_voice_channel(interaction, is_interaction=True)

    async def _leave_voice_channel(self, ctx, is_interaction=False):
        """Helper method for leaving a voice channel"""
        try:
            # For prefix command: ctx is a commands.Context
            # For slash command: ctx is a discord.Interaction
            guild = ctx.guild
            guild_id = guild.id
            
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
                await self.voice_clients[guild_id].disconnect()
                del self.voice_clients[guild_id]
                
                message = create_embed("Disconnected", "Left the voice channel", color=0xFF5733)
                if is_interaction:
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                    
                logger.info(f"Left voice channel in guild {guild.name}")
                return True
            else:
                message = create_error_embed("Not Connected", "I'm not in a voice channel!")
                if is_interaction:
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
        except Exception as e:
            logger.error(f"Error leaving voice channel: {str(e)}")
            message = create_error_embed("Error", f"Failed to leave voice channel: {str(e)}")
            if is_interaction:
                if not ctx.response.is_done():
                    await ctx.response.send_message(embed=message, ephemeral=True)
                else:
                    await ctx.followup.send(embed=message, ephemeral=True)
            else:
                await ctx.send(embed=message)
            return False
    
    @commands.command(name="leavevc", aliases=["leave"])
    async def leave_vc_prefix(self, ctx):
        """Leave the voice channel (prefix command)"""
        await self._leave_voice_channel(ctx, is_interaction=False)
            
    @app_commands.command(name="leavevc", description="Leave the voice channel")
    async def leave_vc(self, interaction: discord.Interaction):
        """Leave the current voice channel (slash command)"""
        await self._leave_voice_channel(interaction, is_interaction=True)

    async def _speak_text(self, ctx, text, is_interaction=False):
        """Helper method for speaking text in voice channel"""
        try:
            guild = ctx.guild
            guild_id = guild.id
            
            # Handle response deferring for interactions
            if is_interaction:
                await ctx.response.defer()
            
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                message = create_error_embed("Not Connected", "I need to join a voice channel first! Use !joinvc or /joinvc")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
            voice_client = self.voice_clients[guild_id]
            
            # Generate TTS audio using Vertex AI with guild voice preferences
            audio_content = await self.generate_speech(text, guild_id)
            
            if not audio_content:
                message = create_error_embed("TTS Error", "Failed to generate speech")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
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
            
            message = create_embed("Speaking", f"Speaking: {text[:100]}{'...' if len(text) > 100 else ''}", color=0x00FFFF)
            if is_interaction:
                await ctx.followup.send(embed=message)
            else:
                await ctx.send(embed=message)
                
            logger.info(f"Speaking TTS message in {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error in speak command: {str(e)}")
            message = create_error_embed("Error", f"Failed to speak: {str(e)}")
            
            if is_interaction:
                await ctx.followup.send(embed=message, ephemeral=True)
            else:
                await ctx.send(embed=message)
            return False
            
    @commands.command(name="speak", aliases=["say", "tts"])
    async def speak_prefix(self, ctx, *, text: str):
        """Make the bot speak text in the voice channel (prefix command)"""
        await self._speak_text(ctx, text, is_interaction=False)
            
    @app_commands.command(name="speak", description="Make the bot speak in the voice channel")
    @app_commands.describe(text="Text for the bot to speak")
    async def speak(self, interaction: discord.Interaction, *, text: str):
        """Speak text using Vertex AI TTS in the voice channel (slash command)"""
        await self._speak_text(interaction, text, is_interaction=True)

    async def generate_speech(self, text, guild_id=None):
        """Generate speech using Google Cloud Text-to-Speech API"""
        try:
            # Import here to avoid errors if the library isn't installed
            from google.cloud import texttospeech
            
            # Create text-to-speech client
            client = texttospeech.TextToSpeechClient()
            
            # Set up the voice parameters
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Default voice
            voice_name = "en-US-Neural2-J"  # Default to high quality male voice
            gender = texttospeech.SsmlVoiceGender.MALE
            language_code = "en-US"
            
            # Check if there's a custom voice config for this guild
            if guild_id:
                voice_config_path = f"voice_config_{guild_id}.json"
                try:
                    if os.path.exists(voice_config_path):
                        with open(voice_config_path, 'r') as f:
                            config = json.load(f)
                            if "voice_name" in config:
                                voice_name = config["voice_name"]
                                
                                # Set appropriate gender based on voice name
                                if "female" in voice_name.lower() or voice_name.endswith("-F") or voice_name.endswith("-C"):
                                    gender = texttospeech.SsmlVoiceGender.FEMALE
                                
                                # Set language code based on voice name
                                if voice_name.startswith("en-GB"):
                                    language_code = "en-GB"
                                elif voice_name.startswith("en-US"):
                                    language_code = "en-US"
                                
                                logger.debug(f"Using custom voice: {voice_name}")
                except Exception as e:
                    logger.error(f"Error loading voice config: {str(e)}")
            
            # Note: Voice names are available here:
            # https://cloud.google.com/text-to-speech/docs/voices
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=gender
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
            return await self.fallback_tts(text)
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

    async def _speak_ai_response(self, ctx, question, is_interaction=False):
        """Helper method for getting AI response and speaking it"""
        try:
            guild = ctx.guild
            guild_id = guild.id
            
            # Handle response deferring for interactions
            if is_interaction:
                await ctx.response.defer()
            
            if guild_id not in self.voice_clients or not self.voice_clients[guild_id].is_connected():
                message = create_error_embed("Not Connected", "I need to join a voice channel first! Use !joinvc or /joinvc")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
            
            # Find the AI Chat cog to use its AI response functionality
            ai_cog = self.bot.get_cog("AIChat")
            if not ai_cog:
                message = create_error_embed("Error", "AI Chat functionality is not available")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
            # Get AI response using the existing AI logic
            logger.info(f"Getting AI response for voice: {question}")
            system_prompt = "Keep responses concise and conversational, suitable for speaking aloud."
            
            # Use the existing get_google_ai_response method from AI cog if available
            if hasattr(ai_cog, 'get_google_ai_response'):
                response = await ai_cog.get_google_ai_response(question, system_prompt)
            else:
                # Fallback to direct AI response
                message = create_error_embed("AI Error", "AI response generation method not available")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
            
            if not response:
                message = create_error_embed("AI Error", "Couldn't generate an AI response")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
            # Generate TTS for the AI response with guild voice preferences
            voice_client = self.voice_clients[guild_id]
            audio_content = await self.generate_speech(response, guild_id)
            
            if not audio_content:
                message = create_error_embed("TTS Error", "Failed to generate speech for AI response")
                if is_interaction:
                    await ctx.followup.send(embed=message, ephemeral=True)
                else:
                    await ctx.send(embed=message)
                return False
                
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
            
            if is_interaction:
                await ctx.followup.send(embed=embed)
            else:
                await ctx.send(embed=embed)
                
            logger.info(f"Speaking AI response in {guild.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error in speak_ai command: {str(e)}")
            message = create_error_embed("Error", f"Failed to get or speak AI response: {str(e)}")
            if is_interaction:
                await ctx.followup.send(embed=message, ephemeral=True)
            else:
                await ctx.send(embed=message)
            return False
    
    @commands.command(name="speakai", aliases=["askai", "askvoice"])
    async def speak_ai_prefix(self, ctx, *, question: str):
        """Ask the AI a question and have it respond in voice (prefix command)"""
        await self._speak_ai_response(ctx, question, is_interaction=False)
            
    @app_commands.command(name="speakai", description="Get AI response and speak it in voice channel")
    @app_commands.describe(question="Question or prompt for the AI")
    async def speak_ai(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and have it respond in voice (slash command)"""
        await self._speak_ai_response(interaction, question, is_interaction=True)

    # List of available voice choices
    VOICE_CHOICES = {
        "male": "en-US-Neural2-J",     # Default male
        "female": "en-US-Neural2-F",   # Default female
        "deep": "en-US-Neural2-D",     # Deep male
        "soft": "en-US-Wavenet-F",     # Soft female
        "british-male": "en-GB-Neural2-B", # British male
        "british-female": "en-GB-Neural2-C" # British female
    }
    
    @commands.command(name="voicestyle", aliases=["voice"])
    async def voice_style_prefix(self, ctx, style: str = None):
        """Change the bot's voice style (prefix command)
        
        Available styles: male, female, deep, soft, british-male, british-female
        Example: !voicestyle female
        """
        if not style:
            # Show available styles
            styles_list = "\n".join([f"• `{name}`: {desc}" for name, desc in {
                "male": "Default male voice",
                "female": "Default female voice",
                "deep": "Deep male voice",
                "soft": "Soft female voice",
                "british-male": "British male accent",
                "british-female": "British female accent"
            }.items()])
            
            embed = create_embed(
                "Available Voice Styles",
                f"Use `!voicestyle <style>` to change the voice.\n\n{styles_list}",
                color=0x00FFFF
            )
            await ctx.send(embed=embed)
            return
            
        style = style.lower()
        if style not in self.VOICE_CHOICES:
            await ctx.send(
                embed=create_error_embed(
                    "Invalid Style", 
                    f"'{style}' is not a valid voice style. Use `!voicestyle` to see options."
                )
            )
            return
            
        voice_name = self.VOICE_CHOICES[style]
        
        try:
            # Create a file to store the voice preference
            voice_config_path = f"voice_config_{ctx.guild.id}.json"
            
            config = {
                "voice_name": voice_name
            }
            
            with open(voice_config_path, 'w') as f:
                json.dump(config, f)
                
            await ctx.send(
                embed=create_embed("Voice Updated", f"Bot voice style changed to: {style}", color=0x00FF00)
            )
            logger.info(f"Changed voice style to {voice_name} in guild {ctx.guild.name}")
            
        except Exception as e:
            logger.error(f"Error changing voice style: {str(e)}")
            await ctx.send(
                embed=create_error_embed("Error", f"Failed to change voice style: {str(e)}")
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
        """Change the bot's voice style (slash command)"""
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