import os
import logging
import pathlib
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from database import db
from sqlalchemy.exc import OperationalError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dashboard.app')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Create data directory if it doesn't exist
data_dir = pathlib.Path("./data")
data_dir.mkdir(exist_ok=True)

# Configure the SQLAlchemy part of the app with better error handling
try:
    # First priority: Use newly created Replit PostgreSQL database
    if os.environ.get("PGUSER") and os.environ.get("PGHOST") and os.environ.get("PGDATABASE"):
        # Recreate the database URL using the environment variables
        local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
        app.config["SQLALCHEMY_DATABASE_URI"] = local_db_url
        logger.info(f"Using Replit PostgreSQL database: {os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}")
    elif os.environ.get("DATABASE_URL") and "neon.tech" not in os.environ.get("DATABASE_URL", ""):
        # Second priority: Use DATABASE_URL if it's not the disabled Neon endpoint
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        logger.info(f"Using database from DATABASE_URL environment variable")
    else:
        # Fallback: Use SQLite for reliability
        sqlite_path = os.path.join(data_dir, "discord_bot.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
        logger.info(f"Using SQLite database as fallback: {sqlite_path}")
        os.environ["USING_SQLITE_FALLBACK"] = "true"
except Exception as config_error:
    logger.error(f"Error configuring database: {str(config_error)}")
    # Emergency fallback to SQLite
    sqlite_path = os.path.join(data_dir, "discord_bot.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    logger.info(f"Emergency fallback to SQLite database: {sqlite_path}")
    os.environ["USING_SQLITE_FALLBACK"] = "true"

# Configure database connection pooling for better performance and reliability
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
}

# Log which redirect URI we're using
logger.info(f"Using Replit redirect URI: {os.environ.get('REPLIT_URL', 'Not set')}/callback")

# Initialize database
db.init_app(app)

# Create all database tables with error handling and retries
MAX_RETRIES = 3
retry_count = 0

while retry_count < MAX_RETRIES:
    try:
        with app.app_context():
            from models.economy import UserEconomy, Item, Inventory, Transaction
            db.create_all()
            logger.info("Database tables created successfully")
            break  # Success, exit the retry loop
    except OperationalError as e:
        retry_count += 1
        logger.error(f"Database initialization error (attempt {retry_count}/{MAX_RETRIES}): {str(e)}")
        
        # Handle Neon database disabled error
        if "endpoint is disabled" in str(e) or "connection to server" in str(e):
            logger.warning("PostgreSQL database connection failed, trying alternatives...")
            
            # Try local PostgreSQL first
            if os.environ.get("PGUSER") and os.environ.get("PGHOST"):
                logger.info("Trying local PostgreSQL database...")
                local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
                app.config["SQLALCHEMY_DATABASE_URI"] = local_db_url
            
            # If we're on the last retry, switch to SQLite as final fallback
            if retry_count >= MAX_RETRIES - 1:
                logger.warning("PostgreSQL connection failed, falling back to SQLite database")
                sqlite_path = os.path.join(data_dir, "discord_bot.db")
                app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
                logger.info(f"Using SQLite database as final fallback: {sqlite_path}")
                # Update environment to help other parts of the app know we're using SQLite
                os.environ["USING_SQLITE_FALLBACK"] = "true"
                
        if retry_count >= MAX_RETRIES:
            logger.warning("Maximum retry attempts reached. Continuing with limited database functionality.")
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {str(e)}")
        
        # Try SQLite as a last resort for any error
        logger.warning("Database error occurred, falling back to SQLite")
        sqlite_path = os.path.join(data_dir, "discord_bot.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
        logger.info(f"Using SQLite database after error: {sqlite_path}")
        os.environ["USING_SQLITE_FALLBACK"] = "true"
        
        # Try one more time with SQLite
        try:
            with app.app_context():
                from models.economy import UserEconomy, Item, Inventory, Transaction
                db.create_all()
                logger.info("Database tables created successfully with SQLite")
                break
        except Exception as sqlite_err:
            logger.error(f"Even SQLite failed: {str(sqlite_err)}")
            logger.warning("Continuing with SEVERELY limited database functionality")
        
        break  # Exit on non-connection errors

# Let main.py know what database we're using for Discord bot
if 'USING_SQLITE_FALLBACK' in os.environ:
    logger.info("Updated app.config with SQLite database URL")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)