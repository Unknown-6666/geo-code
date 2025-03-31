import datetime
import os
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from database import Base, db

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
    def add_message(cls, user_id, role, content):
        """Add a new message to the conversation history"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Get the database URL from environment
                database_url = os.environ.get("DATABASE_URL")
                
                if not database_url:
                    # Fall back to the app's configured database URL
                    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    raise ValueError("No database URL found")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url)
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
            import logging
            logger = logging.getLogger('discord')
            logger.error(f"Error saving message to conversation history: {str(e)}")
            return None
    
    @classmethod
    def get_history(cls, user_id, limit=10):
        """Get the conversation history for a user, limited to the last X messages"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Get the database URL from environment
                database_url = os.environ.get("DATABASE_URL")
                
                if not database_url:
                    # Fall back to the app's configured database URL
                    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    raise ValueError("No database URL found")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url)
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
            import logging
            logger = logging.getLogger('discord')
            logger.error(f"Error fetching conversation history: {str(e)}")
            return []  # Return empty list on error
    
    @classmethod
    def get_formatted_history(cls, user_id, limit=10):
        """
        Get the conversation history formatted for AI context
        Returns a list of {"role": "user"|"assistant", "content": "message"} dictionaries
        """
        messages = cls.get_history(user_id, limit)
        # Reverse to get chronological order (oldest first)
        messages.reverse()
        
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    @classmethod
    def clear_history(cls, user_id):
        """Clear all conversation history for a user"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        try:
            with app.app_context():
                # Create a new session to avoid using a potentially closed one
                from sqlalchemy.orm import Session
                from sqlalchemy import create_engine
                
                # Get the database URL from environment
                database_url = os.environ.get("DATABASE_URL")
                
                if not database_url:
                    # Fall back to the app's configured database URL
                    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
                
                if not database_url:
                    raise ValueError("No database URL found")
                
                # Create a new engine and session for this operation
                engine = create_engine(database_url)
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
            import logging
            logger = logging.getLogger('discord')
            logger.error(f"Error clearing conversation history: {str(e)}")
            return 0  # Return 0 rows affected on error