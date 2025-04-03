# Voice AI Setup

The Voice AI feature allows users to interact with the bot in voice channels, where the bot will respond verbally using text-to-speech technology. This document explains how to set up and use the Voice AI features.

## Required Dependencies

The Voice AI functionality requires several additional packages:

1. **gTTS (Google Text-to-Speech)**: Used to convert text responses to spoken audio
   ```
   pip install gtts
   ```

2. **SpeechRecognition**: Used for voice recognition (future functionality)
   ```
   pip install SpeechRecognition
   ```

3. **FFmpeg**: Required for audio processing and playback
   This is usually installed at the system level. Most environments will already have this installed.

## Current Status

The Voice AI functionality is now fully operational with both text-to-speech and speech recognition capabilities. The required packages have been installed, enabling:

- Full voice channel joining/leaving functionality
- Text messages converted to speech responses
- Voice recognition for spoken commands (using the `!listen` command)
- Two-way voice interaction in Discord voice channels

## Installation Instructions

To enable full Voice AI functionality, follow these steps:

1. Install the required Python packages:
   ```
   pip install gtts SpeechRecognition
   ```

2. Restart the bot to apply the changes

3. Verify the installation by using the `/voicechat` or `!voicechat` command and checking if the bot responds with voice

## Usage

### Commands

- `/voicechat` or `!voicechat` - Join your current voice channel and enable AI voice chat
- `/voice_stop` or `!voice_stop` - Disconnect from the voice channel and end the AI voice chat session
- `/listen` or `!listen` - Start listening to voice input in the voice channel
- `/listen_stop` or `!listen_stop` - Stop listening to voice input but remain in the channel

### How to Use

#### Text-to-Speech Mode:
1. Join a voice channel
2. Use the `/voicechat` command in a text channel
3. The bot will join your voice channel
4. Type messages in the text channel
5. The bot will respond to your messages both in text and voice
6. Use `/voice_stop` when you're done to disconnect the bot

#### Voice Recognition Mode:
1. Join a voice channel
2. Use the `/voicechat` command in a text channel to have the bot join
3. Use the `/listen` command to start voice recognition
4. Speak clearly in the voice channel
5. The bot will recognize your speech, process it through the AI, and respond with voice
6. Use `/listen_stop` to stop voice recognition
7. Use `/voice_stop` when you're done to disconnect the bot

## Troubleshooting

If you encounter issues with the Voice AI feature:

1. Check that the required packages are installed correctly
2. Ensure the bot has permission to connect to and speak in voice channels
3. Verify that FFmpeg is installed and accessible
4. Check the bot's logs for specific error messages

## Notes

- The bot can only respond to one voice channel per server at a time
- Users need to be in the same voice channel as the bot for it to respond to their messages
- The bot will automatically leave the voice channel if no one is using it for an extended period