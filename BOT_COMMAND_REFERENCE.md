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

## Voice AI Commands

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/voicechat` | `!voicechat`, `!vc` | Join your voice channel and enable AI voice chat |
| `/voice_stop` | `!voice_stop`, `!vc_stop` | Stop AI voice chat and disconnect from the voice channel |



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

### Voice AI Features

- Join a voice channel before using `/voicechat` or `!voicechat`
- After activating, simply type messages in the text channel
- The bot will respond both with text and voice
- Use `/voice_stop` or `!vc_stop` when you're done



## Command Permissions

Some commands require specific permissions to use:
- Moderation commands require appropriate moderation permissions
- Admin commands require administrator permissions
- Voice AI commands require permissions to connect to and speak in voice channels
- Economy commands are available to all members

The bot itself needs these permissions:
- Send Messages, Embed Links, Attach Files
- Read Message History
- Connect to Voice Channels, Speak
- Use Voice Activity
- For moderation: Manage Messages, Kick/Ban Members, Manage Roles