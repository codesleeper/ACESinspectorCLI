#!/usr/bin/env python3
"""
Database Adapter for ACES Inspector
Provides unified interface for Access and MySQL databases

Author: Python Enhancement for Multiple Database Support
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
import pyodbc
import pymysql
import mysql.connector


@dataclass
class DatabaseConfig:
    """Database configuration container"""
    db_type: str  # 'access' or 'mysql'
    connection_string: str = ""
    host: str = ""
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""
    file_path: str = ""  # For Access databases
    
    @classmethod
    def from_connection_string(cls, connection_string: str) -> 'DatabaseConfig':
        """Create config from connection string"""
        config = cls(db_type="unknown", connection_string=connection_string)
        
        # Detect database type
        if connection_string.lower().startswith(('mysql://', 'mysql+pymysql://')):
            config.db_type = "mysql"
            config._parse_mysql_connection_string(connection_string)
        elif '.accdb' in connection_string.lower() or '.mdb' in connection_string.lower():
            config.db_type = "access"
            config.file_path = connection_string
        elif 'driver=' in connection_string.lower() and 'dbq=' in connection_string.lower():
            config.db_type = "access"
            config._parse_access_connection_string(connection_string)
        else:
            # Try to parse as MySQL if it contains typical MySQL parameters
            if any(param in connection_string.lower() for param in ['host=', 'user=', 'password=', 'database=']):
                config.db_type = "mysql"
                config._parse_mysql_parameters(connection_string)
            else:
                # Assume it's a file path for Access
                config.db_type = "access"
                config.file_path = connection_string
        
        return config
    
    def _parse_mysql_connection_string(self, connection_string: str):
        """Parse MySQL URL-style connection string"""
        try:
            parsed = urlparse(connection_string)
            self.host = parsed.hostname or "localhost"
            self.port = parsed.port or 3306
            self.username = parsed.username or ""
            self.password = parsed.password or ""
            self.database = parsed.path.lstrip('/') if parsed.path else ""
        except Exception:
            # Fallback to parameter parsing
            self._parse_mysql_parameters(connection_string)
    
    def _parse_mysql_parameters(self, connection_string: str):
        """Parse MySQL parameter-style connection string"""
        params = {}
        for param in connection_string.split(';'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key.lower().strip()] = value.strip()
        
        self.host = params.get('host', 'localhost')
        self.port = int(params.get('port', 3306))
        self.username = params.get('user', params.get('username', ''))
        self.password = params.get('password', params.get('passwd', ''))
        self.database = params.get('database', params.get('db', ''))
    
    def _parse_access_connection_string(self, connection_string: str):
        """Parse Access ODBC connection string"""
        # Extract DBQ parameter which contains the file path
        match = re.search(r'DBQ=([^;]+)', connection_string, re.IGNORECASE)
        if match:
            self.file_path = match.group(1)
        else:
            self.file_path = connection_string


class DatabaseAdapter(ABC):
    """Abstract database adapter interface"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
    
    @abstractmethod
    def connect(self) -> str:
        """Connect to database. Returns empty string on success, error message on failure."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from database"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        pass
    
    @abstractmethod
    def get_cursor(self):
        """Get database cursor"""
        pass
    
    def is_connected(self) -> bool:
        """Check if connected to database"""
        return self.connection is not None


class AccessDatabaseAdapter(DatabaseAdapter):
    """Microsoft Access database adapter using pyodbc"""
    
    def connect(self) -> str:
        """Connect to Access database"""
        try:
            if self.connection:
                self.connection.close()
            
            if self.config.connection_string and 'DRIVER=' in self.config.connection_string.upper():
                # Use provided connection string
                connection_string = self.config.connection_string
            else:
                # Build connection string from file path
                file_path = self.config.file_path or self.config.connection_string
                connection_string = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={file_path};"
            
            self.connection = pyodbc.connect(connection_string)
            return ""
            
        except Exception as ex:
            return str(ex)
    
    def disconnect(self):
        """Disconnect from Access database"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        if not self.connection:
            raise Exception("Not connected to database")
        
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor.fetchall()
    
    def get_cursor(self):
        """Get database cursor"""
        if not self.connection:
            raise Exception("Not connected to database")
        return self.connection.cursor()


class MySQLDatabaseAdapter(DatabaseAdapter):
    """MySQL database adapter using PyMySQL and mysql-connector-python"""
    
    def __init__(self, config: DatabaseConfig, use_connector: bool = False):
        super().__init__(config)
        self.use_connector = use_connector  # Use mysql-connector-python instead of PyMySQL
    
    def connect(self) -> str:
        """Connect to MySQL database"""
        try:
            if self.connection:
                self.connection.close()
            
            connection_params = {
                'host': self.config.host,
                'port': self.config.port,
                'user': self.config.username,
                'password': self.config.password,
                'database': self.config.database,
                'charset': 'utf8mb4',
                'autocommit': True
            }
            
            if self.use_connector:
                # Use mysql-connector-python
                self.connection = mysql.connector.connect(**connection_params)
            else:
                # Use PyMySQL
                self.connection = pymysql.connect(**connection_params)
            
            return ""
            
        except Exception as ex:
            return str(ex)
    
    def disconnect(self):
        """Disconnect from MySQL database"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        if not self.connection:
            raise Exception("Not connected to database")
        
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor.fetchall()
    
    def get_cursor(self):
        """Get database cursor"""
        if not self.connection:
            raise Exception("Not connected to database")
        return self.connection.cursor()


def create_database_adapter(connection_string: str, use_mysql_connector: bool = False) -> DatabaseAdapter:
    """Factory function to create appropriate database adapter"""
    config = DatabaseConfig.from_connection_string(connection_string)
    
    if config.db_type == "mysql":
        return MySQLDatabaseAdapter(config, use_connector=use_mysql_connector)
    elif config.db_type == "access":
        return AccessDatabaseAdapter(config)
    else:
        raise ValueError(f"Unsupported database type: {config.db_type}")


class DatabaseQueryBuilder:
    """Helper class for building database-agnostic queries"""
    
    @staticmethod
    def limit_query(query: str, db_type: str, limit: int) -> str:
        """Add LIMIT clause based on database type"""
        if db_type == "mysql":
            return f"{query} LIMIT {limit}"
        elif db_type == "access":
            return f"SELECT TOP {limit} * FROM ({query})"
        return query
    
    @staticmethod
    def quote_identifier(identifier: str, db_type: str) -> str:
        """Quote identifier based on database type"""
        if db_type == "mysql":
            return f"`{identifier}`"
        elif db_type == "access":
            return f"[{identifier}]"
        return identifier
    
    @staticmethod
    def get_version_query(db_type: str) -> str:
        """Get database version query"""
        if db_type == "mysql":
            return "SELECT VERSION() as version"
        elif db_type == "access":
            return "SELECT VersionDate FROM Version"
        return "SELECT 'Unknown' as version"


# Database connection string examples and patterns
DATABASE_CONNECTION_EXAMPLES = {
    "access_file": "C:\\path\\to\\database.accdb",
    "access_odbc": "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\\path\\to\\database.accdb;",
    "mysql_url": "mysql://username:password@localhost:3306/database_name",
    "mysql_params": "host=localhost;port=3306;database=vcdb;user=username;password=password",
    "mysql_pymysql": "mysql+pymysql://username:password@localhost:3306/database_name"
}