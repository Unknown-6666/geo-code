# Vertex AI Integration Setup Guide

This guide will help you set up and configure Google's Vertex AI integration with the Discord bot. Vertex AI provides higher quality AI responses with more advanced capabilities than the default providers.

## Prerequisites

1. A Google Cloud Platform (GCP) account
2. A GCP project with billing enabled
3. Access to Vertex AI API

## Setup Steps

### 1. Create a Google Cloud Project

If you don't already have a GCP project:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "New Project" at the top right
3. Enter a project name and select a billing account
4. Click "Create"

### 2. Enable the Vertex AI API

1. In your GCP project, go to the [API Library](https://console.cloud.google.com/apis/library)
2. Search for "Vertex AI API"
3. Click on the result and then click "Enable"

### 3. Create a Service Account

1. Navigate to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter a name and description for your service account
4. Click "Create and Continue"
5. Assign the following roles:
   - "Vertex AI User"
   - "Storage Object Viewer" (Optional: only needed if accessing custom models)
6. Click "Continue" and then "Done"

### 4. Create and Download a Service Account Key

1. In the Service Accounts list, find the service account you just created
2. Click the three dots menu (⋮) at the end of the row
3. Select "Manage keys"
4. Click "Add Key" > "Create new key"
5. Choose "JSON" format
6. Click "Create"
7. The key file will be automatically downloaded to your computer

### 5. Configure Environment Variables

Add the following environment variables to your Discord bot:

```
GOOGLE_CREDENTIALS=<content of the JSON key file>
GOOGLE_CLOUD_PROJECT=<your Google Cloud project ID>
VERTEX_LOCATION=us-central1
USE_VERTEX_AI=true
VERTEX_AI_PRIORITY=1
```

Notes:
- For `GOOGLE_CREDENTIALS`, copy the entire content of the JSON key file including braces
- `VERTEX_LOCATION` should be a region where Vertex AI is available (e.g., "us-central1")
- `VERTEX_AI_PRIORITY` sets the priority order for AI providers (1=highest, 3=lowest)

### 6. Test Vertex AI Authentication

Run the test script to verify your Vertex AI setup:

```
python test_vertex_auth.py
```

If successful, you should see a confirmation message showing your project settings and a sample response from Vertex AI.

## Troubleshooting

### Common Issues

#### Authentication Errors

```
Error: google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

Solution: Make sure the `GOOGLE_CREDENTIALS` environment variable is set correctly with the complete JSON content.

#### API Not Enabled

```
Error: google.api_core.exceptions.PermissionDenied: 403 Vertex AI API has not been used in project X before or it is disabled
```

Solution: Go to the Google Cloud Console and ensure the Vertex AI API is enabled for your project.

#### Location Not Available

```
Error: google.api_core.exceptions.InvalidArgument: 400 Location 'X' is not supported for this method
```

Solution: Change `VERTEX_LOCATION` to a supported region like "us-central1" or "us-east1".

#### Permission Issues

```
Error: google.api_core.exceptions.PermissionDenied: 403 Permission 'aiplatform.models.predict' denied
```

Solution: Ensure your service account has the "Vertex AI User" role assigned.

## Usage Notes

- The bot will automatically use Vertex AI when properly configured with the highest priority.
- If Vertex AI encounters an error, the bot will fall back to Google Gemini AI.
- If both Vertex AI and Gemini fail, the bot will use G4F as a final fallback.
- You can monitor AI provider usage in the bot logs.

## Resource Management

Vertex AI usage incurs costs based on the number of tokens processed. To manage costs:

1. Set appropriate usage quotas in the Google Cloud Console
2. Consider setting up budget alerts
3. For free tier or limited usage, use the Gemini AI integration instead

## Model Configuration

The default configuration uses the latest text generation models. To change models:

1. Edit `utils/vertex_ai_client.py`
2. Modify the `VERTEX_AI_MODEL_NAME` constant for each model type

## Advanced Configuration

For advanced users, you can modify:

- System prompts (in `utils/ai_preference_manager.py`)
- Token limits (in `utils/vertex_ai_client.py`)
- Model parameters like temperature and top_k (in `utils/vertex_ai_client.py`)