#!/bin/bash
# Setup script for running the Discord Bot on Google Cloud

# Update system
echo "========================================================"
echo "  Updating System Packages"
echo "========================================================"
apt update
apt upgrade -y

# Install dependencies
echo "========================================================"
echo "  Installing System Dependencies"
echo "========================================================"
apt install -y python3-pip python3-venv git postgresql postgresql-contrib nodejs npm

# Setup Python virtual environment
echo "========================================================"
echo "  Setting Up Python Virtual Environment"
echo "========================================================"
mkdir -p /opt/discord-bot
cd /opt/discord-bot

# Clone repository if it doesn't exist
if [ ! -d ".git" ]; then
    echo "========================================================"
    echo "  Cloning Repository"
    echo "========================================================"
    # Replace with your actual repository URL
    read -p "Enter your repository URL (e.g., https://github.com/yourusername/your-bot-repo.git): " REPO_URL
    git clone "$REPO_URL" .
fi

# Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "========================================================"
echo "  Installing Python Dependencies"
echo "========================================================"
pip install --upgrade pip
pip install discord-py>=2.5.2 email-validator>=2.2.0 flask-login>=0.6.3 flask>=3.1.0 \
    flask-sqlalchemy>=3.1.1 google-api-python-client>=2.164.0 gunicorn>=23.0.0 \
    psycopg2-binary>=2.9.10 pydantic>=2.10.6 flask-wtf>=1.2.2 sqlalchemy>=2.0.39 \
    requests-oauthlib>=2.0.0 requests>=2.32.3 oauthlib>=3.2.2 aiohttp>=3.11.14 \
    twilio>=9.5.0 yt-dlp>=2025.2.19 pynacl>=1.5.0 g4f>=0.4.8.6 psutil>=7.0.0 \
    google-cloud-aiplatform gtts speechrecognition

# Setup PostgreSQL
echo "========================================================"
echo "  Setting Up PostgreSQL Database"
echo "========================================================"
# Start PostgreSQL service
systemctl enable postgresql
systemctl start postgresql

# Create database and user
sudo -u postgres bash -c "
psql -c \"CREATE DATABASE discordbot;\"
psql -c \"CREATE USER botuser WITH PASSWORD 'botpassword';\"
psql -c \"ALTER ROLE botuser SET client_encoding TO 'utf8';\"
psql -c \"ALTER ROLE botuser SET default_transaction_isolation TO 'read committed';\"
psql -c \"ALTER ROLE botuser SET timezone TO 'UTC';\"
psql -c \"GRANT ALL PRIVILEGES ON DATABASE discordbot TO botuser;\"
"

# Create .env file
echo "========================================================"
echo "  Setting Up Environment Variables"
echo "========================================================"
read -p "Enter your Discord Bot Token: " DISCORD_TOKEN
read -p "Enter your Google API Key (or press Enter for default): " GOOGLE_API
GOOGLE_API=${GOOGLE_API:-"AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE"}

cat > .env << EOF
DISCORD_TOKEN=$DISCORD_TOKEN
GOOGLE_API=$GOOGLE_API
DATABASE_URL=postgresql://botuser:botpassword@localhost/discordbot
EOF

# Create systemd service
echo "========================================================"
echo "  Creating Systemd Service"
echo "========================================================"
cat > /etc/systemd/system/discord-bot.service << EOF
[Unit]
Description=Discord Bot Service
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/opt/discord-bot
ExecStart=/opt/discord-bot/venv/bin/python /opt/discord-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for web dashboard (optional)
cat > /etc/systemd/system/discord-bot-web.service << EOF
[Unit]
Description=Discord Bot Web Dashboard
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/opt/discord-bot
ExecStart=/opt/discord-bot/venv/bin/gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
systemctl daemon-reload
systemctl enable discord-bot.service
systemctl start discord-bot.service

# Ask if user wants to start web dashboard
read -p "Do you want to start the web dashboard too? (y/n): " START_WEB
if [[ "$START_WEB" == "y" ]]; then
    systemctl enable discord-bot-web.service
    systemctl start discord-bot-web.service
    echo "Web dashboard started on port 5000"
fi

# Final message
echo "========================================================"
echo "  Setup Complete!"
echo "========================================================"
echo "Your Discord bot is now running as a service and will restart automatically if it crashes."
echo "To check bot status: systemctl status discord-bot"
echo "To view logs: journalctl -u discord-bot -f"
if [[ "$START_WEB" == "y" ]]; then
    echo "Web dashboard is running on port 5000"
    echo "To check dashboard status: systemctl status discord-bot-web"
    echo "To view dashboard logs: journalctl -u discord-bot-web -f"
fi
echo "Remember to configure a firewall if your server is exposed to the internet!"