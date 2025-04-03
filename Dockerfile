FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY setup.py .

# Create a requirements.txt file
RUN python setup.py > requirements.txt || echo "discord-py>=2.5.2\nemail-validator>=2.2.0\nflask-login>=0.6.3\nflask>=3.1.0\nflask-sqlalchemy>=3.1.1\ngoogle-api-python-client>=2.164.0\ngunicorn>=23.0.0\npsycopg2-binary>=2.9.10\npydantic>=2.10.6\nflask-wtf>=1.2.2\nsqlalchemy>=2.0.39\nrequests-oauthlib>=2.0.0\nrequests>=2.32.3\noauthlib>=3.2.2\naiohttp>=3.11.14\ntwilio>=9.5.0\nyt-dlp>=2025.2.19\npynacl>=1.5.0\ng4f>=0.4.8.6\npsutil>=7.0.0\ngoogle-cloud-aiplatform\ngtts\nspeechrecognition" > requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create .env file from environment variables
RUN echo "#!/bin/bash\necho \"DISCORD_TOKEN=\${DISCORD_TOKEN}\" > .env\necho \"GOOGLE_API=\${GOOGLE_API:-AIzaSyC2s3PLPvGtfQloUfkyKmMSTULGob9NpAE}\" >> .env\necho \"DATABASE_URL=\${DATABASE_URL}\" >> .env\nexec python \$@" > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Use the entrypoint script to create .env file at runtime
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command runs the Discord bot
CMD ["bot.py"]