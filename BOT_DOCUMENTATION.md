# Discord Bot Documentation

## For Bot Owners

### Command Management System

The bot includes an advanced command management system that **automatically prevents duplicate commands** in Discord servers. This is a major improvement over previous versions where commands could get registered multiple times, causing users to see duplicate options.

#### Automatic Duplicate Command Prevention

The bot now automatically clears all commands before syncing them with Discord:

1. When the bot starts, it automatically clears all registered commands
2. It then syncs the current command set, ensuring no duplicates are created
3. All command refresh methods now use this clear-first approach

This means **you should no longer experience duplicate commands** in your Discord servers!

#### Why Command Duplication Happened Previously

Command duplication used to occur due to:
1. Discord API issues
2. Bot restarts without proper command clearing
3. Multiple instances of the bot running simultaneously
4. Manual command registration without proper syncing

#### Using the Command Refresh System (Backup Option)

While the automatic system should prevent issues, you can still manually refresh commands if needed:

1. **Web Dashboard** - Visit the [Bot Control Panel](https://workspace.jonahpantz.repl.co/bot_control) (no login required) and use the "Refresh Discord Commands" button
2. **Command Line Scripts**:
   - `python refresh_commands.py` - Interactive refresh with confirmation
   - `python refresh_commands.py -y` - Non-interactive refresh (good for automation)
   - `python sync_commands.py` - Lightweight sync that now includes command clearing
3. **Discord Commands** (for bot owners only):
   - `!sync_commands` - Sync commands globally
   - `!sync_guild_commands` - Sync only in the current server
   - `!clear_commands` - Clear all commands with confirmation

For detailed instructions, see [COMMAND_REFRESH_INSTRUCTIONS.md](COMMAND_REFRESH_INSTRUCTIONS.md) and [COMMAND_MANAGEMENT.md](COMMAND_MANAGEMENT.md)

### Bot Lock Files

The bot uses lock files to prevent multiple instances from running simultaneously:
- `.discord_bot.lock` - Created when the standalone bot is running
- `.main_discord_bot.lock` - Created when the bot is run via the main application

If you encounter issues with the bot not starting, check if these lock files exist. If they do but no bot is running, you can safely delete them.

### Configuration

Important configuration files:
- `config.py` - Main configuration including bot token, owner IDs, and status messages
- `data/profanity_filter.json` - Profanity filter settings
- `data/youtube_channels.json` - YouTube tracker settings

### Adding Bot Owners

To add multiple bot owners, edit the `BOT_OWNER_IDS` tuple in `config.py`:

```python
BOT_OWNER_IDS = (1003686821600960582, 1296213550917881856, YOUR_ID_HERE)
```

### Dashboard Authentication

The dashboard uses Discord OAuth2 for authentication. Only users with their Discord ID in the `BOT_OWNER_IDS` tuple will see owner controls.

### Restart Process

If the bot needs a restart:
1. Stop any running instances
2. Delete any remaining lock files (`rm .*.lock`)
3. Start the bot with either:
   - `python main.py` - Runs both the dashboard and bot
   - `python bot.py` - Runs only the Discord bot

For more details on specific features, refer to the code documentation in each file.

## AI Integration

The bot supports multiple AI providers to power its intelligence, with a flexible fallback system.

### AI Provider Hierarchy

The bot uses the following AI providers in order of preference (configurable):

1. **Google Vertex AI** - Enterprise-grade AI from Google Cloud (requires API credentials)
2. **Google Gemini AI** - Google's Gemini model via direct API integration (requires API key)
3. **G4F Providers** - Fallback free providers when other options are unavailable

### Configuring Vertex AI

To enable Vertex AI integration:

1. Create a Google Cloud project and enable Vertex AI API
2. Create a service account with Vertex AI permissions
3. Download the service account key JSON file
4. Configure the following environment variables in Replit:
   - `GOOGLE_CREDENTIALS` - The full JSON content of your service account key
   - `GOOGLE_CLOUD_PROJECT` - Your Google Cloud project ID
   - `VERTEX_LOCATION` - Region for Vertex AI (e.g., us-central1)
   - `USE_VERTEX_AI` - Set to 'true' to enable Vertex AI
   - `VERTEX_AI_PRIORITY` - Priority level (1 = highest, 2 = second, 3 = lowest)

You can verify your Vertex AI setup by running the test script:
```
python test_vertex_auth.py
```

### Configuring Gemini AI

To use Google's Gemini AI:

1. Obtain a Gemini API key from [Google AI Studio](https://ai.google.dev/)
2. Add the key to Replit Secrets as `GOOGLE_API`

### AI Conversation History

The bot maintains conversation history for each user, allowing for contextual conversations. The history is stored in the PostgreSQL database and is used by both Vertex AI and Gemini models when appropriate.

### Custom AI Responses

The bot supports custom responses for specific patterns, configurable through the `/custom_response` command (admin only).