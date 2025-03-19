import os

# Bot configuration
DEFAULT_PREFIX = "!"
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No Discord token found in environment variables")

# Bot owner and permission configuration
BOT_OWNER_ID = 123456789  # Replace with your Discord ID
MOD_ROLE_IDS = [
    123456789,  # Replace with your mod role IDs
]

# Discord color scheme
COLORS = {
    "PRIMARY": 0x7289DA,    # Discord Blurple
    "SECONDARY": 0x99AAB5,  # Discord Grey
    "SUCCESS": 0x43B581,    # Discord Green
    "ERROR": 0xF04747,      # Discord Red
    "WHITE": 0xFFFFFF       # White
}

# Bot status messages
STATUS_MESSAGES = [
    "Helping users!",
    "Type !help for commands",
    "Serving your server"
]