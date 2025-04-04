import os
import sys
import threading
import importlib
import logging
import signal
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# Set up enhanced debug logger for economy troubleshooting
debug_logger = logging.getLogger('economy_debug')
debug_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('ECONOMY DEBUG - %(message)s'))
debug_logger.addHandler(handler)

# Setup database fallback
def setup_database_fallback():
    """Set up our local PostgreSQL database as a fallback"""
    # Check if we have a working database created by the Replit toolkit
    replit_db_created = os.environ.get("PGDATABASE") and os.environ.get("PGUSER") and os.environ.get("PGHOST") 
    neon_db_disabled = os.environ.get("DATABASE_URL") and "neon.tech" in os.environ.get("DATABASE_URL", "")
    
    # Force use of local PostgreSQL database if we're running in Replit
    if replit_db_created:
        # Create a proper database URL from the environment variables
        local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
        
        # Log which database we're using
        logger.info(f"Using Replit PostgreSQL database: {os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}")
        
        # Update the environment variable to force use of the Replit database
        os.environ["DATABASE_URL"] = local_db_url
        
        # Also update app.config if it's been loaded already
        try:
            from app import app
            if app and hasattr(app, 'config'):
                app.config["SQLALCHEMY_DATABASE_URI"] = local_db_url
                logger.info("Updated app.config with Replit database URL")
        except (ImportError, AttributeError) as e:
            # App not yet loaded or structure is different
            logger.warning(f"Could not update app config directly: {str(e)}")
            pass
        
        # Try importing from dashboard.app as well (alternative structure)
        try:
            from dashboard.app import app as dashboard_app
            if dashboard_app and hasattr(dashboard_app, 'config'):
                dashboard_app.config["SQLALCHEMY_DATABASE_URI"] = local_db_url
                logger.info("Updated dashboard app.config with Replit database URL")
        except (ImportError, AttributeError):
            # dashboard.app not yet loaded, which is fine
            pass
        
        return True
    
    return False

# Call the database fallback setup right away
setup_database_fallback()

# Configure other loggers to reduce noise
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('google.auth').setLevel(logging.WARNING)

# Import the Flask app - this is needed for Gunicorn
from dashboard.app import app

# Import the bot module for running the Discord bot
import bot
import asyncio

# Global flag to track if we're in deployment mode
is_deployment = os.environ.get('DEPLOYMENT', 'false').lower() == 'true'
logger.info(f"Deployment mode: {is_deployment}")

# Thread to run the Discord bot
def run_discord_bot():
    """Run the Discord bot in a separate thread"""
    logger.info("Starting Discord bot thread...")
    try:
        # Create a main app lock file to signal that we're running the bot
        # This helps the discord_bot workflow detect that it shouldn't run
        with open(".main_discord_bot.lock", "w") as f:
            f.write(str(os.getpid()))
            logger.info(f"Created main application lock file with PID {os.getpid()}")
        
        # Check if DISCORD_TOKEN is available
        if not os.environ.get('DISCORD_TOKEN'):
            logger.error("DISCORD_TOKEN environment variable is not set!")
            logger.error("Please make sure your Discord token is properly configured in the Secrets")
            return
            
        # Check if we need to set up a fallback API for AI
        if not os.environ.get('GOOGLE_AI_API_KEY'):
            logger.warning("GOOGLE_AI_API_KEY not found. Using g4f fallback for AI responses.")
            # Set a flag to use fallback mode
            os.environ['USE_AI_FALLBACK'] = 'true'
        
        # Set environment variable to disable command syncing on startup
        # This can be changed to 'true' when you want to sync commands
        os.environ['SYNC_COMMANDS_ON_STARTUP'] = 'false'
        
        # No need for deployment flags anymore - the bot now clears commands
        # on every startup to prevent duplication issues
                
        # Run the bot with better error handling
        try:
            asyncio.run(bot.main())
        except KeyboardInterrupt:
            logger.info("Bot interrupted by user")
        except Exception as e:
            logger.error(f"Error in bot.main(): {e}")
            logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error in Discord bot thread: {e}")
        logger.error(traceback.format_exc())
    
    # Clean up lock file on exit (either success or error)
    try:
        if os.path.exists(".main_discord_bot.lock"):
            os.remove(".main_discord_bot.lock")
            logger.info("Removed bot lock file")
    except Exception as cleanup_error:
        logger.error(f"Error cleaning up lock file: {cleanup_error}")

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info("Termination signal received, shutting down...")
    sys.exit(0)

def run_both_services():
    """Start both the web dashboard and Discord bot"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start Discord bot in a separate thread
    discord_thread = threading.Thread(target=run_discord_bot)
    discord_thread.daemon = True  # Thread will exit when main thread exits
    discord_thread.start()
    logger.info("Discord bot thread started")
    
    # The Flask app will be run by Gunicorn, so we don't need to call app.run() here
    logger.info("Web dashboard is running via Gunicorn")
    return app

def main():
    """Main function to start either:
    1. Just the Flask dashboard
    2. Just the Discord bot
    3. Sync or refresh commands
    4. Or run them together (default)
    """
    import argparse
    parser = argparse.ArgumentParser(description='Discord Bot with Web Dashboard')
    parser.add_argument('--sync-commands', action='store_true', 
                       help='Only sync commands with Discord and exit')
    parser.add_argument('--refresh-commands', action='store_true', 
                       help='Clear and refresh all commands with Discord and exit')
    parser.add_argument('mode', nargs='?', choices=['bot', 'web', 'both'], 
                       default='both', help='Which component to run')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Command sync mode - just sync commands and exit
    if args.sync_commands:
        logger.info("Running in command sync mode")
        # Make sure we enable command syncing when explicitly running sync mode
        os.environ['SYNC_COMMANDS_ON_STARTUP'] = 'true'
        import asyncio
        from bot import sync_commands_only
        result = asyncio.run(sync_commands_only())
        return
        
    # Command refresh mode - clear and sync commands and exit
    if args.refresh_commands:
        logger.info("Running in command refresh mode")
        # Make sure we enable command syncing when refreshing commands
        os.environ['SYNC_COMMANDS_ON_STARTUP'] = 'true'
        import subprocess
        result = subprocess.run(['python', 'refresh_commands.py', '-y'], 
                                capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
        return
    
    # When running as a deployment or in default mode, run both services
    if args.mode == 'both' or is_deployment:
        logger.info("Starting both the web dashboard and Discord bot...")
        if is_deployment:
            # In deployment, we need to start the services directly
            run_both_services()
            # If in deployment with no Gunicorn, run Flask directly
            if 'gunicorn' not in sys.modules:
                app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
        else:
            # For local development when run directly
            try:
                # First try to use run_all.py which handles process monitoring
                import run_all
                run_all_cmd = ["python", "run_all.py"]
                import subprocess
                subprocess.call(run_all_cmd)
            except ImportError:
                # Fall back to running with threads
                run_both_services()
                app.run(host="0.0.0.0", port=5000, debug=True)
    
    # Run just the Discord bot
    elif args.mode == "bot":
        logger.info("Starting Discord bot only...")
        import asyncio
        asyncio.run(bot.main())
    
    # Run just the web dashboard
    elif args.mode == "web":
        logger.info("Starting web dashboard only...")
        app.run(host="0.0.0.0", port=5000, debug=True)

# When imported by Gunicorn or run directly in deployment, 
# initialize both services so the bot always starts
if 'gunicorn' in sys.modules or is_deployment:
    run_both_services()

if __name__ == "__main__":
    # Set the deployment flag when running as main script
    os.environ['DEPLOYMENT'] = 'true'
    main()
