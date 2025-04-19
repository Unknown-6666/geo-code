import discord
import logging
import json
import aiohttp
import os
import re
import datetime
from typing import Dict, List, Tuple, Optional, Literal
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import is_mod, is_admin, is_bot_owner, PermissionChecks
from config import GOOGLE_API_KEY, USE_GOOGLE_AI, USE_VERTEX_AI, GOOGLE_CLOUD_PROJECT, VERTEX_LOCATION, COLORS

# Import Vertex AI clients if available
try:
    from utils.vertex_ai_client import VertexAIClient
    HAS_VERTEX_AI = True
except ImportError:
    HAS_VERTEX_AI = False

# Import our REST API client as fallback
try:
    from utils.vertex_api_client import VertexRESTClient
    HAS_VERTEX_REST = True
except ImportError:
    HAS_VERTEX_REST = False

# Set up logging
logger = logging.getLogger('discord')

class AIModeration(commands.Cog):
    """AI-powered content moderation and analysis"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/ai_moderation_config.json"
        self.config = self.load_config()
        
        # Default model is now Gemini 1.5 (latest version)
        self.gemini_model = "models/gemini-1.5-pro-latest"
        self.gemini_api_version = "v1beta"
        
        # Initialize Vertex AI clients (primary)
        self.vertex_client = None
        self.vertex_rest_client = None
        self.use_vertex_ai = USE_VERTEX_AI
        
        # Try the SDK client first (if available)
        if HAS_VERTEX_AI and self.use_vertex_ai:
            try:
                self.vertex_client = VertexAIClient()
                if self.vertex_client.initialized:
                    logger.info("Vertex AI SDK client initialized successfully for moderation")
                else:
                    logger.warning("Vertex AI SDK client failed to initialize properly")
            except Exception as e:
                logger.error(f"Error initializing Vertex AI SDK client: {str(e)}")
                self.vertex_client = None
                
        # Try the REST API client as fallback or if SDK client failed
        if HAS_VERTEX_REST and self.use_vertex_ai and (not self.vertex_client or not self.vertex_client.initialized):
            try:
                logger.info("Attempting to initialize Vertex REST API client...")
                self.vertex_rest_client = VertexRESTClient()
                if self.vertex_rest_client.initialized:
                    logger.info("Vertex REST API client initialized successfully for moderation")
                else:
                    logger.warning("Vertex REST API client failed to initialize properly")
            except Exception as e:
                logger.error(f"Error initializing Vertex REST API client: {str(e)}")
                self.vertex_rest_client = None
                
        # Log status
        if self.use_vertex_ai and not (self.vertex_client or self.vertex_rest_client):
            logger.warning("Vertex AI requested but both client methods failed to initialize for moderation")
            logger.warning("Will use Google AI API or basic analysis as fallbacks")
        
        # Set default thresholds
        if "toxicity_threshold" not in self.config:
            self.config["toxicity_threshold"] = 0.7
        if "spam_threshold" not in self.config:
            self.config["spam_threshold"] = 0.7
        if "enabled_guilds" not in self.config:
            self.config["enabled_guilds"] = {}
        if "enabled_features" not in self.config:
            self.config["enabled_features"] = {
                "content_filtering": True,
                "spam_detection": True,
                "toxicity_analysis": True,
                "raid_protection": False,
                "conversation_summarization": False,
                "smart_responses": False,
                "image_moderation": False
            }
        
        # Save initial config
        self.save_config()
        logger.info("AI Moderation cog initialized")
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "toxicity_threshold": 0.7,
            "spam_threshold": 0.7,
            "enabled_guilds": {},
            "enabled_features": {
                "content_filtering": True,
                "spam_detection": True,
                "toxicity_analysis": True,
                "raid_protection": False,
                "conversation_summarization": False,
                "smart_responses": False,
                "image_moderation": False
            },
            "message_history": {},
            "raid_detection": {
                "join_threshold": 5,  # Number of joins in timeframe to trigger alert
                "timeframe_seconds": 60,  # Timeframe for join rate monitoring
                "enabled": False
            }
        }
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded AI moderation config")
                    
                    # Update with any missing default values
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    
                    return config
            else:
                logger.info("No AI moderation config found, creating default")
                return default_config
        except Exception as e:
            logger.error(f"Error loading AI moderation config: {str(e)}")
            return default_config
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Saved AI moderation config")
        except Exception as e:
            logger.error(f"Error saving AI moderation config: {str(e)}")
    
    def is_feature_enabled(self, feature: str, guild_id: str) -> bool:
        """Check if a feature is enabled for a guild"""
        # Convert guild_id to string
        guild_id = str(guild_id)
        
        # Check if the guild has AI moderation enabled
        if guild_id not in self.config["enabled_guilds"]:
            return False
        
        if not self.config["enabled_guilds"].get(guild_id, False):
            return False
            
        # Check if the specific feature is enabled globally
        if feature not in self.config["enabled_features"]:
            return False
            
        return self.config["enabled_features"].get(feature, False)
    
    async def analyze_content_toxicity(self, content: str) -> Tuple[float, str]:
        """
        Analyze the toxicity of content using Vertex AI as primary or fallback methods
        Returns a tuple of (toxicity_score, category)
        """
        if not content or len(content.strip()) == 0:
            return 0.0, "none"
            
        # Try using Vertex AI SDK as primary option if available
        if self.vertex_client and self.vertex_client.initialized:
            try:
                logger.info("Using Vertex AI SDK as primary for toxicity analysis")
                result = await self._analyze_with_vertex_ai(content)
                if result and result[0] > 0:
                    return result
            except Exception as e:
                logger.error(f"Error using Vertex AI SDK for toxicity analysis: {str(e)}")
                # Continue to next fallback
                
        # Try using Vertex REST API as first fallback if available
        if self.vertex_rest_client and self.vertex_rest_client.initialized:
            try:
                logger.info("Using Vertex REST API for toxicity analysis")
                result = await self._analyze_with_vertex_rest(content)
                if result and result[0] > 0:
                    return result
            except Exception as e:
                logger.error(f"Error using Vertex REST API for toxicity analysis: {str(e)}")
                # Continue to next fallback
        
        # Use Google Gemini AI as second fallback if available
        if USE_GOOGLE_AI and GOOGLE_API_KEY:
            try:
                logger.info("Using Google Gemini as fallback for toxicity analysis")
                result = await self._analyze_with_gemini(content)
                if result and result[0] > 0:
                    return result
            except Exception as e:
                logger.error(f"Error using Gemini for toxicity analysis: {str(e)}")
                # Continue to next fallback
        
        # Fallback to basic analysis as last resort
        logger.info("Using basic pattern analysis as last resort for toxicity analysis")
        return self._basic_toxicity_analysis(content)
    
    async def _analyze_with_gemini(self, content: str) -> Tuple[float, str]:
        """Use Google's Gemini API to analyze content toxicity"""
        try:
            url = f"https://generativelanguage.googleapis.com/{self.gemini_api_version}/{self.gemini_model}:generateContent?key={GOOGLE_API_KEY}"
            
            # Create the prompt specifically for content moderation
            system_prompt = """
            You are a content moderation AI. Your task is to analyze the provided text and evaluate it for toxicity, inappropriateness, harassment, and policy violations.
            
            Analyze the following text and respond with ONLY a JSON object in this exact format:
            {
                "toxicity_score": [a value from 0.0 to 1.0 where higher means more toxic],
                "category": [one of: "none", "mild", "moderate", "severe"],
                "reason": [brief explanation if toxic, "none" if not toxic]
            }
            
            DO NOT include any other text, explanation, or formatting in your response. Only return the JSON object.
            """
            
            # Combine system prompt and content
            prompt = f"{system_prompt}\n\nText to analyze: {content}"
            
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.0,  # Use deterministic responses for moderation
                    "topP": 1.0,
                    "topK": 1,
                    "maxOutputTokens": 200
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Gemini API error: {response.status}")
                        error_body = await response.text()
                        logger.error(f"Error details: {error_body[:200]}")
                        return 0.0, "none"
                    
                    data = await response.json()
                    try:
                        # Extract the text response
                        text_parts = data["candidates"][0]["content"]["parts"]
                        response_text = " ".join([part["text"] for part in text_parts if "text" in part])
                        
                        # Extract JSON from the response
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        if json_start != -1 and json_end != -1:
                            json_str = response_text[json_start:json_end]
                            result = json.loads(json_str)
                            
                            # Extract the values
                            toxicity_score = float(result.get("toxicity_score", 0.0))
                            category = result.get("category", "none")
                            
                            return toxicity_score, category
                        else:
                            logger.warning(f"Could not find JSON in response: {response_text[:100]}")
                            return 0.0, "none"
                    except Exception as e:
                        logger.error(f"Error processing Gemini response: {str(e)}")
                        logger.error(f"Response data: {str(data)[:200]}")
                        return 0.0, "none"
        except Exception as e:
            logger.error(f"Error in Gemini toxicity analysis: {str(e)}")
            return 0.0, "none"
    
    async def _analyze_with_vertex_ai(self, content: str) -> Tuple[float, str]:
        """Use Vertex AI SDK to analyze content toxicity"""
        try:
            # Create the prompt specifically for content moderation
            system_prompt = """
            You are a content moderation AI. Your task is to analyze the provided text and evaluate it for toxicity, inappropriateness, harassment, and policy violations.
            
            Analyze the following text and respond with ONLY a JSON object in this exact format:
            {
                "toxicity_score": [a value from 0.0 to 1.0 where higher means more toxic],
                "category": [one of: "none", "mild", "moderate", "severe"],
                "reason": [brief explanation if toxic, "none" if not toxic]
            }
            
            DO NOT include any other text, explanation, or formatting in your response. Only return the JSON object.
            """
            
            # Combine system prompt and content
            prompt = f"{system_prompt}\n\nText to analyze: {content}"
            
            # Send to Vertex AI
            response = await self.vertex_client.generate_text(
                prompt=prompt,
                system_prompt=None,  # We've already combined the prompts
                temperature=0.0,  # Use deterministic responses for moderation
                max_output_tokens=200
            )
            
            if not response:
                logger.warning("No response from Vertex AI")
                return 0.0, "none"
                
            # Extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Extract the values
                toxicity_score = float(result.get("toxicity_score", 0.0))
                category = result.get("category", "none")
                
                logger.info(f"Vertex AI toxicity analysis result: {toxicity_score}, {category}")
                return toxicity_score, category
            else:
                logger.warning(f"Could not find JSON in Vertex AI response: {response[:100]}")
                return 0.0, "none"
                
        except Exception as e:
            logger.error(f"Error in Vertex AI toxicity analysis: {str(e)}")
            return 0.0, "none"
    
    async def _analyze_with_vertex_rest(self, content: str) -> Tuple[float, str]:
        """Use Vertex AI REST API to analyze content toxicity"""
        try:
            # Create the prompt specifically for content moderation
            system_prompt = """
            You are a content moderation AI. Your task is to analyze the provided text and evaluate it for toxicity, inappropriateness, harassment, and policy violations.
            
            Analyze the following text and respond with ONLY a JSON object in this exact format:
            {
                "toxicity_score": [a value from 0.0 to 1.0 where higher means more toxic],
                "category": [one of: "none", "mild", "moderate", "severe"],
                "reason": [brief explanation if toxic, "none" if not toxic]
            }
            
            DO NOT include any other text, explanation, or formatting in your response. Only return the JSON object.
            """
            
            # Combine system prompt and content
            prompt = f"{system_prompt}\n\nText to analyze: {content}"
            
            # Send to Vertex AI REST API
            response = await self.vertex_rest_client.generate_text(
                prompt=prompt,
                temperature=0.0,  # Use deterministic responses for moderation
                max_output_tokens=200
            )
            
            if not response:
                logger.warning("No response from Vertex AI REST API")
                return 0.0, "none"
                
            # Extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Extract the values
                toxicity_score = float(result.get("toxicity_score", 0.0))
                category = result.get("category", "none")
                
                logger.info(f"Vertex AI REST toxicity analysis result: {toxicity_score}, {category}")
                return toxicity_score, category
            else:
                logger.warning(f"Could not find JSON in Vertex AI REST response: {response[:100]}")
                return 0.0, "none"
                
        except Exception as e:
            logger.error(f"Error in Vertex AI REST toxicity analysis: {str(e)}")
            return 0.0, "none"
    
    def _basic_toxicity_analysis(self, content: str) -> Tuple[float, str]:
        """Basic fallback toxicity analysis using regex patterns"""
        # List of potentially problematic patterns
        profanity_patterns = [
            r'\b(f+u+c+k+|s+h+i+t+|b+i+t+c+h+|a+s+s+h+o+l+e+|d+i+c+k+|p+u+s+s+y+|c+u+n+t+)\b',
            r'\b(n+i+g+g+[aer]+|f+a+g+g*o*t+)\b',  # Slurs
            r'\b(k+y+s+|k+i+l+l+ *y+o+u+r+s+e+l+f+)\b',  # Self-harm
            r'\b(r+a+p+e+|m+o+l+e+s+t+)\b',  # Violence
        ]
        
        # Check for matches
        toxicity_score = 0.0
        matched_patterns = 0
        
        for pattern in profanity_patterns:
            if re.search(pattern, content.lower()):
                matched_patterns += 1
        
        # Calculate a simple toxicity score based on matched patterns
        if matched_patterns > 0:
            toxicity_score = min(1.0, matched_patterns / len(profanity_patterns) * 2)
        
        # Determine category
        if toxicity_score == 0:
            category = "none"
        elif toxicity_score < 0.4:
            category = "mild"
        elif toxicity_score < 0.7:
            category = "moderate"
        else:
            category = "severe"
        
        return toxicity_score, category
    
    async def detect_spam(self, message: discord.Message) -> Tuple[bool, float]:
        """
        Detect if a message is likely spam
        Returns a tuple of (is_spam, confidence)
        """
        # Skip short messages
        if len(message.content) < 10:
            return False, 0.0
        
        # Check for common spam indicators
        indicators = 0
        confidence = 0.0
        
        # 1. Excessive caps
        caps_ratio = sum(1 for c in message.content if c.isupper()) / len(message.content)
        if caps_ratio > 0.7 and len(message.content) > 10:
            indicators += 1
        
        # 2. Repeated characters
        repeated_chars_pattern = r'(.)\1{5,}'
        if re.search(repeated_chars_pattern, message.content):
            indicators += 1
        
        # 3. Message repetition (check user's recent messages)
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)
        
        if "message_history" not in self.config:
            self.config["message_history"] = {}
            
        if guild_id not in self.config["message_history"]:
            self.config["message_history"][guild_id] = {}
            
        if user_id not in self.config["message_history"][guild_id]:
            self.config["message_history"][guild_id][user_id] = []
        
        # Add current message to history
        self.config["message_history"][guild_id][user_id].append({
            "content": message.content,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        # Keep only recent messages (last 10)
        self.config["message_history"][guild_id][user_id] = self.config["message_history"][guild_id][user_id][-10:]
        
        # Check for repeated messages
        recent_messages = self.config["message_history"][guild_id][user_id]
        if len(recent_messages) >= 3:
            # Check if the last 3 messages are identical
            if len(set(msg["content"] for msg in recent_messages[-3:])) == 1:
                indicators += 2  # Strong indicator
        
        # 4. Multiple mentions
        if len(message.mentions) > 5:
            indicators += 1
        
        # 5. Multiple role mentions
        if len(message.role_mentions) > 3:
            indicators += 1
        
        # 6. Everyone/here mention
        if message.mention_everyone:
            indicators += 1
        
        # 7. Multiple links
        url_pattern = r'https?://\S+'
        urls = re.findall(url_pattern, message.content)
        if len(urls) > 2:
            indicators += 1
        
        # Calculate confidence based on indicators
        confidence = min(1.0, indicators / 5)
        is_spam = confidence >= self.config["spam_threshold"]
        
        return is_spam, confidence
    
    @app_commands.command(name="moderateai", description="Enable or disable AI moderation for this server")
    @app_commands.describe(
        status="Enable or disable AI moderation",
        feature="Which AI moderation feature to configure (default: all)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable")
        ],
        feature=[
            app_commands.Choice(name="All Features", value="all"),
            app_commands.Choice(name="Content Filtering", value="content_filtering"),
            app_commands.Choice(name="Spam Detection", value="spam_detection"),
            app_commands.Choice(name="Toxicity Analysis", value="toxicity_analysis"),
            app_commands.Choice(name="Raid Protection", value="raid_protection"),
            app_commands.Choice(name="Conversation Summarization", value="conversation_summarization"),
            app_commands.Choice(name="Smart Responses", value="smart_responses"),
            app_commands.Choice(name="Image Moderation", value="image_moderation")
        ]
    )
    @app_commands.check(PermissionChecks.slash_is_admin())
    async def moderateai(self, interaction: discord.Interaction, status: str, feature: str = "all"):
        """Enable or disable AI moderation for this server"""
        # Check admin permissions
        if not is_admin(interaction) and not is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Get the guild ID as string
        guild_id = str(interaction.guild.id)
        
        # Make sure the guild is in the config
        if guild_id not in self.config["enabled_guilds"]:
            self.config["enabled_guilds"][guild_id] = False
        
        # Enable or disable based on the status
        if status == "enable":
            if feature == "all":
                self.config["enabled_guilds"][guild_id] = True
                await interaction.response.send_message(
                    embed=create_embed("AI Moderation", "✅ AI moderation has been enabled for this server."),
                    ephemeral=True
                )
            else:
                # Enable the specific feature
                self.config["enabled_features"][feature] = True
                self.config["enabled_guilds"][guild_id] = True
                
                feature_name = feature.replace("_", " ").title()
                await interaction.response.send_message(
                    embed=create_embed("AI Moderation", f"✅ AI moderation feature '{feature_name}' has been enabled."),
                    ephemeral=True
                )
        else:  # status == "disable"
            if feature == "all":
                self.config["enabled_guilds"][guild_id] = False
                await interaction.response.send_message(
                    embed=create_embed("AI Moderation", "❌ AI moderation has been disabled for this server."),
                    ephemeral=True
                )
            else:
                # Disable the specific feature
                self.config["enabled_features"][feature] = False
                
                feature_name = feature.replace("_", " ").title()
                await interaction.response.send_message(
                    embed=create_embed("AI Moderation", f"❌ AI moderation feature '{feature_name}' has been disabled."),
                    ephemeral=True
                )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="setthreshold", description="Set AI moderation thresholds")
    @app_commands.describe(
        threshold_type="Which threshold to configure",
        value="Threshold value (0.0 to 1.0, where 1.0 is most strict)"
    )
    @app_commands.choices(
        threshold_type=[
            app_commands.Choice(name="Toxicity", value="toxicity"),
            app_commands.Choice(name="Spam", value="spam")
        ]
    )
    @app_commands.check(PermissionChecks.slash_is_admin())
    async def setthreshold(self, interaction: discord.Interaction, threshold_type: str, value: float):
        """Set AI moderation thresholds"""
        # Check admin permissions
        if not is_admin(interaction) and not is_bot_owner(interaction.user.id):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Validate the value
        if not 0.0 <= value <= 1.0:
            await interaction.response.send_message(
                embed=create_error_embed("Invalid Value", "Threshold must be between 0.0 and 1.0."),
                ephemeral=True
            )
            return
        
        # Update the appropriate threshold
        if threshold_type == "toxicity":
            self.config["toxicity_threshold"] = value
            threshold_name = "Toxicity"
        else:  # threshold_type == "spam"
            self.config["spam_threshold"] = value
            threshold_name = "Spam"
        
        # Save the config
        self.save_config()
        
        await interaction.response.send_message(
            embed=create_embed(
                "Threshold Updated", 
                f"✅ {threshold_name} threshold has been set to {value:.2f}."
            ),
            ephemeral=True
        )
    
    @app_commands.command(name="analyzetext", description="Analyze text for toxicity and other issues")
    @app_commands.describe(text="The text to analyze")
    async def analyzetext(self, interaction: discord.Interaction, text: str):
        """Analyze text for toxicity and other issues"""
        await interaction.response.defer(ephemeral=True)
        
        # Analyze the content
        toxicity_score, category = await self.analyze_content_toxicity(text)
        
        # Create the embed
        embed = discord.Embed(
            title="Content Analysis Results",
            description=f"Analysis of the provided text:",
            color=COLORS["PRIMARY"]
        )
        
        # Add the analysis results
        embed.add_field(name="Toxicity Score", value=f"{toxicity_score:.2f}/1.00", inline=True)
        embed.add_field(name="Category", value=category.title(), inline=True)
        
        # Add a visual indicator
        if category == "none":
            embed.add_field(name="Status", value="✅ This content appears to be safe.", inline=False)
            embed.color = COLORS["SUCCESS"]
        elif category == "mild":
            embed.add_field(name="Status", value="⚠️ This content may be mildly problematic.", inline=False)
            embed.color = COLORS["WARNING"]
        elif category == "moderate":
            embed.add_field(name="Status", value="🚧 This content is moderately concerning.", inline=False)
            embed.color = COLORS["WARNING"]
        else:  # severe
            embed.add_field(name="Status", value="🛑 This content appears to violate policies.", inline=False)
            embed.color = COLORS["ERROR"]
        
        # Spam detection (simple analysis for the command)
        # Create a fake message object for spam detection
        class FakeMessage:
            def __init__(self, content, author, guild):
                self.content = content
                self.author = author
                self.guild = guild
                self.mentions = []
                self.role_mentions = []
                self.mention_everyone = False
        
        fake_msg = FakeMessage(text, interaction.user, interaction.guild)
        is_spam, spam_confidence = await self.detect_spam(fake_msg)
        
        embed.add_field(name="Spam Confidence", value=f"{spam_confidence:.2f}/1.00", inline=True)
        embed.add_field(
            name="Spam Status", 
            value="🚫 Likely spam" if is_spam else "✅ Not spam", 
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages for toxicity and spam"""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        
        # Check if AI moderation is enabled for this guild
        if not self.is_feature_enabled("content_filtering", guild_id) and not self.is_feature_enabled("toxicity_analysis", guild_id):
            return
        
        # Analyze content for toxicity if content filtering is enabled
        if self.is_feature_enabled("content_filtering", guild_id) or self.is_feature_enabled("toxicity_analysis", guild_id):
            toxicity_score, category = await self.analyze_content_toxicity(message.content)
            
            # If toxicity is above threshold, take action
            if toxicity_score >= self.config["toxicity_threshold"] and category in ["moderate", "severe"]:
                try:
                    # Delete the message
                    await message.delete()
                    logger.info(f"Deleted toxic message from {message.author.name} (score: {toxicity_score:.2f}, category: {category})")
                    
                    # Send a warning to the user
                    warning_embed = create_error_embed(
                        "Content Warning", 
                        f"Your message was removed for containing content that violates our community guidelines.\nToxicity score: {toxicity_score:.2f}"
                    )
                    
                    try:
                        await message.author.send(embed=warning_embed)
                    except discord.Forbidden:
                        # Cannot DM the user
                        pass
                    
                    # Log to mod channel if available
                    try:
                        log_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                        if not log_channel:
                            log_channel = discord.utils.get(message.guild.text_channels, name="logs")
                            
                        if log_channel:
                            log_embed = discord.Embed(
                                title="AI Moderation: Toxic Content Removed",
                                description=f"A message from {message.author.mention} was removed for toxic content.",
                                color=COLORS["ERROR"]
                            )
                            log_embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                            log_embed.add_field(name="Channel", value=f"{message.channel.name}", inline=True)
                            log_embed.add_field(name="Toxicity Score", value=f"{toxicity_score:.2f}", inline=True)
                            log_embed.add_field(name="Category", value=category.title(), inline=True)
                            log_embed.add_field(name="Content", value=f"```{message.content[:1000]}```", inline=False)
                            log_embed.set_footer(text=f"Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                            
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logger.error(f"Error sending to mod log channel: {str(e)}")
                
                except discord.Forbidden:
                    logger.warning(f"No permission to delete toxic message from {message.author.name}")
                except Exception as e:
                    logger.error(f"Error processing toxic message: {str(e)}")
        
        # Check for spam if enabled
        if self.is_feature_enabled("spam_detection", guild_id):
            is_spam, spam_confidence = await self.detect_spam(message)
            
            # If spam confidence is above threshold, take action
            if is_spam:
                try:
                    # Delete the message
                    await message.delete()
                    logger.info(f"Deleted spam message from {message.author.name} (confidence: {spam_confidence:.2f})")
                    
                    # Send a warning to the user
                    warning_embed = create_error_embed(
                        "Spam Warning", 
                        f"Your message was removed for appearing to be spam. Please avoid sending repetitive messages."
                    )
                    
                    try:
                        await message.author.send(embed=warning_embed)
                    except discord.Forbidden:
                        # Cannot DM the user
                        pass
                    
                    # Log to mod channel if available
                    try:
                        log_channel = discord.utils.get(message.guild.text_channels, name="mod-logs")
                        if not log_channel:
                            log_channel = discord.utils.get(message.guild.text_channels, name="logs")
                            
                        if log_channel:
                            log_embed = discord.Embed(
                                title="AI Moderation: Spam Removed",
                                description=f"A message from {message.author.mention} was removed for spam.",
                                color=COLORS["WARNING"]
                            )
                            log_embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                            log_embed.add_field(name="Channel", value=f"{message.channel.name}", inline=True)
                            log_embed.add_field(name="Spam Confidence", value=f"{spam_confidence:.2f}", inline=True)
                            log_embed.add_field(name="Content", value=f"```{message.content[:1000]}```", inline=False)
                            log_embed.set_footer(text=f"Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                            
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logger.error(f"Error sending to mod log channel: {str(e)}")
                
                except discord.Forbidden:
                    logger.warning(f"No permission to delete spam message from {message.author.name}")
                except Exception as e:
                    logger.error(f"Error processing spam message: {str(e)}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Monitor for potential raid activity"""
        # Check if raid protection is enabled for this guild
        guild_id = str(member.guild.id)
        if not self.is_feature_enabled("raid_protection", guild_id):
            return
        
        # Initialize raid detection config if needed
        if "raid_detection" not in self.config:
            self.config["raid_detection"] = {
                "join_threshold": 5,  # Number of joins in timeframe to trigger alert
                "timeframe_seconds": 60,  # Timeframe for join rate monitoring
                "enabled": False
            }
        
        # Initialize join history for this guild if needed
        if "join_history" not in self.config:
            self.config["join_history"] = {}
        
        if guild_id not in self.config["join_history"]:
            self.config["join_history"][guild_id] = []
        
        # Add this join to the history
        now = datetime.datetime.utcnow()
        self.config["join_history"][guild_id].append({
            "user_id": str(member.id),
            "username": member.name,
            "timestamp": now.isoformat()
        })
        
        # Keep only recent joins (last 24 hours)
        day_ago = now - datetime.timedelta(days=1)
        self.config["join_history"][guild_id] = [
            j for j in self.config["join_history"][guild_id]
            if datetime.datetime.fromisoformat(j["timestamp"]) > day_ago
        ]
        
        # Check for potential raid (many joins in a short timeframe)
        threshold = self.config["raid_detection"]["join_threshold"]
        timeframe = self.config["raid_detection"]["timeframe_seconds"]
        
        # Count recent joins within the timeframe
        recent_joins = [
            j for j in self.config["join_history"][guild_id]
            if (now - datetime.datetime.fromisoformat(j["timestamp"])).total_seconds() < timeframe
        ]
        
        # If join rate exceeds threshold, trigger raid alert
        if len(recent_joins) >= threshold:
            # Log potential raid
            logger.warning(f"Potential raid detected in {member.guild.name}: {len(recent_joins)} joins in {timeframe} seconds")
            
            # Notify moderators in log channel
            try:
                log_channel = discord.utils.get(member.guild.text_channels, name="mod-logs")
                if not log_channel:
                    log_channel = discord.utils.get(member.guild.text_channels, name="logs")
                    
                if log_channel:
                    alert_embed = discord.Embed(
                        title="⚠️ POTENTIAL RAID ALERT ⚠️",
                        description=f"Unusual join activity detected: {len(recent_joins)} new members in the last {timeframe} seconds.",
                        color=COLORS["ERROR"]
                    )
                    
                    # List recent joins
                    recent_users = "\n".join([f"• {j['username']} (ID: {j['user_id']})" for j in recent_joins[:10]])
                    if len(recent_joins) > 10:
                        recent_users += f"\n+ {len(recent_joins) - 10} more..."
                    
                    alert_embed.add_field(name="Recent Joins", value=recent_users, inline=False)
                    alert_embed.set_footer(text=f"Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    
                    await log_channel.send(embed=alert_embed)
                    
                    # Ping moderators if possible
                    mod_role = discord.utils.get(member.guild.roles, name="Moderator")
                    if mod_role:
                        await log_channel.send(f"{mod_role.mention} ⚠️ Potential raid detected! Please check the logs.")
            except Exception as e:
                logger.error(f"Error sending raid alert: {str(e)}")
        
        # Save the config
        self.save_config()

async def setup(bot):
    """Add the AI Moderation cog to the bot"""
    await bot.add_cog(AIModeration(bot))
    logger.info("AI Moderation cog loaded")