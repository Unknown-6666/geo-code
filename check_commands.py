"""
Temporary script to check Discord commands registration
"""
import asyncio
import os
import logging
import sys
from bot import Bot

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_commands():
    """Check if commands are correctly registered"""
    # Create a bot instance with the same configuration
    logger.info("Creating bot instance...")
    bot = Bot()
    
    # Load all the essential cogs for checking
    logger.info("Loading cogs...")
    essential_cogs = [
        "cogs.basic_commands",
        "cogs.fun_commands",
        "cogs.ai_moderation",
    ]
    
    database_cogs = [
        "cogs.economy",
        "cogs.moderation",
        "cogs.profanity_filter",
        "cogs.rules_enforcer",
    ]
    
    for cog in essential_cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded {cog} successfully")
        except Exception as e:
            logger.error(f"Error loading {cog}: {e}")
    
    for cog in database_cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded {cog} successfully")
        except Exception as e:
            logger.error(f"Error loading {cog}: {e}")
    
    # Get all registered commands
    logger.info("Checking registered application commands...")
    all_commands = bot.tree.get_commands()
    
    # Log all commands
    logger.info(f"Found {len(all_commands)} total slash commands:")
    for cmd in all_commands:
        logger.info(f"- {cmd.name}: {cmd.description}")
    
    # Check for traditional commands
    logger.info("Checking traditional commands...")
    prefix_commands = [cmd.name for cmd in bot.commands]
    logger.info(f"Found {len(prefix_commands)} total prefix commands: {prefix_commands}")

if __name__ == "__main__":
    asyncio.run(check_commands())