#!/usr/bin/env python3
"""
Create a test user directly in the database (for testing when email is not configured).
Run this in the Docker container or locally with the production database.
"""

import sys
import bcrypt
from datetime import datetime, timezone
from uuid import uuid4

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_test_user(email: str, username: str, password: str):
    """Generate SQL to create a test user."""
    user_id = str(uuid4())
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    
    # SQL for user
    user_sql = f"""
-- Create test user (already verified)
INSERT INTO users (
    id, email, username, password_hash,
    email_verified, email_verified_at, is_active,
    created_at, updated_at
) VALUES (
    '{user_id}',
    '{email}',
    '{username}',
    '{password_hash}',
    1,  -- email_verified = true
    '{now}',
    1,  -- is_active = true
    '{now}',
    '{now}'
);

-- Create default organization
INSERT INTO organizations (
    id, name, slug, owner_id,
    created_at, updated_at
) VALUES (
    '{str(uuid4())}',
    '{username}''s Organization',
    '{username}-org',
    '{user_id}',
    '{now}',
    '{now}'
);
"""
    
    print(f"Generated SQL for user: {username} ({email})")
    print("Password:", password)
    print("\nSQL to execute:")
    print("-" * 60)
    print(user_sql)
    print("-" * 60)
    
    return user_sql

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python create-test-user.py <email> <username> <password>")
        print("Example: python create-test-user.py test@example.com testuser SecurePass123!")
        sys.exit(1)
    
    email = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    create_test_user(email, username, password)