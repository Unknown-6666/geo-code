from database import Base, session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class UserEconomy(Base):
    __tablename__ = 'user_economy'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), unique=True, nullable=False)
    wallet = Column(Integer, default=0)
    bank = Column(Integer, default=0)
    bank_capacity = Column(Integer, default=1000)
    last_daily = Column(DateTime)
    last_work = Column(DateTime)
    last_rob = Column(DateTime)

class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    price = Column(Integer, nullable=False)
    emoji = Column(String(20))
    is_buyable = Column(Boolean, default=True)

class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    quantity = Column(Integer, default=1)
    item = relationship('Item')

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)
    description = Column(String(200))
    timestamp = Column(DateTime, default=datetime.utcnow)

def initialize_shop():
    """Initialize the shop with default items"""
    default_items = [
        {
            'name': 'Fishing Rod',
            'description': 'Used for fishing. Who knows what you might catch!',
            'price': 500,
            'emoji': '🎣'
        },
        {
            'name': 'Lucky Coin',
            'description': 'Increases your chances in gambling games by a small amount',
            'price': 1000,
            'emoji': '🪙'
        },
        {
            'name': 'Bank Note',
            'description': 'Increases your bank capacity by 1000',
            'price': 2500,
            'emoji': '📜'
        },
        {
            'name': 'Trophy',
            'description': 'A symbol of wealth and success',
            'price': 10000,
            'emoji': '🏆'
        }
    ]

    for item_data in default_items:
        item = session.query(Item).filter_by(name=item_data['name']).first()
        if not item:
            item = Item(
                name=item_data['name'],
                description=item_data['description'],
                price=item_data['price'],
                emoji=item_data['emoji'],
                is_buyable=True
            )
            session.add(item)

    session.commit()