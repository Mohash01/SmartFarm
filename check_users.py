#!/usr/bin/env python
"""
Script to check all users and their admin status in Smart Farma
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set Flask to not run automatically
os.environ['FLASK_RUN_FROM_CLI'] = 'false'

from apps import db
from apps.authentication.models import Users
from apps.config import config_dict
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Get the configuration mode
config_mode = 'Debug'
config = config_dict[config_mode]

# Create a minimal Flask app
app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

with app.app_context():
    # Get all users
    users = Users.query.all()
    
    print("=" * 60)
    print("🔍 SMART FARMA USER ADMIN STATUS")
    print("=" * 60)
    print(f"Total users found: {len(users)}\n")
    
    admin_users = []
    regular_users = []
    
    if users:
        print("📋 ALL USERS:")
        print("-" * 60)
        for user in users:
            status = "👑 ADMIN" if user.is_admin else "👤 USER"
            print(f"ID: {user.id:2d} | {user.username:15s} | {user.email:25s} | {status}")
            
            if user.is_admin:
                admin_users.append(user)
            else:
                regular_users.append(user)
        
        print("\n" + "=" * 60)
        print(f"📊 SUMMARY:")
        print(f"   Admin users: {len(admin_users)}")
        print(f"   Regular users: {len(regular_users)}")
        
        if admin_users:
            print(f"\n👑 ADMIN USERS:")
            for admin in admin_users:
                print(f"   • {admin.username} ({admin.email})")
        else:
            print(f"\n❌ NO ADMIN USERS FOUND!")
        
        if regular_users:
            print(f"\n👤 REGULAR USERS:")
            for user in regular_users:
                print(f"   • {user.username} ({user.email})")
    else:
        print("❌ No users found in the database!")
    
    print("=" * 60)