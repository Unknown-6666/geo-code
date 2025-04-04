import datetime
import os
import time
import logging
import threading
import sqlite3
from collections import defaultdict
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import Session
from database import Base, db

# Set up logging
logger = logging.getLogger('discord')

# In-memory conversation history fallback
# This will be used when the database is not available
# Structure: {user_id: [{"role": "user/assistant", "content": "message", "timestamp": time.time()}, ...]}
memory_conversations = defaultdict(list)
memory_lock = threading.Lock()  # Lock for thread-safe operations

class Conversation(Base):
    """Model for storing conversation history between users and the bot"""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)  # Discord user ID
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<Conversation {self.id} - User: {self.user_id}, Role: {self.role}>"
    
    @classmethod
    def _add_to_memory(cls, user_id: str, role: str, content: str) -> Dict[str, Any]:
        """Add a message to the in-memory conversation store"""
        message = {
            "role": role, 
            "content": content, 
            "timestamp": time.time()
        }
        
        with memory_lock:
            # Keep only the last 20 messages per user to avoid memory issues
            if len(memory_conversations[user_id]) >= 20:
                memory_conversations[user_id].pop(0)  # Remove oldest message
            
            memory_conversations[user_id].append(message)
        
        logger.info(f"Added message to in-memory store for user {user_id}")
        return message
    
    @classmethod
    def _get_from_memory(cls, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get messages from the in-memory conversation store"""
        with memory_lock:
            # Return a copy of the messages to avoid modification issues
            messages = memory_conversations.get(user_id, [])[:]
        
        # Sort messages by timestamp (oldest first)
        messages.sort(key=lambda x: x.get("timestamp", 0))
        
        # Return only the requested number of messages
        return messages[-limit:] if limit > 0 else messages
    
    @classmethod
    def _clear_memory(cls, user_id: str) -> int:
        """Clear the in-memory conversation history for a user"""
        with memory_lock:
            count = len(memory_conversations.get(user_id, []))
            if user_id in memory_conversations:
                memory_conversations[user_id] = []
        
        logger.info(f"Cleared in-memory conversation history for user {user_id}")
        return count
    
    @classmethod
    def add_message(cls, user_id: str, role: str, content: str) -> Optional[Any]:
        """Add a new message to the conversation history"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        # First, always add to in-memory store as backup
        cls._add_to_memory(user_id, role, content)
        
        # Then try to add to database if possible
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Check if we're already using SQLite as a fallback
                if os.environ.get("USING_SQLITE_FALLBACK"):
                    # Use SQLite directly
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"Using SQLite fallback for conversation history: {sqlite_path}")
                # Try to use the local PostgreSQL database if available
                elif os.environ.get("PGUSER") and os.environ.get("PGHOST") and os.environ.get("PGDATABASE"):
                    # Create a database URL from environment variables
                    local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
                    database_url = local_db_url
                    logger.info(f"Using local PostgreSQL database for conversation history")
                else:
                    # Fall back to the DATABASE_URL environment variable
                    database_url = os.environ.get("DATABASE_URL")
                    
                    if not database_url:
                        # Fall back to the app's configured database URL
                        database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    # Final fallback to SQLite if all else fails
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"No database URL found, using SQLite fallback: {sqlite_path}")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url, pool_pre_ping=True)
                session = Session(engine)
                
                try:
                    # Create and add the message
                    message = cls(user_id=str(user_id), role=role, content=content)
                    session.add(message)
                    session.commit()
                    return message
                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
                    engine.dispose()
        except Exception as e:
            # Log the error but don't raise - we don't want to break the chat functionality
            logger.error(f"Error saving message to database: {str(e)}")
            logger.info("Message saved to in-memory store as fallback")
            return None
    
    @classmethod
    def get_history(cls, user_id: str, limit: int = 10) -> List[Any]:
        """Get the conversation history for a user, limited to the last X messages"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Check if we're already using SQLite as a fallback
                if os.environ.get("USING_SQLITE_FALLBACK"):
                    # Use SQLite directly
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"Using SQLite fallback for conversation history retrieval: {sqlite_path}")
                # Try to use the local PostgreSQL database if available
                elif os.environ.get("PGUSER") and os.environ.get("PGHOST") and os.environ.get("PGDATABASE"):
                    # Create a database URL from environment variables
                    local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
                    database_url = local_db_url
                    logger.info(f"Using local PostgreSQL database for conversation history retrieval")
                else:
                    # Fall back to the DATABASE_URL environment variable
                    database_url = os.environ.get("DATABASE_URL")
                    
                    if not database_url:
                        # Fall back to the app's configured database URL
                        database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    # Final fallback to SQLite if all else fails
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"No database URL found, using SQLite fallback for retrieval: {sqlite_path}")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url, pool_pre_ping=True)
                session = Session(engine)
                
                try:
                    # Query for messages
                    Base.metadata.create_all(engine)
                    result = session.query(cls).filter(cls.user_id == str(user_id))\
                        .order_by(cls.timestamp.desc())\
                        .limit(limit)\
                        .all()
                    return result
                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
                    engine.dispose()
        except Exception as e:
            # Log the error but don't raise - we don't want to break the chat functionality
            logger.error(f"Error fetching conversation history from database: {str(e)}")
            logger.info("Using in-memory conversation history as fallback")
            
            # Return memory messages in a format compatible with the database model
            class MemoryMessage:
                def __init__(self, role, content):
                    self.role = role
                    self.content = content
                    self.timestamp = datetime.datetime.now()
            
            memory_msgs = cls._get_from_memory(user_id, limit)
            return [MemoryMessage(msg["role"], msg["content"]) for msg in memory_msgs]
    
    @classmethod
    def get_formatted_history(cls, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get the conversation history formatted for AI context
        Returns a list of {"role": "user"|"assistant", "content": "message"} dictionaries
        """
        messages = cls.get_history(user_id, limit)
        
        # Check if we received actual database objects or our memory fallback
        if messages and hasattr(messages[0], 'timestamp'):
            # Reverse to get chronological order (oldest first) for database objects
            messages.reverse()
        
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    @classmethod
    def clear_history(cls, user_id: str) -> int:
        """Clear all conversation history for a user"""
        # Always clear memory first as a fallback
        cls._clear_memory(user_id)
        
        # Then try to clear the database
        # Import here to avoid circular imports
        from dashboard.app import app
        
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Check if we're already using SQLite as a fallback
                if os.environ.get("USING_SQLITE_FALLBACK"):
                    # Use SQLite directly
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"Using SQLite fallback for clearing conversation history: {sqlite_path}")
                # Try to use the local PostgreSQL database if available
                elif os.environ.get("PGUSER") and os.environ.get("PGHOST") and os.environ.get("PGDATABASE"):
                    # Create a database URL from environment variables
                    local_db_url = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/{os.environ.get('PGDATABASE')}"
                    database_url = local_db_url
                    logger.info(f"Using local PostgreSQL database for clearing conversation history")
                else:
                    # Fall back to the DATABASE_URL environment variable
                    database_url = os.environ.get("DATABASE_URL")
                    
                    if not database_url:
                        # Fall back to the app's configured database URL
                        database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    # Final fallback to SQLite if all else fails
                    data_dir = os.path.join(os.getcwd(), "data")
                    os.makedirs(data_dir, exist_ok=True)
                    sqlite_path = os.path.join(data_dir, "discord_bot.db")
                    database_url = f"sqlite:///{sqlite_path}"
                    logger.info(f"No database URL found, using SQLite fallback for clearing history: {sqlite_path}")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url, pool_pre_ping=True)
                session = Session(engine)
                
                try:
                    # Delete messages for this user
                    Base.metadata.create_all(engine)
                    result = session.query(cls).filter(cls.user_id == str(user_id)).delete()
                    session.commit()
                    return result
                except Exception as e:
                    session.rollback()
                    raise e
                finally:
                    session.close()
                    engine.dispose()
        except Exception as e:
            # Log the error but don't raise - we don't want to break the chat functionality
            logger.error(f"Error clearing conversation history from database: {str(e)}")
            logger.info("In-memory conversation history was cleared as fallback")
            return 0  # Return 0 rows affected on error