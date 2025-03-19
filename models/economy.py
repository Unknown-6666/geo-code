from database import db
from datetime import datetime
from sqlalchemy import Index

class UserEconomy(db.Model):
    __tablename__ = 'user_economy'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    wallet = db.Column(db.Integer, default=0)
    bank = db.Column(db.Integer, default=0)
    bank_capacity = db.Column(db.Integer, default=1000)
    last_daily = db.Column(db.DateTime)
    last_work = db.Column(db.DateTime)
    last_rob = db.Column(db.DateTime)  # Added for robbery cooldown

    # Create an index on user_id for faster lookups
    __table_args__ = (Index('idx_user_economy_user_id', 'user_id'),)

    @property
    def total_balance(self):
        """Get total balance (wallet + bank)"""
        return self.wallet + self.bank

class Item(db.Model):
    __tablename__ = 'item'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Integer, nullable=False)
    emoji = db.Column(db.String(20))
    is_buyable = db.Column(db.Boolean, default=True)

    # Create an index on name for faster lookups
    __table_args__ = (Index('idx_item_name', 'name'),)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    # Relationship to get item details
    item = db.relationship('Item', backref='inventories')

    # Create a compound index for user_id and item_id
    __table_args__ = (
        Index('idx_inventory_user_item', 'user_id', 'item_id'),
    )

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Create an index on user_id and timestamp for faster history lookups
    __table_args__ = (
        Index('idx_transaction_user_timestamp', 'user_id', 'timestamp'),
    )

def initialize_shop():
    """Initialize the shop with default items"""
    default_items = [
        {
            'name': 'Fishing Rod',
            'description': 'Used for fishing. Who knows what you might catch!',
            'price': 500,
            'emoji': '🎣',
            'is_buyable': True
        },
        {
            'name': 'Lucky Coin',
            'description': 'Increases your chances in gambling games by a small amount',
            'price': 1000,
            'emoji': '🪙',
            'is_buyable': True
        },
        {
            'name': 'Bank Note',
            'description': 'Increases your bank capacity by 1000',
            'price': 2500,
            'emoji': '📜',
            'is_buyable': True
        },
        {
            'name': 'Trophy',
            'description': 'A symbol of wealth and success',
            'price': 10000,
            'emoji': '🏆',
            'is_buyable': True
        }
    ]

    for item_data in default_items:
        item = Item.query.filter_by(name=item_data['name']).first()
        if not item:
            item = Item(
                name=item_data['name'],
                description=item_data['description'],
                price=item_data['price'],
                emoji=item_data['emoji'],
                is_buyable=item_data['is_buyable']
            )
            db.session.add(item)

    db.session.commit()