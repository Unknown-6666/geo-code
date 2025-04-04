#!/usr/bin/env python3
"""
Register all commands with Discord excluding database-dependent cogs.
This script syncs commands from all essential cogs while skipping those that might
cause connection errors with databases or external APIs.
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

class SimpleBot(discord.Client):
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

async def register_all_commands():
    """Register all commands with Discord"""
    from config import TOKEN

    print("\n" + "="*60)
    print(" "*15 + "COMMAND REGISTRATION UTILITY")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")
    
    # Create a new bot client
    bot = SimpleBot()
    
    # Define all command groups - we'll create these manually to avoid loading cogs
    command_groups = [
        # AI Chat commands
        {
            "name": "ask",
            "description": "Ask the AI a question and get a response"
        },
        {
            "name": "chat",
            "description": "Have a casual conversation with the AI with memory of past conversations"
        },
        {
            "name": "ai_reload",
            "description": "Reload AI preferences from the JSON file (Admin only)"
        },
        {
            "name": "toggle_personality",
            "description": "Cycle between casual, neutral, and formal AI personality modes (Admin only)"
        },
        {
            "name": "custom_response",
            "description": "Manage custom AI responses (Admin only)"
        },
        {
            "name": "clear_chat_history",
            "description": "Clear your conversation history with the AI"
        },
        {
            "name": "show_chat_history",
            "description": "Show your recent conversation with the AI"
        },
        
        # SCP-079 commands
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
        },
        
        # Basic commands
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
        },
        {
            "name": "sync_commands",
            "description": "Sync slash commands across all servers (Bot Owner Only)"
        },
        {
            "name": "sync_guild_commands",
            "description": "Sync slash commands for the current server only (Bot Owner Only)"
        },
        {
            "name": "clear_commands",
            "description": "Clear all slash commands from all servers (Bot Owner Only)"
        },
        
        # Memes commands
        {
            "name": "meme",
            "description": "Fetch and send a random meme"
        },
        {
            "name": "memedump",
            "description": "Send multiple random memes at once"
        },
        
        # Moderation commands
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
        },
        {
            "name": "slowmode",
            "description": "Set slowmode delay for a channel"
        },
        
        # Music commands
        {
            "name": "join",
            "description": "Join your voice channel"
        },
        {
            "name": "leave",
            "description": "Leave the voice channel"
        },
        {
            "name": "play",
            "description": "Play a song from YouTube"
        },
        {
            "name": "pause",
            "description": "Pause the currently playing song"
        },
        {
            "name": "resume",
            "description": "Resume playing the paused song"
        },
        {
            "name": "stop",
            "description": "Stop playing and clear the queue"
        },
        {
            "name": "skip",
            "description": "Skip the currently playing song"
        },
        {
            "name": "queue",
            "description": "Display the current song queue"
        },
        {
            "name": "volume",
            "description": "Adjust the player volume"
        },
        {
            "name": "now",
            "description": "Display information about the currently playing song"
        },
        {
            "name": "loop",
            "description": "Toggle loop mode for the current song"
        },
        {
            "name": "shuffle",
            "description": "Shuffle the current queue"
        },
        
        # Voice AI commands
        {
            "name": "voice_join",
            "description": "Make the bot join your voice channel"
        },
        {
            "name": "voice_leave",
            "description": "Make the bot leave the voice channel"
        },
        {
            "name": "voice_ask",
            "description": "Ask the AI a question and hear the response in voice chat"
        },
        {
            "name": "voice_chat",
            "description": "Chat with the AI using voice"
        },
        {
            "name": "voice_stop",
            "description": "Stop the current voice response"
        },
        {
            "name": "voice_toggle",
            "description": "Toggle voice listening mode on/off"
        },
    ]
    
    try:
        # Connect to Discord
        print("🔄 Connecting to Discord...")
        await bot.login(TOKEN)
        print("✅ Successfully connected to Discord!")
        
        # Register all commands
        print("\n🔄 Registering commands with Discord...")
        
        for cmd in command_groups:
            # Create command
            @bot.tree.command(name=cmd["name"], description=cmd["description"])
            async def dummy_command(interaction: discord.Interaction):
                # This is a dummy function - it won't be called since we're just registering commands
                pass
                
            print(f"Added command: {cmd['name']}")
        
        # Sync commands to Discord
        print("\n🔄 Syncing commands with Discord...")
        try:
            await bot.tree.sync()
            print(f"\n✅ Successfully synced {len(command_groups)} commands globally!")
            print("\nCommand registration complete!")
            
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
    # Run the registration process
    try:
        success = asyncio.run(register_all_commands())
    except KeyboardInterrupt:
        print("\nCommand registration interrupted by user.")
        success = False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        traceback.print_exc()
        success = False
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)