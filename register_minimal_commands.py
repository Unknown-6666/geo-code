#!/usr/bin/env python3
"""
Minimal command registration script for SCP-079 commands.
Uses a very lightweight approach to avoid issues with Discord's API rate limits.
"""
import os
import sys
import json
import time
import logging
import requests
from config import TOKEN

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('minimal_register')

def register_minimal_commands():
    """Register only essential commands using direct API calls"""
    
    print("\n" + "="*60)
    print(" "*20 + "MINIMAL COMMAND REGISTRATION")
    print("="*60)
    
    # Set up the API endpoints and headers
    application_id = None  # We'll fetch this
    api_base = "https://discord.com/api/v10"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get application information to extract the ID
    print("Fetching application information...")
    try:
        response = requests.get(f"{api_base}/applications/@me", headers=headers)
        response.raise_for_status()
        application_id = response.json()["id"]
        print(f"Found application ID: {application_id}")
    except Exception as e:
        print(f"Error getting application ID: {e}")
        return False
    
    # Define the SCP-079 commands
    commands = [
        {
            "name": "scp079",
            "description": "Communicate with SCP-079, the Old AI",
            "options": [
                {
                    "name": "message",
                    "description": "Your message to SCP-079",
                    "type": 3,  # String type
                    "required": True
                }
            ]
        },
        {
            "name": "scp079_info",
            "description": "Get information about SCP-079"
        },
        {
            "name": "scp079_clear",
            "description": "Clear your conversation history with SCP-079"
        }
    ]
    
    # First, let's clear all existing commands to avoid duplication
    print("Clearing existing commands...")
    try:
        response = requests.put(
            f"{api_base}/applications/{application_id}/commands",
            headers=headers,
            json=[]  # Empty array to clear all commands
        )
        
        if response.status_code == 429:  # Rate limited
            reset_after = int(response.headers.get('X-RateLimit-Reset-After', 10))
            print(f"Rate limited while clearing commands. Waiting {reset_after} seconds...")
            time.sleep(reset_after)
            
            # Try again
            response = requests.put(
                f"{api_base}/applications/{application_id}/commands",
                headers=headers,
                json=[]
            )
            
        response.raise_for_status()
        print("Successfully cleared commands")
    except Exception as e:
        print(f"Error clearing commands: {e}")
        if hasattr(response, 'text'):
            print(f"API response: {response.text}")
        return False
    
    # Wait a bit after clearing to avoid rate limits
    time.sleep(2)
    
    # Add each command one by one with delay to avoid rate limits
    for i, command in enumerate(commands):
        try:
            print(f"Registering command {i+1}/{len(commands)}: {command['name']}...")
            
            response = requests.post(
                f"{api_base}/applications/{application_id}/commands",
                headers=headers,
                json=command
            )
            
            if response.status_code == 429:  # Rate limited
                reset_after = int(response.headers.get('X-RateLimit-Reset-After', 10))
                print(f"Rate limited. Waiting {reset_after} seconds...")
                time.sleep(reset_after)
                
                # Try again
                response = requests.post(
                    f"{api_base}/applications/{application_id}/commands",
                    headers=headers,
                    json=command
                )
                
            response.raise_for_status()
            print(f"Successfully registered: {command['name']}")
            
            # Add a delay between commands to avoid rate limits
            if i < len(commands) - 1:
                time.sleep(1.5)
                
        except Exception as e:
            print(f"Error registering command {command['name']}: {e}")
            if hasattr(response, 'text'):
                print(f"API response: {response.text}")
            continue
    
    print("\n✅ Command registration complete!")
    print("Note: It may take up to an hour for commands to appear in all Discord servers.")
    return True

if __name__ == "__main__":
    success = register_minimal_commands()
    sys.exit(0 if success else 1)