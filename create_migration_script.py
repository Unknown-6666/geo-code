#!/usr/bin/env python3
import os
import sys
from app import app
from database import db

def create_migration():
    """Create migration SQL for adding username fields to existing tables"""
    print("Creating migration script to add username fields...")
    
    with app.app_context():
        # Check if the columns already exist
        try:
            from sqlalchemy import text
            conn = db.engine.connect()
            
            # Check user_economy table
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_economy' AND column_name='username'"))
            user_economy_has_username = bool(result.fetchone())
            
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_economy' AND column_name='display_name'"))
            user_economy_has_display_name = bool(result.fetchone())
            
            # Check inventory table
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='inventory' AND column_name='username'"))
            inventory_has_username = bool(result.fetchone())
            
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='inventory' AND column_name='display_name'"))
            inventory_has_display_name = bool(result.fetchone())
            
            # Check transaction table
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transaction' AND column_name='username'"))
            transaction_has_username = bool(result.fetchone())
            
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='transaction' AND column_name='display_name'"))
            transaction_has_display_name = bool(result.fetchone())
            
            conn.close()
            
            # Build migration SQL
            migration_sql = []
            
            if not user_economy_has_username:
                migration_sql.append("ALTER TABLE user_economy ADD COLUMN username VARCHAR(100);")
            if not user_economy_has_display_name:
                migration_sql.append("ALTER TABLE user_economy ADD COLUMN display_name VARCHAR(100);")
                
            if not inventory_has_username:
                migration_sql.append("ALTER TABLE inventory ADD COLUMN username VARCHAR(100);")
            if not inventory_has_display_name:
                migration_sql.append("ALTER TABLE inventory ADD COLUMN display_name VARCHAR(100);")
                
            if not transaction_has_username:
                migration_sql.append("ALTER TABLE transaction ADD COLUMN username VARCHAR(100);")
            if not transaction_has_display_name:
                migration_sql.append("ALTER TABLE transaction ADD COLUMN display_name VARCHAR(100);")
            
            # Write SQL to file
            if migration_sql:
                with open('migration.sql', 'w') as f:
                    f.write('\n'.join(migration_sql))
                print(f"Migration SQL written to migration.sql ({len(migration_sql)} statements)")
                return True
            else:
                print("No migration needed. All columns already exist.")
                return False
                
        except Exception as e:
            print(f"Error creating migration: {str(e)}")
            return False

if __name__ == "__main__":
    create_migration()
