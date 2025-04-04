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

# Create a simplified version of SCP-079 commands
scp079_group = app_commands.Group(name="scp079", description="SCP-079 commands")

@scp079_group.command(name="talk", description="Communicate with SCP-079, the Old AI")
async def scp079_talk(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Command registered successfully.", ephemeral=True)

@app_commands.command(name="scp079_info", description="Get information about SCP-079")
async def scp079_info(interaction: discord.Interaction):
    await interaction.response.send_message("Command registered successfully.", ephemeral=True)

@app_commands.command(name="scp079_clear", description="Clear your conversation history with SCP-079")
async def scp079_clear(interaction: discord.Interaction):
    await interaction.response.send_message("Command registered successfully.", ephemeral=True)

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
        
        # Add the SCP-079 commands to the command tree
        bot.tree.add_command(scp079_group)
        bot.tree.add_command(scp079_info)
        bot.tree.add_command(scp079_clear)
        
        # Sync commands
        print("Syncing SCP-079 commands...")
        await bot.tree.sync()
        print("Successfully synced SCP-079 commands!")
        
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