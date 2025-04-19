# Google Vertex AI Setup Guide

This guide will help you set up Google Vertex AI as the primary AI provider for your Discord bot. Vertex AI provides high-quality AI models that offer advanced capabilities for all bot features.

## Prerequisites

Before you begin, you'll need:

1. A Google Cloud Platform account
2. A Google Cloud project with the Vertex AI API enabled
3. A service account with appropriate permissions for Vertex AI

## Setup Process

### 1. Create a Google Cloud Project (if you don't have one)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project"
3. Enter a project name and click "Create"
4. Note your Project ID, you'll need it later

### 2. Enable the Vertex AI API

1. Go to the [API Library](https://console.cloud.google.com/apis/library)
2. Search for "Vertex AI API"
3. Click on "Vertex AI API" 
4. Click "Enable"

### 3. Create a Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter a service account name (e.g., "discord-bot-vertex-ai")
4. For the role, select "Vertex AI User" (roles/aiplatform.user)
5. Click "Done"

### 4. Create a Service Account Key

1. Find your service account in the list
2. Click on the three dots in the "Actions" column
3. Select "Manage Keys"
4. Click "Add Key" > "Create new key"
5. Select JSON format
6. Click "Create"
7. Save the downloaded JSON file securely

### 5. Configure Environment Variables for Your Bot

There are two main options for configuring your bot to use Vertex AI:

#### Option 1: Set environment variables in your hosting environment

Set the following environment variables:

```
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json  
GOOGLE_CLOUD_PROJECT=your-project-id
VERTEX_LOCATION=us-central1
USE_VERTEX_AI=true
```

#### Option 2: Use Replit Secrets

If you're hosting on Replit, you can set these as secrets:

1. Go to your Repl's "Secrets" tab
2. Create the following secrets:
   - `GOOGLE_CREDENTIALS`: Copy the entire content of your JSON credentials file
   - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
   - `VERTEX_LOCATION`: The GCP region to use (e.g., "us-central1")
   - `USE_VERTEX_AI`: Set to "true"

## Implementation Details

The bot has been designed with a tiered AI system prioritizing Vertex AI:

1. First tries Vertex AI standard client (primary provider)
2. Falls back to Vertex AI REST API client if standard client fails
3. Falls back to Google Gemini AI (if API key is available)
4. Finally falls back to G4F library or basic analysis as a last resort

## Troubleshooting

If you encounter issues with Vertex AI:

1. Run the `/testvertex` command in your Discord server (Admin only)
2. Check the bot logs for detailed error messages
3. Verify your credentials are correct and the service account has proper permissions
4. Ensure the Vertex AI API is enabled for your project

## Additional Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Python Client for Vertex AI](https://cloud.google.com/python/docs/reference/aiplatform/latest)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)

---

For more information on configuring other aspects of the bot, refer to the main documentation.