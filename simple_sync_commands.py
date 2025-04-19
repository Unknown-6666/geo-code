#!/usr/bin/env python3
"""
Simple script to sync commands with Discord.
This script only loads essential cogs to avoid issues with databases or APIs.
"""
import asyncio
import discord
import logging
import os
import sys

from discord.ext import commands
from discord import app_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sync_commands')

# Use the Bot class from bot.py but simplified
class SimpleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

# Placeholder for command groups
# Note: SCP-079 commands have been removed

async def sync_essential_commands():
    """Sync commands from essential cogs only"""
    from config import TOKEN
    
    bot = SimpleBot()
    
    print("\n" + "="*60)
    print(" "*15 + "SIMPLE COMMAND SYNC")
    print("="*60)
    
    try:
        # Connect to Discord
        print("Connecting to Discord...")
        await bot.login(TOKEN)
        print("Successfully connected to Discord!")
        
        # Sync commands
        print("Syncing essential commands...")
        await bot.tree.sync()
        print("Successfully synced essential commands!")
        
        return True
        
    except Exception as e:
        print(f"Error syncing commands: {e}")
        return False
        
    finally:
        # Close the bot connection
        if bot and not bot.is_closed():
            await bot.close()
            print("Closed Discord connection.")

# Main function
if __name__ == "__main__":
    try:
        asyncio.run(sync_essential_commands())
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)