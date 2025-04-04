#!/usr/bin/env python3
"""
Focused script to register only SCP-079 commands with Discord.
This script prioritizes SCP-079 commands and avoids any database dependencies.
"""
import asyncio
import discord
import logging
import os
import sys
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('register_scp079_commands')

class SCP079Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.synced = False

    async def setup_hook(self):
        # This is called when the bot is ready
        if not self.synced:
            await self.tree.sync()
            self.synced = True

async def register_scp079_commands():
    """Register only SCP-079 commands with Discord"""
    from config import TOKEN

    print("\n" + "="*60)
    print(" "*15 + "SCP-079 COMMAND REGISTRATION")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")
    
    # Create a new bot client
    bot = SCP079Bot()
    
    # Commands to register
    commands = [
        {
            "name": "scp079",
            "description": "Communicate with SCP-079, the Old AI",
            "parameters": [
                {
                    "name": "message",
                    "description": "Your message to SCP-079",
                    "required": True,
                    "type": discord.AppCommandOptionType.string
                }
            ]
        },
        {
            "name": "scp079_info",
            "description": "Get information about SCP-079"
        },
        {
            "name": "scp079_clear",
            "description": "Clear your conversation history with SCP-079"
        }
    ]
    
    try:
        # Connect to Discord
        print("🔄 Connecting to Discord...")
        await bot.login(TOKEN)
        print("✅ Successfully connected to Discord!")
        
        # Clear the command tree
        bot.tree.clear_commands(guild=None)
        
        # Add SCP-079 commands
        for cmd in commands:
            # Create command
            # Simple command registration - no need for AppCommandOption
            @bot.tree.command(name=cmd["name"], description=cmd["description"])
            async def dummy_command(interaction: discord.Interaction, message: str = None):
                # This is a dummy function - it won't be called
                # The message parameter will only be used for scp079 command
                await interaction.response.send_message("Command registered.", ephemeral=True)
                
            print(f"Added command: {cmd['name']}")
        
        # Sync commands
        print("Syncing SCP-079 commands...")
        
        try:
            synced = await bot.tree.sync()
            command_count = len(synced)
            
            print(f"✅ Successfully synced {command_count} SCP-079 commands")
                
        except discord.errors.HTTPException as e:
            print(f"⚠️ Error syncing commands: {e}")
            if e.status == 429:  # Rate limited
                retry_after = e.retry_after if hasattr(e, 'retry_after') else 15
                print(f"Rate limited, waiting {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                # Try once more
                synced = await bot.tree.sync()
                command_count = len(synced)
                print(f"✅ Second attempt: Successfully synced {command_count} SCP-079 commands")
            else:
                return False
        
        print("\n✅ SCP-079 command registration complete!")
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
    # Run the registration process
    try:
        success = asyncio.run(register_scp079_commands())
    except KeyboardInterrupt:
        print("\nCommand registration interrupted by user.")
        success = False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        success = False
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)