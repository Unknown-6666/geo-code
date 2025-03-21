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
    import os
    import sys
    import time
    import glob
    import traceback
    
    # Define lock files
    LOCK_FILE = ".discord_bot.lock"
    MAIN_APP_LOCK_FILE = ".main_discord_bot.lock"
    
    # Simple process detection
    # Check for gunicorn running main:app - that's the main application
    try:
        import psutil
        current_pid = os.getpid()
        main_app_running = False
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] != current_pid and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'gunicorn' in cmdline and 'main:app' in cmdline:
                        logger.warning(f"Main application detected running (PID: {proc.info['pid']}). Will exit if in discord_bot workflow.")
                        main_app_running = True
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # If main app is running and we're likely in the standalone workflow, exit
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
        # For normal operation, still check main app lock as a safeguard
        if os.path.exists(MAIN_APP_LOCK_FILE):
            # Check if the lock file is stale (older than 60 seconds)
            lock_time = os.path.getmtime(MAIN_APP_LOCK_FILE)
            if time.time() - lock_time < 120:  # 2 minutes to be safe
                # Main app lock file exists and is recent
                with open(MAIN_APP_LOCK_FILE, 'r') as f:
                    pid = f.read().strip()
                    logger.warning(f"Main application lock file exists. Main app is running the bot (PID: {pid}).")
                    
                    # Always exit if main app is running the bot
                    logger.warning("Main app is running the bot. Exiting if this is a separate process.")
                    sys.exit(0)
        
        # Check for our own instance lock file
        if os.path.exists(LOCK_FILE):
            # Check if the lock file is stale
            lock_time = os.path.getmtime(LOCK_FILE)
            if time.time() - lock_time < 60:
                # Lock file exists and is recent
                with open(LOCK_FILE, 'r') as f:
                    pid = f.read().strip()
                    logger.warning(f"Bot lock file exists. Another instance may be running (PID: {pid}).")
                    
                    # If we're in the discord_bot workflow and the lock exists,
                    # it's likely another instance is running
                    if bot_workflow:
                        logger.warning("Running in discord_bot workflow and lock exists. Exiting to avoid duplicate instances.")
                        sys.exit(0)
        
        # Create/update lock file with our PID
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
            logger.info(f"Created lock file with PID {os.getpid()}")
            
        # Additional process check using psutil if available
        try:
            import psutil
            current_pid = os.getpid()
            
            # If we're in the discord_bot workflow, check for gunicorn processes
            if bot_workflow:
                for proc in psutil.process_iter(['name', 'cmdline', 'pid']):
                    if proc.info['pid'] != current_pid and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'gunicorn' in cmdline and 'main:app' in cmdline:
                            logger.warning(f"Main application already running (PID: {proc.info['pid']}). Exiting workflow to avoid duplicate bot instances.")
                            # Remove our lock file since we're exiting
                            if os.path.exists(LOCK_FILE):
                                os.remove(LOCK_FILE)
                            sys.exit(0)
        except ImportError:
            logger.warning("psutil not available for process detection")
        except Exception as e:
            logger.error(f"Error in process detection: {str(e)}")
        
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