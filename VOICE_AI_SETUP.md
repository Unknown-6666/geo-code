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

### General Issues
1. **Package Installation**
   - Verify that all required packages are installed correctly:
     ```
     pip show gtts speechrecognition
     ```
   - If any package is missing, reinstall it:
     ```
     pip install --force-reinstall gtts SpeechRecognition
     ```

2. **Discord Permissions**
   - Ensure the bot has the following permissions in your server:
     - Connect (to join voice channels)
     - Speak (to send audio to the voice channel)
     - Use Voice Activity (to detect speech)
   - Check these permissions in your Discord server settings → Roles

3. **FFmpeg Installation**
   - Verify FFmpeg is installed and accessible:
     ```
     ffmpeg -version
     ```
   - If FFmpeg is not installed, install it using your system's package manager:
     - For Debian/Ubuntu: `apt-get install ffmpeg`
     - For CentOS/RHEL: `yum install ffmpeg`
     - For macOS: `brew install ffmpeg`

### Text-to-Speech Issues
1. **No Voice Output**
   - Check if the bot is actually in the voice channel
   - Verify your client's volume settings for the bot
   - Check the bot's logs for gTTS errors
   - Try sending a simple, short message first to test

2. **Distorted Audio**
   - This can happen with very long text responses
   - Try sending shorter messages
   - Check if your internet connection is stable

### Voice Recognition Issues
1. **Bot Not Responding to Voice**
   - Make sure you're using the `!listen` command after joining
   - Speak clearly and at a reasonable volume
   - Check if your microphone is working properly
   - Check if Discord has permission to access your microphone

2. **Frequent Misunderstandings**
   - Speak more slowly and clearly
   - Reduce background noise in your environment
   - Use a headset or dedicated microphone instead of built-in mic
   - Keep messages short and use simple language

### Advanced Troubleshooting
1. **Check Bot Logs**
   - Look for specific error messages in the console
   - Common errors include:
     - "FFmpeg not found" - Install FFmpeg
     - "Could not request results from Speech Recognition service" - Check internet connection
     - "Unable to connect to voice channel" - Check Discord permissions

2. **Debug Mode**
   - Enable more verbose logging by adding this at the top of the bot.py file:
     ```python
     logging.basicConfig(level=logging.DEBUG)
     ```
   - Restart the bot and check for more detailed error messages

3. **Internet Connection Issues**
   - Both gTTS and Google's speech recognition require internet access
   - Check if your bot's host has a stable internet connection
   - Some networks might block access to Google's services

## Notes

- The bot can only respond to one voice channel per server at a time
- Users need to be in the same voice channel as the bot for it to respond to their messages
- The bot will automatically leave the voice channel if no one is using it for an extended period