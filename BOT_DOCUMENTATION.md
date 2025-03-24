# Discord Bot Documentation

## For Bot Owners

### Command Refresh System

The bot includes a command refresh system that helps prevent duplicate commands in Discord servers. This occurs when the bot's slash commands get registered multiple times, causing users to see duplicate options.

#### Why Command Duplication Happens

Command duplication can occur due to:
1. Discord API issues
2. Bot restarts without proper command clearing
3. Multiple instances of the bot running simultaneously
4. Manual command registration without proper syncing

#### Using the Command Refresh System

There are several ways to refresh commands:

1. **Web Dashboard** - Log in as a bot owner and use the "Refresh Commands" button
2. **Command Line Scripts**:
   - `python refresh_commands.py` - Interactive refresh with confirmation
   - `python refresh_commands.py -y` - Non-interactive refresh (good for automation)
   - `python sync_commands.py` - Lightweight sync without clearing first
3. **Discord Commands** (for bot owners only):
   - `!sync` - Sync commands globally
   - `!sync_guild` - Sync only in the current server
   - `!clear_commands` - Clear all commands with confirmation

For detailed instructions, see [COMMAND_REFRESH_INSTRUCTIONS.md](COMMAND_REFRESH_INSTRUCTIONS.md)

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