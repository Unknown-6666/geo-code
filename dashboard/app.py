import os
import json
import logging
import asyncio
import datetime
import subprocess
import threading
import uuid
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from requests_oauthlib import OAuth2Session
from werkzeug.security import generate_password_hash, check_password_hash

# Discord.py imports for bot integration
import discord
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SESSION_SECRET', 'your-secret-key')

# Discord OAuth2 configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_API_BASE_URL = 'https://discord.com/api'
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

# Determine the correct redirect URI based on environment
if os.getenv('REPL_SLUG') and os.getenv('REPL_OWNER'):
    # For Replit, we need to use workspace.{owner}.repl.co format
    DISCORD_REDIRECT_URI = f'https://workspace.{os.getenv("REPL_OWNER")}.repl.co/callback'
    logger.info(f"Using Replit redirect URI: {DISCORD_REDIRECT_URI}")
else:
    DISCORD_REDIRECT_URI = 'http://localhost:5000/callback'
    logger.info("Using localhost redirect URI")

# Import db after app configuration
from database import db
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models after db initialization
from models.user import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def token_updater(token):
    session['oauth2_token'] = token

def make_discord_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=DISCORD_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=DISCORD_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
        },
        auto_refresh_url=DISCORD_TOKEN_URL,
        token_updater=token_updater
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    scope = ['identify', 'guilds']
    discord = make_discord_session(scope=scope)
    authorization_url, state = discord.authorization_url(DISCORD_AUTHORIZATION_BASE_URL)
    session['oauth2_state'] = state

    logger.debug(f"Login initiated. Redirect URI: {DISCORD_REDIRECT_URI}")
    logger.debug(f"Authorization URL: {authorization_url}")

    return redirect(authorization_url)

@app.route('/callback')
def callback():
    if request.values.get('error'):
        error_msg = request.values["error"]
        logger.error(f"OAuth error: {error_msg}")
        flash(f'Error: {error_msg}')
        return redirect(url_for('index'))

    try:
        discord = make_discord_session(state=session.get('oauth2_state'))
        logger.debug(f"Callback received. URL: {request.url}")

        token = discord.fetch_token(
            DISCORD_TOKEN_URL,
            client_secret=DISCORD_CLIENT_SECRET,
            authorization_response=request.url
        )
        session['oauth2_token'] = token

        discord = make_discord_session(token=token)
        user_data = discord.get(DISCORD_API_BASE_URL + '/users/@me').json()
        logger.debug(f"Received user data: {user_data}")

        # Get or create user
        user = User.query.filter_by(discord_id=user_data['id']).first()
        if not user:
            user = User(
                discord_id=user_data['id'],
                username=user_data['username'],
                avatar_url=f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get('avatar') else None
            )
            db.session.add(user)
            db.session.commit()
            logger.info(f"Created new user: {user.username}")

        login_user(user)
        logger.info(f"User {user.username} logged in successfully")
        return redirect(url_for('dashboard'))

    except Exception as e:
        logger.error(f"Error during callback: {str(e)}", exc_info=True)
        flash('An error occurred during login. Please try again.')
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    # No login required anymore
    return render_template('dashboard.html')

@app.route('/livebot')
def livebot():
    """LiveBot interface - View Discord from the bot's perspective"""
    return render_template('livebot.html')

@app.route('/bot_control')
def bot_control():
    """Public control panel for the bot"""
    from datetime import datetime
    return render_template('bot_control.html', current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
@app.route('/command_refresh_status', methods=['GET'])
def command_refresh_status():
    """Get the status of the most recent command refresh"""
    try:
        # Check if status file exists
        if not os.path.exists('data/command_refresh_status.json'):
            return jsonify({
                'status': 'unknown',
                'message': 'No command refresh history found',
                'timestamp': None
            })
        
        # Read the status file
        with open('data/command_refresh_status.json', 'r') as f:
            status_data = json.load(f)
            
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Error getting command refresh status: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving status: {str(e)}',
            'timestamp': datetime.datetime.now().isoformat()
        }), 500

@app.route('/refresh_commands', methods=['POST'])
def refresh_commands():
    """Handle the refresh commands request - No login required"""
    try:
        logger.info(f"Command refresh initiated from public interface")
        
        # Create a function to run the command sync in the background
        def run_command_sync():
            try:
                # Use the enhanced refresh_commands.py script instead
                # This ensures we're using the same logic for all refresh methods
                result = subprocess.run(['python', 'refresh_commands.py', '--yes'], 
                                      capture_output=True, text=True, timeout=45)
                
                logger.info(f"Command sync process completed with exit code {result.returncode}")
                if result.returncode != 0:
                    logger.error(f"Command sync failed: {result.stderr}")
                    # Update the status file with error information
                    with open('data/command_refresh_status.json', 'w') as f:
                        json.dump({
                            'status': 'error',
                            'message': 'Command refresh failed. See logs for details.',
                            'timestamp': datetime.datetime.now().isoformat(),
                            'output': result.stderr
                        }, f)
                else:
                    logger.info(f"Command sync successful")
                    # Update the status file with success information
                    with open('data/command_refresh_status.json', 'w') as f:
                        json.dump({
                            'status': 'success',
                            'message': 'Commands successfully cleared and refreshed.',
                            'timestamp': datetime.datetime.now().isoformat(),
                            'output': result.stdout
                        }, f)
                    
            except subprocess.TimeoutExpired:
                logger.error("Command sync process timed out after 45 seconds")
                # Update the status file with timeout information
                with open('data/command_refresh_status.json', 'w') as f:
                    json.dump({
                        'status': 'error',
                        'message': 'Command refresh timed out after 45 seconds.',
                        'timestamp': datetime.datetime.now().isoformat()
                    }, f)
            except Exception as e:
                logger.error(f"Error in command sync process: {str(e)}")
                # Update the status file with error information
                with open('data/command_refresh_status.json', 'w') as f:
                    json.dump({
                        'status': 'error',
                        'message': f'Error during command refresh: {str(e)}',
                        'timestamp': datetime.datetime.now().isoformat()
                    }, f)
        
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Update the status file with pending information
        with open('data/command_refresh_status.json', 'w') as f:
            json.dump({
                'status': 'pending',
                'message': 'Command refresh is in progress...',
                'timestamp': datetime.datetime.now().isoformat()
            }, f)
        
        # Start the subprocess in a separate thread to avoid blocking
        thread = threading.Thread(target=run_command_sync)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Commands refresh initiated. This may take a few seconds to complete.'
        })
        
    except Exception as e:
        logger.error(f"Error during command refresh: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500

# Get a reference to the bot instance from the main module
def get_bot():
    """Get the bot instance from the main module"""
    try:
        from main import discord_bot
        return discord_bot
    except (ImportError, AttributeError):
        logger.error("Could not import bot instance from main module")
        return None

# LiveBot API Endpoints
@app.route('/api/bot_info', methods=['GET'])
def api_bot_info():
    """Get information about the bot"""
    try:
        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Get the bot's user information
        user = bot.user
        return jsonify({
            'status': 'success',
            'username': user.name,
            'discriminator': user.discriminator if hasattr(user, 'discriminator') else None,
            'id': str(user.id),
            'avatar_url': user.avatar.url if user.avatar else None,
            'is_bot': user.bot
        })
    except Exception as e:
        logger.error(f"Error getting bot info: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting bot info: {str(e)}'
        }), 500

@app.route('/api/guilds', methods=['GET'])
def api_guilds():
    """Get a list of guilds the bot is in"""
    try:
        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        guilds = []
        for guild in bot.guilds:
            guilds.append({
                'id': str(guild.id),
                'name': guild.name,
                'member_count': guild.member_count,
                'icon_url': guild.icon.url if guild.icon else None,
                'owner_id': str(guild.owner_id) if guild.owner_id else None
            })

        return jsonify({
            'status': 'success',
            'guilds': guilds
        })
    except Exception as e:
        logger.error(f"Error getting guilds: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting guilds: {str(e)}'
        }), 500

@app.route('/api/channels', methods=['GET'])
def api_channels():
    """Get a list of channels in a guild"""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing guild_id parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Find the guild
        guild = bot.get_guild(int(guild_id))
        if not guild:
            return jsonify({
                'status': 'error',
                'message': f'Guild with ID {guild_id} not found'
            }), 404

        channels = []
        for channel in guild.channels:
            # Add only text channels and categories
            if channel.type in [discord.ChannelType.text, discord.ChannelType.category]:
                channels.append({
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': int(channel.type.value),
                    'position': channel.position,
                    'parent_id': str(channel.category_id) if hasattr(channel, 'category_id') and channel.category_id else None
                })

        return jsonify({
            'status': 'success',
            'channels': channels
        })
    except Exception as e:
        logger.error(f"Error getting channels: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting channels: {str(e)}'
        }), 500

@app.route('/api/channel_info', methods=['GET'])
def api_channel_info():
    """Get information about a channel"""
    try:
        channel_id = request.args.get('channel_id')
        if not channel_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing channel_id parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Find the channel
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return jsonify({
                'status': 'error',
                'message': f'Channel with ID {channel_id} not found'
            }), 404

        return jsonify({
            'status': 'success',
            'id': str(channel.id),
            'name': channel.name,
            'type': int(channel.type.value),
            'guild_id': str(channel.guild.id),
            'position': channel.position,
            'parent_id': str(channel.category_id) if hasattr(channel, 'category_id') and channel.category_id else None
        })
    except Exception as e:
        logger.error(f"Error getting channel info: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting channel info: {str(e)}'
        }), 500

@app.route('/api/messages', methods=['GET'])
def api_messages():
    """Get a list of messages in a channel"""
    try:
        channel_id = request.args.get('channel_id')
        if not channel_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing channel_id parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Find the channel
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return jsonify({
                'status': 'error',
                'message': f'Channel with ID {channel_id} not found'
            }), 404

        # Get the most recent messages (async function, need to run it in the bot's event loop)
        messages = []
        # Use run_until_complete with a new event loop if we need to
        try:
            # Warning: This can lead to unexpected behaviors if running in a different thread
            # Since the bot's event loop is already running, we'll create a new one for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Get recent messages (up to 50)
            # Handle the async generator directly instead of using flatten()
            history = channel.history(limit=50)
            message_objects = []
            
            # Collect messages
            async def collect_messages():
                async for message in history:
                    message_objects.append(message)
            
            loop.run_until_complete(collect_messages())
            loop.close()
            
            # Convert to serializable format
            for message in message_objects:
                messages.append({
                    'id': str(message.id),
                    'content': message.content,
                    'author': {
                        'id': str(message.author.id),
                        'username': message.author.name,
                        'discriminator': message.author.discriminator if hasattr(message.author, 'discriminator') else None,
                        'avatarUrl': message.author.avatar.url if message.author.avatar else None
                    },
                    'timestamp': message.created_at.isoformat(),
                    'edited_timestamp': message.edited_at.isoformat() if message.edited_at else None,
                    'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments],
                    'embeds': [{'title': embed.title, 'description': embed.description} for embed in message.embeds]
                })
        except Exception as inner_e:
            logger.error(f"Error getting message history: {str(inner_e)}", exc_info=True)
            # Provide a fallback response with empty messages to avoid breaking the UI
            messages = []

        return jsonify({
            'status': 'success',
            'messages': messages
        })
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting messages: {str(e)}'
        }), 500

@app.route('/api/members', methods=['GET'])
def api_members():
    """Get a list of members in a guild"""
    try:
        guild_id = request.args.get('guild_id')
        if not guild_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing guild_id parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Find the guild
        guild = bot.get_guild(int(guild_id))
        if not guild:
            return jsonify({
                'status': 'error',
                'message': f'Guild with ID {guild_id} not found'
            }), 404

        members = []
        for member in guild.members:
            # Get the member's highest role
            highest_role = None
            highest_role_name = None
            highest_role_color = None
            
            if len(member.roles) > 1:  # Skip the @everyone role
                highest_role = member.roles[-1]  # Roles are sorted by position
                highest_role_name = highest_role.name
                highest_role_color = f"#{highest_role.color.value:06x}" if highest_role.color.value else None
            
            members.append({
                'id': str(member.id),
                'username': member.name,
                'discriminator': member.discriminator if hasattr(member, 'discriminator') else None,
                'nick': member.nick,
                'avatar_url': member.avatar.url if member.avatar else None,
                'status': 'online',  # We can't directly get status, so assume online
                'highest_role_id': str(highest_role.id) if highest_role else None,
                'highest_role_name': highest_role_name,
                'highest_role_color': highest_role_color,
                'is_bot': member.bot
            })

        return jsonify({
            'status': 'success',
            'members': members
        })
    except Exception as e:
        logger.error(f"Error getting members: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting members: {str(e)}'
        }), 500

@app.route('/api/send_message', methods=['POST'])
def api_send_message():
    """Send a message to a channel"""
    try:
        data = request.json
        channel_id = data.get('channel_id')
        content = data.get('content')
        
        if not channel_id or not content:
            return jsonify({
                'status': 'error',
                'message': 'Missing channel_id or content parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        # Find the channel
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return jsonify({
                'status': 'error',
                'message': f'Channel with ID {channel_id} not found'
            }), 404

        # Send the message (async function, need to run it in the bot's event loop)
        try:
            # Warning: This can lead to unexpected behaviors if running in a different thread
            # Since the bot's event loop is already running, we'll create a new one for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            message = loop.run_until_complete(channel.send(content))
            loop.close()
            
            return jsonify({
                'status': 'success',
                'message_id': str(message.id)
            })
        except Exception as inner_e:
            logger.error(f"Error sending message: {str(inner_e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error sending message: {str(inner_e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error sending message: {str(e)}'
        }), 500
        
@app.route('/api/send_dm', methods=['POST'])
def api_send_dm():
    """Send a direct message to a user"""
    try:
        data = request.json
        user_id = data.get('user_id')
        content = data.get('content')
        
        if not user_id or not content:
            return jsonify({
                'status': 'error',
                'message': 'Missing user_id or content parameter'
            }), 400

        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500

        try:
            # Find the user and DM channel
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a function to fetch user and send message
            async def send_dm():
                user = await bot.fetch_user(int(user_id))
                if not user:
                    return None, f'User with ID {user_id} not found'
                
                # Send the DM
                dm_channel = await user.create_dm()
                message = await dm_channel.send(content)
                return message, None
            
            # Run the async function
            message, error = loop.run_until_complete(send_dm())
            loop.close()
            
            if error:
                return jsonify({
                    'status': 'error',
                    'message': error
                }), 404
            
            return jsonify({
                'status': 'success',
                'message_id': str(message.id)
            })
        except Exception as inner_e:
            logger.error(f"Error sending DM: {str(inner_e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error sending DM: {str(inner_e)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in send_dm endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error sending DM: {str(e)}'
        }), 500
        
@app.route('/api/dm_channels', methods=['GET'])
def api_dm_channels():
    """Get a list of DM channels"""
    try:
        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500
        
        # Get all private channels
        private_channels = []
        
        for channel in bot.private_channels:
            if isinstance(channel, discord.DMChannel) and channel.recipient:
                private_channels.append({
                    'id': str(channel.id),
                    'type': 'dm',
                    'recipient': {
                        'id': str(channel.recipient.id),
                        'username': channel.recipient.name,
                        'discriminator': channel.recipient.discriminator if hasattr(channel.recipient, 'discriminator') else None,
                        'avatar_url': channel.recipient.avatar.url if channel.recipient.avatar else None,
                        'is_bot': channel.recipient.bot
                    },
                    'last_message_id': str(channel.last_message_id) if channel.last_message_id else None
                })
        
        return jsonify({
            'status': 'success',
            'dm_channels': private_channels
        })
        
    except Exception as e:
        logger.error(f"Error getting DM channels: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting DM channels: {str(e)}'
        }), 500
        
@app.route('/api/older_messages', methods=['GET'])
def api_older_messages():
    """Get older messages before a certain message ID"""
    try:
        channel_id = request.args.get('channel_id')
        before_message_id = request.args.get('before_message_id')
        limit = request.args.get('limit', 50, type=int)
        
        if not channel_id:
            return jsonify({
                'status': 'error',
                'message': 'Missing channel_id parameter'
            }), 400
            
        bot = get_bot()
        if not bot:
            return jsonify({
                'status': 'error',
                'message': 'Bot is not running'
            }), 500
            
        # Find the channel
        channel = bot.get_channel(int(channel_id))
        if not channel:
            try:
                # If not found, try to fetch a DM channel
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def fetch_dm_channel():
                    for dm_channel in bot.private_channels:
                        if str(dm_channel.id) == channel_id:
                            return dm_channel
                    return None
                
                channel = loop.run_until_complete(fetch_dm_channel())
                loop.close()
                
                if not channel:
                    return jsonify({
                        'status': 'error',
                        'message': f'Channel with ID {channel_id} not found'
                    }), 404
            except Exception as inner_e:
                logger.error(f"Error fetching DM channel: {str(inner_e)}", exc_info=True)
                return jsonify({
                    'status': 'error',
                    'message': f'Error fetching DM channel: {str(inner_e)}'
                }), 500
            
        messages = []
        
        try:
            # Warning: This can lead to unexpected behaviors if running in a different thread
            # Since the bot's event loop is already running, we'll create a new one for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get messages before the specified ID
            history_kwargs = {'limit': limit}
            if before_message_id:
                history_kwargs['before'] = discord.Object(id=int(before_message_id))
                
            # Handle the async generator directly
            message_objects = []
            
            # Collect messages
            async def collect_messages():
                async for message in channel.history(**history_kwargs):
                    message_objects.append(message)
            
            loop.run_until_complete(collect_messages())
            loop.close()
            
            # Convert to serializable format
            for message in message_objects:
                messages.append({
                    'id': str(message.id),
                    'content': message.content,
                    'author': {
                        'id': str(message.author.id),
                        'username': message.author.name,
                        'discriminator': message.author.discriminator if hasattr(message.author, 'discriminator') else None,
                        'avatarUrl': message.author.avatar.url if message.author.avatar else None
                    },
                    'timestamp': message.created_at.isoformat(),
                    'edited_timestamp': message.edited_at.isoformat() if message.edited_at else None,
                    'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments],
                    'embeds': [{'title': embed.title, 'description': embed.description} for embed in message.embeds]
                })
        except Exception as inner_e:
            logger.error(f"Error getting older messages: {str(inner_e)}", exc_info=True)
            # Provide a fallback response with empty messages to avoid breaking the UI
            messages = []
            
        return jsonify({
            'status': 'success',
            'messages': messages
        })
    except Exception as e:
        logger.error(f"Error getting older messages: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error getting older messages: {str(e)}'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)