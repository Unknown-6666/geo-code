from database import Base
from sqlalchemy import Column, Integer, String
from datetime import datetime

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    username = Column(String(100), nullable=False)
    avatar_url = Column(String(200))
    currency = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)