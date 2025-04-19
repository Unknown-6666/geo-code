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
    
    # Load the basic commands cog for checking
    logger.info("Loading basic commands cog...")
    try:
        await bot.load_extension("cogs.basic_commands")
        logger.info("Basic commands cog loaded successfully")
    except Exception as e:
        logger.error(f"Error loading basic commands cog: {e}")
        return
    
    # Get all registered commands
    logger.info("Checking registered application commands...")
    all_commands = bot.tree.get_commands()
    
    # Check for basic commands
    basic_commands = [cmd for cmd in all_commands if cmd.name in ['ping', 'help', 'info']]
    
    logger.info(f"Found {len(basic_commands)} basic commands:")
    for cmd in basic_commands:
        logger.info(f"- {cmd.name}: {cmd.description}")
    
    # Check for traditional commands
    logger.info("Checking traditional commands...")
    prefix_commands = [cmd.name for cmd in bot.commands if cmd.name in ['ping', 'help', 'info']]
    logger.info(f"Found {len(prefix_commands)} basic prefix commands: {prefix_commands}")

if __name__ == "__main__":
    asyncio.run(check_commands())