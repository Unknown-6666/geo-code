import discord
import logging
import g4f
import asyncio
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("AI Chat cog initialized")
        # Configure g4f settings
        g4f.debug.logging = False  # Disable debug logging

    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="The question or prompt for the AI")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and get a response"""
        try:
            await interaction.response.defer()  # This might take a while
            logger.info(f"Processing AI request from {interaction.user}: {question}")

            # Generate response using g4f
            response = await asyncio.wait_for(
                self.bot.loop.run_in_executor(
                    None,
                    lambda: g4f.ChatCompletion.create(
                        messages=[{"role": "user", "content": question}]
                    )
                ),
                timeout=30.0  # 30 second timeout
            )

            if not response:
                raise ValueError("Empty response received from AI provider")

            logger.info(f"AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            # Create embed with the response
            embed = create_embed(
                "🤖 AI Response",
                response,
                color=0x7289DA
            )
            embed.add_field(name="Your Question", value=question)

            await interaction.followup.send(embed=embed)
            logger.info("Successfully sent AI response")

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

            # Generate response using g4f
            response = await asyncio.wait_for(
                self.bot.loop.run_in_executor(
                    None,
                    lambda: g4f.ChatCompletion.create(
                        messages=[
                            {"role": "system", "content": "You are a friendly and helpful chat bot. Keep responses concise and engaging."},
                            {"role": "user", "content": message}
                        ]
                    )
                ),
                timeout=30.0  # 30 second timeout
            )

            if not response:
                raise ValueError("Empty response received from AI provider")

            logger.info(f"Casual AI Response generated successfully: {response[:100]}...")  # Log first 100 chars

            embed = create_embed(
                "💭 AI Chat",
                response,
                color=0x43B581
            )

            await interaction.followup.send(embed=embed)
            logger.info("Successfully sent casual AI response")

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