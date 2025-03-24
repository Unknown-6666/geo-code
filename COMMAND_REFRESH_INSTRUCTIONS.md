# Discord Bot Command Refresh Utility

This utility helps prevent duplicate commands in your Discord servers by refreshing the bot's slash commands.

## When to use this utility

Run the command refresh utility when:
- You notice duplicate slash commands in your Discord servers
- You've added new commands and want to make sure they're properly registered
- You've removed commands but they still appear in Discord
- After making changes to command descriptions or parameters

## How to refresh commands

### Method 1: Using the Web Dashboard (For Bot Owners Only)

1. Log in to the bot's web dashboard
2. Navigate to the Dashboard page
3. Find the "Bot Owner Controls" section
4. Click the "Refresh Commands" button
5. Wait for the success message

### Method 2: Using the command-line script

Run the following command in the terminal:

```bash
python refresh_commands.py
```

This will:
1. Clear all existing slash commands registered with Discord
2. Re-sync all commands defined in the bot's code
3. Show progress and result information

#### Options

- Add `-y` or `--yes` to skip the confirmation prompt:
  ```bash
  python refresh_commands.py --yes
  ```

## Manually refreshing commands in Discord

If you prefer to use Discord itself, bot owners can also use these commands:

- `!sync` - Sync all commands globally across all servers
- `!sync_guild` - Sync commands only for the current server
- `!clear_commands` - Clear all slash commands (requires confirmation)

## Rate Limits and Best Practices

Discord enforces rate limits on command updates to prevent abuse of their API:

1. **Avoid Frequent Refreshes**: Do not refresh commands more than once every 10-15 minutes
2. **Schedule Updates**: Plan command changes during low-usage times
3. **Batch Changes**: Make multiple command changes at once, then refresh once
4. **Expect Delays**: Global commands can take up to an hour to fully propagate to all servers

If you see a "Rate Limited" message, wait at least 15 minutes before trying again.

## Troubleshooting

If command refresh doesn't solve the issue:
1. Check the bot's logs for any errors
2. Make sure the bot has the proper permissions in Discord
3. Try using the Discord Developer Portal to manually view and manage commands
4. Wait at least one hour - Discord can take time to update commands globally

For persistent issues, try kicking and reinviting the bot to your server. As a last resort, you can use the Discord Developer Portal to manually delete commands.