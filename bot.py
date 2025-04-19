import os
import sys
import time
import random
import asyncio
import discord
import logging
import argparse
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
        
    async def is_owner(self, user: discord.User) -> bool:
        """
        Override the default is_owner check to use our BOT_OWNER_IDS from config.
        This ensures consistency between is_bot_owner() and Discord.py's is_owner().
        """
        from config import BOT_OWNER_IDS
        # Check if the user ID is in our BOT_OWNER_IDS tuple
        is_owner = user.id in BOT_OWNER_IDS
        logger.debug(f"Owner check for {user} (ID: {user.id}): {is_owner}")
        return is_owner

    async def setup_hook(self):
        """Load cogs and start tasks"""
        logger.info("Setting up bot...")
        
        # Organize cogs by dependency
        essential_cogs = [
            "cogs.basic_commands",
            "cogs.member_events",
            "cogs.memes",
            "cogs.fun_commands",    # Fun commands cog including jog command
            "cogs.ai_chat",         # AI Chat cog
            "cogs.voice_ai",        # Voice AI chat cog
            "cogs.ai_moderation",   # AI-powered content moderation
            "cogs.ai_conversation", # AI-powered conversation features
            "cogs.ai_content_analysis" # AI-powered image and link analysis
        ]
        
        database_dependent_cogs = [
            "cogs.economy",
            "cogs.moderation",
            "cogs.youtube_tracker",
            "cogs.music",
            "cogs.profanity_filter",
            "cogs.rules_enforcer",
            "cogs.verification",
        ]
        
        # First, load all essential cogs that don't depend on database
        for cog in essential_cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded essential cog: {cog}")
            except Exception as e:
                logger.error(f"Error loading essential cog {cog}: {str(e)}")
        
        # Then try to load database-dependent cogs, but continue if they fail
        db_load_success = True
        for cog in database_dependent_cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded database-dependent cog: {cog}")
            except Exception as e:
                db_load_success = False
                logger.error(f"Error loading database-dependent cog {cog}: {str(e)}")
        
        if db_load_success:
            logger.info("All cogs loaded successfully")
        else:
            logger.warning("Some database-dependent cogs failed to load. Bot will continue with limited functionality.")
        
        # Check if we should sync commands on startup
        # Default to False (don't sync) unless explicitly set to true
        should_sync = os.environ.get('SYNC_COMMANDS_ON_STARTUP', 'false').lower() == 'true'
        
        if should_sync:
            # Always clear commands before syncing to prevent duplicates
            logger.info("Clearing all commands before syncing...")
            try:
                await self.http.request(
                    discord.http.Route("PUT", "/applications/{application_id}/commands", 
                                    application_id=self.application_id), 
                    json=[]
                )
                logger.info("Commands cleared successfully")
            except Exception as e:
                logger.error(f"Error clearing commands: {str(e)}")
                logger.info("Continuing with sync despite clearing error")
                
            # Sync commands after clearing with rate limit handling
            logger.info("Syncing global commands with Discord...")
            rate_limit_count = 0
            max_rate_limits = 3  # Maximum number of rate limit retries
            
            while rate_limit_count < max_rate_limits:
                try:
                    synced = await self.tree.sync()
                    logger.info(f"Synced {len(synced)} commands globally")
                    break  # Successfully synced, exit the loop
                except discord.errors.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        rate_limit_count += 1
                        retry_after = e.retry_after if hasattr(e, 'retry_after') else 60
                        
                        logger.warning(f"Rate limited while syncing commands ({rate_limit_count}/{max_rate_limits}). "
                                    f"Retrying in {retry_after:.2f} seconds...")
                        
                        if rate_limit_count >= max_rate_limits:
                            logger.warning(f"Hit rate limit {max_rate_limits} times, stopping command sync. "
                                        f"Commands may be partially updated or use old versions.")
                            break
                            
                        # Wait for the rate limit to expire
                        await asyncio.sleep(retry_after)
                    else:
                        # Not a rate limit error, re-raise
                        raise
        else:
            logger.info("Skipping command sync on startup - use !sync command manually if needed")
         
        # Handle any unexpected errors in setup_hook
        try:
            # This try-except block is just a final safety net
            # It's not actively doing anything but catching any unexpected errors
            # that might occur after the command sync logic
            pass
        except Exception as error:
            logger.error(f"Error in setup: {str(error)}")
            logger.info("If commands are not updating, use !sync or !clear_commands manually as the bot owner.")

    async def on_ready(self):
        """Called when the bot is ready"""
        from config import BOT_OWNER_IDS
        
        logger.info(f'Successfully logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guilds')
        logger.info('Bot is now ready to receive commands')
        print(f'Logged in as {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print('------')
        
        # Log the configured bot owners for verification
        logger.info(f'Configured BOT_OWNER_IDS: {BOT_OWNER_IDS}')

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
            # Use Activity.custom to display just the status without "Playing"
            await self.change_presence(
                activity=discord.CustomActivity(name=status)
            )
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
        
        # Don't add any additional processing here
        # This event handler should only log commands, not respond to them

def init_db():
    """Initialize database tables"""
    from dashboard.app import app
    from models.economy import initialize_shop, UserEconomy, Item, Inventory, Transaction
    from models.conversation import Conversation  # Import Conversation model
    
    # Add enhanced economy debugging
    debug_logger = logging.getLogger('economy_debug')
    debug_logger.info("Initializing database and economy system...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Verify economy tables exist
        debug_logger.info("Verifying economy tables...")
        
        # Check UserEconomy table
        try:
            user_count = UserEconomy.query.count()
            debug_logger.info(f"UserEconomy table verified: Contains {user_count} records")
        except Exception as e:
            debug_logger.error(f"Error verifying UserEconomy table: {e}")
            
        # Check Item table
        try:
            item_count = Item.query.count()
            debug_logger.info(f"Item table verified: Contains {item_count} records")
        except Exception as e:
            debug_logger.error(f"Error verifying Item table: {e}")
        
        # Initialize shop items
        initialize_shop()
        
        logger.info("Database tables and shop items created successfully")
        
    # Print environment info for debugging
    debug_logger.info(f"Discord token length: {len(os.environ.get('DISCORD_TOKEN', ''))}")
    debug_logger.info(f"Database URL available: {'yes' if os.environ.get('DATABASE_URL') else 'no'}")
    
    # Do not force SYNC_COMMANDS_ON_STARTUP to avoid Discord rate limiting
    debug_logger.info("Using default command sync settings to avoid Discord rate limiting")
    # os.environ['SYNC_COMMANDS_ON_STARTUP'] = 'true'

async def main():
    """Main function to run the bot"""
    logger.info("Starting bot...")
    
    # Validate that the token exists before attempting to start the bot
    if not TOKEN:
        logger.error("No Discord token found in environment variables")
        logger.error("The bot cannot start without a valid token")
        logger.error("Please set the DISCORD_TOKEN environment variable and restart")
        return
    
    # Initialize database tables
    try:
        init_db()
    except Exception as db_error:
        logger.error(f"Database initialization failed: {str(db_error)}")
        logger.error("Attempting to continue despite database error")
    
    try:
        async with Bot() as bot:
            await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN environment variable.")
    except discord.HTTPException as e:
        logger.error(f"HTTP error connecting to Discord: {str(e)}")
        logger.error("This could be a temporary network issue, try again later.")
    except Exception as e:
        logger.error(f"Critical error starting the bot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

async def sync_commands_only():
    """Function to only sync commands without starting the full bot"""
    logger.info("Starting command sync mode...")
    
    # When explicitly running sync_commands_only, we want to sync commands
    # so we'll set the variable to true
    os.environ['SYNC_COMMANDS_ON_STARTUP'] = 'true'
    
    # Initialize database first
    init_db()
    
    # Create bot instance
    bot = Bot()
    success_with_warning = False
    warning_message = ""
    command_count = 0
    
    try:
        # We need to login before we can sync commands, but we don't want to start the bot fully
        await bot._async_setup_hook()  # Set up the bot's internal state
        await bot.login(TOKEN)  # Login to Discord
        
        # Load all cogs
        cogs = [
            "cogs.basic_commands",
            "cogs.member_events",
            "cogs.youtube_tracker", 
            "cogs.economy",
            "cogs.memes",
            "cogs.fun_commands",    # Fun commands cog including jog command
            "cogs.moderation",
            "cogs.music",
            "cogs.profanity_filter",
            "cogs.rules_enforcer",
            "cogs.verification",
            "cogs.ai_chat",
            "cogs.voice_ai",
            "cogs.ai_moderation",   # AI-powered content moderation
            "cogs.ai_conversation", # AI-powered conversation features
            "cogs.ai_content_analysis" # AI-powered image and link analysis
        ]
        
        # Load each cog with error handling
        cog_load_errors = []
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                logger.info(f"Loaded {cog}")
            except discord.errors.ExtensionAlreadyLoaded:
                logger.warning(f"Cog {cog} was already loaded, continuing")
                success_with_warning = True
                cog_load_errors.append(cog)
                continue
            except Exception as e:
                logger.error(f"Error loading cog {cog}: {str(e)}")
                cog_load_errors.append(cog)
                success_with_warning = True
        
        if cog_load_errors:
            warning_message = f"Some cogs had loading warnings: {', '.join(cog_load_errors)}"
            logger.warning(warning_message)
        else:
            logger.info("All cogs loaded successfully")
        
        # Clear commands first to ensure we don't have duplicates
        logger.info("Clearing all commands...")
        try:
            # Wait for bot to be ready and have application_id
            if not bot.application_id:
                logger.info("Waiting for application ID...")
                await asyncio.sleep(2)  # Give it a moment to initialize
                
            if bot.application_id:
                await bot.http.request(
                    discord.http.Route("PUT", "/applications/{application_id}/commands", 
                                    application_id=bot.application_id), 
                    json=[]
                )
                logger.info("Commands cleared!")
            else:
                logger.error("Could not get application ID, skipping clear step")
                success_with_warning = True
                warning_message += "\nCould not get application ID, skipped clear step."
        except Exception as e:
            logger.error(f"Error clearing commands: {str(e)}")
            success_with_warning = True
            warning_message += f"\nError clearing commands: {str(e)}"
        
        # Sync commands with rate limit handling
        logger.info("Syncing global commands with Discord...")
        rate_limit_count = 0
        max_rate_limits = 3  # Maximum number of rate limit retries
        command_count = 0
        
        while rate_limit_count < max_rate_limits:
            try:
                synced = await bot.tree.sync()
                command_count = len(synced)
                logger.info(f"Successfully synced {command_count} commands globally!")
                break  # Successfully synced, exit the loop
            except discord.errors.HTTPException as e:
                if e.status == 429:  # Rate limited
                    rate_limit_count += 1
                    retry_after = e.retry_after if hasattr(e, 'retry_after') else 60
                    
                    logger.warning(f"Rate limited while syncing commands ({rate_limit_count}/{max_rate_limits}). "
                                   f"Retrying in {retry_after:.2f} seconds...")
                    
                    if rate_limit_count >= max_rate_limits:
                        logger.warning(f"Hit rate limit {max_rate_limits} times, stopping command sync. "
                                       f"Commands may be partially updated or use old versions.")
                        # We'll return success with a warning instead of failing completely
                        return (True, f"Synced commands with rate limit warnings after {rate_limit_count} attempts")
                        
                    # Wait for the rate limit to expire
                    await asyncio.sleep(retry_after)
                else:
                    # Not a rate limit error, re-raise
                    logger.error(f"Error syncing commands: {str(e)}")
                    return False
            except Exception as e:
                logger.error(f"Error syncing commands: {str(e)}")
                return False
        
        # Return appropriate status
        if success_with_warning:
            return (True, f"Synced {command_count} commands with warnings: {warning_message}")
        return True
    except Exception as e:
        error_str = str(e)
        logger.error(f"Error during command sync: {error_str}")
        
        # Special case: If the only error is that extensions are already loaded
        if "Extension 'cogs." in error_str and "is already loaded" in error_str:
            # This is actually okay - the commands still got synced
            if command_count > 0:
                return (True, f"Synced {command_count} commands despite extension loading warnings")
        
        return False
    finally:
        # Close bot session
        try:
            if bot.is_closed():
                logger.info("Bot session already closed")
            else:
                await bot.close()
                logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error closing bot session: {str(e)}")

if __name__ == "__main__":
    import os
    import sys
    import time
    import glob
    import asyncio
    
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Discord Bot Runner')
    parser.add_argument('--sync-commands', action='store_true', help='Only sync commands without starting the bot')
    args = parser.parse_args()
    
    # If --sync-commands flag is provided, only sync commands and exit
    if args.sync_commands:
        logger.info("Running in command sync mode")
        result = asyncio.run(sync_commands_only())
        sys.exit(0 if result else 1)
    
    # Normal bot startup
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