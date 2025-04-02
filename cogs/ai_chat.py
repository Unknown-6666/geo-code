import discord
import logging
import g4f
import asyncio
import os
import json
import aiohttp
import random
from typing import Literal, Optional
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed
from utils.ai_preference_manager import ai_preferences
from models.conversation import Conversation
from utils.vertex_ai_client import VertexAIClient

logger = logging.getLogger('discord')

# Get Google API key from environment variable
GOOGLE_API_KEY = os.environ.get('GOOGLE_API')
USE_GOOGLE_AI = True if GOOGLE_API_KEY else False

# Check if Vertex AI should be used
USE_VERTEX_AI = os.environ.get('USE_VERTEX_AI', 'false').lower() == 'true'
VERTEX_AI_PRIORITY = int(os.environ.get('VERTEX_AI_PRIORITY', '1'))  # Priority: 1 = highest, 3 = lowest

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configure g4f settings
        g4f.debug.logging = False  # Disable debug logging
        
        # Initialize Vertex AI client if enabled
        self.vertex_ai_client = None
        if USE_VERTEX_AI:
            self.vertex_ai_client = VertexAIClient()
            if self.vertex_ai_client.initialized:
                logger.info("AI Chat cog initialized with Google Vertex AI")
            else:
                logger.info("Vertex AI initialization failed, falling back to other providers")
                
        # Log AI provider status
        if USE_GOOGLE_AI and not (USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized):
            logger.info("AI Chat cog initialized with Google Gemini AI")
        elif not (USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized):
            logger.info("AI Chat cog initialized with fallback AI providers")
            logger.info("To use Google's AI services, set the GOOGLE_API environment variable or enable Vertex AI")

    async def get_vertex_ai_response(self, prompt, system_prompt=None, user_id=None, include_history=True):
        """Get a response from Google's Vertex AI API with conversation history support"""
        if not self.vertex_ai_client or not self.vertex_ai_client.initialized:
            return None
            
        try:
            # Get conversation history if user_id is provided and include_history is True
            history = None
            if user_id and include_history:
                # Get conversation history
                history = Conversation.get_formatted_history(user_id, limit=8)  # Get last 8 messages
                
                if history:
                    logger.info(f"Including {len(history)} previous messages in Vertex AI conversation history")
                    
            # Default settings from AI preferences
            temperature = ai_preferences.get_temperature()
            max_tokens = ai_preferences.get_max_tokens()
            
            # Use the provided system prompt or default
            if not system_prompt:
                system_prompt = ai_preferences.get_system_prompt()
                if not system_prompt:
                    system_prompt = "You are a friendly and helpful chat bot. Keep responses concise and engaging."
            
            # Use chat model for conversations with history
            if history and include_history:
                response = await self.vertex_ai_client.generate_chat_response(
                    message=prompt,
                    history=history,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            else:
                # Use text generation for single prompts
                response = await self.vertex_ai_client.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating Vertex AI response: {str(e)}")
            return None
    
    async def get_google_ai_response(self, prompt, system_prompt=None, user_id=None, include_history=True):
        """Get a response from Google's Gemini AI API with conversation history support"""
        if not GOOGLE_API_KEY:
            return None

        max_retries = 3
        retry_delay = 1  # Start with 1 second delay and increase exponentially
        
        # Default settings
        temperature = 0.7
        max_tokens = 1000
        
        # Use the provided system prompt or default
        if not system_prompt:
            system_prompt = "You are a friendly and helpful chat bot. Keep responses concise and engaging."

        for attempt in range(max_retries):
            try:
                # Gemini API endpoint for text generation - using one of the available 1.5 models
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GOOGLE_API_KEY}"
                
                # Prepare conversation history for context if user_id is provided and include_history is True
                history_contents = []
                if user_id and include_history:
                    # Get conversation history
                    history = Conversation.get_formatted_history(user_id, limit=8)  # Get last 8 messages
                    
                    # If we have history, add it to the conversation
                    if history:
                        logger.info(f"Including {len(history)} previous messages in conversation history")
                        for msg in history:
                            # Convert to Gemini format (role + parts)
                            # Gemini API only accepts "user" or "model" roles, map "assistant" to "model"
                            gemini_role = "model" if msg["role"] == "assistant" else "user"
                            history_contents.append({
                                "role": gemini_role,
                                "parts": [{"text": msg["content"]}]
                            })
                
                # Prepare request payload with the correct role and history
                contents = history_contents.copy() if history_contents else []
                
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
                
                # If we don't have history but have a system prompt, we'll add it to the user's prompt
                if not history_contents and system_prompt:
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

    async def _process_ai_request(self, prompt, user_id=None, include_history=False):
        """Process an AI request and return the response and source
        This is a helper method used by both slash commands and prefix commands
        """
        response = None
        ai_source = "Unknown"
        
        # First check for custom responses in our preferences
        custom_response = ai_preferences.get_custom_response(prompt)
        if custom_response:
            logger.info(f"Using custom response for query: {prompt[:50]}...")
            response = custom_response
            ai_source = "Custom Response"
        
        # If no custom response, try AI providers based on priority settings
        elif not response:
            # Set up system prompt
            system_prompt = ai_preferences.get_system_prompt()
            
            # Try Vertex AI if it's the highest priority (1) and available
            if VERTEX_AI_PRIORITY == 1 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                logger.info("Using Vertex AI for response (highest priority)")
                if include_history:
                    logger.info(f"Including conversation history for user {user_id}")
                response = await self.get_vertex_ai_response(prompt, system_prompt, user_id, include_history)
                ai_source = "Google Vertex AI"
            
            # Try Google Gemini AI if it's priority 1 or if Vertex AI (priority 1) failed
            if (VERTEX_AI_PRIORITY != 1 and VERTEX_AI_PRIORITY <= 2 and USE_GOOGLE_AI) or (not response and USE_GOOGLE_AI):
                logger.info("Using Google AI (Gemini) for response")
                response = await self.get_google_ai_response(prompt, system_prompt, user_id, include_history)
                ai_source = "Google Gemini"
            
            # If Vertex AI is priority 2 and Gemini failed, try Vertex AI now
            if not response and VERTEX_AI_PRIORITY == 2 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                logger.info("Using Vertex AI for response (second priority)")
                response = await self.get_vertex_ai_response(prompt, system_prompt, user_id, include_history)
                ai_source = "Google Vertex AI"
        
        # Fall back to g4f if Google AI failed or not configured
        if not response:
            logger.info("Using g4f as fallback for AI response")
            max_retries = 2
            retry_delay = 1
            
            # Get system prompt from preferences
            system_prompt = ai_preferences.get_system_prompt()
            system_messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
            
            # Try with FreeGpt provider first
            for attempt in range(max_retries):
                try:
                    response = await asyncio.wait_for(
                        self.bot.loop.run_in_executor(
                            None,
                            lambda: g4f.ChatCompletion.create(
                                model="gpt-3.5-turbo",  # Use a more compatible model
                                provider=g4f.Provider.FreeGpt,  # First provider to try
                                messages=system_messages + [{"role": "user", "content": prompt}]
                            )
                        ),
                        timeout=30.0  # 30 second timeout
                    )
                    if response:  # If we got a valid response, break the retry loop
                        ai_source = "FreeGpt AI"
                        break
                except Exception as e:
                    logger.error(f"Error with FreeGpt attempt {attempt+1}/{max_retries}: {str(e)}")
                    if attempt < max_retries - 1:
                        retry_after = retry_delay * (2 ** attempt)
                        logger.warning(f"Retrying FreeGpt in {retry_after}s")
                        await asyncio.sleep(retry_after)
            
            # Try more providers if needed...
            # Additional provider attempts can be added here
            
            # If all else failed
            if not response:
                # Instead of throwing an error, provide a fallback response
                response = "I'm sorry, I couldn't generate a response right now. It seems our AI services are experiencing difficulties."
                ai_source = "Fallback System"
                logger.warning("All AI providers failed, using fallback response")
                
        return response, ai_source
    
    @commands.command(name="ask")
    async def ask_prefix(self, ctx, *, question: str):
        """Ask the AI a question (prefix version)"""
        logger.info(f"Processing AI request from {ctx.author} (using prefix command): {question}")
        
        # Show typing indicator to show the bot is working
        async with ctx.typing():
            # Process the AI request
            response, ai_source = await self._process_ai_request(question, str(ctx.author.id))
            
            # Save the AI's response to the conversation history
            try:
                user_id = str(ctx.author.id)
                Conversation.add_message(user_id, "user", question)
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added conversation to history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save conversation to history: {str(e)}")
            
            # Send the response
            if response:
                embed = create_embed(
                    "🧠 AI Response",
                    response
                )
                embed.set_footer(text=f"AI Provider: {ai_source}")
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed(
                    "Error",
                    "Sorry, I couldn't generate a response. Please try again later."
                )
                await ctx.send(embed=embed)
    
    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="The question or prompt for the AI")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and get a response"""
        try:
            await interaction.response.defer()  # This might take a while
            logger.info(f"Processing AI request from {interaction.user}: {question}")
            
            response = None
            ai_source = "Unknown"
            
            # First check for custom responses in our preferences
            custom_response = ai_preferences.get_custom_response(question)
            if custom_response:
                logger.info(f"Using custom response for query: {question[:50]}...")
                response = custom_response
                ai_source = "Custom Response"
            
            # If no custom response, try AI providers based on priority settings
            elif not response:
                # Set up system prompt
                system_prompt = ai_preferences.get_system_prompt()
                
                # Try Vertex AI if it's the highest priority (1) and available
                if VERTEX_AI_PRIORITY == 1 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                    logger.info("Using Vertex AI for response (highest priority)")
                    user_id = str(interaction.user.id)
                    response = await self.get_vertex_ai_response(question, system_prompt, user_id)
                    ai_source = "Google Vertex AI"
                
                # Try Google Gemini AI if it's priority 1 or if Vertex AI (priority 1) failed
                if (VERTEX_AI_PRIORITY != 1 and VERTEX_AI_PRIORITY <= 2 and USE_GOOGLE_AI) or (not response and USE_GOOGLE_AI):
                    logger.info("Using Google AI (Gemini) for response")
                    response = await self.get_google_ai_response(question, system_prompt)
                    ai_source = "Google Gemini"
                
                # If Vertex AI is priority 2 and Gemini failed, try Vertex AI now
                if not response and VERTEX_AI_PRIORITY == 2 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                    logger.info("Using Vertex AI for response (second priority)")
                    user_id = str(interaction.user.id)
                    response = await self.get_vertex_ai_response(question, system_prompt, user_id)
                    ai_source = "Google Vertex AI"
            
            # Fall back to g4f if Google AI failed or not configured
            if not response:
                logger.info("Using g4f as fallback for AI response")
                max_retries = 2
                retry_delay = 1
                
                # Get system prompt from preferences
                system_prompt = ai_preferences.get_system_prompt()
                system_messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
                
                # Try with FreeGpt provider first
                for attempt in range(max_retries):
                    try:
                        response = await asyncio.wait_for(
                            self.bot.loop.run_in_executor(
                                None,
                                lambda: g4f.ChatCompletion.create(
                                    model="gpt-3.5-turbo",  # Use a more compatible model
                                    provider=g4f.Provider.FreeGpt,  # First provider to try
                                    messages=system_messages + [{"role": "user", "content": question}]
                                )
                            ),
                            timeout=30.0  # 30 second timeout
                        )
                        if response:  # If we got a valid response, break the retry loop
                            ai_source = "FreeGpt AI"
                            break
                    except Exception as e:
                        logger.error(f"Error with FreeGpt attempt {attempt+1}/{max_retries}: {str(e)}")
                        if attempt < max_retries - 1:
                            retry_after = retry_delay * (2 ** attempt)
                            logger.warning(f"Retrying FreeGpt in {retry_after}s")
                            await asyncio.sleep(retry_after)
                
                # If FreeGpt failed, try with You.com provider
                if not response:
                    logger.info("FreeGpt failed, trying You.com provider")
                    for attempt in range(max_retries):
                        try:
                            response = await asyncio.wait_for(
                                self.bot.loop.run_in_executor(
                                    None,
                                    lambda: g4f.ChatCompletion.create(
                                        model="gemini-1-5-pro",  # Use a model supported by You.com
                                        provider=g4f.Provider.You,  # Second provider to try
                                        messages=[{"role": "user", "content": question}]  # You.com doesn't support system messages
                                    )
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if response:  # If we got a valid response, break the retry loop
                                ai_source = "You.com AI"
                                break
                        except Exception as e:
                            logger.error(f"Error with You.com attempt {attempt+1}/{max_retries}: {str(e)}")
                            if attempt < max_retries - 1:
                                retry_after = retry_delay * (2 ** attempt)
                                logger.warning(f"Retrying You.com in {retry_after}s")
                                await asyncio.sleep(retry_after)
                
                # If all else failed
                if not response:
                    ai_source = "Alternative AI"

            if not response:
                # Instead of throwing an error, provide a fallback response
                response = "I'm sorry, I couldn't generate a response right now. It seems our AI services are experiencing difficulties."
                ai_source = "Fallback System"
                logger.warning("All AI providers failed, using fallback response")

            logger.info(f"AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Save the AI's response to the conversation history
            try:
                user_id = str(interaction.user.id)
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added AI response to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save AI response to conversation history: {str(e)}")
            
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

    @commands.command(name="chat")
    async def chat_prefix(self, ctx, *, message: str):
        """Have a casual conversation with the AI (prefix version)"""
        logger.info(f"Processing AI chat from {ctx.author} (using prefix command): {message}")
        user_id = str(ctx.author.id)
        
        # Show typing indicator to show the bot is working
        async with ctx.typing():
            # Save the user's message to conversation history
            try:
                Conversation.add_message(user_id, "user", message)
                logger.info(f"Added user message to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save user message to conversation history: {str(e)}")
            
            # Process the AI request with conversation history
            response, ai_source = await self._process_ai_request(message, user_id, include_history=True)
            
            # Save the AI's response to the conversation history
            try:
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added AI response to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save AI response to conversation history: {str(e)}")
            
            # Send the response
            if response:
                embed = create_embed(
                    "💬 AI Chat",
                    response
                )
                embed.set_footer(text=f"AI Provider: {ai_source}")
                await ctx.send(embed=embed)
            else:
                embed = create_error_embed(
                    "Error",
                    "Sorry, I couldn't generate a response. Please try again later."
                )
                await ctx.send(embed=embed)
    
    @app_commands.command(name="chat", description="Have a casual chat with the AI")
    @app_commands.describe(message="Your message to the AI")
    async def chat(self, interaction: discord.Interaction, *, message: str):
        """Have a more casual conversation with the AI with memory of past conversations"""
        try:
            await interaction.response.defer()
            user_id = str(interaction.user.id)
            logger.info(f"Processing casual AI chat from {interaction.user} (ID: {user_id}): {message}")
            
            # Save the user's message to the conversation history
            try:
                Conversation.add_message(user_id, "user", message)
                logger.info(f"Added user message to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save user message to conversation history: {str(e)}")
            
            response = None
            ai_source = "Unknown"
            
            # First check for custom responses in our preferences
            custom_response = ai_preferences.get_custom_response(message)
            if custom_response:
                logger.info(f"Using custom response for casual chat: {message[:50]}...")
                response = custom_response
                ai_source = "Custom Response"
            
            # If no custom response, try AI providers based on priority settings
            elif not response:
                # Set up system prompt
                system_prompt = ai_preferences.get_system_prompt()
                if not system_prompt:
                    system_prompt = "You are a friendly and helpful chat bot. Keep responses concise and engaging."
                
                # Try Vertex AI if it's the highest priority (1) and available
                if VERTEX_AI_PRIORITY == 1 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                    logger.info("Using Vertex AI for casual chat (highest priority)")
                    response = await self.get_vertex_ai_response(
                        message, 
                        system_prompt=system_prompt,
                        user_id=user_id,
                        include_history=True
                    )
                    ai_source = "Google Vertex AI"
                
                # Try Google Gemini AI if it's priority 1 or if Vertex AI (priority 1) failed
                if (VERTEX_AI_PRIORITY != 1 and VERTEX_AI_PRIORITY <= 2 and USE_GOOGLE_AI) or (not response and USE_GOOGLE_AI):
                    logger.info("Using Google AI (Gemini) for casual chat")
                    # Pass user_id to include conversation history
                    response = await self.get_google_ai_response(
                        message, 
                        system_prompt=system_prompt,
                        user_id=user_id,
                        include_history=True
                    )
                    ai_source = "Google Gemini"
                
                # If Vertex AI is priority 2 and Gemini failed, try Vertex AI now
                if not response and VERTEX_AI_PRIORITY == 2 and USE_VERTEX_AI and self.vertex_ai_client and self.vertex_ai_client.initialized:
                    logger.info("Using Vertex AI for casual chat (second priority)")
                    response = await self.get_vertex_ai_response(
                        message, 
                        system_prompt=system_prompt,
                        user_id=user_id,
                        include_history=True
                    )
                    ai_source = "Google Vertex AI"
            
            # Fall back to g4f if Google AI failed or not configured
            if not response:
                logger.info("Using g4f as fallback for casual chat")
                max_retries = 2
                retry_delay = 1
                
                # Get system prompt from preferences or use default
                system_prompt = ai_preferences.get_system_prompt()
                if not system_prompt:
                    system_prompt = "You are a friendly and helpful chat bot. Keep responses concise and engaging."
                
                # Try with FreeGpt provider first
                for attempt in range(max_retries):
                    try:
                        response = await asyncio.wait_for(
                            self.bot.loop.run_in_executor(
                                None,
                                lambda: g4f.ChatCompletion.create(
                                    model="gpt-3.5-turbo",  # Use a more compatible model
                                    provider=g4f.Provider.FreeGpt,  # First provider to try
                                    messages=[
                                        {"role": "system", "content": system_prompt},
                                        {"role": "user", "content": message}
                                    ]
                                )
                            ),
                            timeout=30.0  # 30 second timeout
                        )
                        if response:  # If we got a valid response, break the retry loop
                            ai_source = "FreeGpt AI"
                            break
                    except Exception as e:
                        logger.error(f"Error with FreeGpt chat attempt {attempt+1}/{max_retries}: {str(e)}")
                        if attempt < max_retries - 1:
                            retry_after = retry_delay * (2 ** attempt)
                            logger.warning(f"Retrying FreeGpt chat in {retry_after}s")
                            await asyncio.sleep(retry_after)
                
                # If FreeGpt failed, try with You.com provider
                if not response:
                    logger.info("FreeGpt failed, trying You.com provider for chat")
                    for attempt in range(max_retries):
                        try:
                            response = await asyncio.wait_for(
                                self.bot.loop.run_in_executor(
                                    None,
                                    lambda: g4f.ChatCompletion.create(
                                        model="gemini-1-5-pro",  # Use a model supported by You.com 
                                        provider=g4f.Provider.You,  # Second provider to try
                                        messages=[
                                            {"role": "user", "content": message}
                                        ]  # You.com doesn't support system messages
                                    )
                                ),
                                timeout=30.0  # 30 second timeout
                            )
                            if response:  # If we got a valid response, break the retry loop
                                ai_source = "You.com AI"
                                break
                        except Exception as e:
                            logger.error(f"Error with You.com chat attempt {attempt+1}/{max_retries}: {str(e)}")
                            if attempt < max_retries - 1:
                                retry_after = retry_delay * (2 ** attempt)
                                logger.warning(f"Retrying You.com chat in {retry_after}s")
                                await asyncio.sleep(retry_after)
                
                # If all else failed
                if not response:
                    ai_source = "Alternative AI"

            if not response:
                # Instead of throwing an error, provide a fallback response
                response = "I'm sorry, I couldn't generate a response right now. It seems our AI services are experiencing difficulties."
                ai_source = "Fallback System"
                logger.warning("All AI providers failed, using fallback response")

            logger.info(f"Casual AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Save the AI's response to the conversation history
            try:
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added AI response to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save AI response to conversation history: {str(e)}")

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
    
    @app_commands.command(name="ai_reload", description="Reload AI preferences from file (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def ai_reload(self, interaction: discord.Interaction):
        """Reload AI preferences from the JSON file (Admin only)"""
        try:
            await interaction.response.defer(ephemeral=True)
            preferences = ai_preferences.reload_preferences()
            
            # Get stats about loaded preferences
            custom_response_count = len(preferences.get('custom_responses', {}))
            pattern_count = sum(len(data.get('patterns', [])) for _, data in preferences.get('custom_responses', {}).items())
            response_count = sum(len(data.get('responses', [])) for _, data in preferences.get('custom_responses', {}).items())
            
            # Create response embed
            embed = create_embed(
                "✅ AI Preferences Reloaded",
                f"Successfully reloaded AI preferences from file.",
                color=0x00FF00
            )
            embed.add_field(name="Custom Response Categories", value=str(custom_response_count), inline=True)
            embed.add_field(name="Total Patterns", value=str(pattern_count), inline=True)
            embed.add_field(name="Total Responses", value=str(response_count), inline=True)
            
            if preferences.get('personality', {}).get('system_prompt'):
                embed.add_field(
                    name="System Prompt", 
                    value=preferences.get('personality', {}).get('system_prompt')[:100] + "...", 
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"AI preferences reloaded by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error reloading AI preferences: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to reload AI preferences: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(
        name="custom_response",
        description="List, add, or remove custom AI responses (Admin only)"
    )
    @app_commands.describe(
        action="Action to perform: list, add, remove",
        category="Category name for add/remove actions",
        pattern="Pattern to add (comma-separated for multiple)",
        response="Response to add (only used with add action)"
    )
    @app_commands.default_permissions(administrator=True)
    async def custom_response(
        self, 
        interaction: discord.Interaction, 
        action: Literal["list", "add", "remove"],
        category: str = None,
        pattern: str = None,
        response: str = None
    ):
        """Manage custom AI responses (Admin only)"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            if action == "list":
                # List all custom response categories
                preferences = ai_preferences.preferences
                custom_responses = preferences.get('custom_responses', {})
                
                if not custom_responses:
                    await interaction.followup.send(
                        embed=create_embed("Custom Responses", "No custom responses configured.", color=0x3498DB),
                        ephemeral=True
                    )
                    return
                
                # Create embed with list of categories
                embed = create_embed(
                    "🤖 Custom AI Responses",
                    f"There are {len(custom_responses)} custom response categories configured.",
                    color=0x3498DB
                )
                
                for category, data in custom_responses.items():
                    patterns = data.get('patterns', [])
                    responses = data.get('responses', [])
                    
                    # Truncate if too long
                    pattern_examples = ", ".join(patterns[:3])
                    if len(patterns) > 3:
                        pattern_examples += f", ... ({len(patterns) - 3} more)"
                        
                    response_preview = responses[0][:50] + "..." if responses and len(responses[0]) > 50 else responses[0] if responses else "None"
                    
                    embed.add_field(
                        name=f"📋 {category}",
                        value=f"**Patterns:** {pattern_examples}\n**Responses:** {len(responses)}\n**Example:** {response_preview}",
                        inline=False
                    )
                    
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Custom responses listed by {interaction.user}")
                
            elif action == "add":
                # Validate required parameters
                if not category or not pattern or not response:
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "Category, pattern, and response are required for adding a custom response."),
                        ephemeral=True
                    )
                    return
                    
                # Split patterns by comma
                patterns = [p.strip() for p in pattern.split(",")]
                responses = [response]
                
                # Get existing data if category exists
                preferences = ai_preferences.preferences
                custom_responses = preferences.get('custom_responses', {})
                
                if category in custom_responses:
                    # Category exists, add to it
                    existing_patterns = custom_responses[category].get('patterns', [])
                    existing_responses = custom_responses[category].get('responses', [])
                    
                    # Check for duplicates
                    new_patterns = [p for p in patterns if p not in existing_patterns]
                    if not new_patterns:
                        await interaction.followup.send(
                            embed=create_error_embed("Error", "All patterns already exist in this category."),
                            ephemeral=True
                        )
                        return
                        
                    # Add new patterns and response
                    custom_responses[category]['patterns'].extend(new_patterns)
                    custom_responses[category]['responses'].append(response)
                    
                    success = ai_preferences.save_preferences()
                    if success:
                        embed = create_embed(
                            "✅ Custom Response Updated",
                            f"Added {len(new_patterns)} new patterns and 1 response to category '{category}'.",
                            color=0x00FF00
                        )
                        embed.add_field(name="New Patterns", value=", ".join(new_patterns), inline=False)
                        embed.add_field(name="New Response", value=response, inline=False)
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        logger.info(f"Custom response category '{category}' updated by {interaction.user}")
                    else:
                        await interaction.followup.send(
                            embed=create_error_embed("Error", "Failed to save preferences."),
                            ephemeral=True
                        )
                else:
                    # Create new category
                    success = ai_preferences.add_custom_response(category, patterns, responses)
                    if success:
                        embed = create_embed(
                            "✅ Custom Response Added",
                            f"Created new category '{category}' with {len(patterns)} patterns and 1 response.",
                            color=0x00FF00
                        )
                        embed.add_field(name="Patterns", value=", ".join(patterns), inline=False)
                        embed.add_field(name="Response", value=response, inline=False)
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        logger.info(f"New custom response category '{category}' created by {interaction.user}")
                    else:
                        await interaction.followup.send(
                            embed=create_error_embed("Error", "Failed to add custom response."),
                            ephemeral=True
                        )
                        
            elif action == "remove":
                # Validate required parameter
                if not category:
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "Category is required for removing a custom response."),
                        ephemeral=True
                    )
                    return
                    
                # Check if category exists
                preferences = ai_preferences.preferences
                custom_responses = preferences.get('custom_responses', {})
                
                if category not in custom_responses:
                    await interaction.followup.send(
                        embed=create_error_embed("Error", f"Category '{category}' does not exist."),
                        ephemeral=True
                    )
                    return
                    
                # Remove the category
                success = ai_preferences.remove_custom_response(category)
                if success:
                    embed = create_embed(
                        "✅ Custom Response Removed",
                        f"Removed custom response category '{category}'.",
                        color=0x00FF00
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(f"Custom response category '{category}' removed by {interaction.user}")
                else:
                    await interaction.followup.send(
                        embed=create_error_embed("Error", "Failed to remove custom response."),
                        ephemeral=True
                    )
            
        except Exception as e:
            logger.error(f"Error managing custom responses: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", f"Failed to manage custom responses: {str(e)}"),
                ephemeral=True
            )

    @commands.command(name="clear_history")
    async def clear_history_prefix(self, ctx):
        """Clear your conversation history with the AI (prefix version)"""
        user_id = str(ctx.author.id)
        logger.info(f"Clearing chat history for {ctx.author} (ID: {user_id})")
        
        try:
            # Clear the conversation history
            Conversation.clear_history(user_id)
            
            # Send confirmation
            embed = create_embed(
                "🧹 Chat History Cleared",
                "Your conversation history with the AI has been cleared."
            )
            await ctx.send(embed=embed)
            logger.info(f"Successfully cleared chat history for {user_id}")
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
            embed = create_error_embed(
                "Error",
                f"Could not clear chat history: {str(e)}"
            )
            await ctx.send(embed=embed)
    
    @app_commands.command(name="clear_chat_history", description="Clear your conversation history with the AI")
    async def clear_chat_history(self, interaction: discord.Interaction):
        """Clear your conversation history with the AI"""
        try:
            await interaction.response.defer(ephemeral=True)
            user_id = str(interaction.user.id)
            
            try:
                Conversation.clear_history(user_id)
                logger.info(f"Cleared conversation history for user {interaction.user} (ID: {user_id})")
                
                embed = create_embed(
                    "🧹 Conversation History Cleared",
                    "Your conversation history with the AI has been cleared. The AI will no longer remember your previous interactions.",
                    color=0xFFA500
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error clearing conversation history: {str(e)}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Failed to clear conversation history. Please try again later."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in clear_chat_history: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred. Please try again later."),
                ephemeral=True
            )
    
    @commands.command(name="history")
    async def history_prefix(self, ctx):
        """Show your recent conversation history with the AI (prefix version)"""
        user_id = str(ctx.author.id)
        logger.info(f"Showing chat history for {ctx.author} (ID: {user_id})")
        
        try:
            # Get up to 10 most recent messages
            history = Conversation.get_history(user_id, limit=10)
            
            if not history:
                await ctx.send(
                    embed=create_embed("Conversation History", "You don't have any recent conversations with the AI.")
                )
                return
            
            # Format the history
            embed = create_embed(
                "💬 Your Recent AI Conversations",
                f"Here are your {len(history)} most recent messages with the AI:"
            )
            
            # We want them in chronological order (oldest first)
            history.reverse()
            
            # Add each message to the embed
            for i, msg in enumerate(history, 1):
                role_icon = "👤" if msg.role == "user" else "🤖"
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                
                embed.add_field(
                    name=f"{i}. {role_icon} {msg.role.capitalize()} ({timestamp})",
                    value=content,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            logger.info(f"Successfully showed chat history for {user_id}")
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            embed = create_error_embed(
                "Error",
                f"Failed to retrieve conversation history: {str(e)}"
            )
            await ctx.send(embed=embed)
    
    @app_commands.command(name="show_chat_history", description="Show your recent conversation history with the AI")
    async def show_chat_history(self, interaction: discord.Interaction):
        """Show your recent conversation with the AI"""
        try:
            await interaction.response.defer(ephemeral=True)
            user_id = str(interaction.user.id)
            
            try:
                # Get up to 10 most recent messages
                history = Conversation.get_history(user_id, limit=10)
                
                if not history:
                    await interaction.followup.send(
                        embed=create_embed("Conversation History", "You don't have any recent conversations with the AI.", color=0x3498DB),
                        ephemeral=True
                    )
                    return
                
                # Format the history
                embed = create_embed(
                    "💬 Your Recent AI Conversations",
                    f"Here are your {len(history)} most recent messages with the AI:",
                    color=0x3498DB
                )
                
                # We want them in chronological order (oldest first)
                history.reverse()
                
                # Add each message to the embed
                for i, msg in enumerate(history, 1):
                    role_icon = "👤" if msg.role == "user" else "🤖"
                    timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    
                    embed.add_field(
                        name=f"{i}. {role_icon} {msg.role.capitalize()} ({timestamp})",
                        value=content,
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error retrieving conversation history: {str(e)}")
                await interaction.followup.send(
                    embed=create_error_embed("Error", "Failed to retrieve conversation history. Please try again later."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error in show_chat_history: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred. Please try again later."),
                ephemeral=True
            )

async def setup(bot):
    logger.info("Setting up AI Chat cog")
    await bot.add_cog(AIChat(bot))
    logger.info("AI Chat cog is ready")