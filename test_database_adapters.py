#!/usr/bin/env python3
"""
Test script for database adapters
Tests both Access and MySQL database connectivity

Usage:
  python test_database_adapters.py
"""

import os
import sys
from database_adapter import DatabaseConfig, create_database_adapter, DATABASE_CONNECTION_EXAMPLES


def test_config_parsing():
    """Test database configuration parsing"""
    print("Testing database configuration parsing...")
    
    test_cases = [
        ("C:\\data\\vcdb.accdb", "access"),
        ("/home/user/data/vcdb.accdb", "access"),
        ("DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\data\\vcdb.accdb;", "access"),
        ("mysql://user:pass@localhost:3306/vcdb", "mysql"),
        ("mysql+pymysql://user:pass@localhost:3306/vcdb", "mysql"),
        ("host=localhost;database=vcdb;user=test;password=secret", "mysql"),
        ("host=192.168.1.100;port=3307;database=vcdb;user=aces;password=pass123", "mysql"),
    ]
    
    for connection_string, expected_type in test_cases:
        try:
            config = DatabaseConfig.from_connection_string(connection_string)
            result = "✓" if config.db_type == expected_type else "✗"
            print(f"  {result} {connection_string[:60]:60} -> {config.db_type}")
            
            if config.db_type == "mysql":
                print(f"      Host: {config.host}, Port: {config.port}, DB: {config.database}")
            elif config.db_type == "access":
                print(f"      File: {config.file_path}")
                
        except Exception as ex:
            print(f"  ✗ {connection_string[:60]:60} -> ERROR: {ex}")
    
    print()


def test_adapter_creation():
    """Test database adapter creation"""
    print("Testing database adapter creation...")
    
    test_cases = [
        "sample.accdb",
        "mysql://testuser:testpass@localhost:3306/testdb",
        "host=localhost;database=testdb;user=testuser;password=testpass"
    ]
    
    for connection_string in test_cases:
        try:
            adapter = create_database_adapter(connection_string)
            adapter_type = type(adapter).__name__
            db_type = adapter.config.db_type
            print(f"  ✓ {connection_string[:50]:50} -> {adapter_type} ({db_type})")
        except Exception as ex:
            print(f"  ✗ {connection_string[:50]:50} -> ERROR: {ex}")
    
    print()


def test_connection_examples():
    """Test predefined connection examples"""
    print("Testing predefined connection examples...")
    
    for name, example in DATABASE_CONNECTION_EXAMPLES.items():
        try:
            config = DatabaseConfig.from_connection_string(example)
            print(f"  ✓ {name:20} -> {config.db_type:8} | {example}")
        except Exception as ex:
            print(f"  ✗ {name:20} -> ERROR: {ex}")
    
    print()


def test_mysql_connection_if_available():
    """Test actual MySQL connection if credentials are provided via environment"""
    print("Testing MySQL connection (if credentials available)...")
    
    # Check for environment variables
    mysql_host = os.getenv('MYSQL_HOST', 'localhost')
    mysql_user = os.getenv('MYSQL_USER')
    mysql_password = os.getenv('MYSQL_PASSWORD')
    mysql_database = os.getenv('MYSQL_DATABASE')
    
    if mysql_user and mysql_password and mysql_database:
        connection_string = f"mysql://{mysql_user}:{mysql_password}@{mysql_host}:3306/{mysql_database}"
        try:
            adapter = create_database_adapter(connection_string)
            result = adapter.connect()
            if not result:
                print(f"  ✓ Successfully connected to MySQL at {mysql_host}")
                adapter.disconnect()
            else:
                print(f"  ✗ Failed to connect to MySQL: {result}")
        except Exception as ex:
            print(f"  ✗ MySQL connection error: {ex}")
    else:
        print("  ℹ No MySQL credentials provided via environment variables")
        print("    Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE to test")
    
    print()


def test_access_connection_if_available():
    """Test actual Access connection if file is available"""
    print("Testing Access connection (if .accdb file available)...")
    
    # Look for sample Access files
    test_files = [
        "vcdb.accdb",
        "sample.accdb", 
        "test.accdb",
        "data/vcdb.accdb",
        "../data/vcdb.accdb"
    ]
    
    found_file = None
    for test_file in test_files:
        if os.path.exists(test_file):
            found_file = test_file
            break
    
    if found_file:
        try:
            adapter = create_database_adapter(found_file)
            result = adapter.connect()
            if not result:
                print(f"  ✓ Successfully connected to Access file: {found_file}")
                adapter.disconnect()
            else:
                print(f"  ✗ Failed to connect to Access file: {result}")
        except Exception as ex:
            print(f"  ✗ Access connection error: {ex}")
    else:
        print("  ℹ No Access database files found for testing")
        print("    Place a test .accdb file to test Access connectivity")
    
    print()


def main():
    """Run all tests"""
    print("=" * 70)
    print("Database Adapter Test Suite")
    print("=" * 70)
    print()
    
    test_config_parsing()
    test_adapter_creation()
    test_connection_examples()
    test_mysql_connection_if_available()
    test_access_connection_if_available()
    
    print("=" * 70)
    print("Test suite completed")
    print("=" * 70)


if __name__ == "__main__":
    main()