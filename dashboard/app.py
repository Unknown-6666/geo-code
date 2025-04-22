import os
import json
import logging
import asyncio
import datetime
import subprocess
import threading
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from requests_oauthlib import OAuth2Session
from werkzeug.security import generate_password_hash, check_password_hash

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)