#!/usr/bin/env python3
"""
Simple script to sync commands with Discord.
This script only loads essential cogs to avoid issues with databases or APIs.
"""
import os
import sys
import asyncio
import logging
import traceback
import discord
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('simple_sync')

async def sync_essential_commands():
    """Sync commands from essential cogs only"""
    # Import the minimum required components for command registration
    from discord.ext import commands
    from config import TOKEN
    
    print("\n" + "="*60)
    print(" "*15 + "SIMPLE COMMAND SYNC UTILITY")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")
    
    # Create a simple bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # List of essential cogs to load
    essential_cogs = [
        "cogs.basic_commands",
        "cogs.ai_chat",
        "cogs.scp_079"
    ]
    
    try:
        # Connect to Discord
        print("🔄 Connecting to Discord...")
        await bot.login(TOKEN)
        print("✅ Successfully connected to Discord!")
        
        # Load essential cogs
        print("\n🔄 Loading essential cogs...")
        for cog in essential_cogs:
            try:
                await bot.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {str(e)}")
                traceback.print_exc()
        
        # Sync commands to Discord
        print("\n🔄 Syncing commands with Discord...")
        try:
            synced = await bot.tree.sync()
            command_count = len(synced)
            command_names = [cmd.name for cmd in synced]
            command_list = ", ".join(command_names)
            
            print(f"\n✅ Successfully synced {command_count} commands globally!")
            print(f"\nCommand list: {command_list}")
            print("\nCommand sync complete!")
            
        except Exception as e:
            print(f"\n❌ Error syncing commands: {str(e)}")
            traceback.print_exc()
            return False
        
        return True
    
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        # Always properly close the connection
        try:
            if bot and bot.is_closed() is False:
                await bot.close()
                print("\nClosed Discord connection.")
        except:
            pass

if __name__ == "__main__":
    # Run the sync process
    try:
        success = asyncio.run(sync_essential_commands())
    except KeyboardInterrupt:
        print("\nSync process interrupted by user.")
        success = False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        success = False
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)