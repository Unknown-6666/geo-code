# Voice AI Commands Reference

This document provides a comprehensive list of all Voice AI commands available in the bot. These commands allow users to interact with the AI in voice channels, where the bot can join, listen to messages, and respond both in text and voice (when fully configured).

## Voice Channel Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `/voicechat` | `!voicechat`, `!vc` | Join your current voice channel and enable AI voice chat |
| `/voice_stop` | `!voice_stop`, `!vc_stop` | Disconnect from the voice channel and end the AI voice chat session |
| `/listen` | `!listen`, `!listen_start` | Start listening to the voice channel for speech to convert to text |
| `/listen_stop` | `!listen_stop`, `!stop_listen` | Stop listening to the voice channel |

## Command Details

### Join Voice Channel - `/voicechat`

**Slash Command:** `/voicechat`  
**Prefix Command:** `!voicechat` or `!vc`

**Description:**  
This command makes the bot join your current voice channel and enables AI voice chat. Once the bot has joined, it will listen for messages in the text channel where the command was used. When a message is detected, the bot will:

1. Process the message using the same AI system as the regular chat commands
2. Generate a text response
3. Convert that text to speech (when fully configured)
4. Play the voice response in the voice channel
5. Also send the text response in the text channel

**Requirements:**
- You must be in a voice channel to use this command
- The bot needs permission to connect to and speak in voice channels
- For full functionality with voice output, the bot needs the gtts package installed

**Example:**
```
!voicechat
```

### Stop Voice Chat - `/voice_stop`

**Slash Command:** `/voice_stop`  
**Prefix Command:** `!voice_stop` or `!vc_stop`

**Description:**  
This command disconnects the bot from the voice channel and ends the AI voice chat session. The bot will:

1. Stop any currently playing audio
2. Disconnect from the voice channel
3. End all active voice AI sessions in the server

**Example:**
```
!vc_stop
```

### Start Voice Recognition - `/listen`

**Slash Command:** `/listen`  
**Prefix Command:** `!listen` or `!listen_start`

**Description:**  
This command makes the bot start actively listening to the voice channel and responding to voice messages. It will:

1. Begin capturing audio from the voice channel
2. Convert spoken words to text using speech recognition
3. Process the recognized text with the AI system
4. Generate and play voice responses
5. Also send text responses in the text channel

**Requirements:**
- The bot must already be in your voice channel (via `/voicechat`)
- You must be in the same voice channel as the bot
- The speech recognition package must be installed for this to work

**Example:**
```
!listen
```

### Stop Voice Recognition - `/listen_stop`

**Slash Command:** `/listen_stop`  
**Prefix Command:** `!listen_stop` or `!stop_listen`

**Description:**  
This command makes the bot stop listening to voice in the channel. The bot will:

1. Stop capturing audio from the voice channel
2. Stop processing voice recognition
3. Still remain in the voice channel
4. Continue to respond to text messages with voice

**Example:**
```
!stop_listen
```

## Interacting with the Voice AI

Once the bot has joined your voice channel with the `/voicechat` command, you can interact with it by typing messages in the text channel where you used the command. 

The bot will treat these messages as conversation prompts and respond to them both in text and voice (when fully configured). The conversation works just like normal AI chat, but with the added benefit of voice responses.

**Example Interaction:**
```
User: What's the weather like?
Bot: [Responds in voice and text with a message about not having real-time weather data]

User: Tell me a joke
Bot: [Responds in voice and text with a joke]
```

## Notes and Limitations

1. **Limited Mode**: If the bot doesn't have the required text-to-speech packages installed, it will operate in "Limited Mode" where it can only respond with text messages.

2. **One Voice Channel Per Server**: The bot can only be in one voice channel per server at a time. If you use the `/voicechat` command while the bot is already in another channel, it will move to your channel.

3. **Permission Requirements**: The bot needs "Connect" and "Speak" permissions in the voice channel.

4. **Automatic Disconnection**: The bot will automatically leave the voice channel if no one uses it for an extended period.

5. **Command Filtering**: The bot will not respond to commands via voice. If you use a command while the bot is in a voice channel, it will process the command normally without giving a voice response.

## Troubleshooting

If you encounter issues with the Voice AI:

1. **Joining Voice Channels**
   - Make sure you're in a voice channel before using `/voicechat` or `!vc`
   - Check that the bot has "Connect" and "Speak" permissions in the voice channel
   - If the bot fails to join, try having it disconnect from any other voice channels first with `/voice_stop`

2. **Text-to-Speech Issues**
   - If the bot joins but doesn't respond with voice, it may be in Limited Mode due to missing dependencies
   - Verify that the `gtts` package is properly installed 
   - Check the bot logs for any errors related to TTS generation
   - The bot will fall back to text-only responses if TTS fails

3. **Voice Recognition Issues**
   - The `!listen` command requires both `SpeechRecognition` and a working internet connection as it uses Google's speech recognition service
   - Speak clearly and at a normal volume - background noise can interfere with recognition
   - Keep sentences relatively short and simple for better recognition accuracy
   - The bot will show an error message if speech recognition fails

4. **Advanced Troubleshooting**
   - Check for errors in the bot's console log
   - Restart the bot if voice features stop working unexpectedly
   - The bot requires `ffmpeg` to be installed for audio processing
   - Make sure your Discord client has proper access to your microphone
   - Try using headphones to prevent audio feedback loops

5. **For Bot Administrators**
   - For full voice functionality, ensure the following packages are installed:
     * `discord.py[voice]` - For Discord voice connections
     * `gtts` - For text-to-speech generation
     * `SpeechRecognition` - For voice recognition
     * `ffmpeg` - For audio processing
   - Refer to the VOICE_AI_SETUP.md file for complete setup instructions