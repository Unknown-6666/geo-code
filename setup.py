#!/usr/bin/env python3
"""
Setup script for the Discord Bot.
This script will:
1. Install all required dependencies
2. Set up the database
3. Configure environment variables
"""
import os
import subprocess
import sys
import time

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60)

def install_dependencies():
    """Install all required Python dependencies."""
    print_header("Installing Required Dependencies")
    
    dependencies = [
        "discord-py>=2.5.2",
        "email-validator>=2.2.0",
        "flask-login>=0.6.3",
        "flask>=3.1.0",
        "flask-sqlalchemy>=3.1.1",
        "google-api-python-client>=2.164.0",
        "gunicorn>=23.0.0",
        "psycopg2-binary>=2.9.10",
        "pydantic>=2.10.6",
        "flask-wtf>=1.2.2",
        "sqlalchemy>=2.0.39",
        "requests-oauthlib>=2.0.0",
        "requests>=2.32.3",
        "oauthlib>=3.2.2",
        "aiohttp>=3.11.14",
        "twilio>=9.5.0",
        "yt-dlp>=2025.2.19",
        "pynacl>=1.5.0",
        "g4f>=0.4.8.6",
        "psutil>=7.0.0",
        "google-cloud-aiplatform",
        "gtts",
        "speechrecognition"
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        except subprocess.CalledProcessError as e:
            print(f"Error installing {dep}: {e}")
            print("Continuing with other installations...")

def setup_database():
    """Set up the PostgreSQL database if it's not already set up."""
    print_header("Setting Up Database")
    
    try:
        # Check if PostgreSQL is installed
        subprocess.check_call(["which", "psql"])
        print("PostgreSQL is installed.")
        
        # Attempt to create database if it doesn't exist
        db_name = input("Enter the database name to use (default: discordbot): ") or "discordbot"
        db_user = input("Enter the database user to use (default: postgres): ") or "postgres"
        db_password = input("Enter the database password: ")
        
        # Create database if it doesn't exist
        try:
            subprocess.check_call([
                "sudo", "-u", "postgres", "psql", "-c", 
                f"CREATE DATABASE {db_name};"
            ])
            print(f"Database '{db_name}' created successfully.")
        except subprocess.CalledProcessError:
            print(f"Database '{db_name}' might already exist. Continuing...")
        
        # Create user if it doesn't exist
        try:
            subprocess.check_call([
                "sudo", "-u", "postgres", "psql", "-c", 
                f"CREATE USER {db_user} WITH PASSWORD '{db_password}';"
            ])
            print(f"User '{db_user}' created successfully.")
        except subprocess.CalledProcessError:
            print(f"User '{db_user}' might already exist. Continuing...")
        
        # Grant privileges
        try:
            subprocess.check_call([
                "sudo", "-u", "postgres", "psql", "-c", 
                f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
            ])
            print(f"Privileges granted to '{db_user}' on database '{db_name}'.")
        except subprocess.CalledProcessError:
            print("Error granting privileges. Please check your PostgreSQL setup.")
        
        # Set environment variable for database URL
        db_url = f"postgresql://{db_user}:{db_password}@localhost/{db_name}"
        os.environ["DATABASE_URL"] = db_url
        print(f"Database URL set: {db_url}")
        
        # Write the database URL to .env file for persistence
        with open(".env", "a") as f:
            f.write(f"DATABASE_URL={db_url}\n")
        
    except subprocess.CalledProcessError:
        print("PostgreSQL is not installed. Please install PostgreSQL first.")
        print("You can install it using: sudo apt update && sudo apt install postgresql")
        sys.exit(1)

def setup_env_variables():
    """Set up environment variables needed for the bot."""
    print_header("Setting Up Environment Variables")
    
    env_vars = {}
    
    # Check if .env file exists
    if os.path.exists(".env"):
        print("Found existing .env file.")
        with open(".env", "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
    
    # Discord Bot Token
    if "DISCORD_TOKEN" not in env_vars:
        discord_token = input("Enter your Discord Bot Token: ")
        env_vars["DISCORD_TOKEN"] = discord_token
    
    # Google API Key
    if "GOOGLE_API" not in env_vars:
        google_api = input("Enter your Google API Key (for Gemini AI): ") or "AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE"
        env_vars["GOOGLE_API"] = google_api
    
    # Write all environment variables to .env file
    with open(".env", "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print("Environment variables saved to .env file.")

def create_systemd_service():
    """Create a systemd service file for running the bot as a service."""
    print_header("Setting Up Systemd Service")
    
    service_content = """[Unit]
Description=Discord Bot Service
After=network.target postgresql.service

[Service]
User=YOUR_USERNAME
WorkingDirectory=BOT_DIRECTORY
ExecStart=BOT_DIRECTORY/run_bot.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    # Get current user
    try:
        username = subprocess.check_output(["whoami"]).decode().strip()
        print(f"Current user: {username}")
    except subprocess.CalledProcessError:
        username = input("Enter the username to run the bot service: ")
    
    # Get current directory
    bot_directory = os.path.abspath(os.getcwd())
    print(f"Bot directory: {bot_directory}")
    
    # Update service content
    service_content = service_content.replace("YOUR_USERNAME", username)
    service_content = service_content.replace("BOT_DIRECTORY", bot_directory)
    
    # Create run_bot.sh
    with open("run_bot.sh", "w") as f:
        f.write("""#!/bin/bash
cd "$(dirname "$0")"
source .env
python3 bot.py
""")
    
    # Make run_bot.sh executable
    os.chmod("run_bot.sh", 0o755)
    
    # Create service file
    service_file_path = f"{bot_directory}/discord_bot.service"
    with open(service_file_path, "w") as f:
        f.write(service_content)
    
    print(f"Created systemd service file at: {service_file_path}")
    print("\nTo install the service, run:")
    print(f"sudo cp {service_file_path} /etc/systemd/system/")
    print("sudo systemctl daemon-reload")
    print("sudo systemctl enable discord_bot.service")
    print("sudo systemctl start discord_bot.service")

def final_message():
    """Display a final message with instructions."""
    print_header("Setup Complete!")
    print("Your Discord bot has been set up successfully!")
    print("\nTo start the bot manually, run:")
    print("python bot.py")
    print("\nTo start the web dashboard, run:")
    print("python main.py")
    print("\nTo run both together, run:")
    print("python run_all.py")
    print("\nIf you set up the systemd service, the bot should start automatically on boot.")
    print("You can check its status with: sudo systemctl status discord_bot.service")
    print("\nThank you for using the setup script!")

def main():
    """Main function to run all setup steps."""
    print_header("Discord Bot Setup")
    print("This script will help you set up your Discord bot with all required dependencies.")
    print("Make sure you have administrative privileges to install packages.")
    
    continue_setup = input("Do you want to continue? (y/n): ")
    if continue_setup.lower() != "y":
        print("Setup cancelled.")
        return
    
    try:
        # Run each setup step
        install_dependencies()
        setup_env_variables()
        
        # Ask if user wants to set up a database
        setup_db = input("\nDo you want to set up a PostgreSQL database? (y/n): ")
        if setup_db.lower() == "y":
            setup_database()
        
        # Ask if user wants to set up a systemd service
        setup_service = input("\nDo you want to set up a systemd service for the bot? (y/n): ")
        if setup_service.lower() == "y":
            create_systemd_service()
        
        # Display final message
        final_message()
        
    except KeyboardInterrupt:
        print("\nSetup interrupted.")
    except Exception as e:
        print(f"\nAn error occurred during setup: {e}")
        print("Please try running the setup again or set up manually.")

if __name__ == "__main__":
    main()