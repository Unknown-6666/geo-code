# AI-Powered Discord Bot Features

This document outlines the AI-powered moderation and enhancement features available in your Discord bot.

## AI Moderation Features

### Content Filtering

The bot can automatically detect and filter inappropriate content:
- Analyzes message content for toxicity, hate speech, and other policy violations
- Automatically removes messages that exceed toxicity thresholds
- Sends warnings to users who post inappropriate content
- Logs moderation actions to designated channels

**Commands:**
- `/moderateai enable|disable content_filtering` - Enable or disable content filtering
- `/setthreshold toxicity 0.7` - Set toxicity threshold (0.0-1.0)
- `/analyzetext <text>` - Manually analyze text for toxicity

### Spam Detection

Identifies and filters spam messages in real-time:
- Detects message repetition patterns
- Identifies excessive caps, mentions, and links
- Removes spam messages automatically
- Warns users who post spam

**Commands:**
- `/moderateai enable|disable spam_detection` - Enable or disable spam detection
- `/setthreshold spam 0.7` - Set spam detection threshold (0.0-1.0)

### Toxicity Analysis

Measures the toxicity level of conversations:
- Analyzes messages for toxicity scores
- Categorizes content as none, mild, moderate, or severe
- Takes appropriate action based on severity
- Provides detailed analysis in mod logs

**Commands:**
- `/moderateai enable|disable toxicity_analysis` - Enable or disable toxicity analysis
- `/analyzetext <text>` - Analyze text for toxicity levels

### Raid Protection

Detects unusual patterns of new users joining:
- Monitors join rates to identify potential raids
- Alerts moderators when unusual activity is detected
- Provides information about recent joins
- Helps prevent coordinated attacks

**Commands:**
- `/moderateai enable|disable raid_protection` - Enable or disable raid protection

## AI Enhancement Features

### Conversation Summarization

Provides summaries of long discussions:
- Automatically offers summaries when conversation reaches trigger count
- Groups related messages by topic
- Creates concise, informative summaries
- Makes catching up on missed conversations easier

**Commands:**
- `/summarize` - Generate a summary of recent conversation in the channel
- `/enablesummarization enable|disable [channel]` - Enable or disable automatic summarization

### Smart Responses

Automatically answers frequently asked questions:
- Responds to common questions without moderator intervention
- Customizable responses for server-specific questions
- Reduces repetitive answering by moderators
- Improves server member experience

**Commands:**
- `/enablesmartresponses enable|disable [channel]` - Enable or disable smart responses
- `/addsmartresponse <question> <response>` - Add a new smart response
- `/removesmartresponse <question>` - Remove a smart response
- `/listsmartresponses` - List all configured smart responses

### Content Moderation for Images and Links

Scans shared media and links for inappropriate content:
- Analyzes images for inappropriate content
- Checks links for safety and summarizes linked content
- Blocks malicious or inappropriate links
- Maintains whitelist and blocklist for domains

**Commands:**
- `/enableimagemod enable|disable [threshold]` - Enable or disable image moderation
- `/enablelinkanalysis enable|disable` - Enable or disable link analysis
- `/managelinkfilter add|remove|list blocklist|whitelist [domain]` - Manage domain filtering
- `/analyzeimage <image_url>` - Analyze an image for inappropriate content
- `/analyzelink <url>` - Analyze and summarize a link

## Setup Instructions

1. First, ensure you have the necessary API keys:
   - For Vertex AI (primary provider), set the following environment variables:
     - `GOOGLE_CLOUD_PROJECT` - Your Google Cloud project ID
     - `VERTEX_LOCATION` - The Vertex AI location (e.g., "us-central1")
     - `GOOGLE_CREDENTIALS` - Your Google Cloud service account JSON
   - For Google Gemini (fallback provider), set `GOOGLE_AI_API_KEY` environment variable
   - The bot uses a multi-tier AI system for maximum reliability:
     1. Vertex AI SDK (primary)
     2. Vertex AI REST API (first fallback)
     3. Google Gemini (second fallback)
     4. Basic pattern matching (final fallback)

2. Enable features for your server:
   - Use the `/moderateai` command to enable features server-wide
   - Configure individual features with their respective commands
   - Set appropriate thresholds with `/setthreshold`

3. Set up logging:
   - Create a channel named `mod-logs` or `logs` for moderation notifications
   - The bot will automatically log moderation actions there

## Best Practices

- Start with higher thresholds (0.7-0.8) and adjust based on your server's needs
- Enable one feature at a time to test its impact
- Use the analysis commands to test detection before enabling automatic moderation
- Regularly review moderation logs to ensure appropriate actions
- Customize smart responses to match your community's frequently asked questions

## Troubleshooting

- If the bot doesn't respond to moderation commands, ensure it has proper permissions
- If content isn't being filtered properly, try adjusting thresholds
- For image analysis issues, ensure the bot has access to view attachments
- If link analysis is slow, consider adding common domains to the whitelist

### Vertex AI Integration Troubleshooting

- Use the `/testvertex` command to check your Vertex AI configuration status
- If Vertex AI isn't connecting:
  - Verify your Google Cloud credentials are correctly formatted JSON
  - Check that your project ID and location are correct
  - Ensure your service account has the necessary Vertex AI permissions
- If you see authentication errors:
  - Make sure your service account has the "Vertex AI User" role
  - Verify that the Vertex AI API is enabled in your Google Cloud project
- If PyJWT errors occur:
  - The bot includes a fallback to use the direct REST API instead
  - No action is required as fallback is automatic