#!/usr/bin/env python3
"""
Database Configuration Helper for ACES Inspector
Provides utilities for setting up database connections

Author: Python Enhancement for Multiple Database Support
"""

import os
from typing import Dict, List, Optional
from database_adapter import DatabaseConfig, create_database_adapter


class DatabaseManager:
    """Helper class for managing multiple database connections"""
    
    def __init__(self):
        self.vcdb_config: Optional[DatabaseConfig] = None
        self.pcdb_config: Optional[DatabaseConfig] = None
        self.qdb_config: Optional[DatabaseConfig] = None
        self.adapters: Dict[str, 'DatabaseAdapter'] = {}
    
    def setup_from_arguments(self, vcdb_path: str, pcdb_path: str, qdb_path: str):
        """Setup database configurations from command line arguments"""
        self.vcdb_config = DatabaseConfig.from_connection_string(vcdb_path)
        self.pcdb_config = DatabaseConfig.from_connection_string(pcdb_path)
        self.qdb_config = DatabaseConfig.from_connection_string(qdb_path)
    
    def get_database_info(self) -> Dict[str, str]:
        """Get information about configured databases"""
        info = {}
        if self.vcdb_config:
            info['VCdb'] = f"{self.vcdb_config.db_type} - {self.vcdb_config.connection_string[:50]}..."
        if self.pcdb_config:
            info['PCdb'] = f"{self.pcdb_config.db_type} - {self.pcdb_config.connection_string[:50]}..."
        if self.qdb_config:
            info['Qdb'] = f"{self.qdb_config.db_type} - {self.qdb_config.connection_string[:50]}..."
        return info
    
    def validate_all_connections(self) -> Dict[str, str]:
        """Test all database connections. Returns dict of connection results."""
        results = {}
        
        # Test VCdb
        try:
            adapter = create_database_adapter(self.vcdb_config.connection_string)
            result = adapter.connect()
            results['VCdb'] = "Success" if not result else f"Error: {result}"
            adapter.disconnect()
        except Exception as ex:
            results['VCdb'] = f"Error: {ex}"
        
        # Test PCdb
        try:
            adapter = create_database_adapter(self.pcdb_config.connection_string)
            result = adapter.connect()
            results['PCdb'] = "Success" if not result else f"Error: {result}"
            adapter.disconnect()
        except Exception as ex:
            results['PCdb'] = f"Error: {ex}"
        
        # Test Qdb
        try:
            adapter = create_database_adapter(self.qdb_config.connection_string)
            result = adapter.connect()
            results['Qdb'] = "Success" if not result else f"Error: {result}"
            adapter.disconnect()
        except Exception as ex:
            results['Qdb'] = f"Error: {ex}"
        
        return results


# Database connection string templates and examples
DATABASE_TEMPLATES = {
    "access": {
        "file_path": "{file_path}",
        "odbc_string": "DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={file_path};",
        "description": "Microsoft Access database file"
    },
    "mysql": {
        "url_format": "mysql://{username}:{password}@{host}:{port}/{database}",
        "pymysql_format": "mysql+pymysql://{username}:{password}@{host}:{port}/{database}",
        "param_format": "host={host};port={port};database={database};user={username};password={password}",
        "description": "MySQL database connection"
    }
}

EXAMPLE_CONFIGURATIONS = {
    "development_access": {
        "vcdb": "data/VCdb20230126.accdb",
        "pcdb": "data/PCdb20230126.accdb",
        "qdb": "data/Qdb20230126.accdb",
        "description": "Local Access database files in data directory"
    },
    "production_mysql": {
        "vcdb": "mysql://aces_user:password@localhost:3306/vcdb_prod",
        "pcdb": "mysql://aces_user:password@localhost:3306/pcdb_prod",
        "qdb": "mysql://aces_user:password@localhost:3306/qdb_prod",
        "description": "Production MySQL databases on localhost"
    },
    "remote_mysql": {
        "vcdb": "mysql://aces_user:password@db.company.com:3306/vcdb",
        "pcdb": "mysql://aces_user:password@db.company.com:3306/pcdb",
        "qdb": "mysql://aces_user:password@db.company.com:3306/qdb",
        "description": "Remote MySQL databases"
    },
    "mixed_environment": {
        "vcdb": "mysql://aces_user:password@localhost:3306/vcdb",
        "pcdb": "data/PCdb20230126.accdb",
        "qdb": "host=localhost;database=qdb;user=aces_user;password=password",
        "description": "Mixed database types - MySQL VCdb, Access PCdb, MySQL Qdb with parameters"
    }
}


def generate_config_file(config_name: str, file_path: str = "database_config.txt"):
    """Generate a configuration file with database connection examples"""
    with open(file_path, 'w') as f:
        f.write("# ACES Inspector Database Configuration Examples\n")
        f.write("# Copy and modify these examples for your environment\n\n")
        
        for name, config in EXAMPLE_CONFIGURATIONS.items():
            f.write(f"# {config['description']}\n")
            f.write(f"# Configuration: {name}\n")
            f.write(f"python aces_inspector.py \\\n")
            f.write(f"  -i input.xml \\\n")
            f.write(f"  -o ./output \\\n")
            f.write(f"  -t ./temp \\\n")
            f.write(f"  -v \"{config['vcdb']}\" \\\n")
            f.write(f"  -p \"{config['pcdb']}\" \\\n")
            f.write(f"  -q \"{config['qdb']}\" \\\n")
            f.write(f"  --verbose\n\n")
        
        f.write("# Database Connection String Formats:\n\n")
        f.write("# Access Database:\n")
        f.write("#   File path: /path/to/database.accdb\n")
        f.write("#   ODBC: DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=/path/to/database.accdb;\n\n")
        
        f.write("# MySQL Database:\n")
        f.write("#   URL format: mysql://username:password@hostname:port/database_name\n")
        f.write("#   PyMySQL format: mysql+pymysql://username:password@hostname:port/database_name\n")
        f.write("#   Parameter format: host=hostname;port=3306;database=dbname;user=username;password=password\n\n")


if __name__ == "__main__":
    # Generate example configuration file
    generate_config_file("examples", "database_examples.txt")
    print("Generated database_examples.txt with configuration examples")
    
    # Test database configuration parsing
    print("\nTesting database configuration parsing:")
    
    test_configs = [
        "data/VCdb20230126.accdb",
        "mysql://user:pass@localhost:3306/vcdb",
        "host=localhost;database=vcdb;user=test;password=secret"
    ]
    
    for config_str in test_configs:
        config = DatabaseConfig.from_connection_string(config_str)
        print(f"  {config_str[:50]:50} -> {config.db_type}")