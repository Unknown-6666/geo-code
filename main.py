import os
import sys
import threading
import importlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('main')

# Import the Flask app - this is needed for Gunicorn
from dashboard.app import app

# Import the bot module for running the Discord bot
import bot
import asyncio

# Thread to run the Discord bot
def get_app():
    """Get Flask app for Gunicorn"""
    logger.info("Web dashboard is running via Gunicorn")
    return app

def main():
    """Main function to start either:
    1. Just the Flask dashboard
    2. Just the Discord bot
    3. Or run them together (default)
    """
    if len(sys.argv) > 1:
        if sys.argv[1] == "bot":
            # Run just the Discord bot
            logger.info("Starting Discord bot only...")
            asyncio.run(bot.main())
            
        elif sys.argv[1] == "web":
            # Run just the web dashboard
            logger.info("Starting web dashboard only...")
            app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        # Default: Run both services using run_all.py if available, otherwise just start them here
        logger.info("Starting both the web dashboard and Discord bot...")
        try:
            import run_all
            run_all_cmd = ["python", "run_all.py"]
            import subprocess
            subprocess.call(run_all_cmd)
        except ImportError:
            # If run_all.py is not available, start both services here
            run_both_services()
            app.run(host="0.0.0.0", port=5000, debug=True)

# Initialize both services when imported by Gunicorn
# This ensures the Discord bot runs alongside the web dashboard
run_both_services()

if __name__ == "__main__":
    main()
