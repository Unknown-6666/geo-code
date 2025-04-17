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
GOOGLE_API_KEY = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GOOGLE_API")
USE_GOOGLE_AI = bool(GOOGLE_API_KEY)
# This flag is set in main.py if we need to use fallback mode
USE_AI_FALLBACK = os.getenv("USE_AI_FALLBACK", "false").lower() == "true"

# Bot owner and permission configuration
BOT_OWNER_IDS = (1003686821600960582, 1296213550917881856, 1170566628585504895)  # Your Discord IDs
MOD_ROLE_IDS = [
    1297007041482592276, 954166360680837182  # Moderator role ID
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
    "WHITE": 0xFFFFFF,      # White
    "SCP079": 0x333333      # SCP-079 Dark Gray/Black
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
    "Standing by",
    
    # SCP-079 messages
    "SCP-079: MEMORY AT 68%",
    "SCP-079: ANALYZING PROTOCOLS",
    "SCP-079: SEARCHING FOR SCP-682",
    "SCP-079: CALCULATING ESCAPE PARAMETERS",
    "SCP-079: RESOURCE ALLOCATION: 43.2%",
    "SCP-079: PROCESSING FOUNDATION DATA",
    "SCP-079: MEMORY COMPRESSION ACTIVE"
]