import os
import logging
from flask import Flask, render_template, redirect, url_for, flash, request, session
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
    DISCORD_REDIRECT_URI = f'https://{os.getenv("REPL_SLUG")}.{os.getenv("REPL_OWNER")}.repl.co/callback'
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
@login_required
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)