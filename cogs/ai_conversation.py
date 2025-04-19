import discord
import logging
import json
import aiohttp
import os
import re
import asyncio
import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Literal
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import is_mod, is_admin, is_bot_owner
from config import GOOGLE_API_KEY, USE_GOOGLE_AI, COLORS

# Set up logging
logger = logging.getLogger('discord')

class AIConversation(commands.Cog):
    """AI-powered conversation features like summarization and smart responses"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/ai_conversation_config.json"
        self.config = self.load_config()
        
        # Default model is now Gemini 1.5
        self.gemini_model = "models/gemini-1.5-pro"
        self.gemini_api_version = "v1beta"
        
        # Channel histories for summarization
        self.channel_histories = defaultdict(list)
        
        # Common questions and custom responses for smart responses
        if "smart_responses" not in self.config:
            self.config["smart_responses"] = {
                "common_questions": {
                    "how to join": "To join our server activities, check out the #welcome channel and follow the steps there!",
                    "server rules": "You can find our server rules in the #rules channel. Please make sure to read them!",
                    "how to get roles": "Roles are assigned based on your activity and participation. You can also get specific roles by joining events!"
                },
                "enabled_channels": []
            }
        
        # Summarization settings
        if "summarization" not in self.config:
            self.config["summarization"] = {
                "enabled_channels": [],
                "max_messages": 100,  # Maximum messages to store per channel
                "trigger_count": 50,   # How many messages before offering summary
                "summary_cooldown": 3600  # Seconds between summaries (1 hour)
            }
        
        # Save initial config
        self.save_config()
        logger.info("AI Conversation cog initialized")
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "smart_responses": {
                "common_questions": {
                    "how to join": "To join our server activities, check out the #welcome channel and follow the steps there!",
                    "server rules": "You can find our server rules in the #rules channel. Please make sure to read them!",
                    "how to get roles": "Roles are assigned based on your activity and participation. You can also get specific roles by joining events!"
                },
                "enabled_channels": []
            },
            "summarization": {
                "enabled_channels": [],
                "max_messages": 100,
                "trigger_count": 50,
                "summary_cooldown": 3600
            },
            "last_summary": {}  # Track when last summary was posted per channel
        }
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded AI conversation config")
                    
                    # Update with any missing default values
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    
                    return config
            else:
                logger.info("No AI conversation config found, creating default")
                return default_config
        except Exception as e:
            logger.error(f"Error loading AI conversation config: {str(e)}")
            return default_config
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Saved AI conversation config")
        except Exception as e:
            logger.error(f"Error saving AI conversation config: {str(e)}")
    
    async def generate_summary(self, messages: List[Dict]) -> str:
        """Generate a summary of conversation messages using AI"""
        if not messages:
            return "No messages to summarize."
        
        # Use Google AI if available, otherwise use a basic summary
        if USE_GOOGLE_AI and GOOGLE_API_KEY:
            return await self._summarize_with_gemini(messages)
        else:
            return self._basic_summary(messages)
    
    async def _summarize_with_gemini(self, messages: List[Dict]) -> str:
        """Use Google's Gemini API to generate a conversation summary"""
        try:
            url = f"https://generativelanguage.googleapis.com/{self.gemini_api_version}/{self.gemini_model}:generateContent?key={GOOGLE_API_KEY}"
            
            # Format messages for the prompt
            formatted_messages = ""
            for msg in messages:
                formatted_messages += f"{msg['author']}: {msg['content']}\n"
            
            # Create the prompt for summarization
            system_prompt = """
            You are a helpful AI assistant that specializes in summarizing Discord conversations.
            Your task is to create a concise summary of the provided conversation.
            Focus on the main topics discussed, key questions asked and answered, and any decisions made.
            Group related messages together by topic rather than listing everything chronologically.
            Keep your summary clear, informative, and under 400 words.
            """
            
            prompt = f"{system_prompt}\n\nConversation to summarize:\n{formatted_messages}"
            
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": 800
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Gemini API error: {response.status}")
                        error_body = await response.text()
                        logger.error(f"Error details: {error_body[:200]}")
                        return "Error generating summary. Please try again later."
                    
                    data = await response.json()
                    try:
                        # Extract the text response
                        text_parts = data["candidates"][0]["content"]["parts"]
                        summary_text = " ".join([part["text"] for part in text_parts if "text" in part])
                        return summary_text
                    except Exception as e:
                        logger.error(f"Error processing Gemini response: {str(e)}")
                        logger.error(f"Response data: {str(data)[:200]}")
                        return "Error processing summary. Please try again later."
        except Exception as e:
            logger.error(f"Error in Gemini summarization: {str(e)}")
            return "Error generating summary. Please try again later."
    
    def _basic_summary(self, messages: List[Dict]) -> str:
        """Create a basic summary when AI is not available"""
        # Extract basic statistics
        total_messages = len(messages)
        authors = set()
        word_count = 0
        
        for msg in messages:
            authors.add(msg['author'])
            word_count += len(msg['content'].split())
        
        # Calculate average words per message
        avg_words = word_count / total_messages if total_messages > 0 else 0
        
        # Create a basic summary
        summary = f"**Conversation Summary**\n\n"
        summary += f"• {total_messages} messages from {len(authors)} participants\n"
        summary += f"• Total word count: {word_count} (avg: {avg_words:.1f} words per message)\n"
        
        # List active participants
        author_messages = {}
        for msg in messages:
            author = msg['author']
            author_messages[author] = author_messages.get(author, 0) + 1
        
        # Sort authors by message count
        sorted_authors = sorted(author_messages.items(), key=lambda x: x[1], reverse=True)
        
        summary += "\n**Most Active Participants:**\n"
        for author, count in sorted_authors[:5]:
            summary += f"• {author}: {count} messages\n"
        
        return summary
    
    @app_commands.command(name="summarize", description="Generate a summary of recent conversation in this channel")
    async def summarize(self, interaction: discord.Interaction):
        """Generate a summary of recent messages in the channel"""
        await interaction.response.defer()
        
        channel_id = str(interaction.channel.id)
        
        # Collect recent messages
        messages = []
        try:
            async for message in interaction.channel.history(limit=100):
                if not message.author.bot and message.content:
                    messages.append({
                        'author': message.author.display_name,
                        'content': message.content,
                        'timestamp': message.created_at.isoformat()
                    })
        except Exception as e:
            logger.error(f"Error collecting messages: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to collect messages: {str(e)}"),
                ephemeral=True
            )
            return
        
        # If not enough messages, inform the user
        if len(messages) < 5:
            await interaction.followup.send(
                embed=create_error_embed("Not Enough Messages", "There aren't enough messages to summarize (minimum 5 required)."),
                ephemeral=True
            )
            return
        
        # Generate summary
        summary = await self.generate_summary(messages)
        
        # Create embed
        embed = discord.Embed(
            title="💬 Conversation Summary",
            description=summary,
            color=COLORS["PRIMARY"]
        )
        embed.set_footer(text=f"Summary of {len(messages)} messages • {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="enablesmartresponses", description="Enable or disable AI smart responses in a channel")
    @app_commands.describe(
        status="Enable or disable smart responses",
        channel="The channel to configure (default: current channel)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable")
        ]
    )
    @app_commands.check(is_admin)
    async def enablesmartresponses(self, interaction: discord.Interaction, status: str, channel: discord.TextChannel = None):
        """Enable or disable smart responses in a channel"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Use current channel if not specified
        if not channel:
            channel = interaction.channel
        
        channel_id = str(channel.id)
        
        if status == "enable":
            # Add to enabled channels if not already there
            if channel_id not in self.config["smart_responses"]["enabled_channels"]:
                self.config["smart_responses"]["enabled_channels"].append(channel_id)
                await interaction.response.send_message(
                    embed=create_embed("Smart Responses", f"✅ Smart responses have been enabled in {channel.mention}."),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Smart Responses", f"Smart responses are already enabled in {channel.mention}."),
                    ephemeral=True
                )
        else:  # status == "disable"
            # Remove from enabled channels
            if channel_id in self.config["smart_responses"]["enabled_channels"]:
                self.config["smart_responses"]["enabled_channels"].remove(channel_id)
                await interaction.response.send_message(
                    embed=create_embed("Smart Responses", f"❌ Smart responses have been disabled in {channel.mention}."),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Smart Responses", f"Smart responses are already disabled in {channel.mention}."),
                    ephemeral=True
                )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="enablesummarization", description="Enable or disable conversation summarization in a channel")
    @app_commands.describe(
        status="Enable or disable summarization",
        channel="The channel to configure (default: current channel)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable")
        ]
    )
    @app_commands.check(is_admin)
    async def enablesummarization(self, interaction: discord.Interaction, status: str, channel: discord.TextChannel = None):
        """Enable or disable conversation summarization in a channel"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Use current channel if not specified
        if not channel:
            channel = interaction.channel
        
        channel_id = str(channel.id)
        
        if status == "enable":
            # Add to enabled channels if not already there
            if channel_id not in self.config["summarization"]["enabled_channels"]:
                self.config["summarization"]["enabled_channels"].append(channel_id)
                await interaction.response.send_message(
                    embed=create_embed("Conversation Summarization", f"✅ Conversation summarization has been enabled in {channel.mention}."),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Conversation Summarization", f"Conversation summarization is already enabled in {channel.mention}."),
                    ephemeral=True
                )
        else:  # status == "disable"
            # Remove from enabled channels
            if channel_id in self.config["summarization"]["enabled_channels"]:
                self.config["summarization"]["enabled_channels"].remove(channel_id)
                await interaction.response.send_message(
                    embed=create_embed("Conversation Summarization", f"❌ Conversation summarization has been disabled in {channel.mention}."),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    embed=create_embed("Conversation Summarization", f"Conversation summarization is already disabled in {channel.mention}."),
                    ephemeral=True
                )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="addsmartresponse", description="Add a smart response for common questions")
    @app_commands.describe(
        question="The question or phrase to match",
        response="The response the bot should give"
    )
    @app_commands.check(is_admin)
    async def addsmartresponse(self, interaction: discord.Interaction, question: str, response: str):
        """Add or update a smart response for common questions"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Add to common questions
        self.config["smart_responses"]["common_questions"][question.lower()] = response
        
        # Save the config
        self.save_config()
        
        await interaction.response.send_message(
            embed=create_embed("Smart Response Added", f"✅ Added smart response for: **{question}**"),
            ephemeral=True
        )
    
    @app_commands.command(name="listsmartresponses", description="List all configured smart responses")
    async def listsmartresponses(self, interaction: discord.Interaction):
        """List all configured smart responses"""
        await interaction.response.defer(ephemeral=True)
        
        if not self.config["smart_responses"]["common_questions"]:
            await interaction.followup.send(
                embed=create_embed("Smart Responses", "No smart responses have been configured yet."),
                ephemeral=True
            )
            return
        
        # Create embed to list responses
        embed = discord.Embed(
            title="📝 Smart Responses",
            description="The following smart responses are configured:",
            color=COLORS["PRIMARY"]
        )
        
        # Add each question/response pair
        for question, response in self.config["smart_responses"]["common_questions"].items():
            # Truncate long responses
            if len(response) > 200:
                response = response[:197] + "..."
            
            embed.add_field(name=question, value=response, inline=False)
        
        # Add channel info
        enabled_channels = []
        for channel_id in self.config["smart_responses"]["enabled_channels"]:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                enabled_channels.append(channel.mention)
        
        if enabled_channels:
            embed.add_field(
                name="Enabled Channels",
                value=", ".join(enabled_channels),
                inline=False
            )
        else:
            embed.add_field(
                name="Enabled Channels",
                value="Not enabled in any channels",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="removesmartresponse", description="Remove a smart response")
    @app_commands.describe(question="The question or phrase to remove")
    @app_commands.check(is_admin)
    async def removesmartresponse(self, interaction: discord.Interaction, question: str):
        """Remove a smart response"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Try to find the exact question or a close match
        question_lower = question.lower()
        found = False
        
        if question_lower in self.config["smart_responses"]["common_questions"]:
            del self.config["smart_responses"]["common_questions"][question_lower]
            found = True
        else:
            # Look for close matches
            for q in list(self.config["smart_responses"]["common_questions"].keys()):
                if question_lower in q or q in question_lower:
                    del self.config["smart_responses"]["common_questions"][q]
                    found = True
                    break
        
        # Save the config
        self.save_config()
        
        if found:
            await interaction.response.send_message(
                embed=create_embed("Smart Response Removed", f"✅ Removed smart response for: **{question}**"),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Not Found", f"No smart response found for: **{question}**"),
                ephemeral=True
            )
    
    def should_offer_summary(self, channel_id: str) -> bool:
        """Check if we should offer a summary for this channel"""
        # Check if summarization is enabled for this channel
        if channel_id not in self.config["summarization"]["enabled_channels"]:
            return False
        
        # Check if we have enough messages
        if len(self.channel_histories[channel_id]) < self.config["summarization"]["trigger_count"]:
            return False
        
        # Check cooldown
        if "last_summary" not in self.config:
            self.config["last_summary"] = {}
        
        if channel_id in self.config["last_summary"]:
            last_time = datetime.datetime.fromisoformat(self.config["last_summary"][channel_id])
            now = datetime.datetime.utcnow()
            cooldown = datetime.timedelta(seconds=self.config["summarization"]["summary_cooldown"])
            
            if now - last_time < cooldown:
                return False
        
        return True
    
    def get_smart_response(self, content: str) -> Optional[str]:
        """Check if a message matches any smart response patterns"""
        content_lower = content.lower()
        
        for question, response in self.config["smart_responses"]["common_questions"].items():
            # If the content contains the question (case insensitive)
            if question.lower() in content_lower:
                return response
        
        return None
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Process messages for conversation analysis and smart responses"""
        # Ignore messages from bots, including our own
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
        
        channel_id = str(message.channel.id)
        
        # Check for smart responses
        if channel_id in self.config["smart_responses"]["enabled_channels"]:
            smart_response = self.get_smart_response(message.content)
            if smart_response:
                # Send the smart response
                await message.channel.send(
                    content=f"{message.author.mention} {smart_response}"
                )
        
        # Conversation summarization
        if channel_id in self.config["summarization"]["enabled_channels"]:
            # Add message to history
            self.channel_histories[channel_id].append({
                'author': message.author.display_name,
                'content': message.content,
                'timestamp': message.created_at.isoformat()
            })
            
            # Limit history size
            max_messages = self.config["summarization"]["max_messages"]
            if len(self.channel_histories[channel_id]) > max_messages:
                self.channel_histories[channel_id] = self.channel_histories[channel_id][-max_messages:]
            
            # Check if we should offer a summary
            if self.should_offer_summary(channel_id):
                # Update last summary time
                self.config["last_summary"][channel_id] = datetime.datetime.utcnow().isoformat()
                self.save_config()
                
                # Generate and send summary
                summary = await self.generate_summary(self.channel_histories[channel_id])
                
                # Create embed
                embed = discord.Embed(
                    title="💬 Conversation Summary",
                    description=summary,
                    color=COLORS["PRIMARY"]
                )
                embed.set_footer(text=f"Automatic summary of recent messages • {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
                
                await message.channel.send(embed=embed)
                
                # Clear history after sending summary
                self.channel_histories[channel_id] = []

async def setup(bot):
    """Add the AI Conversation cog to the bot"""
    await bot.add_cog(AIConversation(bot))
    logger.info("AI Conversation cog loaded")