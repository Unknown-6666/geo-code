import os
import sys
import threading
import importlib
import logging
import signal

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('main')

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
        
        # Set environment variable to enable command syncing
        # This prevents multiple instances from all trying to sync
        os.environ['SYNC_COMMANDS'] = 'true'
        asyncio.run(bot.main())
    except Exception as e:
        logger.error(f"Error in Discord bot thread: {e}")
        # Clean up lock file on error
        try:
            if os.path.exists(".main_discord_bot.lock"):
                os.remove(".main_discord_bot.lock")
        except:
            pass

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
    3. Or run them together (default)
    """
    # When running as a deployment or without arguments, run both services
    if len(sys.argv) <= 1 or is_deployment:
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
    elif sys.argv[1] == "bot":
        # Run just the Discord bot
        logger.info("Starting Discord bot only...")
        asyncio.run(bot.main())
    elif sys.argv[1] == "web":
        # Run just the web dashboard
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
