#!/usr/bin/env python
"""
Script to test admin login directly
"""
import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

import requests
import time

def test_admin_login():
    # Start a session
    session = requests.Session()
    
    # First, get the login page to see if we can access it
    print("1. Accessing admin login page...")
    login_page = session.get('http://127.0.0.1:5000/admin/login')
    print(f"   Status: {login_page.status_code}")
    
    if login_page.status_code == 200:
        print("   ✅ Admin login page accessible")
    else:
        print("   ❌ Admin login page not accessible")
        return
    
    # Try to login
    print("\n2. Attempting admin login...")
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'login': 'Sign In'
    }
    
    response = session.post('http://127.0.0.1:5000/admin/login', data=login_data, allow_redirects=False)
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}")
    
    if response.status_code == 302:  # Redirect
        print("   ✅ Login appears successful (redirecting)")
        print(f"   Redirect location: {response.headers.get('Location')}")
        
        # Follow the redirect
        print("\n3. Following redirect...")
        redirect_response = session.get(response.headers.get('Location'), allow_redirects=False)
        print(f"   Status: {redirect_response.status_code}")
        
        if redirect_response.status_code == 302:
            print(f"   Another redirect to: {redirect_response.headers.get('Location')}")
            # Follow this redirect too
            final_response = session.get(redirect_response.headers.get('Location'))
            print(f"   Final page status: {final_response.status_code}")
            print(f"   Final URL: {final_response.url}")
        else:
            print(f"   Final page status: {redirect_response.status_code}")
            print(f"   Final URL: {redirect_response.url}")
    else:
        print("   ❌ Login failed")
        print(f"   Response text: {response.text[:500]}")

if __name__ == "__main__":
    print("🔍 Testing Admin Login Flow...")
    print("=" * 50)
    test_admin_login()