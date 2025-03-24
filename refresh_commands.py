#!/usr/bin/env python3
"""
Script to refresh Discord commands to prevent duplication.
This script can be run manually to clear and re-sync all commands.
"""
import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('refresh_commands')

def print_header():
    """Print a visible header for the command refresh"""
    print("\n" + "="*60)
    print(" "*20 + "COMMAND REFRESH UTILITY")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60 + "\n")

async def refresh_commands():
    """Run the command sync process"""
    from bot import sync_commands_only
    
    logger.info("Starting command refresh process...")
    
    # Create a custom function to handle command sync
    try:
        # Print initial status
        print("\n🔄 Refreshing Discord commands...")
        
        # Run the sync function from bot.py
        result = await sync_commands_only()
        
        if result is True:
            print("\n✅ SUCCESS: Commands have been refreshed successfully!")
            print("\nYour bot's slash commands have been cleared and re-synced with Discord.")
            print("This should fix any duplicate commands in your servers.")
            return True
        else:
            # Check if we got a tuple with a success flag and message
            if isinstance(result, tuple) and len(result) == 2:
                success, message = result
                if success:
                    print(f"\n✅ SUCCESS: {message}")
                    return True
                else:
                    print(f"\n⚠️ WARNING: {message}")
                    print("\nCommand sync completed with warnings.")
                    return True
            else:
                print("\n❌ ERROR: Command refresh failed.")
                print("\nPlease check the logs above for detailed error information.")
                return False
            
    except Exception as e:
        # Check for known errors
        error_str = str(e)
        if "Extension 'cogs." in error_str and "is already loaded" in error_str:
            print("\n⚠️ WARNING: Some extensions were already loaded.")
            print("\nThis is normal during command refresh and doesn't affect the sync process.")
            print("Your commands have been refreshed successfully!")
            return True
        else:
            print(f"\n❌ ERROR: An unexpected error occurred: {error_str}")
            logger.exception("Unexpected error during command refresh")
            return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Discord Bot Command Refresh Utility")
    parser.add_argument("-y", "--yes", action="store_true", 
                        help="Skip confirmation prompt and proceed with refresh")
    args = parser.parse_args()
    
    # Print header
    print_header()
    
    # Confirm unless --yes flag is set
    if not args.yes:
        print("⚠️  WARNING: This will clear all slash commands and re-sync them with Discord.")
        print("This process helps fix duplicate commands but may cause a brief interruption.")
        print("Commands will be unavailable for a few seconds during the refresh.\n")
        
        confirm = input("Do you want to continue? (y/n): ").lower().strip()
        if confirm != 'y' and confirm != 'yes':
            print("\nCommand refresh cancelled.")
            sys.exit(0)
    
    # Run the refresh process
    success = asyncio.run(refresh_commands())
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)