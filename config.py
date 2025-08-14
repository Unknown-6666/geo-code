import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Bot configuration
DEFAULT_PREFIX = "!"
TOKEN = os.getenv("DISCORD_TOKEN")
# We'll handle missing token errors gracefully in main.py and deploy.py instead of raising exceptions
# This allows the web dashboard to still function even if the bot can't start

# AI configuration
# AIML API configuration (primary)
AIML_API_KEY = "bc3b9f2a9df6447bbc451a43c18a703f"  # Hard-coded API key
USE_AIML_API = bool(AIML_API_KEY)

# Gemini API configuration (fallback)
GOOGLE_API_KEY = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API")
USE_GOOGLE_AI = bool(GOOGLE_API_KEY)

# Google Vertex AI configuration (disabled by default)
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1") 
USE_VERTEX_AI = os.getenv("USE_VERTEX_AI", "false").lower() == "true"  # Disabled by default

# This flag is set in main.py if we need to use fallback mode
USE_AI_FALLBACK = os.getenv("USE_AI_FALLBACK", "false").lower() == "true"

# Bot owner and permission configuration
BOT_OWNER_IDS = (1003686821600960582, 1296213550917881856, 1170566628585504895)  # Your Discord IDs
MOD_ROLE_IDS = [
    1297007041482592276, 954166360680837182  # Moderator role ID
]

# User allowed to use the !jog command (in addition to bot owner)
JOG_ALLOWED_USER_ID = 399759194712047627, 904434729602928680  # User ID to allow jog command access
os.environ["JOG_ALLOWED_USER_ID"] = str(JOG_ALLOWED_USER_ID)  # Also set this in environment

# List of user IDs allowed to use fun commands (in addition to bot owner)
# The bot owner can add/remove from this list using a command
FUN_COMMAND_ALLOWED_IDS = [
    399759194712047627,  # Same ID as JOG_ALLOWED_USER_ID for now
]

# YouTube channel configuration
YOUTUBE_CHANNELS = [

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
    # Standard bot messages
    "Online and operational",
    "Processing commands",
    "Serving your server",
    "Monitoring chat activity",
    "Awaiting instructions",
    "Ready for commands",
    "AI systems engaged",
    "Ready to assist",
    "Command processing active",
    "Running system diagnostics",
    "Updating knowledge base",
    "Executing primary functions",
    "Standing by"
]