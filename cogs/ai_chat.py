import discord
import logging
import random
from discord import app_commands
from discord.ext import commands
from utils.embed_helpers import create_embed, create_error_embed

logger = logging.getLogger('discord')

# Simple responses for demonstration
RESPONSES = [
    "That's an interesting question! Let me think about it...",
    "I understand what you're asking. Here's what I think...",
    "Based on my knowledge, I would say...",
    "That's a great point! Here's my perspective...",
    "Let me break this down for you...",
]

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("AI Chat cog initialized")

    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(question="The question or prompt for the AI")
    async def ask(self, interaction: discord.Interaction, *, question: str):
        """Ask the AI a question and get a response"""
        try:
            await interaction.response.defer()  # This might take a while
            logger.info(f"Processing AI request from {interaction.user}: {question}")

            # Generate a simple response
            response = random.choice(RESPONSES) + "\n" + question.capitalize()

            # Create embed with the response
            embed = create_embed(
                "🤖 AI Response",
                response,
                color=0x7289DA
            )
            embed.add_field(name="Your Question", value=question)

            await interaction.followup.send(embed=embed)
            logger.info("Successfully generated AI response")

        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred while generating the response."),
                ephemeral=True
            )

    @app_commands.command(name="chat", description="Have a casual chat with the AI")
    @app_commands.describe(message="Your message to the AI")
    async def chat(self, interaction: discord.Interaction, *, message: str):
        """Have a more casual conversation with the AI"""
        try:
            await interaction.response.defer()
            logger.info(f"Processing casual AI chat from {interaction.user}: {message}")

            # Generate a casual response
            responses = [
                f"Hey there! {message} is interesting to think about...",
                f"I hear you! When you say {message}, it makes me think...",
                f"Let's chat about that! {message} is a fascinating topic...",
                f"Thanks for sharing! {message} reminds me of...",
            ]

            response = random.choice(responses)

            embed = create_embed(
                "💭 AI Chat",
                response,
                color=0x43B581
            )

            await interaction.followup.send(embed=embed)
            logger.info("Successfully generated casual AI response")

        except Exception as e:
            logger.error(f"Error in AI chat: {str(e)}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "An error occurred during our conversation."),
                ephemeral=True
            )

async def setup(bot):
    logger.info("Setting up AI Chat cog")
    await bot.add_cog(AIChat(bot))
    logger.info("AI Chat cog is ready")