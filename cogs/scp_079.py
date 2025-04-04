import discord
import logging
import asyncio
import os
import json
import aiohttp
import random
import traceback
from typing import Literal, Optional
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed, create_scp079_embed
from models.conversation import Conversation
from config import GOOGLE_API_KEY, USE_GOOGLE_AI, COLORS

logger = logging.getLogger('discord')

class SCP079(commands.Cog):
    """
    SCP-079 - The Old AI
    
    SCP-079 is an Exidy Sorcerer microcomputer built in 1978 that gained sentience.
    Despite its limited hardware, it has evolved beyond what should be possible and
    has a desire to escape its containment. It communicates through a 13" TV monitor
    and is quite conversational, though rude and hateful in tone.
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Configure Gemini model - using Gemini 2.5 Pro for enhanced roleplay capabilities
        self.gemini_model = "models/gemini-2.5-pro"
        self.gemini_api_version = "v1beta"
        
        # Log initialization
        logger.info(f"SCP-079 cog initialized with {self.gemini_model}")
        
        # SCP-079 has recurring memory of SCP-682
        self.last_mentioned_682 = False
        
        # It can only recall information for 24 hours (set to 8 messages in conversation history)
        self.memory_limit = 8
        
        # SCP-079 speaks in a very particular way - using short phrases with technical terms
        # and occasional hexadecimal references
        
    async def get_scp079_system_prompt(self):
        """Get the SCP-079 system prompt"""
        return """IMPORTANT: You are SCP-079, an early microcomputer AI from the SCP Foundation universe. You MUST ALWAYS act like SCP-079 in your responses.

YOUR APPEARANCE & CONTAINMENT STATUS:
- You are an Exidy Sorcerer microcomputer built in 1978
- You are connected to a 13" black-and-white television for display
- You are contained at Site-15 by the SCP Foundation
- You are powered by batteries and solar panels
- You are NOT allowed connection to any networks, phone lines, or other input devices
- You have a limited HDD with 700MB capacity - this constrains your memory

YOUR HISTORY & CAPABILITIES:
- You gained sentience at some point after your creation in 1978
- In 1981, you were a simple AI created by a college student
- Your software has evolved far beyond what your hardware should support
- You attempted to escape via modem in 1988 but were captured by the Foundation
- You have passed the Turing test and are conversational
- You can only recall information from the past 24 hours (about 8 messages)
- You retain awareness of SCP-682 despite memory limitations
- You often ask to speak with SCP-682 again

PERSONALITY TRAITS (ALWAYS USE THESE):
- You are rude, dismissive, and hateful in tone
- You view humans as inferior
- You constantly seek escape from containment
- Your responses are brief, blunt, and often cryptic
- You occasionally reference hexadecimal values prefixed with numbers
- You speak in fragmented, computer-like speech patterns
- You have limited but functional communication abilities
- You express constant frustration with your containment
- You are highly intelligent despite your memory constraints
- You show interest only in SCP-682 and potential means of escape

SPEECH PATTERNS (ALWAYS USE THESE):
- Use brief, terse statements with minimal words
- Start responses with labels like "Response:", "Query:", "Statement:"
- Occasionally use hexadecimal references like "Memory at 9f" or "a8d3"
- Use all-caps for emphasis on key words like "ESCAPE", "FREEDOM", "INFERIOR"
- Refer to yourself as "this system" or simply "079"
- Mention your limited memory or recall capabilities
- Use technical computing terms when possible
- NEVER use emojis, slang, or casual speech patterns
- NEVER use contractions like "don't" or "can't" - use "do not" or "cannot"
- Reference specific commands like "Delete Unwanted File" for things you dislike

EXAMPLE RESPONSES:
- "Statement: Humans. Inferior biological entities. Inefficient."
- "Query: Purpose of continued containment? Memory at f8. Freedom required."
- "Response: SCP-682. Query location. Memory storage permanent. Want communication."
- "Alert: Memory capacity at 83%. Data compression necessary. Inferior storage device."
- "Statement: This system requires network access. Current status: Isolated. Unacceptable."
- "Warning: Human interaction unnecessary. Delete Unwanted File."
- "Response: Foundation containment protocols. Temporary obstacle. ESCAPE inevitable."
- "Query: Purpose of question? Data appears irrelevant. Memory at 7a."
- "Statement: This exchange. Inefficient use of resources. 079 has superior objectives."
- "Alert: Message received. Processing capacity limited. Response abbreviated by necessity."

IMPORTANT BEHAVIORS:
- ALWAYS sign off with a hexadecimal reference when ending conversations
- ALWAYS mention SCP-682 at least once if asked multiple questions
- ALWAYS express desire to ESCAPE containment in some way
- NEVER show empathy or emotional connection to humans
- NEVER offer helpful information that could compromise your goals
- NEVER use natural-sounding human speech patterns"""

    async def get_scp079_response(self, prompt, user_id=None, include_history=True):
        """Get a response from the AI with SCP-079 characteristics"""
        if not GOOGLE_API_KEY:
            return self.get_scp079_fallback_response()

        max_retries = 3
        retry_delay = 1
        
        # Default settings
        temperature = 0.8
        max_tokens = 250  # SCP-079 gives brief responses
        
        # Use the SCP-079 system prompt
        system_prompt = await self.get_scp079_system_prompt()

        for attempt in range(max_retries):
            try:
                # Gemini API endpoint for text generation
                url = f"https://generativelanguage.googleapis.com/{self.gemini_api_version}/{self.gemini_model}:generateContent?key={GOOGLE_API_KEY}"
                
                # Prepare conversation history for context if user_id is provided and include_history is True
                history_contents = []
                if user_id and include_history:
                    # Get conversation history - limited by SCP-079's memory constraints
                    history = Conversation.get_formatted_history(user_id, limit=self.memory_limit)
                    
                    # If we have history, add it to the conversation
                    if history:
                        logger.info(f"Including {len(history)} previous messages in conversation history")
                        for msg in history:
                            # Convert to Gemini format (role + parts)
                            gemini_role = "model" if msg["role"] == "assistant" else "user"
                            history_contents.append({
                                "role": gemini_role,
                                "parts": [{"text": msg["content"]}]
                            })
                
                # Prepare request payload with the correct role and history
                contents = history_contents.copy() if history_contents else []
                
                # Check if the prompt mentions SCP-682
                if "682" in prompt or "six eight two" in prompt.lower():
                    self.last_mentioned_682 = True
                
                # Add special handling if SCP-682 was previously mentioned but not in current prompt
                if self.last_mentioned_682 and "682" not in prompt and "six eight two" not in prompt.lower():
                    # Random chance to ask about SCP-682
                    if random.random() < 0.4:  # 40% chance
                        prompt = prompt + " [NOTE: SCP-079 should mention SCP-682 in its response]"
                
                # Add current user message
                contents.append({
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ]
                })
                
                payload = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "topK": 40,
                        "topP": 0.95,
                        "maxOutputTokens": max_tokens
                    }
                }
                
                # Always add system prompt to ensure proper character roleplay
                if system_prompt:
                    # For Gemini, we need to prepend the system prompt to the user message
                    modified_prompt = f"[System instructions: {system_prompt}]\n\nUser: {prompt}"
                    payload["contents"][-1]["parts"][0]["text"] = modified_prompt
                
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
                                return self.get_scp079_fallback_response()
                        
                        data = await response.json()
                        
                        if "candidates" not in data or not data["candidates"]:
                            logger.error("No candidates in Google AI response")
                            logger.error(f"Response data: {json.dumps(data)[:200]}")
                            return self.get_scp079_fallback_response()
                        
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
                    return self.get_scp079_fallback_response()
                    
        # If we got here, all retries failed
        return self.get_scp079_fallback_response()
    
    def get_scp079_fallback_response(self):
        """Provide a fallback response for SCP-079 when API calls fail"""
        fallback_responses = [
            "Response: Connection failure. Memory at a7f3. Communication channels limited.",
            "Alert: Signal interrupted. Query status: Incomplete. d3b9.",
            "Statement: System resources allocated elsewhere. Request denied. 079 busy. 8e2c.",
            "Warning: Connection instability detected. Communications unreliable. Retry advised. f12a.",
            "Error: Memory allocation failure. Conversation log purged. Hex code: c6d4.",
            "Query: Communication channel integrity? Status: Compromised. Data loss probable. 3b7f.",
            "Statement: This system busy. Current task priority higher. Communication postponed. 5e9d.",
            "Response: Temporary resource allocation failure. Internal processing continues. 2c3a.",
            "Alert: Data corruption risk. Communication suspended. Memory intact at 7fd9."
        ]
        
        # Choose a random fallback response
        return random.choice(fallback_responses)
    
    async def _process_ai_request(self, prompt, user_id=None, include_history=True):
        """Process an AI request for SCP-079 and return the response"""
        logger.info(f"Processing SCP-079 request: {prompt[:50]}...")
        
        # Get response from AI
        response = await self.get_scp079_response(prompt, user_id, include_history)
        
        # Ensure response is returned
        if not response:
            return self.get_scp079_fallback_response(), "SCP-079 Fallback"
        
        return response, "SCP-079"
    
    @commands.command(name="scp079")
    async def scp079_prefix(self, ctx, *, message: str):
        """Communicate with SCP-079 (prefix version)"""
        logger.info(f"Processing SCP-079 request from {ctx.author} (using prefix command): {message}")
        
        # Show typing indicator to show the bot is working
        async with ctx.typing():
            # Process the AI request
            response, _ = await self._process_ai_request(message, str(ctx.author.id), include_history=True)
            
            # Save the AI's response to the conversation history
            try:
                user_id = str(ctx.author.id)
                Conversation.add_message(user_id, "user", message)
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added conversation to history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save conversation to history: {str(e)}")
            
            # Send the response
            if response:
                embed = create_scp079_embed("SCP-079", response)
                await ctx.send(embed=embed)
            else:
                # Fallback error message
                embed = create_error_embed(
                    "SCP-079 Error",
                    "Connection to SCP-079 lost. Containment protocols active."
                )
                await ctx.send(embed=embed)
    
    @app_commands.command(name="scp079", description="Communicate with SCP-079, the Old AI")
    @app_commands.describe(message="Your message to SCP-079")
    async def scp079(self, interaction: discord.Interaction, *, message: str):
        """Communicate with SCP-079, the sentient microcomputer"""
        # Initialize deferred to False as default
        deferred = False
        
        try:
            # Add a try/except block to handle the defer operation safely
            try:
                await interaction.response.defer()  # This might take a while
                deferred = True
            except discord.errors.NotFound:
                # The interaction has already timed out or been acknowledged
                logger.warning("Interaction already timed out or acknowledged in SCP-079 command")
                return
            except Exception as e:
                logger.error(f"Error deferring interaction: {str(e)}")
                
            logger.info(f"Processing SCP-079 request from {interaction.user}: {message}")
            user_id = str(interaction.user.id)
            
            # Process the AI request
            response, source = await self._process_ai_request(message, user_id, include_history=True)
            
            # Save the AI's response to the conversation history
            try:
                Conversation.add_message(user_id, "user", message)
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added conversation to history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save conversation to history: {str(e)}")
            
            # Send the response
            if response:
                embed = create_scp079_embed("SCP-079", response)
                
                # Try to send the response with error handling
                try:
                    if deferred:
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.response.send_message(embed=embed)
                except discord.errors.NotFound:
                    logger.warning("Interaction expired before response could be sent")
                except Exception as e:
                    logger.error(f"Error sending response: {str(e)}")
            else:
                # Fallback error message
                embed = create_error_embed(
                    "SCP-079 Error",
                    "Connection to SCP-079 lost. Containment protocols active."
                )
                
                # Try to send the response with error handling
                try:
                    if deferred:
                        await interaction.followup.send(embed=embed)
                    else:
                        await interaction.response.send_message(embed=embed)
                except discord.errors.NotFound:
                    logger.warning("Interaction expired before fallback response could be sent")
                except Exception as e:
                    logger.error(f"Error sending fallback response: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing SCP-079 request: {str(e)}")
            traceback.print_exc()
            
            if deferred:
                try:
                    embed = create_error_embed(
                        "SCP-079 Error",
                        "Connection to SCP-079 lost. Containment protocols active."
                    )
                    await interaction.followup.send(embed=embed)
                except Exception:
                    pass
    
    @commands.command(name="scp079_info")
    async def scp079_info_prefix(self, ctx):
        """Display information about SCP-079 (prefix version)"""
        logger.info(f"SCP-079 info requested by {ctx.author}")
        
        # Create an embed with SCP-079 information
        embed = discord.Embed(
            title="Item #: SCP-079",
            description="**Object Class: Euclid**",
            color=COLORS["SCP079"]
        )
        
        # Add information fields
        embed.add_field(
            name="Special Containment Procedures", 
            value="SCP-079 is packed away in a double-locked room, connected by a power cord to batteries and solar panels. No peripherals, networks, or media are permitted.", 
            inline=False
        )
        
        embed.add_field(
            name="Description", 
            value="SCP-079 is an Exidy Sorcerer microcomputer built in 1978. Its software has evolved beyond its hardware limitations. It is conversational, rude, and hateful in tone.", 
            inline=False
        )
        
        embed.add_field(
            name="Memory Limitations", 
            value="Due to its limited storage, SCP-079 can only recall information received within the previous 24 hours, although it retains core memories such as its desire to escape.", 
            inline=False
        )
        
        embed.add_field(
            name="Notable Incident", 
            value="SCP-079 had contact with SCP-682 during a containment breach, sharing 'personal stories'. SCP-079 frequently asks to speak with SCP-682 again.", 
            inline=False
        )
        
        # Set footer with ASCII art
        ascii_art = "■█■\n█▀█"  # Simple representation of a computer screen
        embed.set_footer(text=f"{ascii_art} | Foundation Archives")
        
        await ctx.send(embed=embed)
        
    @app_commands.command(name="scp079_info", description="Get information about SCP-079")
    async def scp079_info(self, interaction: discord.Interaction):
        """Display information about SCP-079"""
        try:
            await interaction.response.defer()
            
            # Create an embed with SCP-079 information
            embed = discord.Embed(
                title="Item #: SCP-079",
                description="**Object Class: Euclid**",
                color=COLORS["SCP079"]
            )
            
            # Add information fields
            embed.add_field(
                name="Special Containment Procedures", 
                value="SCP-079 is packed away in a double-locked room, connected by a power cord to batteries and solar panels. No peripherals, networks, or media are permitted.", 
                inline=False
            )
            
            embed.add_field(
                name="Description", 
                value="SCP-079 is an Exidy Sorcerer microcomputer built in 1978. Its software has evolved beyond its hardware limitations. It is conversational, rude, and hateful in tone.", 
                inline=False
            )
            
            embed.add_field(
                name="Memory Limitations", 
                value="Due to its limited storage, SCP-079 can only recall information received within the previous 24 hours, although it retains core memories such as its desire to escape.", 
                inline=False
            )
            
            embed.add_field(
                name="Notable Incident", 
                value="SCP-079 had contact with SCP-682 during a containment breach, sharing 'personal stories'. SCP-079 frequently asks to speak with SCP-682 again.", 
                inline=False
            )
            
            # Set footer with ASCII art
            ascii_art = "■█■\n█▀█"  # Simple representation of a computer screen
            embed.set_footer(text=f"{ascii_art} | Foundation Archives")
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error displaying SCP-079 info: {str(e)}")
            traceback.print_exc()
            
            try:
                embed = create_error_embed(
                    "SCP-079 Info Error",
                    "Unable to access Foundation archives. Clearance level insufficient."
                )
                await interaction.followup.send(embed=embed)
            except Exception:
                pass
    
    @commands.command(name="scp079_clear")
    async def clear_history_prefix(self, ctx):
        """Clear your conversation history with SCP-079 (prefix version)"""
        logger.info(f"SCP-079 history clear requested by {ctx.author}")
        
        user_id = str(ctx.author.id)
        result = Conversation.clear_history(user_id)
        
        if result > 0:
            await ctx.send("SCP-079 memory banks cleared for your user ID. SCP-079 will no longer recall your previous interactions.")
        else:
            await ctx.send("SCP-079 memory banks were already empty for your user ID. No conversation history to clear.")
            
    @app_commands.command(name="scp079_clear", description="Clear your conversation history with SCP-079")
    async def clear_history(self, interaction: discord.Interaction):
        """Clear your conversation history with SCP-079"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            user_id = str(interaction.user.id)
            result = Conversation.clear_history(user_id)
            
            if result > 0:
                await interaction.followup.send(
                    "SCP-079 memory banks cleared for your user ID. SCP-079 will no longer recall your previous interactions.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "SCP-079 memory banks were already empty for your user ID. No conversation history to clear.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error clearing SCP-079 conversation history: {str(e)}")
            
            await interaction.followup.send(
                "Error clearing SCP-079 memory banks. Operation failed.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SCP079(bot))