# Discord Bot Command Reference

This document provides a complete reference of all commands available in the bot. The bot supports both modern slash commands (`/command`) and traditional prefix commands (`!command`). Use whichever style you prefer!

## Basic Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/ping` | `!ping` | Check the bot's response time |
| `/help` | `!help` | Display help information about the bot |
| `/info` | `!info` | Show server information |
| `/userinfo [member]` | `!userinfo [member]` | Display information about a user |

## AI Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/ask <question>` | `!ask <question>` | Ask the AI a one-time question |
| `/chat <message>` | `!chat <message>` | Have a casual conversation with the AI (with memory) |
| `/clear_chat_history` | `!clear_history` | Clear your conversation history with the AI |
| `/show_chat_history` | `!history` | Show your recent conversation with the AI |

## Music Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/join` | `!join` | Join your current voice channel |
| `/leave` | `!leave` | Leave the voice channel |
| `/play <query>` | `!play <query>` | Play a song from YouTube, SoundCloud, or Spotify |
| `/stop` | `!stop` | Stop playing and clear the queue |
| `/skip` | `!skip` | Skip to the next song in the queue |
| `/queue` | `!queue` | Show the current music queue |
| `/volume <0-100>` | `!volume <0-100>` | Set the playback volume |
| `/search <query> <platform>` | `!search <query>` | Search for music on YouTube or SoundCloud |

## Economy Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/balance` | `!balance` | Check your wallet and bank balance |
| `/daily` | `!daily` | Collect daily rewards |
| `/work` | `!work` | Work to earn coins |
| `/deposit <amount>` | `!deposit <amount>` | Deposit money into bank |
| `/withdraw <amount>` | `!withdraw <amount>` | Withdraw money from bank |
| `/rob <target>` | `!rob <target>` | Attempt to rob another user |
| `/coinflip <amount> <choice>` | `!coinflip <amount> <choice>` | Gamble coins on a coin flip |
| `/slots <amount>` | `!slots <amount>` | Play the slot machine |
| `/shop` | `!shop` | View available items in the shop |
| `/buy <item_name>` | `!buy <item_name>` | Buy an item from the shop |
| `/inventory` | `!inventory` | View your inventory |

## Fun Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/meme` | `!meme` | Get a random meme |
| `/memedump [count]` | `!memedump [count]` | Get multiple random memes at once |

## Moderation Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/clear <count>` | `!clear <count>` | Clear messages from a channel |
| `/kick <member> [reason]` | `!kick <member> [reason]` | Kick a member from the server |
| `/ban <member> [reason]` | `!ban <member> [reason]` | Ban a member from the server |
| `/unban <user_id>` | `!unban <user_id>` | Unban a user from the server |
| `/mute <member> <duration> [reason]` | `!mute <member> <duration> [reason]` | Mute a member for a specified duration |
| `/unmute <member>` | `!unmute <member>` | Unmute a member |
| `/warn <member> [reason]` | `!warn <member> [reason]` | Warn a member |
| `/warnings <member>` | `!warnings <member>` | Check a member's warnings |

## Admin Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| N/A | `!sync_commands` | Sync slash commands across all servers (Bot Owner Only) |
| N/A | `!sync_guild` | Sync slash commands for the current server only (Bot Owner Only) |
| `/ai_reload` | `!ai_reload` | Reload AI preferences from file (Admin only) |
| `/custom_response` | `!custom_response` | Manage custom AI responses (Admin only) |

## Tips

### AI Chat Features

- The `/ask` command is for one-off questions without history
- The `/chat` command maintains conversation history between you and the AI
- You can view your conversation history with `!history` or clear it with `!clear_history`

### Using Music Commands

The bot supports various music sources:
- **YouTube**: Just use the song name or YouTube URL
- **SoundCloud**: Prefix your search with "soundcloud:" or use a SoundCloud URL
- **Spotify**: Use a Spotify track URL

Examples:
```
!play despacito
!play soundcloud: chill beats
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
!play https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
```

## Command Permissions

Some commands require specific permissions to use:
- Moderation commands require appropriate moderation permissions
- Admin commands require administrator permissions
- Music commands can be used by anyone with access to the voice channels
- Economy commands are available to all members