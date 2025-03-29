# Discord Bot Command Management

This document explains how the Discord bot's command system works and how duplicate commands are now automatically prevented.

## How Discord Commands Work

Discord slash commands must be registered with Discord's API before they can be used. There are two types of commands:

1. **Global Commands**: These are available in all servers where the bot is installed.
2. **Guild-Specific Commands**: These are only available in specific servers.

## The Duplicate Command Problem

In the past, you may have experienced duplicate commands appearing in your Discord servers. This happened because:

1. The bot would register commands each time it started
2. Discord wouldn't automatically remove old commands
3. Over time, multiple identical commands would appear in the command list

## The Solution: Automatic Command Clearing

The bot now includes a robust automatic command management system:

### Automatic Prevention on Every Bot Start

The bot now **automatically clears all commands before syncing** them every time it starts up:

```python
# Always clear commands before syncing to prevent duplicates
logger.info("Clearing all commands before syncing...")
try:
    await self.http.request(
        discord.http.Route("PUT", "/applications/{application_id}/commands", 
                          application_id=self.application_id), 
        json=[]
    )
    logger.info("Commands cleared successfully")
except Exception as e:
    logger.error(f"Error clearing commands: {str(e)}")
    logger.info("Continuing with sync despite clearing error")
    
# Sync commands after clearing with rate limit handling
logger.info("Syncing global commands with Discord...")
rate_limit_count = 0
max_rate_limits = 3  # Maximum number of rate limit retries

while rate_limit_count < max_rate_limits:
    try:
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} commands globally")
        break  # Successfully synced, exit the loop
    except discord.errors.HTTPException as e:
        if e.status == 429:  # Rate limited
            rate_limit_count += 1
            retry_after = e.retry_after if hasattr(e, 'retry_after') else 60
            
            logger.warning(f"Rate limited while syncing commands ({rate_limit_count}/{max_rate_limits}). "
                          f"Retrying in {retry_after:.2f} seconds...")
            
            if rate_limit_count >= max_rate_limits:
                logger.warning(f"Hit rate limit {max_rate_limits} times, stopping command sync.")
                break
                
            # Wait for the rate limit to expire
            await asyncio.sleep(retry_after)
        else:
            # Not a rate limit error, re-raise
            raise
```

### Enhanced Manual Refresh System

For rare cases where issues persist, you can use the Bot Control Panel to manually refresh commands:

1. Visit the [Bot Control Panel](https://workspace.jonahpantz.repl.co/bot_control)
2. Click the "Refresh Discord Commands" button
3. The system will:
   - Update you with real-time status
   - Clear all existing commands
   - Re-sync the latest commands
   - Confirm when the process completes

## Additional Command Management Tools

The bot also includes several other command management methods:

1. **Command Refresh Script**: Running `python refresh_commands.py` from the command line
2. **Command-Line Flag**: Using `python bot.py --sync-commands` 
3. **Owner-Only Commands**: Server owners can use the following commands in Discord:
   - `!sync_commands` - Sync all commands globally
   - `!sync_guild_commands` - Sync commands for the current server only
   - `!clear_commands` - Clear all commands (Owner confirmation required)

## Why You Won't See Duplicates Anymore

With these changes, duplicate commands are now automatically prevented because:

1. **Every bot start** begins with a clean slate by clearing all commands
2. **All refresh methods** properly clear commands before syncing
3. **Real-time status tracking** confirms successful updates
4. **Rate limiting protection** prevents Discord API issues

If you ever encounter command issues in the future, simply restart the bot or use the Bot Control Panel's refresh button.

## Additional Information

- **Rate Limit Protection**: The bot now automatically handles Discord API rate limits:
  - Attempts to sync commands up to 3 times when rate limited
  - Waits for the appropriate time between attempts
  - Will stop after 3 consecutive rate limits to prevent excessive waiting
  - Provides clear warning logs about rate limiting status

- Discord has rate limits that occasionally cause temporary issues with command syncing
- Command changes may take up to an hour to propagate across all Discord servers
- New commands are added automatically when new features are implemented in the bot

For more information, refer to [Discord's documentation on application commands](https://discord.com/developers/docs/interactions/application-commands).