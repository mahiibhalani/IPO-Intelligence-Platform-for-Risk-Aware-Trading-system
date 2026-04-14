"""
Database Initialization Script
==============================
Run this script to initialize the database and create a test user.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from flask_app import app, db, logger
from src.models import User, UserPreferences

def init_database():
    """Initialize database and create test user."""
    with app.app_context():
        # Create tables
        db.create_all()
        logger.info("Database tables created")
        
        # Check if test user exists
        test_user = User.query.filter_by(username='testuser').first()
        
        if not test_user:
            print("Creating test user...")
            test_user = User(
                username='testuser',
                email='test@example.com',
                first_name='Test',
                last_name='User',
                is_active=True
            )
            test_user.set_password('Test@1234')
            db.session.add(test_user)
            db.session.flush()
            
            # Create preferences
            prefs = UserPreferences(
                user_id=test_user.id,
                risk_tolerance='moderate',
                theme='dark'
            )
            db.session.add(prefs)
            db.session.commit()
            
            print("✅ Test user created successfully!")
            print("   Username: testuser")
            print("   Password: Test@1234")
            print("   Email: test@example.com")
            logger.info("Test user created: testuser/Test@1234")
        else:
            print("✅ Test user already exists!")
            print("   Username: testuser")
            print("   Password: Test@1234")

if __name__ == '__main__':
    try:
        init_database()
        print("\n✅ Database initialization complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)
