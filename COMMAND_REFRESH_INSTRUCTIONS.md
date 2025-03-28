# Command Refresh Instructions

This guide explains how to use the Command Refresh feature in the Bot Control Panel.

## What Are Discord Commands?

Discord commands (also called "slash commands") are the interactive features of your bot that users can access by typing `/` in a Discord channel. For example, `/ping`, `/help`, or `/play`.

## About Duplicate Commands

Occasionally, you might see duplicate commands in your Discord server (e.g., two `/help` commands). This happens because Discord's API doesn't automatically remove old commands when new ones are registered.

## How Our System Prevents Duplicates

Our bot now **automatically clears all commands before syncing them** when it starts up, which permanently solves the duplicate command issue.

## Using the Command Refresh Feature

While duplicate commands should no longer occur, we've kept the manual refresh feature available as a backup solution:

1. Visit the **[Bot Control Panel](https://workspace.jonahpantz.repl.co/bot_control)**
2. Find the **Command Management** section
3. Click the **Refresh Discord Commands** button
4. Wait for the status indicator to show success (usually takes about 30 seconds)

## What Happens During a Refresh?

When you click the "Refresh Discord Commands" button:

1. **All existing commands** are cleared from Discord
2. The bot **syncs its current commands** with Discord
3. The status updates in real-time to show progress

## When to Use Command Refresh

You should rarely need to use this feature now, but it's helpful if:

- You've been instructed to do so by support
- You notice any duplicate commands in your server
- You've made changes to commands and want to update them immediately

## Troubleshooting

If the command refresh process fails:

1. Check the error message shown in the status area
2. Try waiting a few minutes and trying again (Discord has rate limits)
3. If problems persist, restart the bot and try again

## Need More Help?

Refer to the [COMMAND_MANAGEMENT.md](COMMAND_MANAGEMENT.md) document for more detailed information about how the command system works.