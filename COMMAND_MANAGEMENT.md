# Discord Command Management Guide

This guide explains how to manage Discord slash commands for the bot, including syncing, clearing, and troubleshooting command registration issues.

## Understanding Discord Slash Commands

Discord slash commands are registered with Discord's API and appear when users type `/` in the chat. Unlike traditional text commands that start with a prefix (like `!`), slash commands:

- Offer parameter auto-completion
- Provide a user-friendly interface
- Can be seen in the Discord command menu
- Require registration with Discord's API

## Command Syncing

When you add, modify, or remove slash commands in your code, you need to sync these changes with Discord. The bot provides several methods to do this:

### Global Command Syncing

Global commands are available in all servers where the bot is present. They take up to an hour to propagate across all servers.

To sync global commands:
```
!sync_commands
```

This command is restricted to bot owners and will sync all slash commands to Discord globally.

### Guild-Specific Command Syncing

Guild (server) commands are immediately available but only in the specific server where you run the sync command.

To sync commands to the current server only:
```
!sync_guild
```

This is useful for testing new commands quickly without waiting for global propagation.

## Clearing Commands

If you need to remove all slash commands (for example, to fix duplication issues), you can use:

```
!clear_commands_prefix
```

or the slash command version:

```
/clear_commands
```

Both commands will ask for confirmation before proceeding, as this action removes all slash commands from all servers.

## Automatic Command Management

The bot includes automated command management:

1. **On Startup**: By default, the bot does not automatically sync commands on startup to prevent accidental duplication. The log message "Skipping command sync on startup" indicates this behavior.

2. **Refresh Script**: To completely refresh commands (clear and re-sync), you can run:
   ```
   python refresh_commands.py
   ```
   This script will clear all existing commands and then re-register them.

3. **Sync Script**: To only sync commands without clearing, run:
   ```
   python sync_commands.py
   ```

## Common Command Issues

### Duplicate Commands

If you see duplicate commands in your server (multiple versions of the same command), this is usually caused by:

1. Having both global and guild-specific versions registered
2. Syncing commands multiple times with different code versions

To fix duplicates:
1. Run `!clear_commands_prefix` to remove all commands
2. Run `!sync_commands` to register a clean set of commands

### Commands Not Appearing

If slash commands don't appear when typing `/`:

1. **Permission Issues**: Ensure the bot has the `applications.commands` scope
2. **Propagation Delay**: Global commands can take up to an hour to appear
3. **Cache Issues**: Discord client sometimes needs a restart to see new commands
4. **Registration Failure**: Check bot logs for any errors during command sync

### Command Errors

If commands appear but return errors when used:

1. **Code Mismatch**: The registered command doesn't match the current code implementation
2. **Parameter Issues**: The command is being called with incorrect parameters
3. **Permission Problems**: The bot lacks necessary permissions in the channel

## Maintaining Command Documentation

When adding or modifying commands, remember to update:
- `BOT_COMMAND_REFERENCE.md`: The main command reference
- Feature-specific documentation (e.g., `AI_COMMANDS.md` or `MUSIC_COMMANDS.md`)

## Dual Command System

This bot uses a dual command system that supports both slash commands (`/command`) and prefix commands (`!command`). When adding new features:

1. Implement both command versions for maximum compatibility
2. Use helper methods to avoid code duplication 
3. Sync slash commands after adding new features

## Monitoring Command Status

To check the current status of command registration, you can:

1. View the slash command menu in Discord
2. Check the bot's startup logs for command sync information
3. View the command refresh status file at `data/command_refresh_status.json`

This status file shows the last command sync operation and its result.