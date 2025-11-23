#!/usr/bin/env python3
"""
Script to create test users for Smart Farma application
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from apps import create_app, db
from apps.authentication.models import Users
from apps.authentication.util import hash_pass
from apps.config import config_dict
import os

def create_test_users():
    """Create test users for the application"""
    
    # Get configuration
    config_mode = os.environ.get('FLASK_ENV', 'Debug')
    app_config = config_dict.get(config_mode, config_dict['Debug'])
    
    # Initialize the app
    app = create_app(app_config)
    
    with app.app_context():
        try:
            # Check if users already exist
            existing_normal_user = Users.query.filter_by(username='testuser').first()
            existing_admin_user = Users.query.filter_by(username='admin').first()
            
            # Create normal user if doesn't exist
            if not existing_normal_user:
                normal_user = Users(
                    username='testuser',
                    email='testuser@smartfarma.com',
                    password='password123',
                    is_admin=False
                )
                db.session.add(normal_user)
                print("✅ Created normal user: testuser")
            else:
                print("ℹ️ Normal user 'testuser' already exists")
            
            # Create admin user if doesn't exist
            if not existing_admin_user:
                admin_user = Users(
                    username='admin',
                    email='admin@smartfarma.com',
                    password='admin123',
                    is_admin=True
                )
                db.session.add(admin_user)
                print("✅ Created admin user: admin")
            else:
                print("ℹ️ Admin user 'admin' already exists")
            
            # Commit the changes
            db.session.commit()
            
            print("\n" + "="*60)
            print("🎉 TEST USERS CREATED SUCCESSFULLY!")
            print("="*60)
            print("\n📝 LOGIN CREDENTIALS:")
            print("\n👤 NORMAL USER:")
            print("   Username: testuser")
            print("   Password: password123")
            print("   Email: testuser@smartfarma.com")
            print("   Login URL: http://127.0.0.1:5002/login")
            
            print("\n👑 ADMIN USER:")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Email: admin@smartfarma.com")
            print("   Admin Login URL: http://127.0.0.1:5002/admin/login")
            
            print("\n🔗 APPLICATION URLS:")
            print("   Main App: http://127.0.0.1:5002")
            print("   Normal Login: http://127.0.0.1:5002/login")
            print("   Admin Login: http://127.0.0.1:5002/admin/login")
            print("   Register: http://127.0.0.1:5002/register")
            print("   Forgot Password: http://127.0.0.1:5002/forgot-password")
            
            print("\n💡 TIPS:")
            print("   - Normal users access predictions and chat features")
            print("   - Admin users access dashboard with analytics")
            print("   - Test the forgot password feature with either user")
            print("   - Try downloading PDF reports after making predictions")
            print("="*60)
            
        except Exception as e:
            print(f"❌ Error creating users: {str(e)}")
            db.session.rollback()
            return False
            
    return True

if __name__ == '__main__':
    success = create_test_users()
    sys.exit(0 if success else 1)