"""
Helper module to set up Google Cloud credentials
"""
import os
import json
import logging

logger = logging.getLogger('discord')

CREDENTIALS_FILE_PATH = "google_credentials.json"

def setup_google_credentials():
    """Set up Google Cloud credentials from environment variables"""
    try:
        # Check if credentials JSON string is available in environment
        credentials_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        
        if credentials_json:
            # Write credentials to file
            with open(CREDENTIALS_FILE_PATH, 'w') as f:
                f.write(credentials_json)
            
            # Set environment variable to point to the file
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_FILE_PATH
            logger.info(f"Google Cloud credentials set up from environment variable")
            return True
        
        # Check if file already exists
        if os.path.exists(CREDENTIALS_FILE_PATH):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_FILE_PATH
            logger.info(f"Google Cloud credentials already set up at {CREDENTIALS_FILE_PATH}")
            return True
            
        logger.warning("No Google Cloud credentials found in environment")
        return False
        
    except Exception as e:
        logger.error(f"Error setting up Google Cloud credentials: {str(e)}")
        return False