from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base


class VerificationSetting(Base):
    """Server-specific verification settings"""
    __tablename__ = 'verification_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(20), unique=True, nullable=False)
    
    # Verification types enabled
    require_captcha = Column(Boolean, default=False)
    require_questions = Column(Boolean, default=False)
    require_role_accept = Column(Boolean, default=False)
    require_account_age = Column(Boolean, default=False)
    
    # Configuration
    min_account_age_days = Column(Integer, default=0)
    verification_channel_id = Column(String(20), nullable=True)
    verified_role_id = Column(String(20), nullable=True)
    welcome_message = Column(Text, nullable=True)
    
    # If enabled, send a welcome message in this channel after verification
    welcome_channel_id = Column(String(20), nullable=True)
    
    # Questions and acceptable answers stored as JSON
    # Format: [{"question": "Q1", "answers": ["A1", "A2"]}]
    custom_questions = Column(JSON, default=list)
    
    # Usage statistics
    total_attempts = Column(Integer, default=0)
    successful_verifications = Column(Integer, default=0)
    failed_verifications = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    verification_logs = relationship("VerificationLog", back_populates="setting", cascade="all, delete-orphan")


class VerificationLog(Base):
    """Log of verification attempts"""
    __tablename__ = 'verification_logs'
    
    id = Column(Integer, primary_key=True)
    
    # References
    setting_id = Column(Integer, ForeignKey('verification_settings.id', ondelete='CASCADE'))
    setting = relationship("VerificationSetting", back_populates="verification_logs")
    
    # User info
    user_id = Column(String(20), nullable=False)
    guild_id = Column(String(20), nullable=False)
    
    # Verification details
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    success = Column(Boolean, nullable=True)  # True=verified, False=failed, None=in progress
    
    # Tracking progress on different verification steps
    captcha_attempts = Column(Integer, default=0)
    captcha_completed = Column(Boolean, default=False)
    
    questions_attempts = Column(Integer, default=0)
    questions_completed = Column(Boolean, default=False)
    
    role_accept_completed = Column(Boolean, default=False)
    
    # Details about the failure if any
    failure_reason = Column(Text, nullable=True)
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)