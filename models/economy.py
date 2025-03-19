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