#!/usr/bin/env python3
"""
Generate a requirements.txt file for the Discord bot.
This script will create a requirements.txt file containing all the necessary dependencies.
"""
import os

def generate_requirements_file():
    """Generate a requirements.txt file with all necessary dependencies."""
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
    
    # Create or overwrite requirements.txt
    with open("requirements.txt", "w") as f:
        for dep in dependencies:
            f.write(f"{dep}\n")
    
    print("Requirements file generated successfully!")
    print("To install all dependencies, run: pip install -r requirements.txt")

if __name__ == "__main__":
    generate_requirements_file()