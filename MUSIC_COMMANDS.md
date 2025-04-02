# Music Commands

This Discord bot supports both slash commands (`/command`) and traditional prefix commands (`!command`). Use whichever style you prefer!

## Basic Music Controls

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/join` | `!join` | Join your current voice channel |
| `/leave` | `!leave` | Leave the voice channel |
| `/play <query>` | `!play <query>` | Play a song from YouTube, SoundCloud, or Spotify |
| `/pause` | `!pause` | Pause the current playback |
| `/resume` | `!resume` | Resume paused playback |
| `/stop` | `!stop` | Stop playing and clear the queue |
| `/skip` | `!skip` | Skip to the next song in the queue |
| `/volume <0-100>` | `!volume <0-100>` | Set the playback volume |

## Queue Management

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/queue` | `!queue` | Show the current music queue |
| `/clear` | `!clear` | Clear the music queue |
| `/shuffle` | `!shuffle` | Shuffle the music queue |
| `/remove <position>` | `!remove <position>` | Remove a specific song from the queue |
| `/skipto <position>` | `!skipto <position>` | Skip to a specific position in the queue |

## Song Information

| Slash Command | Prefix Command | Description |
|--------------|---------------|-------------|
| `/nowplaying` | `!nowplaying` | Display information about the current song |
| `/search <query> <platform>` | `!search <query>` | Search for music on YouTube or SoundCloud |

## Tips for Using Music Commands

### Playing Music

The bot supports various music sources:
1. **YouTube**: Just use the song name or YouTube URL
   ```
   !play despacito
   !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

2. **SoundCloud**: Prefix your search with "soundcloud:" or use a SoundCloud URL
   ```
   !play soundcloud: chill beats
   !play https://soundcloud.com/artist/track
   ```

3. **Spotify**: Use a Spotify track URL
   ```
   !play https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
   ```

### Playlist Management

* Check the current queue with `!queue` or `/queue`
* Remove specific songs with `!remove 3` (removes the 3rd song from queue)
* Skip to a specific song with `!skipto 5` (jumps to the 5th song)
* Clear the entire queue with `!clear` or `/clear`

### Volume Control

* The default volume is 50%
* Set the volume with `!volume 75` for 75% volume
* Keep volume reasonable (below 100%) to avoid distortion

### Common Issues

* **Bot not joining**: Make sure you're in a voice channel before using `!join`
* **No sound**: Check if the bot has permission to speak in the channel
* **Song not playing**: Check if the URL is valid or try a different search term
* **Lag or stuttering**: Try lowering the volume or using a different voice channel

### Voice Channel Rules

* The bot will automatically leave if left alone in a voice channel
* Only server members with appropriate permissions can use the `!stop`, `!skip`, and `!volume` commands to affect everyone's experience
* Anyone can use `!play` to add songs to the queue