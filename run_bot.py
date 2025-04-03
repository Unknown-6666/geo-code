#!/usr/bin/env python3
"""
Helper script for running the Discord bot on Google Cloud.
This script:
1. Makes sure environment variables are properly set
2. Checks database connectivity
3. Runs the bot with proper error handling and restart capabilities
"""
import os
import sys
import time
import subprocess
import signal
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_runner.log")
    ]
)
logger = logging.getLogger("BotRunner")

def check_environment():
    """Check that required environment variables are set."""
    required_vars = ["DISCORD_TOKEN", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Please create a .env file with the following variables:")
        for var in missing_vars:
            logger.info(f"  {var}=your_value_here")
        return False
    
    # Set default Google API key if not provided
    if not os.environ.get("GOOGLE_API"):
        os.environ["GOOGLE_API"] = "AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE"
        logger.info("Using default Google API key")
    
    return True

def load_env_file():
    """Load environment variables from .env file if it exists."""
    if os.path.exists(".env"):
        logger.info("Loading environment variables from .env file")
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

def check_database():
    """Check database connectivity."""
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(os.environ["DATABASE_URL"])
        connection = engine.connect()
        connection.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def run_bot(max_retries=5, retry_delay=30):
    """Run the Discord bot with retry logic."""
    retries = 0
    
    while retries < max_retries:
        try:
            logger.info("Starting Discord bot...")
            process = subprocess.Popen([sys.executable, "bot.py"])
            process.wait()
            
            # If the process exited with a non-zero code, it's an error
            if process.returncode != 0:
                logger.error(f"Bot exited with code {process.returncode}")
                retries += 1
                logger.info(f"Retrying in {retry_delay} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(retry_delay)
            else:
                logger.info("Bot exited normally")
                break
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            if process:
                process.send_signal(signal.SIGTERM)
                process.wait()
            break
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            retries += 1
            logger.info(f"Retrying in {retry_delay} seconds... (Attempt {retries}/{max_retries})")
            time.sleep(retry_delay)
    
    if retries >= max_retries:
        logger.error(f"Maximum retry attempts ({max_retries}) reached. Giving up.")
        return False
    
    return True

def main():
    """Main function to run the bot with all necessary checks."""
    logger.info("=" * 50)
    logger.info("Discord Bot Runner Starting")
    logger.info("=" * 50)
    
    # Load environment variables from .env file
    load_env_file()
    
    # Check environment variables
    if not check_environment():
        return 1
    
    # Check database connectivity
    if not check_database():
        logger.error("Database checks failed. Please fix database issues before continuing.")
        return 1
    
    # Run the bot
    success = run_bot()
    
    if not success:
        logger.error("Bot runner failed after multiple attempts")
        return 1
    
    logger.info("Bot runner completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())