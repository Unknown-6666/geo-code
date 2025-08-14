# Discord Bot with Web Dashboard

## Overview
A sophisticated Discord bot platform with advanced AI-powered community management capabilities, focusing on intelligent conversation analysis and user interaction enhancement.

## Key Technologies
- Discord.py framework
- Flask web dashboard with OAuth2 authentication
- PostgreSQL database with SQLAlchemy ORM
- Multi-AI model integration (Gemini, PaLM, G4F fallback)
- Advanced AI-driven conversation summarization
- Intelligent moderation and content analysis tools
- Dynamic conversation insights generation
- Economy system with shop, gambling, and user management
- Fun commands with advanced permission management

## Project Architecture

### Main Components
1. **Discord Bot** (`bot.py`) - Core Discord bot with cog-based architecture
2. **Web Dashboard** (`dashboard/app.py`) - Flask web interface for bot management
3. **Database Models** (`models/`) - SQLAlchemy models for user data and economy
4. **Main Application** (`main.py`) - Orchestrates both bot and web services
5. **Configuration** (`config.py`) - Bot settings and API keys

### Cogs Structure
- `cogs.basic_commands` - Basic bot commands (ping, help, info)
- `cogs.member_events` - User join/leave event handling
- `cogs.memes` - Meme generation and sharing
- `cogs.fun_commands` - Entertainment commands (jog, spam, mock)
- `cogs.ai_chat` - AI-powered chat responses
- `cogs.voice_ai` - Voice AI chat capabilities
- `cogs.ai_conversation` - Conversation analysis and summarization
- `cogs.ai_content_analysis` - Image and link analysis
- `cogs.economy` - Virtual economy system
- `cogs.moderation` - Moderation tools
- `cogs.profanity_filter` - Content filtering
- `cogs.rules_enforcer` - Rule enforcement

### Database Schema
- `UserEconomy` - User wallet, bank, and transaction history
- `Item` - Shop items with prices and descriptions
- `Inventory` - User item ownership tracking
- `Transaction` - Financial transaction logging
- `User` - Discord user authentication for web dashboard
- `Conversation` - Chat history and analysis data

## Current Issues Being Fixed

### 1. Database Connection Issues
- **Problem**: Neon PostgreSQL endpoint is disabled, causing connection failures
- **Fix**: Implementing automatic fallback to local PostgreSQL or SQLite
- **Status**: In Progress

### 2. Duplicate Slash Commands
- **Problem**: Multiple bot instances causing command duplication
- **Fix**: Implemented lockfile system and instance detection
- **Status**: Implemented - prevents multiple bot instances

### 3. Async Context Manager Errors
- **Problem**: Flask routes trying to use Discord.py async methods incorrectly
- **Fix**: Proper async context handling for message history API
- **Status**: Identified - needs async route implementation

### 4. Missing Import Errors
- **Problem**: Missing time module import in main.py
- **Fix**: Added proper imports
- **Status**: Fixed

## Recent Changes
- 2025-08-14: Fixed bot instance duplication with lockfile system
- 2025-08-14: Added command sync throttling (30-minute intervals)
- 2025-08-14: Enhanced error handling for database fallbacks
- 2025-08-14: Improved process detection to prevent multiple bot instances

## User Preferences
- Non-technical communication style
- Fix all bugs comprehensively before completing tasks
- Ensure single bot instance operation
- Maintain robust error handling and fallbacks

## Environment Variables Required
- `DISCORD_TOKEN` - Discord bot token
- `DISCORD_CLIENT_ID` - Discord OAuth2 client ID  
- `DISCORD_CLIENT_SECRET` - Discord OAuth2 client secret
- `GOOGLE_AI_API_KEY` - Google AI API key (optional, falls back to G4F)
- `DATABASE_URL` - PostgreSQL database URL
- `SESSION_SECRET` - Flask session secret key
- `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, `PGDATABASE` - Local PostgreSQL credentials

## Deployment
- Uses Gunicorn for production Flask deployment
- Runs Discord bot in separate thread
- Automatic database migration and setup
- Health checks and graceful shutdown handling

## Development Notes
- Economy system uses indexed database queries for performance
- AI responses have multiple fallback options
- Command syncing is throttled to prevent Discord rate limiting
- Web dashboard provides real-time bot monitoring
- All sensitive operations require proper authentication