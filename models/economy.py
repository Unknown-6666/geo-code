from database import db
from datetime import datetime

class UserEconomy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    wallet = db.Column(db.Integer, default=0)
    bank = db.Column(db.Integer, default=0)
    bank_capacity = db.Column(db.Integer, default=1000)
    last_daily = db.Column(db.DateTime)
    last_work = db.Column(db.DateTime)
    last_rob = db.Column(db.DateTime)  # Added for robbery cooldown

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Integer, nullable=False)
    emoji = db.Column(db.String(20))
    is_buyable = db.Column(db.Boolean, default=True)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    item = db.relationship('Item')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
        item = Item.query.filter_by(name=item_data['name']).first()
        if not item:
            item = Item(
                name=item_data['name'],
                description=item_data['description'],
                price=item_data['price'],
                emoji=item_data['emoji'],
                is_buyable=True
            )
            db.session.add(item)

    db.session.commit()