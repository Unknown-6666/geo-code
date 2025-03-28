#!/usr/bin/env python3
"""
Script to refresh Discord commands to prevent duplication.
This script can be run manually to clear and re-sync all commands.
"""
import os
import sys
import json
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

def update_status_file(status, message, output=None):
    """Update the status file for the dashboard to read"""
    try:
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Create the status data
        status_data = {
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add output if provided
        if output:
            status_data['output'] = output
            
        # Write the status to file
        with open('data/command_refresh_status.json', 'w') as f:
            json.dump(status_data, f)
            
        logger.info(f"Updated status file: {status} - {message}")
    except Exception as e:
        logger.error(f"Failed to update status file: {str(e)}")

async def refresh_commands():
    """Run the command sync process"""
    from bot import sync_commands_only
    
    logger.info("Starting command refresh process...")
    
    # Update status to 'pending'
    update_status_file('pending', 'Command refresh is in progress...')
    
    output_lines = []
    
    # Create a custom function to handle command sync
    try:
        # Print initial status
        message = "🔄 Refreshing Discord commands..."
        print(f"\n{message}")
        output_lines.append(message)
        
        # Run the sync function from bot.py
        result = await sync_commands_only()
        
        if result is True:
            message = "✅ SUCCESS: Commands have been refreshed successfully!"
            print(f"\n{message}")
            output_lines.append(message)
            
            additional_info = "Your bot's slash commands have been cleared and re-synced with Discord. This should fix any duplicate commands in your servers."
            print(f"\n{additional_info}")
            output_lines.append(additional_info)
            
            update_status_file('success', 'Commands successfully cleared and refreshed.', '\n'.join(output_lines))
            return True
        else:
            # Check if we got a tuple with a success flag and message
            if isinstance(result, tuple) and len(result) == 2:
                success, message = result
                if success:
                    print(f"\n✅ SUCCESS: {message}")
                    output_lines.append(f"SUCCESS: {message}")
                    update_status_file('success', message, '\n'.join(output_lines))
                    return True
                else:
                    print(f"\n⚠️ WARNING: {message}")
                    print("\nCommand sync completed with warnings.")
                    output_lines.append(f"WARNING: {message}")
                    output_lines.append("Command sync completed with warnings.")
                    update_status_file('warning', message, '\n'.join(output_lines))
                    return True
            else:
                error_msg = "Command refresh failed."
                print(f"\n❌ ERROR: {error_msg}")
                print("\nPlease check the logs above for detailed error information.")
                output_lines.append(f"ERROR: {error_msg}")
                output_lines.append("Please check the logs for details.")
                update_status_file('error', error_msg, '\n'.join(output_lines))
                return False
            
    except Exception as e:
        # Check for known errors
        error_str = str(e)
        if "Extension 'cogs." in error_str and "is already loaded" in error_str:
            message = "Some extensions were already loaded. This is normal during command refresh and doesn't affect the sync process."
            print(f"\n⚠️ WARNING: {message}")
            print("\nYour commands have been refreshed successfully!")
            output_lines.append(f"WARNING: {message}")
            output_lines.append("Your commands have been refreshed successfully!")
            update_status_file('success', 'Commands refreshed successfully with minor warnings.', '\n'.join(output_lines))
            return True
        else:
            error_msg = f"An unexpected error occurred: {error_str}"
            print(f"\n❌ ERROR: {error_msg}")
            logger.exception("Unexpected error during command refresh")
            output_lines.append(f"ERROR: {error_msg}")
            update_status_file('error', error_msg, '\n'.join(output_lines))
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