# Deployment Instructions for c00lkidd Discord Bot

## Prerequisites

1. Make sure you have set up all required secrets in the Replit Secrets tab:
   - `DISCORD_TOKEN` - Your Discord bot token (required)
   - `GOOGLE_AI_API_KEY` - Google AI API key for Gemini (optional, g4f will be used as fallback)
   - `DATABASE_URL` - Database connection string (optional, will use Replit Database if not provided)

## Deployment Steps

### 1. Prepare for Deployment

Before deploying, make sure to:

1. Test your bot locally by running the "Start application" workflow
2. Ensure all commands are working correctly
3. Check that the AI chat, economy, and other features are functioning

### 2. Deploy to Replit

1. Click on the Deploy button in the Replit interface (found at the top of the screen)
2. Wait for the deployment process to complete - Replit will handle the deployment automatically

### 3. Verify Deployment

After deployment, verify that:

1. The bot is online in your Discord server
2. Commands are registered and working
3. The web dashboard is accessible

### 4. Troubleshooting

If you encounter issues:

1. Check the logs in the deployment tab for errors
2. Verify all required secrets are properly set
3. If the bot fails to start:
   - Try running the sync commands script manually with `python sync_commands.py`
   - Check the database status from the dashboard
   - Restart the deployment
4. If you're having dependency resolution issues:
   - See the `DEPLOYMENT_FIX.md` file for information about optional dependencies
   - The `google-cloud-aiplatform` package is now optional and not included in default requirements
   - The bot will automatically use g4f fallback for AI responses

## Deployment Configuration

The deployment uses:
- Gunicorn to serve the web dashboard
- A separate thread for running the Discord bot
- Automatic error handling and restart mechanisms
- Fallback for AI features when no API key is available

Both the web dashboard and Discord bot will be deployed and run together.
