import discord
import logging
import g4f
import asyncio
import os
import json
import aiohttp
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

# Get Google API key from environment variable
GOOGLE_API_KEY = os.environ.get('GOOGLE_API')
USE_GOOGLE_AI = True if GOOGLE_API_KEY else False

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configure g4f settings
        g4f.debug.logging = False  # Disable debug logging
        
        # Log AI provider status
        if USE_GOOGLE_AI:
            logger.info("AI Chat cog initialized with Google Gemini AI")
        else:
            logger.info("AI Chat cog initialized with fallback AI providers")
            logger.info("To use Google's Gemini AI, set the GOOGLE_API environment variable")

    async def get_google_ai_response(self, prompt, system_prompt=None):
        """Get a response from Google's Gemini AI API"""
        if not GOOGLE_API_KEY:
            return None

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay and increase exponentially

        for attempt in range(max_retries):
            try:
                # Gemini API endpoint for text generation - using v1beta for compatibility
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
                
                # Prepare request payload
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": 1000
                    }
                }
                
                # Add system prompt if provided
                if system_prompt:
                    payload["contents"].insert(0, {
                        "role": "system",
                        "parts": [{"text": system_prompt}]
                    })
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status == 429:  # Rate limited
                            retry_after = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Google AI API rate limited. Retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                            await asyncio.sleep(retry_after)
                            continue
                            
                        elif response.status != 200:
                            logger.error(f"Google AI API returned status code {response.status}")
                            error_text = await response.text()
                            logger.error(f"Error details: {error_text[:200]}")
                            
                            if attempt < max_retries - 1:
                                retry_after = retry_delay * (2 ** attempt)
                                logger.warning(f"Retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                return None
                        
                        data = await response.json()
                        
                        if "candidates" not in data or not data["candidates"]:
                            logger.error("No candidates in Google AI response")
                            logger.error(f"Response data: {json.dumps(data)[:200]}")
                            return None
                        
                        # Extract the response text
                        text_parts = data["candidates"][0]["content"]["parts"]
                        response_text = " ".join([part["text"] for part in text_parts if "text" in part])
                        return response_text
            
            except Exception as e:
                logger.error(f"Error getting Google AI response: {str(e)}")
                if attempt < max_retries - 1:
                    retry_after = retry_delay * (2 ** attempt)
                    logger.warning(f"Retrying in {retry_after}s (attempt {attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                else:
                    return None
                    
        # If we got here, all retries failed
        return None

    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="The question or prompt for the AI")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and get a response"""
        try:
            await interaction.response.defer()  # This might take a while
            logger.info(f"Processing AI request from {interaction.user}: {question}")
            
            response = None
            ai_source = "Unknown"
            
            # Try Google AI first if API key is available
            if USE_GOOGLE_AI:
                logger.info("Using Google AI (Gemini) for response")
                response = await self.get_google_ai_response(question)
                ai_source = "Google Gemini"
            
            # Fall back to g4f if Google AI failed or not configured
            if not response:
                logger.info("Using g4f as fallback for AI response")
                max_retries = 2
                retry_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        response = await asyncio.wait_for(
                            self.bot.loop.run_in_executor(
                                None,
                                lambda: g4f.ChatCompletion.create(
                                    model=g4f.models.gemini,  # Using the constant from g4f
                                    provider=g4f.Provider.GeminiPro,  # Use a reliable provider
                                    messages=[{"role": "user", "content": question}]
                                )
                            ),
                            timeout=30.0  # 30 second timeout
                        )
                        if response:  # If we got a valid response, break the retry loop
                            break
                    except Exception as e:
                        logger.error(f"Error with g4f attempt {attempt+1}/{max_retries}: {str(e)}")
                        if attempt < max_retries - 1:
                            retry_after = retry_delay * (2 ** attempt)
                            logger.warning(f"Retrying g4f in {retry_after}s")
                            await asyncio.sleep(retry_after)
                
                ai_source = "Alternative AI"

            if not response:
                raise ValueError("Empty response received from AI provider")

            logger.info(f"AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Create embed with the response
            embed = create_embed(
                f"🤖 AI Response",
                response,
                color=0x7289DA
            )
            embed.add_field(name="Your Question", value=question)
            embed.set_footer(text=f"Powered by {ai_source}")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully sent AI response from {ai_source}")

        except asyncio.TimeoutError:
            logger.error("AI request timed out")
            await interaction.followup.send(
                embed=create_error_embed("Error", "The AI is taking too long to respond. Please try again."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "I'm having trouble connecting to the AI service right now. Please try again in a few moments."),
                ephemeral=True
            )

    @app_commands.command(name="chat", description="Have a casual chat with the AI")
    @app_commands.describe(message="Your message to the AI")
    async def chat(self, interaction: discord.Interaction, *, message: str):
        """Have a more casual conversation with the AI"""
        try:
            await interaction.response.defer()
            logger.info(f"Processing casual AI chat from {interaction.user}: {message}")
            
            response = None
            ai_source = "Unknown"
            system_prompt = "You are a friendly and helpful chat bot. Keep responses concise and engaging."
            
            # Try Google AI first if API key is available
            if USE_GOOGLE_AI:
                logger.info("Using Google AI (Gemini) for casual chat")
                response = await self.get_google_ai_response(message, system_prompt)
                ai_source = "Google Gemini"
            
            # Fall back to g4f if Google AI failed or not configured
            if not response:
                logger.info("Using g4f as fallback for casual chat")
                max_retries = 2
                retry_delay = 1
                
                for attempt in range(max_retries):
                    try:
                        response = await asyncio.wait_for(
                            self.bot.loop.run_in_executor(
                                None,
                                lambda: g4f.ChatCompletion.create(
                                    model=g4f.models.gemini,  # Using the constant from g4f
                                    provider=g4f.Provider.GeminiPro,  # Use a reliable provider
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": message}
                                    ]
                                )
                            ),
                            timeout=30.0  # 30 second timeout
                        )
                        if response:  # If we got a valid response, break the retry loop
                            break
                    except Exception as e:
                        logger.error(f"Error with g4f chat attempt {attempt+1}/{max_retries}: {str(e)}")
                        if attempt < max_retries - 1:
                            retry_after = retry_delay * (2 ** attempt)
                            logger.warning(f"Retrying g4f chat in {retry_after}s")
                            await asyncio.sleep(retry_after)
                
                ai_source = "Alternative AI"

            if not response:
                raise ValueError("Empty response received from AI provider")

            logger.info(f"Casual AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            embed = create_embed(
                "💭 AI Chat",
                response,
                color=0x43B581
            )
            embed.set_footer(text=f"Powered by {ai_source}")

            await interaction.followup.send(embed=embed)
            logger.info(f"Successfully sent casual AI response from {ai_source}")

        except asyncio.TimeoutError:
            logger.error("AI chat request timed out")
            await interaction.followup.send(
                embed=create_error_embed("Error", "The AI is taking too long to respond. Please try again."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in AI chat: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "I'm having trouble connecting to the AI service right now. Please try again in a few moments."),
                ephemeral=True
            )

async def setup(bot):
    logger.info("Setting up AI Chat cog")
    await bot.add_cog(AIChat(bot))
    logger.info("AI Chat cog is ready")