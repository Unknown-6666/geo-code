import os
import sys
import random
import asyncio
import discord
import logging
from discord.ext import commands, tasks
from discord import app_commands
from config import TOKEN, DEFAULT_PREFIX, STATUS_MESSAGES
from database import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=DEFAULT_PREFIX,
            intents=intents,
            help_command=None
        )
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self):
        """Load cogs and start tasks"""
        logger.info("Setting up bot...")
        # Load all cogs
        await self.load_extension("cogs.basic_commands")
        await self.load_extension("cogs.member_events")
        await self.load_extension("cogs.youtube_tracker")
        await self.load_extension("cogs.economy")
        await self.load_extension("cogs.memes")
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.music")  
        # AI chat temporarily disabled due to provider issues
        # await self.load_extension("cogs.ai_chat")
        logger.info("Loaded all cogs successfully")
        
        # Only sync commands automatically if SYNC_COMMANDS env var is set
        # This prevents multiple bot instances from all trying to sync
        if os.environ.get('SYNC_COMMANDS', 'false').lower() == 'true':
            logger.info("Syncing commands with Discord...")
            await self.tree.sync()
            logger.info("Commands synced successfully")
        else:
            logger.info("Automatic command syncing disabled. Use !sync to sync commands manually.")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Successfully logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info('Bot is now ready to receive commands')
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print('------')

        # Start status rotation after bot is ready
        if not self.change_status.is_running():
            self.change_status.start()
            logger.info("Started status rotation task")

    @tasks.loop(minutes=5)
    async def change_status(self):
        """Rotate through status messages"""
        try:
            status = random.choice(STATUS_MESSAGES)
            logger.info(f'Changing status to: {status}')
            await self.change_presence(activity=discord.Game(status))
        except Exception as e:
            logger.error(f"Error changing status: {str(e)}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle slash command errors"""
        logger.error(f'Slash command error: {str(error)}')

        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)

    async def on_command(self, ctx):
        """Log when commands are used"""
        logger.info(f'Command "{ctx.command}" used by {ctx.author} in {ctx.guild}')

def init_db():
    """Initialize database tables"""
    from dashboard.app import app
    from models.economy import initialize_shop
    with app.app_context():
        db.create_all()
        initialize_shop()  # Initialize shop items
        logger.info("Database tables and shop items created successfully")

async def main():
    """Main function to run the bot"""
    logger.info("Starting bot...")
    init_db()  # Initialize database tables
    async with Bot() as bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Check if we're running directly from the "discord_bot" workflow
    # If the main application is running, we'll exit to avoid duplicate instances
    if os.environ.get('DISCORD_BOT_WORKFLOW', 'false').lower() == 'true':
        # First check if there's already a bot instance running
        try:
            import psutil
            current_pid = os.getpid()
            python_processes = [p for p in psutil.process_iter(['name', 'cmdline', 'pid']) 
                              if p.info['name'] == 'python' and p.info['pid'] != current_pid]
            
            for proc in python_processes:
                if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']):
                    logger.warning("Main application already running the Discord bot. Exiting to avoid duplicate instances.")
                    sys.exit(0)
        except ImportError:
            # If psutil isn't available, we'll try to run anyway
            logger.warning("Unable to check for existing bot instances. Proceeding with caution.")
    
    # If we get here, it's safe to run the bot
    asyncio.run(main())