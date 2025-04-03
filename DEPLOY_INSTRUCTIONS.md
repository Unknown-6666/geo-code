# Discord Bot Deployment Instructions

This document explains how to deploy your Discord bot to run reliably on Google Cloud Platform.

## Files Included for Deployment:

1. `generate_requirements.py` - Generates a requirements.txt file with all necessary dependencies
2. `setup.py` - Interactive setup script that helps install dependencies and configure the bot
3. `run_bot.py` - Helper script that runs the bot with error handling and automatic restarts

## Quick Start Guide

### Option 1: Running on Google Cloud Compute Engine

1. **Create a VM in Google Cloud**:
   - Sign up for Google Cloud Platform (you get $300 free credits as a new user)
   - Go to Compute Engine → VM instances → Create instance
   - Choose e2-micro (free tier eligible) with Ubuntu
   - Allow HTTP/HTTPS traffic if needed
   - Create and start the VM

2. **Set up Your Server**:
   ```bash
   # Connect to your VM using SSH
   # Update system packages
   sudo apt update
   sudo apt upgrade -y
   
   # Install required system packages
   sudo apt install -y python3-pip python3-venv git postgresql postgresql-contrib
   
   # Clone your bot repository
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   
   # Generate requirements file
   python3 generate_requirements.py
   
   # Create a virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install requirements
   pip install -r requirements.txt
   
   # Set up PostgreSQL
   sudo -u postgres psql -c "CREATE DATABASE discordbot;"
   sudo -u postgres psql -c "CREATE USER botuser WITH PASSWORD 'YourPassword';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE discordbot TO botuser;"
   
   # Create .env file
   echo "DISCORD_TOKEN=your_discord_token" > .env
   echo "GOOGLE_API=AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE" >> .env
   echo "DATABASE_URL=postgresql://botuser:YourPassword@localhost/discordbot" >> .env
   
   # Run the bot with the helper script
   python3 run_bot.py
   ```

3. **Set Up as a System Service**:
   ```bash
   # Create a service file
   sudo nano /etc/systemd/system/discord-bot.service
   
   # Paste the following (replace paths with your actual paths):
   [Unit]
   Description=Discord Bot
   After=network.target postgresql.service
   
   [Service]
   User=YOUR_USERNAME
   WorkingDirectory=/home/YOUR_USERNAME/YOUR_REPO
   ExecStart=/home/YOUR_USERNAME/YOUR_REPO/venv/bin/python /home/YOUR_USERNAME/YOUR_REPO/run_bot.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   
   # Enable and start the service
   sudo systemctl daemon-reload
   sudo systemctl enable discord-bot.service
   sudo systemctl start discord-bot.service
   
   # Check the status
   sudo systemctl status discord-bot.service
   ```

### Option 2: Using Docker and Google Cloud Run

1. **Create a Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   # Install system dependencies
   RUN apt-get update && apt-get install -y git ffmpeg libffi-dev \
       && rm -rf /var/lib/apt/lists/*
   
   # Generate and use requirements
   COPY generate_requirements.py .
   RUN python generate_requirements.py
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy the application
   COPY . .
   
   # Create entrypoint script
   RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
       echo 'echo "DISCORD_TOKEN=${DISCORD_TOKEN}" > .env' >> /app/entrypoint.sh && \
       echo 'echo "GOOGLE_API=${GOOGLE_API:-AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE}" >> .env' >> /app/entrypoint.sh && \
       echo 'echo "DATABASE_URL=${DATABASE_URL}" >> .env' >> /app/entrypoint.sh && \
       echo 'exec python "$@"' >> /app/entrypoint.sh && \
       chmod +x /app/entrypoint.sh
   
   ENTRYPOINT ["/app/entrypoint.sh"]
   CMD ["run_bot.py"]
   ```

2. **Build and Deploy**:
   ```bash
   # Install Google Cloud CLI
   # Build the Docker image
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/discord-bot
   
   # Deploy to Cloud Run
   gcloud run deploy discord-bot \
     --image gcr.io/YOUR_PROJECT_ID/discord-bot \
     --platform managed \
     --set-env-vars="DISCORD_TOKEN=YOUR_TOKEN,DATABASE_URL=YOUR_DB_URL"
   ```

## Troubleshooting

- **Bot crashes immediately**: Check logs with `journalctl -u discord-bot -f`
- **Database connection issues**: Make sure PostgreSQL is running and the DATABASE_URL is correct
- **Missing packages**: Run `pip install -r requirements.txt` again
- **Permission issues**: Check that the user running the bot has access to all necessary files

## Additional Tips

1. **Set up monitoring**: Configure Cloud Monitoring to track your VM's health
2. **Regular backups**: Schedule regular database backups
3. **Update dependencies**: Periodically run `pip install --upgrade -r requirements.txt`
4. **Security**: Never put your Discord token directly in your code
5. **Scalability**: For a very active bot, consider upgrading to a larger VM instance