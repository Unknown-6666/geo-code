#!/usr/bin/env python3
"""
Script to force sync ALL commands with Discord.
This script skips the command clearing step and just syncs all available commands.
"""
import os
import sys
import asyncio
import logging
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
logger = logging.getLogger('force_sync')

async def force_sync_commands():
    """Force sync all commands with Discord without clearing first"""
    from bot import Bot
    
    print("\n" + "="*60)
    print(" "*15 + "FORCE COMMAND SYNC UTILITY")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")
    
    print("⚠️  This utility will FORCE SYNC all commands with Discord.")
    print("This will register all commands available in your bot's cogs.\n")
    
    # Create a new bot instance
    bot = Bot()
    
    try:
        # Load all cogs
        print("🔄 Loading all cogs...")
        
        # Setup hook will load all cogs
        await bot.setup_hook()
        
        print("✅ All cogs loaded successfully!")
        
        # Sync commands with rate limit handling
        print("\n🔄 Force syncing all commands with Discord...")
        
        rate_limit_count = 0
        max_rate_limits = 5  # Maximum number of rate limit retries
        
        while rate_limit_count < max_rate_limits:
            try:
                # Sync the command tree
                synced = await bot.tree.sync()
                command_count = len(synced)
                
                # List all synced commands
                command_names = [cmd.name for cmd in synced]
                command_list = ", ".join(command_names)
                
                print(f"\n✅ Successfully synced {command_count} commands globally!")
                print(f"\nCommand list: {command_list}")
                print("\nCommand sync complete!")
                return True
                
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    rate_limit_count += 1
                    retry_after = e.retry_after if hasattr(e, 'retry_after') else 60
                    
                    print(f"\n⚠️  Rate limited while syncing commands ({rate_limit_count}/{max_rate_limits}).")
                    print(f"Retrying in {retry_after:.2f} seconds...")
                    
                    if rate_limit_count >= max_rate_limits:
                        print(f"\n⚠️  Hit rate limit {max_rate_limits} times, stopping command sync.")
                        print("Commands may be partially updated or use old versions.")
                        return False
                        
                    # Wait for the rate limit to expire
                    await asyncio.sleep(retry_after)
                else:
                    # Not a rate limit error
                    print(f"\n❌ Error syncing commands: {str(e)}")
                    return False
            except Exception as e:
                print(f"\n❌ Error syncing commands: {str(e)}")
                return False
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        logger.exception("Error during force sync")
        return False

if __name__ == "__main__":
    # Run the force sync process
    success = asyncio.run(force_sync_commands())
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)