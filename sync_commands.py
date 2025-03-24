#!/usr/bin/env python3
"""
Script to sync Discord bot commands without starting the full bot.
This helps prevent duplication of commands in Discord servers.
"""
import os
import sys
import logging
import asyncio
from bot import sync_commands_only

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

if __name__ == "__main__":
    logger.info("=== COMMAND SYNC UTILITY ===")
    logger.info("Refreshing Discord bot slash commands...")
    
    try:
        result = asyncio.run(sync_commands_only())
        if result:
            logger.info("✅ Command sync completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Command sync failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Command sync failed with error: {str(e)}")
        sys.exit(1)