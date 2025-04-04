#!/usr/bin/env python3
"""
Register essential commands with Discord in smaller batches.
This script syncs commands in smaller groups to avoid timeouts or rate limits.
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
logger = logging.getLogger('register_commands')

class BatchBot(discord.Client):
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

async def register_essential_commands():
    """Register essential commands with Discord in smaller batches"""
    from config import TOKEN

    print("\n" + "="*60)
    print(" "*15 + "BATCH COMMAND REGISTRATION")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")
    
    # Create a new bot client
    bot = BatchBot()
    
    # Define essential command groups in smaller batches
    command_batches = [
        # Batch 1: SCP-079 commands (highest priority)
        [
            {
                "name": "scp079",
                "description": "Communicate with SCP-079, the Old AI"
            },
            {
                "name": "scp079_info",
                "description": "Get information about SCP-079"
            },
            {
                "name": "scp079_clear",
                "description": "Clear your conversation history with SCP-079"
            }
        ],
        
        # Batch 2: AI Chat commands
        [
            {
                "name": "ask",
                "description": "Ask the AI a question and get a response"
            },
            {
                "name": "chat",
                "description": "Have a casual conversation with the AI with memory of past conversations"
            },
            {
                "name": "clear_chat_history",
                "description": "Clear your conversation history with the AI"
            }
        ],
        
        # Batch 3: Basic utility commands
        [
            {
                "name": "ping",
                "description": "Check the bot's response time"
            },
            {
                "name": "help",
                "description": "Show help information about bot commands"
            },
            {
                "name": "info",
                "description": "Show server information"
            },
            {
                "name": "userinfo",
                "description": "Show information about a user"
            }
        ],
        
        # Batch 4: Moderation commands
        [
            {
                "name": "kick",
                "description": "Kick a member from the server"
            },
            {
                "name": "ban",
                "description": "Ban a member from the server"
            },
            {
                "name": "timeout",
                "description": "Timeout a member for a specified duration"
            },
            {
                "name": "warn",
                "description": "Issue a warning to a member"
            },
            {
                "name": "clear",
                "description": "Clear a specified number of messages from a channel"
            }
        ],
        
        # Batch 5: Entertainment commands
        [
            {
                "name": "meme",
                "description": "Fetch and send a random meme"
            },
            {
                "name": "memedump",
                "description": "Send multiple random memes at once"
            }
        ]
    ]
    
    try:
        # Connect to Discord
        print("🔄 Connecting to Discord...")
        await bot.login(TOKEN)
        print("✅ Successfully connected to Discord!")
        
        total_command_count = 0
        
        # Process each batch
        for batch_num, batch in enumerate(command_batches, 1):
            print(f"\n🔄 Processing Batch {batch_num} ({len(batch)} commands)...")
            
            try:
                # Clear the command tree for this batch
                bot.tree.clear_commands(guild=None)
                
                # Add all commands in this batch
                for cmd in batch:
                    # Create command
                    @bot.tree.command(name=cmd["name"], description=cmd["description"])
                    async def dummy_command(interaction: discord.Interaction):
                        # This is a dummy function - it won't be called since we're just registering commands
                        pass
                        
                    print(f"Added command: {cmd['name']}")
                
                # Sync this batch of commands
                print(f"Syncing Batch {batch_num}...")
                
                try:
                    synced = await bot.tree.sync()
                    command_count = len(synced)
                    total_command_count += command_count
                    
                    print(f"✅ Successfully synced {command_count} commands in Batch {batch_num}")
                    
                    # Sleep between batches to avoid rate limits
                    if batch_num < len(command_batches):
                        await asyncio.sleep(5)
                        
                except discord.errors.HTTPException as e:
                    print(f"⚠️ Error syncing Batch {batch_num}: {e}")
                    if e.status == 429:  # Rate limited
                        retry_after = e.retry_after if hasattr(e, 'retry_after') else 15
                        print(f"Rate limited, waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                    continue
                    
            except Exception as e:
                print(f"⚠️ Error processing Batch {batch_num}: {e}")
                continue
        
        print(f"\n✅ Command registration complete! Synced {total_command_count} commands across {len(command_batches)} batches.")
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
        success = asyncio.run(register_essential_commands())
    except KeyboardInterrupt:
        print("\nCommand registration interrupted by user.")
        success = False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        success = False
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)