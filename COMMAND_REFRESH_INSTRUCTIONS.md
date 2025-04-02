# Refreshing Discord Slash Commands

This document provides step-by-step instructions for refreshing Discord slash commands when you encounter issues like duplicated commands, missing commands, or commands not behaving as expected.

## When to Refresh Commands

You should consider refreshing Discord slash commands when:

1. You see duplicate commands in the Discord interface
2. Commands fail with "Unknown Command" errors
3. Command options/parameters are outdated
4. After making significant code changes to command handlers
5. Commands are missing from the Discord interface

## Method 1: Using Bot Commands

The easiest way to refresh commands is using the bot's built-in command management features.

### Clearing Commands First

1. Ensure the bot is running
2. In a Discord channel where the bot has access, type:
   ```
   !clear_commands_prefix
   ```
3. Confirm the action when prompted by clicking the "Confirm" button
4. Wait for the bot to report successful command clearing

### Syncing Commands

After clearing commands (or if you just want to sync without clearing):

1. In a Discord channel where the bot has access, type:
   ```
   !sync_commands
   ```
2. Wait for the bot to report successful command syncing
3. Note: Global commands may take up to an hour to propagate to all servers

### Guild-Specific Syncing

If you want faster command updates for a specific server:

1. In the server where you want to sync commands, type:
   ```
   !sync_guild
   ```
2. Guild-specific commands appear immediately but only in the current server

## Method 2: Using the Refresh Script

For more thorough command refreshing, especially when recovering from command registration issues:

1. Stop the bot if it's currently running
2. Open a terminal in the bot's directory
3. Run the command refresh script:
   ```
   python refresh_commands.py
   ```
4. The script will:
   - Clear all existing commands
   - Register all slash commands again
   - Show progress and results in the terminal

This method provides more detailed logs and handles the entire process automatically.

## Method 3: Manual Process

For the most control over the command registration process:

1. Stop the bot if it's currently running
2. Open a terminal in the bot's directory
3. Run the sync commands script:
   ```
   python sync_commands.py
   ```
4. Start the bot again with:
   ```
   python main.py
   ```

## Troubleshooting Command Refresh Issues

### Commands Still Duplicated After Refresh

If you still see duplicated commands after refreshing:

1. Make sure you're using the bot owner account when running `!clear_commands_prefix`
2. Try the complete refresh script: `python refresh_commands.py`
3. Check if you have both guild-specific and global commands registered

### Commands Not Appearing After Sync

If commands don't appear after syncing:

1. Remember that global commands can take up to an hour to propagate
2. Try using guild-specific commands for testing (`!sync_guild`)
3. Check the Discord Developer Portal to ensure your bot has the `applications.commands` scope
4. Restart your Discord client to clear the command cache

### Permission Errors During Refresh

If you see permission errors during command refresh:

1. Ensure the bot has the "applications.commands" scope
2. Verify that the bot has been invited with the proper permissions
3. Check if the bot token is valid and has not been reset

## Verifying Successful Refresh

To verify that commands have been successfully refreshed:

1. Type `/` in a Discord text channel where the bot has access
2. Check if your bot's commands appear in the command list
3. Try using a few commands to ensure they work as expected
4. Check the `data/command_refresh_status.json` file for the most recent refresh status

## Scheduled Command Maintenance

For larger bots that undergo frequent updates, consider scheduled command maintenance:

1. Inform users of upcoming command refresh
2. Perform the refresh during low-activity periods
3. Document any changes to command parameters or behavior

## Additional Resources

For more information about Discord slash commands, refer to:

- The complete [COMMAND_MANAGEMENT.md](COMMAND_MANAGEMENT.md) guide
- Discord's [official documentation on slash commands](https://discord.com/developers/docs/interactions/application-commands)