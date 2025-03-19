import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from database import db

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure the SQLAlchemy part of the app
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Create all database tables
with app.app_context():
    from models.economy import UserEconomy, Item, Inventory, Transaction
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)