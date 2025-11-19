#!/usr/bin/env python
"""
Script to create an admin account for Smart Farma
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
    # Check if admin user already exists
    admin = Users.query.filter_by(username='moha').first()
    
    if admin:
        print(f"✅ Admin user 'moha' already exists!")
        print(f"   Email: {admin.email}")
        print(f"   Is Admin: {admin.is_admin}")
    else:
        # Create new admin user
        admin_user = Users(
            username='moha',
            email='moha@smartfarma.com',
            password='admin123',  # Will be hashed automatically
            is_admin=True
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("✅ Admin account created successfully!")
        print("=" * 50)
        print("Username: moha")
        print("Password: admin123")
        print("Email: moha@smartfarma.com")
        print("Role: Admin")
        print("=" * 50)
        print("\n🔐 Login at: http://127.0.0.1:5000/admin/login")
