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
    
    # Load only the SCP-079 cog
    logger.info("Loading SCP-079 cog...")
    try:
        await bot.load_extension("cogs.scp_079")
        logger.info("SCP-079 cog loaded successfully")
    except Exception as e:
        logger.error(f"Error loading SCP-079 cog: {e}")
        return
    
    # Get all registered commands
    logger.info("Checking registered application commands...")
    all_commands = bot.tree.get_commands()
    
    # Check for SCP-079 related commands
    scp079_commands = [cmd for cmd in all_commands if cmd.name.startswith('scp079')]
    
    logger.info(f"Found {len(scp079_commands)} SCP-079 related commands:")
    for cmd in scp079_commands:
        logger.info(f"- {cmd.name}: {cmd.description}")
    
    # Check for traditional commands
    logger.info("Checking traditional commands...")
    prefix_commands = [cmd.name for cmd in bot.commands if cmd.name.startswith('scp079')]
    logger.info(f"Found {len(prefix_commands)} SCP-079 related prefix commands: {prefix_commands}")

if __name__ == "__main__":
    asyncio.run(check_commands())