import os
import sys
import time
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
        # First load all cogs - this is where commands are added to the command tree
        try:
            await self.load_extension("cogs.basic_commands")
            await self.load_extension("cogs.member_events")
            await self.load_extension("cogs.youtube_tracker")
            await self.load_extension("cogs.economy")
            await self.load_extension("cogs.memes")
            await self.load_extension("cogs.moderation")
            await self.load_extension("cogs.music")  
            await self.load_extension("cogs.profanity_filter")
            # AI chat temporarily disabled due to provider issues
            # await self.load_extension("cogs.ai_chat")
            logger.info("Loaded all cogs successfully")
        except Exception as e:
            logger.error(f"Error loading cogs: {str(e)}")
            
        # First check if there's a deploy flag file which indicates this is a deployment
        # This helps prevent command duplication when deploying
        is_deployment = os.path.exists('deploy.flag') or '--deploy' in sys.argv
        
        # Modified approach for syncing commands:
        # When deploying, we'll clear commands first to prevent duplication
        # Otherwise we'll just sync to update existing commands
        logger.info("Syncing global commands with Discord...")
        try:
            if is_deployment:
                logger.warning("Deployment mode detected - clearing commands first to prevent duplication")
                # Clear all commands to prevent duplication
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                logger.info("Cleared all commands before re-syncing")
                
                # Create a marker file to prevent clearing on the next restart
                # unless it's another deployment
                with open('deploy.flag', 'w') as f:
                    f.write(str(time.time()))
                    
            # Now sync application commands with Discord
            synced = await self.tree.sync()
            logger.info(f"Global commands synced successfully - registered {len(synced)} commands")
            
        except Exception as e:
            logger.error(f"Error syncing commands: {str(e)}")
            logger.info("If commands are not updating, use !sync or !clear_commands manually as the bot owner.")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Successfully logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info('Bot is now ready to receive commands')
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print('------')

        # We'll only sync guild-specific commands if needed via the !sync_guild command
        # This prevents command duplication - global commands are sufficient for most bots
        logger.info("Global commands are already synced. Guild-specific commands can be synced with !sync_guild")
        
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
    import os
    import sys
    import time
    import glob
    import asyncio
    
    # Define lock files
    LOCK_FILE = ".discord_bot.lock"
    MAIN_APP_LOCK_FILE = ".main_discord_bot.lock"
    
    # Simple process detection: check for gunicorn running main:app (main application)
    try:
        import psutil
        current_pid = os.getpid()
        main_app_running = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] != current_pid and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'gunicorn' in cmdline and 'main:app' in cmdline:
                        logger.warning(f"Main application detected running (PID: {proc.info['pid']}). Will exit.")
                        main_app_running = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # If main app is running, exit immediately
        if main_app_running:
            # Get a list of lock files for logging
            try:
                lock_files = glob.glob(".*.lock")
                logger.warning(f"Lock files found: {', '.join(lock_files)}")
            except Exception:
                pass
            
            # Exit to avoid duplicate bot instances
            logger.warning("Exiting to avoid duplicate bot instances with main application.")
            sys.exit(0)
    except ImportError:
        logger.warning("psutil not available for process detection")
    except Exception as e:
        logger.error(f"Error during process detection: {str(e)}")
    
    # Try to create a lock file
    try:
        # Double-check main app lock as a safeguard
        if os.path.exists(MAIN_APP_LOCK_FILE):
            # Check if the lock file is recent (within the last 2 minutes)
            lock_time = os.path.getmtime(MAIN_APP_LOCK_FILE)
            if time.time() - lock_time < 120:
                # Main app lock file exists and is recent
                with open(MAIN_APP_LOCK_FILE, 'r') as f:
                    pid = f.read().strip()
                logger.warning(f"Main application lock file exists. Main app is running the bot (PID: {pid}).")
                logger.warning("Exiting to avoid duplicate instances.")
                sys.exit(0)
        
        # Create/update our lock file with current PID
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
            logger.info(f"Created lock file with PID {os.getpid()}")
        
        # Register a function to remove the lock file on exit
        import atexit
        def remove_lock_file():
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                logger.info("Removed lock file on exit")
        atexit.register(remove_lock_file)
        
        # If we get here, it's safe to run the bot
        logger.info("No other bot instances detected, proceeding with startup.")
        asyncio.run(main())
        
    except Exception as e:
        logger.error(f"Error during lock file management: {str(e)}")
        # Run anyway if there was an error with the lock file
        asyncio.run(main())