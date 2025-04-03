#!/usr/bin/env python3
"""
Deployment script for running both web dashboard and Discord bot.
This is used by Replit's deployment service.
"""
import os
import sys
import logging
import threading
import time
import signal
import asyncio
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('deploy')

# Import our components
import bot
from dashboard.app import app

def run_discord_bot():
    """Run the Discord bot"""
    logger.info("Starting Discord bot...")
    
    # Check required environment variables
    if not os.environ.get('DISCORD_TOKEN'):
        logger.error("DISCORD_TOKEN environment variable is not set!")
        logger.error("The bot cannot start without a valid Discord token")
        # Don't retry if token is missing
        return
        
    # Check for API key and set fallback flag if needed
    if not os.environ.get('GOOGLE_AI_API_KEY') and not os.environ.get('GOOGLE_API'):
        logger.warning("No Google AI API key found, using g4f fallback")
        os.environ['USE_AI_FALLBACK'] = 'true'
    
    # Set deployment flag
    os.environ['DEPLOYMENT'] = 'true'
    
    try:
        # Import asyncio here to make sure we have a fresh event loop
        import asyncio
        asyncio.run(bot.main())
    except Exception as e:
        logger.error(f"Error in Discord bot: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Add a short delay before retrying to prevent rapid restarts
        time.sleep(10)
        
        # Maximum retry attempts
        max_retries = 3
        for attempt in range(max_retries):
            logger.info(f"Attempting to restart bot (attempt {attempt+1}/{max_retries})")
            try:
                import asyncio
                asyncio.run(bot.main())
                break  # If successful, break out of retry loop
            except Exception as retry_error:
                logger.error(f"Retry attempt {attempt+1} failed: {str(retry_error)}")
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    time.sleep(30)  # Exponential backoff for retries

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info("Termination signal received, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Deployment script starting...")
    
    # Mark that we're in deployment mode
    os.environ['DEPLOYMENT'] = 'true'
    
    # No need for deployment flags anymore - the bot now clears commands
    # on every startup to prevent duplication issues
    
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_discord_bot)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("Discord bot thread started")
    
    # Determine the port for the web server
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting web dashboard on port {port}...")
    
    # Start Flask app
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)