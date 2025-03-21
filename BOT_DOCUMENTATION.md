# Geo-Bot Documentation

## Table of Contents
1. [Adding New Commands](#adding-new-commands)
2. [Managing the Profanity Filter](#managing-the-profanity-filter)
   - [How the Filter Works](#how-the-filter-works)
   - [Updating the Filter](#updating-the-filter)
   - [Enhancing the Warning System](#enhancing-the-warning-system)
     - [Showing Usernames and Server Names](#showing-usernames-and-server-names-with-warnings)
     - [Adding List Warnings Command](#adding-a-list-warnings-command)
     - [Enhanced Timeout Notifications](#enhancing-the-timeout-notifications)
     - [Improved Warning Reset Logging](#improving-warning-reset-logging)
3. [Bot Configuration](#bot-configuration)
4. [Troubleshooting](#troubleshooting)
5. [Common Tasks](#common-tasks)
6. [Command Quick Reference](#command-quick-reference)

---

## Adding New Commands

### Adding a Simple Command

To add a new command to the bot, you need to add it to the appropriate cog file in the `cogs` directory. Each cog represents a group of related functionality.

**Steps to add a new slash command:**

1. Open the appropriate cog file (e.g., `cogs/basic_commands.py` for general commands)
2. Add your new command following this template:

```python
@app_commands.command(name="command_name", description="Description of what your command does")
@app_commands.describe(parameter="Description of this parameter")
async def command_name(self, interaction: discord.Interaction, parameter: str):
    """Detailed docstring explaining the command"""
    # Your command logic here
    await interaction.response.send_message("Your response message")
```

3. For a traditional prefix command (starting with `!`), use this template:

```python
@commands.command(name="command_name")
async def command_name_prefix(self, ctx, parameter: str):
    """Detailed docstring explaining the command"""
    # Your command logic here
    await ctx.send("Your response message")
```

### Adding a New Cog (Command Group)

If you want to add an entirely new category of commands:

1. Create a new file in the `cogs` directory (e.g., `cogs/my_feature.py`)
2. Use the following template:

```python
import discord
from discord import app_commands
from discord.ext import commands
import logging

logger = logging.getLogger('discord')

class MyFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("MyFeature cog initialized")
    
    # Add your commands here
    @app_commands.command(name="my_command", description="Description")
    async def my_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("Hello from my command!")

async def setup(bot):
    await bot.add_cog(MyFeature(bot))
```

3. To load the new cog, add it to the `setup_hook` method in `bot.py`:

```python
async def setup_hook(self):
    # Add your cog to this list
    initial_extensions = [
        'cogs.basic_commands',
        'cogs.moderation',
        'cogs.my_feature',  # Add your new cog here
        # ... other existing cogs
    ]
```

### Syncing New Commands

After adding new commands, you need to sync them with Discord:

1. Use the `/sync_commands` command in Discord (bot owner only)
2. Or run `!sync_guild` in a specific server to sync only to that server

---

## Managing the Profanity Filter

### How the Filter Works

The profanity filter system stores blocked words and settings in `data/profanity_config.json`. Users receive warnings when using filtered words, and after 3 warnings they receive a timeout.

### Updating the Filter

#### Adding Words to the Filter

You can add words to the filter using the `/add_filtered_word` command:

```
/add_filtered_word word:bad_word
```

or with the traditional command:

```
!addfilterword bad_word
```

#### Removing Words from the Filter

To remove a word from the filter, use:

```
/remove_filtered_word word:word_to_remove
```

or with the traditional command:

```
!removefilterword word_to_remove
```

#### Viewing Filtered Words

To view all filtered words:

```
/list_filtered_words
```

or with the traditional command:

```
!listfilterwords
```

#### Enabling/Disabling the Filter

To toggle the filter on or off for a server:

```
/toggle_filter enabled:True
```

or 

```
!togglefilter True
```

### Enhancing the Warning System

#### Showing Usernames and Server Names With Warnings

The warning system has been enhanced to show usernames and server names alongside user IDs. Here's how to implement this feature in the `cogs/profanity_filter.py` file:

```python
@app_commands.command(name="checkwarnings", description="Check warnings for a user")
@app_commands.default_permissions(manage_messages=True)
async def check_user_warnings(self, interaction: discord.Interaction, user: discord.Member):
    """Check how many profanity warnings a user has"""
    # Check if user has appropriate permissions
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
        
    # Get warning count and server details
    guild_id = str(interaction.guild_id)
    user_id = str(user.id)
    server_name = interaction.guild.name
    
    if guild_id not in self.warning_count:
        await interaction.response.send_message(f"No warnings have been issued in server '{server_name}'.", ephemeral=True)
        return
        
    if user_id not in self.warning_count[guild_id]:
        await interaction.response.send_message(f"User **{user.display_name}** has no warnings in server '{server_name}'.", ephemeral=True)
        return
        
    count = self.warning_count[guild_id][user_id]
    
    await interaction.response.send_message(
        f"User **{user.display_name}** has {count} profanity warning(s) in server '{server_name}'.", 
        ephemeral=True
    )
```

#### Adding a List Warnings Command

To add a command that lists all users with warnings, implement this:

```python
@app_commands.command(name="listwarnings", description="List all users with warnings")
@app_commands.default_permissions(manage_messages=True)
async def list_warnings(self, interaction: discord.Interaction):
    """List all users with warnings in this server"""
    # Check if user has appropriate permissions
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
        
    guild_id = str(interaction.guild_id)
    server_name = interaction.guild.name
    
    if guild_id not in self.warning_count or not self.warning_count[guild_id]:
        await interaction.response.send_message(f"No warnings have been issued in server '{server_name}'.", ephemeral=True)
        return
        
    # Create a list of users with warnings
    warning_list = []
    for user_id, count in self.warning_count[guild_id].items():
        if count > 0:  # Only include users with active warnings
            # Try to resolve user
            try:
                member = await interaction.guild.fetch_member(int(user_id))
                user_name = member.display_name if member else f"Unknown User ({user_id})"
            except:
                user_name = f"Unknown User ({user_id})"
                
            warning_list.append(f"**{user_name}** - {count} warning(s)")
    
    if not warning_list:
        await interaction.response.send_message(f"No active warnings in server '{server_name}'.", ephemeral=True)
        return
        
    # Create embed for better formatting
    embed = discord.Embed(
        title=f"Warning List for {server_name}",
        description="Users with active warnings:",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="Users", value="\n".join(warning_list))
    embed.set_footer(text=f"Total Users with Warnings: {len(warning_list)} | Server ID: {guild_id}")
    embed.timestamp = datetime.datetime.utcnow()
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
```

#### Enhancing the Timeout Notifications

To improve the timeout notification embeds with more context:

```python
embed = discord.Embed(
    title="User Timed Out",
    description=f"User {message.author.mention} has been timed out for 10 minutes.",
    color=discord.Color.red()
)
embed.add_field(name="User", value=f"{message.author.name} ({message.author.id})", inline=True)
embed.add_field(name="Server", value=message.guild.name, inline=True)
embed.add_field(name="Reason", value="Repeated use of inappropriate language", inline=False)
embed.add_field(name="Warning Count", value=str(warning_count), inline=True)
embed.set_footer(text=f"Triggered: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

await log_channel.send(embed=embed)
logger.info(f"Notification sent to log channel in server '{message.guild.name}'")
```

#### Improving Warning Reset Logging

Improve the reset_warnings method to include better logging:

```python
def reset_warnings(self, user_id, guild_id):
    """Reset warnings for a user"""
    # Convert IDs to strings for JSON compatibility
    user_id = str(user_id)
    guild_id = str(guild_id)
    
    # Initialize the guild dict if it doesn't exist
    if guild_id not in self.warning_count:
        self.warning_count[guild_id] = {}
        logger.info(f"No warnings to reset for guild ID {guild_id} - guild not in warning registry")
        return
        
    # Reset the warning count
    previous_warnings = self.warning_count[guild_id].get(user_id, 0)
    if user_id in self.warning_count[guild_id]:
        self.warning_count[guild_id][user_id] = 0
        self.save_config()
        logger.info(f"Reset warnings for user ID {user_id} in guild ID {guild_id} from {previous_warnings} to 0")
```

---

## Bot Configuration

### General Configuration

The bot's main configuration is stored in `config.py`. This file contains:

- Bot token (loaded from environment variables)
- Command prefix
- Owner ID
- Other global settings

### Environment Variables

Important environment variables used by the bot:

- `DISCORD_TOKEN`: Your bot's token from Discord Developer Portal
- `BOT_OWNER_ID`: Your Discord user ID for owner commands
- `DATABASE_URL`: Connection string for PostgreSQL database

---

## Troubleshooting

### Common Issues

1. **Command not responding**: Make sure commands are synced with `/sync_commands`
2. **Music not playing**: Voice connections may timeout on cloud platforms. Use the robust error handling already implemented.
3. **Database errors**: Check that the database is running and the connection string is correct
4. **Bot not responding to commands**: Ensure the bot has the proper permissions in your Discord server

### Voice and Music Issues

The music system has been recently improved with:
- Better error handling for voice connections
- Timeout handling with clear error messages
- Multiple fallback options for audio sources

If music playback issues persist, check:
1. The bot has permission to join voice channels
2. Your voice channel permissions allow bots to connect
3. The server you're running the bot on allows outbound connections to Discord's voice servers

---

## Common Tasks

### Restarting the Bot

To restart the bot properly:

1. In the Replit environment, stop the current process
2. Run `python main.py` to start both the Discord bot and web dashboard

### Backing Up Data

Key data to backup regularly:
- `data/profanity_config.json` (Profanity filter settings)
- Any database data (economy information, user settings, etc.)

### Adding New Dependencies

If you need to add new Python packages:

1. Add the package to `pyproject.toml`
2. Run `pip install -r requirements.txt` to install the new dependencies

---

## Command Quick Reference

### Moderation Commands
- `/kick user:@username reason:optional_reason` - Kick a user
- `/ban user:@username reason:optional_reason` - Ban a user
- `/unban user_id:123456789 reason:optional_reason` - Unban a user
- `/timeout user:@username duration:minutes reason:optional_reason` - Timeout a user
- `/clear amount:10 user:@username` - Clear messages

### Music Commands
- `/join` - Join your voice channel
- `/play query:song_name` - Play music (YouTube, SoundCloud, Spotify)
- `/stop` - Stop playback and clear queue
- `/skip` - Skip the current song
- `/queue` - Show the current song queue
- `/volume volume:50` - Set the volume (0-100)
- `/search query:song_name platform:youtube` - Search for songs
- `/leave` - Leave the voice channel

### Profanity Filter Commands
#### Slash Commands
- `/addfilter word:word_to_add` - Add a word to filter
- `/removefilter word:word_to_remove` - Remove a word from filter
- `/listfilters` - Show all filtered words
- `/togglefilter enabled:True` - Enable/disable the filter
- `/resetwarnings user:@username` - Reset warnings for a user
- `/checkwarnings user:@username` - Check warning count for a specific user
- `/listwarnings` - List all users with warnings and their counts
- `/filterstatus` - Check if the profanity filter is enabled for this server

#### Traditional Prefix Commands
- `!addfilter word_to_add` - Add a word to filter
- `!removefilter word_to_remove` - Remove a word from filter
- `!listfilters` - Show all filtered words
- `!togglefilter True/False` - Enable/disable the filter
- `!resetwarnings @username` - Reset warnings for a user
- `!checkwarnings @username` - Check warning count for a specific user
- `!listwarnings` - List all users with warnings and their counts
- `!filterstatus` - Check if the profanity filter is enabled for this server

### Economy Commands
- `/balance` - Check your wallet and bank balance
- `/daily` - Collect daily rewards
- `/work` - Work to earn coins
- `/deposit amount:100` - Deposit money to bank
- `/withdraw amount:100` - Withdraw money from bank
- `/shop` - View available items
- `/buy item_name:item` - Buy an item from the shop
- `/inventory` - View your inventory