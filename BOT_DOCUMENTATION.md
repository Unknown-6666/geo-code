# Discord Bot Documentation

## Overview

This Discord bot is a feature-rich community management and entertainment solution that combines powerful moderation tools, economy features, AI chat capabilities, music playback, and more. The bot supports both modern slash commands and traditional prefix commands for all features.

## Setup Instructions

### Requirements

- Python 3.8+
- PostgreSQL database
- Discord Bot Token
- Google Cloud Project (for Vertex AI)
- FFmpeg (for music playback and voice AI)
- gTTS and PyAudio (for voice AI functionality)

### Environment Variables

Set up the following environment variables:

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Your Discord bot token |
| `DATABASE_URL` | PostgreSQL database connection string |
| `GOOGLE_CREDENTIALS` | JSON content of Google Cloud service account key |
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud project ID |
| `VERTEX_LOCATION` | Location for Vertex AI (e.g., `us-central1`) |
| `USE_VERTEX_AI` | Set to `true` to use Vertex AI as primary AI provider |
| `VERTEX_AI_PRIORITY` | Priority of Vertex AI (1-3, with 1 being highest) |

### Setup Steps

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables
4. Run the bot: `python main.py`

## Feature Modules

The bot is organized into several cogs (modules), each handling different functionality:

### AI Chat (cogs/ai_chat.py)

Provides AI chat capabilities using:
- Google Vertex AI (primary, if configured)
- Google Gemini AI (secondary)
- G4F (fallback)

Features:
- One-time questions with `/ask` or `!ask`
- Conversation memory with `/chat` or `!chat`
- Conversation history management

See [AI_COMMANDS.md](AI_COMMANDS.md) for detailed commands.

### Voice AI (cogs/voice_ai.py)

Provides voice-based AI interaction in Discord voice channels:
- Joins voice channels on command
- Listens for text messages and responds with voice
- Uses the same AI backend as the text-based AI chat
- Text-to-speech conversion for AI responses

Features:
- Voice channel joining with `/voicechat` or `!voicechat`
- Voice chat responses to text messages
- Text and voice responses to user messages
- Voice channel management

See [VOICE_AI_COMMANDS.md](VOICE_AI_COMMANDS.md) for detailed commands.

### Music (cogs/music.py)

Provides music playback from various sources:
- YouTube
- SoundCloud
- Spotify links

Features:
- Voice channel joining/leaving
- Song playback with queue management
- Volume control and playback options

See [MUSIC_COMMANDS.md](MUSIC_COMMANDS.md) for detailed commands.

### Economy (cogs/economy.py)

Virtual economy system with:
- Currency earning (daily rewards, work)
- Banking system
- Shop with purchasable items
- Gambling games (coinflip, slots)

### Moderation (cogs/moderation.py)

Tools for server management:
- Message clearing
- Member kick/ban functions
- Mute/timeout functionality
- Warning system

### Member Events (cogs/member_events.py)

Handles member join/leave events with customizable messages.

### Memes (cogs/memes.py)

Fetches and displays random memes from Reddit.

### Profanity Filter (cogs/profanity_filter.py)

Detects and handles messages containing profanity.

### Rules Enforcer (cogs/rules_enforcer.py)

Enforces server rules through automated detection.

### Verification (cogs/verification.py)

Provides user verification functionality.

### YouTube Tracker (cogs/youtube_tracker.py)

Tracks new uploads from specified YouTube channels.

## Database Structure

The bot uses a PostgreSQL database with the following main models:

- **Conversation**: Stores AI chat history
- **UserEconomy**: Tracks user balances and economy stats
- **Item**: Represents shop items
- **Inventory**: Tracks user-owned items
- **Transaction**: Records economic transactions

## AI Integration

### Vertex AI

1. Create a Google Cloud project
2. Enable Vertex AI API
3. Create a service account with Vertex AI User role
4. Generate a JSON key and set as `GOOGLE_CREDENTIALS`
5. Run `test_vertex_auth.py` to verify setup

Vertex AI is used when:
- `USE_VERTEX_AI` is set to `true`
- `VERTEX_AI_PRIORITY` is set to a valid priority (1-3)
- Google credentials are valid

The bot will fall back to Gemini AI and then G4F if Vertex AI is unavailable.

## Command Handling

The bot implements a dual-command approach:
- **Slash Commands**: Modern Discord integration with `/command`
- **Prefix Commands**: Traditional text-based commands with `!command`

All major features support both command styles for maximum flexibility.

## Command Syncing

Use these commands to sync slash commands:
- `!sync_commands`: Sync commands globally (all servers)
- `!sync_guild`: Sync commands to current server only
- `!clear_commands_prefix` or `/clear_commands`: Remove all commands

## Dashboard Integration

The bot includes a web dashboard (under `dashboard/`) for:
- Bot status monitoring
- Configuration management
- Command statistics

Access the dashboard by running the web server component with `python run_all.py`.

## Contributing

To contribute to this bot:
1. Set up a development environment following the setup steps
2. Create a feature branch
3. Implement your changes
4. Test thoroughly
5. Submit a pull request

## Troubleshooting

Common issues:
- **Bot doesn't respond**: Check if token is valid and bot is online
- **AI responses fail**: Verify Google credentials and API enablement
- **Database errors**: Check PostgreSQL connection and schema
- **Music playback issues**: Ensure ffmpeg is installed correctly
- **Voice AI issues**: Verify the bot has permission to connect to and speak in voice channels
- **Text-to-speech fails**: Check that gtts library is properly installed

For issues with Vertex AI, run `test_vertex_auth.py` to diagnose authentication problems.

For voice-related issues, ensure that the bot has the following permissions in Discord:
- Connect (to voice channels)
- Speak
- Use Voice Activity

## Command Reference

For a complete list of all commands, see:
- [BOT_COMMAND_REFERENCE.md](BOT_COMMAND_REFERENCE.md)
- [AI_COMMANDS.md](AI_COMMANDS.md)
- [VOICE_AI_COMMANDS.md](VOICE_AI_COMMANDS.md)
- [MUSIC_COMMANDS.md](MUSIC_COMMANDS.md)