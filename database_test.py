#!/usr/bin/env python3
"""
Database Connection Test Script for ABB Store Management System
Run this script to test your MySQL database connection before starting the main application.
"""

import os
import sys
from dotenv import load_dotenv
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

def test_pymysql_connection():
    """Test direct PyMySQL connection"""
    print("Testing PyMySQL connection...")
    
    try:
        connection = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'abb_store_management'),
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ PyMySQL connection successful!")
            print(f"   MySQL Version: {version[0]}")
            
            # Test table existence
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   Found {len(tables)} tables: {[table[0] for table in tables]}")
            
            # Test user count
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"   Users in database: {user_count}")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ PyMySQL connection failed: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    print("\nTesting SQLAlchemy connection...")
    
    try:
        # Build connection string
        db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            db_uri = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
        
        print(f"   Connection URI: {db_uri.replace(os.getenv('MYSQL_PASSWORD', ''), '***')}")
        
        # Create engine
        engine = create_engine(
            db_uri,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={'charset': 'utf8mb4'}
        )
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            version = result.scalar()
            print(f"✅ SQLAlchemy connection successful!")
            print(f"   MySQL Version: {version}")
            
            # Test queries
            result = connection.execute(text("SELECT COUNT(*) FROM materials WHERE is_active = 1"))
            material_count = result.scalar()
            print(f"   Active materials: {material_count}")
            
            result = connection.execute(text("SELECT COUNT(*) FROM material_requests WHERE status = 'pending'"))
            pending_requests = result.scalar()
            print(f"   Pending requests: {pending_requests}")
            
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_sample_queries():
    """Test sample application queries"""
    print("\nTesting sample application queries...")
    
    try:
        db_uri = os.getenv('SQLALCHEMY_DATABASE_URI')
        if not db_uri:
            db_uri = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
        
        engine = create_engine(db_uri, pool_pre_ping=True)
        
        with engine.connect() as connection:
            # Test low stock query
            result = connection.execute(text("""
                SELECT COUNT(*) FROM materials 
                WHERE current_stock <= minimum_stock AND is_active = 1
            """))
            low_stock_count = result.scalar()
            print(f"   Low stock items: {low_stock_count}")
            
            # Test user roles
            result = connection.execute(text("""
                SELECT role, COUNT(*) as count 
                FROM users 
                WHERE is_active = 1 
                GROUP BY role
            """))
            roles = result.fetchall()
            print(f"   User roles: {dict(roles)}")
            
            # Test recent transactions
            result = connection.execute(text("""
                SELECT COUNT(*) FROM transactions 
                WHERE transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """))
            recent_transactions = result.scalar()
            print(f"   Recent transactions (30 days): {recent_transactions}")
            
        print("✅ Sample queries executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Sample queries failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("ABB Store Management System - Database Connection Test")
    print("=" * 60)
    
    # Check environment variables
    print("Checking environment variables...")
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'MYSQL_PASSWORD':
                print(f"   {var}: {'*' * len(value)}")
            else:
                print(f"   {var}: {value}")
        else:
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("Please check your .env file")
        return False
    
    print("✅ All required environment variables found")
    
    # Run tests
    tests_passed = 0
    total_tests = 3
    
    if test_pymysql_connection():
        tests_passed += 1
    
    if test_sqlalchemy_connection():
        tests_passed += 1
        
    if test_sample_queries():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Your database is ready for the application.")
        print("\nYou can now run: python app.py")
    else:
        print("❌ Some tests failed. Please check your database setup.")
        print("\nTroubleshooting tips:")
        print("1. Ensure MySQL server is running")
        print("2. Verify database credentials in .env file")
        print("3. Check if database 'abb_store_management' exists")
        print("4. Ensure all database scripts have been executed")
        print("5. Check MySQL user permissions")
    
    print("=" * 60)
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
