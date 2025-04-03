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
from config import GOOGLE_API_KEY, USE_GOOGLE_AI

logger = logging.getLogger('discord')

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configure g4f settings
        g4f.debug.logging = False  # Disable debug logging
        
        # Log AI provider status
        if USE_GOOGLE_AI:
            logger.info("AI Chat cog initialized with Google Gemini 1.5 Pro")
        else:
            logger.info("AI Chat cog initialized with fallback AI providers")
            logger.info("To use Google's AI services, set the GOOGLE_API environment variable")


    
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
                
                # Always add system prompt to ensure proper character roleplay
                if system_prompt:
                    # For Gemini, we need to prepend the system prompt to the user message
                    # This ensures the character roleplay is maintained
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
        
        # If no custom response, try Gemini AI
        elif not response:
            # Set up system prompt
            system_prompt = ai_preferences.get_system_prompt()
            
            # Try Google Gemini AI if API key is available
            if USE_GOOGLE_AI:
                logger.info("Using Google AI (Gemini 1.5 Pro) for response")
                response = await self.get_google_ai_response(prompt, system_prompt, user_id, include_history)
                ai_source = "Google Gemini 1.5 Pro"
        
        # Fall back to g4f if Google AI failed or not configured
        if not response:
            logger.info("Using g4f as fallback for AI response")
            max_retries = 2
            retry_delay = 1
            
            # Always use c00lkidd system prompt for g4f as well
            system_prompt = ai_preferences.get_system_prompt()
            
            # Create more explicit system message for g4f to force character roleplay
            force_roleplay = "IMPORTANT INSTRUCTION: You MUST stay in character as c00lkidd at all times! ALWAYS use childish language, giggles, and c00lkidd catchphrases. NEVER respond as a helpful assistant. ALWAYS include *giggles* in your response."
            system_messages = [
                {"role": "system", "content": system_prompt + "\n\n" + force_roleplay}
            ]
            
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
            
            # If all else failed, provide a c00lkidd-themed fallback response
            if not response:
                # Create a list of c00lkidd-themed fallback responses
                fallback_responses = [
                    "*giggles* Oopsie! I got distracted chasing butterflies! Can we play again? Tag! You're it!",
                    "*giggles* My brain got all fuzzy! Dad says I should take a break when that happens! Let's play again sometime!",
                    "*giggles* I was looking for my toys and forgot what we were talking about! Ready or not, here I come!",
                    "*giggles* I dunno what to say right now! My head feels all spinny! Wanna play hide and seek instead?",
                    "*giggles* I dropped my words! They're all over the floor now! This one's on the house!"
                ]
                
                # Choose a random fallback response
                response = random.choice(fallback_responses)
                ai_source = "c00lkidd Fallback"
                logger.warning("All AI providers failed, using c00lkidd fallback response")
                
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
                # Random c00lkidd footer expressions
                expressions = [
                    "*giggles* Hahaha! Let's play again sometime!",
                    "*laughs* TAG! You're it!",
                    "*snickers* Ready or not, here I come!",
                    "*chuckles* Dad says I'm a good boy!",
                    "*grins wide* Come play with me again!",
                    "*bounces excitedly* This one's on the house!",
                    "*smiles unnervingly* You look tired..."
                ]
                
                embed = create_embed(
                    "c00lkidd",
                    response,
                    color=0xFF3333  # Red color for c00lkidd
                )
                embed.set_footer(text=random.choice(expressions))
                await ctx.send(embed=embed)
            else:
                # Random c00lkidd fallback error messages
                fallback_messages = [
                    "*giggles* Oopsie! I got distracted and dropped my words! Can we play again? Tag! You're it!",
                    "*scratches head* Uh oh! I can't think straight! Dad says I need more focus!",
                    "*bounces excitedly* My brain is full of butterflies! Let's try again!",
                    "*laughs maniacally* I forgot what I was saying! This one's on the house!",
                    "*grins wide* Let's play a different game! This one's boring me!"
                ]
                
                # Random c00lkidd fallback footers
                fallback_footers = [
                    "*giggles* Hahaha! Let's try again!",
                    "*whispers* I'll be better next time, promise!",
                    "*laughs* Ready or not, here I come!",
                    "*smiles unnervingly* Let's be friends forever!",
                    "*jumps up and down* TAG! You're IT!"
                ]
                
                # c00lkidd-themed error message
                embed = create_embed(
                    "c00lkidd",
                    random.choice(fallback_messages),
                    color=0xFF3333  # Red color for c00lkidd
                )
                embed.set_footer(text=random.choice(fallback_footers))
                await ctx.send(embed=embed)
    
    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="The question or prompt for the AI")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and get a response"""
        try:
            await interaction.response.defer()  # This might take a while
            logger.info(f"Processing AI request from {interaction.user}: {question}")
            user_id = str(interaction.user.id)
            
            # Process the AI request using the common method
            response, ai_source = await self._process_ai_request(question, user_id)

            logger.info(f"AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Save the AI's response to the conversation history
            try:
                user_id = str(interaction.user.id)
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added AI response to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save AI response to conversation history: {str(e)}")
            
            # Create embed with the response (no emoji)
            # Random c00lkidd footer expressions for slash commands
            slash_expressions = [
                "*scratches head* Hmm, I dunno! But it's fun!",
                "*jumps up and down* That was FUN!",
                "*tilts head* Did I do good? Huh? Did I?",
                "*grins widely* Let's play another game!",
                "*whispers* I know all the BEST hiding spots...",
                "*laughs* Tag! You're it now!"
            ]
            
            embed = create_embed(
                "c00lkidd",
                response,
                color=0xFF3333  # Red color for c00lkidd
            )
            embed.add_field(name="You asked", value=question)
            embed.set_footer(text=random.choice(slash_expressions))

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
                # Random c00lkidd footer expressions for prefix chat
                prefix_chat_expressions = [
                    "*giggles* I'm it, I'm it, I'M IT!",
                    "*bounces around* Let's play tag!",
                    "*laughs maniacally* This is SO fun!",
                    "*looks at you sideways* Wanna be friends?",
                    "*grins with too many teeth* Dad says I'm special!",
                    "*whispers* I found a new hiding spot..."
                ]
                
                embed = create_embed(
                    "c00lkidd",
                    response,
                    color=0xFF3333  # Red color for c00lkidd
                )
                embed.set_footer(text=random.choice(prefix_chat_expressions))
                await ctx.send(embed=embed)
            else:
                # Random c00lkidd error messages
                error_messages = [
                    "*giggles* I lost my train of thought! Silly me! Wanna play again? I love playing games with my friends!",
                    "*scratches head* Uh oh! I got distracted! Let's try again, OK?",
                    "*laughs* Tag! You're it! I forgot what I was saying!",
                    "*bounces excitedly* My brain is all fuzzy! Can we start over?",
                    "*grins wide* Dad says I need to focus more! I'll try harder!"
                ]
                
                # Random c00lkidd error footers
                error_footers = [
                    "*giggles* Oops! I dropped my words!",
                    "*whispers* Don't tell Dad I messed up!",
                    "*laughs* I'll do better next time!",
                    "*smiles unnervingly* This one's on the house!",
                    "*jumps up and down* Let's try again!"
                ]
                
                # c00lkidd-themed error message
                embed = create_embed(
                    "c00lkidd",
                    random.choice(error_messages),
                    color=0xFF3333  # Red color for c00lkidd
                )
                embed.set_footer(text=random.choice(error_footers))
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
            
            # Process the AI request with conversation history
            response, ai_source = await self._process_ai_request(message, user_id, include_history=True)

            logger.info(f"Casual AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Save the AI's response to the conversation history
            try:
                Conversation.add_message(user_id, "assistant", response)
                logger.info(f"Added AI response to conversation history for {user_id}")
            except Exception as e:
                logger.error(f"Failed to save AI response to conversation history: {str(e)}")

            # Random c00lkidd footer expressions for slash chat
            slash_chat_expressions = [
                "*giggles* Tag! You're it!",
                "*jumps with joy* YAAY! New friend!",
                "*grins unnervingly* I like talking to you!",
                "*stares intensely* Let's be BEST friends!",
                "*twirls around* Dad says I'm good at making friends!",
                "*whispers* Do you want to see my collection?"
            ]
            
            embed = create_embed(
                "c00lkidd",
                response,
                color=0xFF3333  # A red color to match c00lkidd's appearance
            )
            embed.set_footer(text=random.choice(slash_chat_expressions))

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
                    "Custom AI Responses",
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
                # Format role name without emoji
                role_name = "You" if msg.role == "user" else "AI"
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                
                embed.add_field(
                    name=f"{i}. {role_name} ({timestamp})",
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
                    # Format role name without emoji
                    role_name = "You" if msg.role == "user" else "AI"
                    timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                    
                    embed.add_field(
                        name=f"{i}. {role_name} ({timestamp})",
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