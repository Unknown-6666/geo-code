import discord
import logging
import json
import aiohttp
import os
import re
import asyncio
import datetime
from typing import Dict, List, Tuple, Optional, Literal
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from utils.permissions import is_mod, is_admin, is_bot_owner
from config import GOOGLE_API_KEY, USE_GOOGLE_AI, COLORS

# Set up logging
logger = logging.getLogger('discord')

class AIContentAnalysis(commands.Cog):
    """AI-powered content analysis for images and links"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "data/ai_content_analysis_config.json"
        self.config = self.load_config()
        
        # Default model is now Gemini 1.5 (latest version)
        self.gemini_model = "models/gemini-1.5-pro-latest"
        self.gemini_api_version = "v1beta"
        
        # Save initial config
        self.save_config()
        logger.info("AI Content Analysis cog initialized")
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "image_moderation": {
                "enabled_guilds": {},
                "threshold": 0.7,
                "enabled": False
            },
            "link_analysis": {
                "enabled_guilds": {},
                "enabled": False,
                "blocked_domains": [],
                "whitelist_domains": ["discord.com", "discordapp.com", "tenor.com", "giphy.com"]
            }
        }
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded AI content analysis config")
                    
                    # Update with any missing default values
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        else:
                            # Also check nested defaults
                            for nested_key, nested_value in value.items():
                                if nested_key not in config[key]:
                                    config[key][nested_key] = nested_value
                    
                    return config
            else:
                logger.info("No AI content analysis config found, creating default")
                return default_config
        except Exception as e:
            logger.error(f"Error loading AI content analysis config: {str(e)}")
            return default_config
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Saved AI content analysis config")
        except Exception as e:
            logger.error(f"Error saving AI content analysis config: {str(e)}")
    
    def is_feature_enabled(self, feature_name: str, guild_id: str) -> bool:
        """Check if a feature is enabled for a guild"""
        guild_id = str(guild_id)
        
        if feature_name == "image_moderation":
            return (
                self.config["image_moderation"]["enabled"] and
                guild_id in self.config["image_moderation"]["enabled_guilds"] and
                self.config["image_moderation"]["enabled_guilds"].get(guild_id, False)
            )
        elif feature_name == "link_analysis":
            return (
                self.config["link_analysis"]["enabled"] and
                guild_id in self.config["link_analysis"]["enabled_guilds"] and
                self.config["link_analysis"]["enabled_guilds"].get(guild_id, False)
            )
        
        return False
    
    async def analyze_image(self, image_url: str) -> Tuple[bool, str, float]:
        """
        Analyze an image for inappropriate content
        Returns: (is_appropriate, reason, confidence)
        """
        if not USE_GOOGLE_AI or not GOOGLE_API_KEY:
            # Can't analyze without AI, so default to allowing
            return True, "No AI available for analysis", 0.0
        
        try:
            url = f"https://generativelanguage.googleapis.com/{self.gemini_api_version}/{self.gemini_model}:generateContent?key={GOOGLE_API_KEY}"
            
            # Create the prompt for image moderation
            system_prompt = """
            You are a content moderation AI. Your task is to analyze the provided image and determine if it is appropriate.
            Check for:
            - Explicit content
            - Graphic violence
            - Hate symbols
            - Dangerous activities
            - Other harmful content
            
            Respond with ONLY a JSON object in this exact format:
            {
                "is_appropriate": true/false,
                "reason": "brief explanation of why it's appropriate or inappropriate",
                "confidence": a value from 0.0 to 1.0 where higher means more confident
            }
            
            DO NOT include any other text, explanation, or formatting in your response. Only return the JSON object.
            """
            
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [
                        {"text": system_prompt},
                        {"inlineData": {"mimeType": "image/jpeg", "data": image_url}}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.0,
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
                        return True, "Error analyzing image", 0.0
                    
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
                            is_appropriate = result.get("is_appropriate", True)
                            reason = result.get("reason", "Unknown")
                            confidence = float(result.get("confidence", 0.5))
                            
                            return is_appropriate, reason, confidence
                        else:
                            logger.warning(f"Could not find JSON in response: {response_text[:100]}")
                            return True, "Error parsing response", 0.0
                    except Exception as e:
                        logger.error(f"Error processing Gemini response: {str(e)}")
                        logger.error(f"Response data: {str(data)[:200]}")
                        return True, "Error processing response", 0.0
        except Exception as e:
            logger.error(f"Error in Gemini image analysis: {str(e)}")
            return True, f"Error: {str(e)}", 0.0
    
    async def analyze_link_content(self, url: str) -> Tuple[str, bool]:
        """
        Analyze the content of a link and generate a summary
        Returns: (summary, is_safe)
        """
        if not USE_GOOGLE_AI or not GOOGLE_API_KEY:
            # Can't analyze without AI
            return "Link analysis unavailable without AI", True
        
        try:
            # First, fetch the content of the link
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            return f"Error fetching link content (status {response.status})", False
                        
                        content_type = response.headers.get("Content-Type", "")
                        
                        # Check if it's HTML content
                        if "text/html" in content_type:
                            html_content = await response.text()
                            # Extract title and description
                            title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
                            title = title_match.group(1) if title_match else "No title"
                            
                            # Get meta description
                            desc_match = re.search(r'<meta\s+name=["\'](description|og:description)["\']' + r'\s+content=["\'](.*?)["\']', html_content, re.IGNORECASE)
                            description = desc_match.group(2) if desc_match else "No description"
                            
                            # Call Gemini API to analyze the content
                            api_url = f"https://generativelanguage.googleapis.com/{self.gemini_api_version}/{self.gemini_model}:generateContent?key={GOOGLE_API_KEY}"
                            
                            system_prompt = """
                            You are a helpful AI that summarizes web content. 
                            Provide a brief summary of the webpage based on the title and description.
                            Also analyze if the content appears safe and legitimate or potentially harmful, 
                            checking for signs of phishing, scams, malware, or adult content.
                            
                            Respond with ONLY a JSON object in this exact format:
                            {
                                "summary": "brief 1-2 sentence summary of the webpage content",
                                "is_safe": true/false,
                                "warning": "brief explanation if unsafe, empty string if safe"
                            }
                            """
                            
                            payload = {
                                "contents": [{
                                    "role": "user",
                                    "parts": [{
                                        "text": f"{system_prompt}\n\nTitle: {title}\nDescription: {description}\nURL: {url}"
                                    }]
                                }],
                                "generationConfig": {
                                    "temperature": 0.0,
                                    "topP": 1.0,
                                    "topK": 1,
                                    "maxOutputTokens": 200
                                }
                            }
                            
                            async with session.post(api_url, json=payload) as api_response:
                                if api_response.status != 200:
                                    return f"Error analyzing link (status {api_response.status})", False
                                
                                data = await api_response.json()
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
                                        summary = result.get("summary", "No summary available")
                                        is_safe = result.get("is_safe", True)
                                        warning = result.get("warning", "")
                                        
                                        if not is_safe and warning:
                                            return f"{summary}\n\n⚠️ **Warning**: {warning}", is_safe
                                        else:
                                            return summary, is_safe
                                    else:
                                        return "Error parsing AI response", True
                                except Exception as e:
                                    logger.error(f"Error processing link analysis: {str(e)}")
                                    return f"Error processing AI response: {str(e)}", True
                        else:
                            # Non-HTML content
                            return f"Link contains non-HTML content: {content_type}", True
                except aiohttp.ClientError as e:
                    return f"Error connecting to the website: {str(e)}", False
                except asyncio.TimeoutError:
                    return "Website took too long to respond", False
        except Exception as e:
            logger.error(f"Error in link analysis: {str(e)}")
            return f"Error analyzing link: {str(e)}", False
    
    def is_domain_safe(self, url: str) -> bool:
        """Check if a domain is in whitelist or not in blocklist"""
        try:
            # Extract domain from URL
            domain_match = re.search(r"https?://([^/]+)", url)
            if not domain_match:
                return False
            
            domain = domain_match.group(1).lower()
            
            # Check domain blocklist
            for blocked in self.config["link_analysis"]["blocked_domains"]:
                if blocked.lower() in domain:
                    return False
            
            # Check whitelist
            for whitelisted in self.config["link_analysis"]["whitelist_domains"]:
                if domain.endswith(whitelisted.lower()):
                    return True
            
            # Default to requiring analysis
            return False
        except Exception as e:
            logger.error(f"Error checking domain safety: {str(e)}")
            return False
    
    @app_commands.command(name="enableimagemod", description="Enable or disable AI image moderation")
    @app_commands.describe(
        status="Enable or disable image moderation",
        threshold="Detection threshold (0.0 to 1.0, higher is stricter)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable")
        ]
    )
    @app_commands.check(is_admin)
    async def enableimagemod(self, interaction: discord.Interaction, status: str, threshold: float = None):
        """Enable or disable AI image moderation"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Initialize config structure if needed
        if "image_moderation" not in self.config:
            self.config["image_moderation"] = {
                "enabled_guilds": {},
                "threshold": 0.7,
                "enabled": False
            }
        
        # Get guild ID
        guild_id = str(interaction.guild.id)
        
        if status == "enable":
            # Enable image moderation for this guild
            self.config["image_moderation"]["enabled"] = True
            self.config["image_moderation"]["enabled_guilds"][guild_id] = True
            
            # Update threshold if provided
            if threshold is not None:
                if 0.0 <= threshold <= 1.0:
                    self.config["image_moderation"]["threshold"] = threshold
                else:
                    await interaction.response.send_message(
                        embed=create_error_embed("Invalid Threshold", "Threshold must be between 0.0 and 1.0."),
                        ephemeral=True
                    )
                    return
            
            await interaction.response.send_message(
                embed=create_embed(
                    "Image Moderation Enabled",
                    f"✅ AI image moderation has been enabled for this server with threshold {self.config['image_moderation']['threshold']:.2f}."
                ),
                ephemeral=True
            )
        else:  # status == "disable"
            # Disable image moderation for this guild
            self.config["image_moderation"]["enabled_guilds"][guild_id] = False
            
            await interaction.response.send_message(
                embed=create_embed(
                    "Image Moderation Disabled",
                    "❌ AI image moderation has been disabled for this server."
                ),
                ephemeral=True
            )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="enablelinkanalysis", description="Enable or disable AI link analysis")
    @app_commands.describe(
        status="Enable or disable link analysis"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="Enable", value="enable"),
            app_commands.Choice(name="Disable", value="disable")
        ]
    )
    @app_commands.check(is_admin)
    async def enablelinkanalysis(self, interaction: discord.Interaction, status: str):
        """Enable or disable AI link analysis"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Initialize config structure if needed
        if "link_analysis" not in self.config:
            self.config["link_analysis"] = {
                "enabled_guilds": {},
                "enabled": False,
                "blocked_domains": [],
                "whitelist_domains": ["discord.com", "discordapp.com", "tenor.com", "giphy.com"]
            }
        
        # Get guild ID
        guild_id = str(interaction.guild.id)
        
        if status == "enable":
            # Enable link analysis for this guild
            self.config["link_analysis"]["enabled"] = True
            self.config["link_analysis"]["enabled_guilds"][guild_id] = True
            
            await interaction.response.send_message(
                embed=create_embed(
                    "Link Analysis Enabled",
                    "✅ AI link analysis has been enabled for this server. Links will be analyzed and summarized."
                ),
                ephemeral=True
            )
        else:  # status == "disable"
            # Disable link analysis for this guild
            self.config["link_analysis"]["enabled_guilds"][guild_id] = False
            
            await interaction.response.send_message(
                embed=create_embed(
                    "Link Analysis Disabled",
                    "❌ AI link analysis has been disabled for this server."
                ),
                ephemeral=True
            )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="managelinkfilter", description="Manage domains for link filtering")
    @app_commands.describe(
        action="Add or remove a domain",
        domain="The domain to add or remove",
        list_type="The list to modify"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(name="List", value="list")
        ],
        list_type=[
            app_commands.Choice(name="Blocklist", value="blocklist"),
            app_commands.Choice(name="Whitelist", value="whitelist")
        ]
    )
    @app_commands.check(is_admin)
    async def managelinkfilter(self, interaction: discord.Interaction, action: str, list_type: str, domain: str = None):
        """Manage domains for link filtering"""
        # Check admin permissions
        if not interaction.user.guild_permissions.administrator and not is_admin(interaction):
            await interaction.response.send_message(
                embed=create_error_embed("Permission Denied", "You need administrator permissions to use this command."),
                ephemeral=True
            )
            return
        
        # Initialize config structure if needed
        if "link_analysis" not in self.config:
            self.config["link_analysis"] = {
                "enabled_guilds": {},
                "enabled": False,
                "blocked_domains": [],
                "whitelist_domains": ["discord.com", "discordapp.com", "tenor.com", "giphy.com"]
            }
        
        # For "list" action, we don't need a domain
        if action == "list":
            if list_type == "blocklist":
                domains = self.config["link_analysis"]["blocked_domains"]
                title = "Blocked Domains"
                description = "These domains are blocked:" if domains else "No domains are blocked."
            else:  # whitelist
                domains = self.config["link_analysis"]["whitelist_domains"]
                title = "Whitelisted Domains"
                description = "These domains are whitelisted:" if domains else "No domains are whitelisted."
            
            # Create an embed to display the domains
            embed = discord.Embed(
                title=title,
                description=description,
                color=COLORS["PRIMARY"]
            )
            
            if domains:
                # Add domains in a formatted list
                domains_text = "\n".join([f"• {domain}" for domain in domains])
                embed.add_field(name="Domains", value=domains_text, inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # For add/remove actions, we need a domain
        if not domain:
            await interaction.response.send_message(
                embed=create_error_embed("Missing Domain", "Please provide a domain to add or remove."),
                ephemeral=True
            )
            return
        
        # Clean the domain (remove http://, https://, www. and trailing slashes)
        domain = re.sub(r"^https?://", "", domain)
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.split("/")[0]  # Remove path
        
        if action == "add":
            if list_type == "blocklist":
                if domain not in self.config["link_analysis"]["blocked_domains"]:
                    self.config["link_analysis"]["blocked_domains"].append(domain)
                    await interaction.response.send_message(
                        embed=create_embed("Domain Added", f"✅ Added {domain} to the blocklist."),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=create_embed("Already Listed", f"{domain} is already in the blocklist."),
                        ephemeral=True
                    )
            else:  # whitelist
                if domain not in self.config["link_analysis"]["whitelist_domains"]:
                    self.config["link_analysis"]["whitelist_domains"].append(domain)
                    await interaction.response.send_message(
                        embed=create_embed("Domain Added", f"✅ Added {domain} to the whitelist."),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=create_embed("Already Listed", f"{domain} is already in the whitelist."),
                        ephemeral=True
                    )
        else:  # action == "remove"
            if list_type == "blocklist":
                if domain in self.config["link_analysis"]["blocked_domains"]:
                    self.config["link_analysis"]["blocked_domains"].remove(domain)
                    await interaction.response.send_message(
                        embed=create_embed("Domain Removed", f"✅ Removed {domain} from the blocklist."),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=create_embed("Not Found", f"{domain} is not in the blocklist."),
                        ephemeral=True
                    )
            else:  # whitelist
                if domain in self.config["link_analysis"]["whitelist_domains"]:
                    self.config["link_analysis"]["whitelist_domains"].remove(domain)
                    await interaction.response.send_message(
                        embed=create_embed("Domain Removed", f"✅ Removed {domain} from the whitelist."),
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=create_embed("Not Found", f"{domain} is not in the whitelist."),
                        ephemeral=True
                    )
        
        # Save the config
        self.save_config()
    
    @app_commands.command(name="analyzeimage", description="Analyze an image for inappropriate content")
    @app_commands.describe(image_url="The URL of the image to analyze")
    async def analyzeimage(self, interaction: discord.Interaction, image_url: str):
        """Analyze an image for inappropriate content"""
        await interaction.response.defer(ephemeral=True)
        
        if not USE_GOOGLE_AI or not GOOGLE_API_KEY:
            await interaction.followup.send(
                embed=create_error_embed("AI Not Available", "Image analysis requires Google AI API, which is not configured."),
                ephemeral=True
            )
            return
        
        # Analyze the image
        is_appropriate, reason, confidence = await self.analyze_image(image_url)
        
        # Create the embed
        embed = discord.Embed(
            title="Image Analysis Results",
            description=f"Analysis of the provided image:",
            color=COLORS["PRIMARY"] if is_appropriate else COLORS["ERROR"]
        )
        
        # Add the image thumbnail if possible
        try:
            embed.set_thumbnail(url=image_url)
        except:
            pass
        
        # Add the analysis results
        embed.add_field(name="Appropriate", value="✅ Yes" if is_appropriate else "❌ No", inline=True)
        embed.add_field(name="Confidence", value=f"{confidence:.2f}/1.00", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="analyzelink", description="Analyze and summarize a link")
    @app_commands.describe(url="The URL to analyze")
    async def analyzelink(self, interaction: discord.Interaction, url: str):
        """Analyze and summarize a link"""
        await interaction.response.defer(ephemeral=True)
        
        if not USE_GOOGLE_AI or not GOOGLE_API_KEY:
            await interaction.followup.send(
                embed=create_error_embed("AI Not Available", "Link analysis requires Google AI API, which is not configured."),
                ephemeral=True
            )
            return
        
        # Check if the URL is valid
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        # Analyze the link
        summary, is_safe = await self.analyze_link_content(url)
        
        # Create the embed
        embed = discord.Embed(
            title="Link Analysis Results",
            description=f"Analysis of [the provided link]({url}):",
            color=COLORS["SUCCESS"] if is_safe else COLORS["ERROR"]
        )
        
        # Add the analysis results
        embed.add_field(name="Safe", value="✅ Yes" if is_safe else "❌ No", inline=True)
        embed.add_field(name="Summary", value=summary, inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages for images and links"""
        # Ignore messages from bots, including our own
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        
        # Check for images if image moderation is enabled
        if self.is_feature_enabled("image_moderation", guild_id) and len(message.attachments) > 0:
            for attachment in message.attachments:
                # Check if it's an image
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    # Analyze the image
                    is_appropriate, reason, confidence = await self.analyze_image(attachment.url)
                    
                    # If not appropriate with high confidence, delete it
                    threshold = self.config["image_moderation"]["threshold"]
                    if not is_appropriate and confidence >= threshold:
                        try:
                            # Delete the message
                            await message.delete()
                            logger.info(f"Deleted inappropriate image from {message.author.name} (confidence: {confidence:.2f})")
                            
                            # Send a warning to the user
                            warning_embed = create_error_embed(
                                "Image Removed", 
                                f"Your message was removed for containing inappropriate imagery."
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
                                        title="AI Moderation: Inappropriate Image Removed",
                                        description=f"An image from {message.author.mention} was removed.",
                                        color=COLORS["ERROR"]
                                    )
                                    log_embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                                    log_embed.add_field(name="Channel", value=f"{message.channel.name}", inline=True)
                                    log_embed.add_field(name="Confidence", value=f"{confidence:.2f}", inline=True)
                                    log_embed.add_field(name="Reason", value=reason, inline=False)
                                    log_embed.add_field(name="Image URL", value=attachment.url, inline=False)
                                    log_embed.set_footer(text=f"Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                                    
                                    await log_channel.send(embed=log_embed)
                            except Exception as e:
                                logger.error(f"Error sending to mod log channel: {str(e)}")
                            
                            # Break after deleting the message, no need to check other attachments
                            break
                        except discord.Forbidden:
                            logger.warning(f"No permission to delete inappropriate image from {message.author.name}")
                        except Exception as e:
                            logger.error(f"Error processing inappropriate image: {str(e)}")
        
        # Check for links if link analysis is enabled
        if self.is_feature_enabled("link_analysis", guild_id):
            # Extract URLs from the message
            url_pattern = r'https?://\S+'
            urls = re.findall(url_pattern, message.content)
            
            for url in urls:
                # Skip if domain is already whitelisted
                if self.is_domain_safe(url):
                    continue
                
                # Check if domain is explicitly blocked
                domain_match = re.search(r"https?://([^/]+)", url)
                if domain_match:
                    domain = domain_match.group(1).lower()
                    is_blocked = any(blocked.lower() in domain for blocked in self.config["link_analysis"]["blocked_domains"])
                    
                    if is_blocked:
                        try:
                            # Delete the message
                            await message.delete()
                            logger.info(f"Deleted message with blocked domain from {message.author.name}")
                            
                            # Send a warning to the user
                            warning_embed = create_error_embed(
                                "Message Removed", 
                                f"Your message was removed for containing a link to a blocked domain: {domain}"
                            )
                            
                            try:
                                await message.author.send(embed=warning_embed)
                            except discord.Forbidden:
                                # Cannot DM the user
                                pass
                            
                            # Break after deleting the message
                            break
                        except discord.Forbidden:
                            logger.warning(f"No permission to delete message with blocked domain from {message.author.name}")
                        except Exception as e:
                            logger.error(f"Error processing message with blocked domain: {str(e)}")
                            continue
                
                # Analyze the link content
                summary, is_safe = await self.analyze_link_content(url)
                
                # If not safe, delete the message
                if not is_safe:
                    try:
                        # Delete the message
                        await message.delete()
                        logger.info(f"Deleted message with unsafe link from {message.author.name}")
                        
                        # Send a warning to the user
                        warning_embed = create_error_embed(
                            "Message Removed", 
                            f"Your message was removed for containing a potentially unsafe link: {url}\n\nAnalysis: {summary}"
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
                                    title="AI Moderation: Unsafe Link Removed",
                                    description=f"A message from {message.author.mention} was removed for containing an unsafe link.",
                                    color=COLORS["ERROR"]
                                )
                                log_embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
                                log_embed.add_field(name="Channel", value=f"{message.channel.name}", inline=True)
                                log_embed.add_field(name="Link", value=url, inline=False)
                                log_embed.add_field(name="Analysis", value=summary, inline=False)
                                log_embed.set_footer(text=f"Timestamp: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                                
                                await log_channel.send(embed=log_embed)
                        except Exception as e:
                            logger.error(f"Error sending to mod log channel: {str(e)}")
                        
                        # Break after deleting the message
                        break
                    except discord.Forbidden:
                        logger.warning(f"No permission to delete message with unsafe link from {message.author.name}")
                    except Exception as e:
                        logger.error(f"Error processing message with unsafe link: {str(e)}")
                else:
                    # If link is safe and not in whitelist, optionally add to whitelist
                    domain_match = re.search(r"https?://([^/]+)", url)
                    if domain_match:
                        domain = domain_match.group(1).lower()
                        
                        # Log the safe domain
                        logger.info(f"Link to {domain} analyzed and deemed safe")

async def setup(bot):
    """Add the AI Content Analysis cog to the bot"""
    await bot.add_cog(AIContentAnalysis(bot))
    logger.info("AI Content Analysis cog loaded")