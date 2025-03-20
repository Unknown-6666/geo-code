#!/usr/bin/env python3
"""
Unified starter script for launching both the Flask web dashboard and Discord bot
"""
import os
import sys
import time
import threading
import subprocess
import logging
import signal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('run_all')

# Global process references for cleanup
flask_process = None
discord_process = None

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info("Termination signal received, shutting down...")
    if flask_process:
        logger.info("Terminating Flask process...")
        flask_process.terminate()
    if discord_process:
        logger.info("Terminating Discord bot process...")
        discord_process.terminate()
    sys.exit(0)

def start_flask():
    """Start the Flask web dashboard"""
    global flask_process
    logger.info("Starting Flask web dashboard...")
    
    flask_cmd = ["gunicorn", "--bind", "0.0.0.0:5000", "--reuse-port", "--reload", "dashboard.app:app"]
    flask_process = subprocess.Popen(
        flask_cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Monitor and log Flask output
    while True:
        if flask_process.stdout is None:
            time.sleep(1)
            continue
            
        output = flask_process.stdout.readline()
        if output:
            print(f"[FLASK] {output.strip()}")
        if flask_process.poll() is not None:
            logger.warning("Flask process terminated unexpectedly, restarting...")
            time.sleep(5)  # Wait before restarting
            flask_process = subprocess.Popen(
                flask_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

def start_discord_bot():
    """Start the Discord bot"""
    global discord_process
    logger.info("Starting Discord bot...")
    
    discord_cmd = ["python", "bot.py"]
    discord_process = subprocess.Popen(
        discord_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Monitor and log Discord bot output
    while True:
        if discord_process.stdout is None:
            time.sleep(1)
            continue
            
        output = discord_process.stdout.readline()
        if output:
            print(f"[DISCORD] {output.strip()}")
        if discord_process.poll() is not None:
            logger.warning("Discord bot process terminated unexpectedly, restarting...")
            time.sleep(5)  # Wait before restarting
            discord_process = subprocess.Popen(
                discord_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

if __name__ == "__main__":
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting all application components...")
    
    # Start Flask and Discord bot in separate threads
    flask_thread = threading.Thread(target=start_flask)
    discord_thread = threading.Thread(target=start_discord_bot)
    
    flask_thread.daemon = True
    discord_thread.daemon = True
    
    flask_thread.start()
    discord_thread.start()
    
    logger.info("All components started successfully")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        signal_handler(None, None)