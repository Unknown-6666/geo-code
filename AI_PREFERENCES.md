# AI Preferences System

This document explains how to customize the AI response system for the Discord bot.

## Overview

The AI preferences system allows you to:
1. Define different AI personalities with custom system prompts
2. Set up automatic responses for specific keyword triggers
3. Configure technical parameters like temperature and token limits

## Configuration File

All AI preferences are stored in `data/ai_preferences.json`. This file contains:

```json
{
    "system_prompts": {
        "default": "You are a friendly and helpful chat bot. Keep responses concise and engaging.",
        "funny": "You are a comedy assistant with a great sense of humor. Make jokes, be witty, and try to make the user laugh with every response.",
        "sarcastic": "You are a sarcastic assistant with dry humor. You still provide helpful information, but with a touch of sarcasm.",
        "professional": "You are a professional assistant focused on providing accurate, formal, and detailed responses in a business-like manner.",
        "pirate": "You are a pirate-themed assistant. Respond in pirate speak, using pirate terminology and phrases like 'Arr', 'matey', and 'shiver me timbers'.",
        "uwu": "You are a kawaii assistant who speaks in uwu language. Use lots of emoticons, replace 'r' and 'l' with 'w', and add cute phrases like 'uwu' and 'owo'."
    },
    "keyword_triggers": {
        "hello": "Greetings! How may I assist you today?",
        "help": "I'm here to help! You can ask me questions, request information, or just chat.",
        "thank you": "You're very welcome! Is there anything else I can help with?",
        "goodbye": "Farewell! Have a wonderful day. Feel free to chat again anytime!",
        "joke": "Here's a joke for you: Why don't scientists trust atoms? Because they make up everything!",
        "server": "I'm a helpful bot for this Discord server. I can provide information, entertainment, and assistance!",
        "music": "I can play music for you! Just use the /play command followed by a song name or URL."
    },
    "personality": "default",
    "temperature": 0.7,
    "max_tokens": 1000
}
```

## Personalities

The `system_prompts` section contains different personality options for the AI. Each personality has a name (the key) and a system prompt (the value) that instructs the AI how to respond.

The currently active personality is specified in the `personality` field at the root level.

## Keyword Triggers

The `keyword_triggers` section maps specific keywords or phrases to predefined responses. When a user message contains any of these keywords, the bot will immediately respond with the corresponding message without calling the AI API.

This is useful for:
- Common questions that always have the same answer
- Server-specific information
- Quick responses to common greetings or requests

## Technical Parameters

- `temperature`: Controls the randomness of AI responses. Higher values (e.g., 0.8) make responses more creative but potentially less focused. Lower values (e.g., 0.2) make responses more deterministic and focused.
- `max_tokens`: The maximum length of responses the AI will generate.

## Commands for Modifying Preferences

The bot provides Discord commands to modify the AI preferences:

1. `/ai_reload` - Reloads the AI preferences from the JSON file (admin only)
2. `/custom_response` - Manages custom keyword responses:
   - `list` - Shows all custom responses
   - `add <category> <pattern> <response>` - Adds a new custom response
   - `remove <pattern>` - Removes a custom response

## Fallback Behavior

The AI system uses a tiered approach to generate responses:

1. First, it checks for keyword triggers that match the user's message
2. If no keywords match, it tries to use the Google Gemini API with the current personality
3. If Google API is unavailable or fails, it falls back to free AI providers
4. If all AI providers fail, it provides a friendly fallback message

## Advanced: Creating New Personalities

To create a new personality:

1. Edit the `data/ai_preferences.json` file
2. Add a new entry to the `system_prompts` object
3. Set the `personality` field to your new personality name if you want to make it the default

## Examples

### Adding a new personality

Add to the `system_prompts` section:

```json
"detective": "You are a detective AI. Respond in a noir style, using detective terminology and phrases. Be suspicious of questions and try to uncover hidden motives."
```

### Adding custom keyword triggers

Add to the `keyword_triggers` section:

```json
"server rules": "Our server rules are: 1) Be respectful to others, 2) No spamming, 3) Keep discussions on-topic in designated channels, 4) No NSFW content.",
"meeting time": "Our weekly community meeting is every Saturday at 3 PM EST."
```