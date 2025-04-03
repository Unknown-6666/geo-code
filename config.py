import os

# Bot configuration
DEFAULT_PREFIX = "!"
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("No Discord token found in environment variables")

# Bot owner and permission configuration
BOT_OWNER_IDS = (1003686821600960582, 1296213550917881856)  # Your Discord IDs
MOD_ROLE_IDS = [
    954166360680837182, 972579273493872710  # Moderator role ID
]

# YouTube channel configuration
YOUTUBE_CHANNELS = [
    "UCJXJvWQMfnp7P36_jab4dog",
    "UChwib7NAVu03BvV3nUUqpSQ"
]
DEFAULT_ANNOUNCEMENT_CHANNEL = None  # Will be set when first announcement channel is configured

# Discord color scheme
COLORS = {
    "PRIMARY": 0x7289DA,    # Discord Blurple
    "SECONDARY": 0x99AAB5,  # Discord Grey
    "SUCCESS": 0x43B581,    # Discord Green
    "ERROR": 0xF04747,      # Discord Red
    "WARNING": 0xFAA61A,    # Warning/Orange
    "WHITE": 0xFFFFFF       # White
}

# Bot status messages
STATUS_MESSAGES = [
    "Looking for survivors"
]