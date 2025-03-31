import datetime
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
        
        with app.app_context():
            message = cls(user_id=str(user_id), role=role, content=content)
            db.session.add(message)
            db.session.commit()
            return message
    
    @classmethod
    def get_history(cls, user_id, limit=10):
        """Get the conversation history for a user, limited to the last X messages"""
        # Import here to avoid circular imports
        from dashboard.app import app
        
        with app.app_context():
            return cls.query.filter_by(user_id=str(user_id)) \
                .order_by(cls.timestamp.desc()) \
                .limit(limit) \
                .all()
    
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
        
        with app.app_context():
            cls.query.filter_by(user_id=str(user_id)).delete()
            db.session.commit()