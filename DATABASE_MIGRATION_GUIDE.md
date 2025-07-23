# Database Migration Guide for ACES Inspector

This guide explains how to migrate from Microsoft Access databases to MySQL, or use mixed database environments.

## Overview

The ACES Inspector now supports multiple database backends:
- **Microsoft Access** (.accdb/.mdb files) - Original format
- **MySQL** - For better performance, scalability, and multi-user access
- **Mixed environments** - Use different database types for different data sources

## Migration Strategies

### 1. Full MySQL Migration

Convert all three databases (VCdb, PCdb, Qdb) to MySQL for maximum performance and scalability.

**Benefits:**
- Better performance for large datasets
- Multi-user concurrent access
- Network accessibility
- Better backup and recovery options
- Integration with existing MySQL infrastructure

**Considerations:**
- Requires MySQL server setup and maintenance
- Schema conversion needed
- Data migration process required

### 2. Selective Migration

Migrate only specific databases based on usage patterns:
- Keep frequently accessed databases (like VCdb) in MySQL
- Keep smaller, less frequently updated databases (like Qdb) as Access files

### 3. Development vs Production

- **Development**: Use Access files for simplicity
- **Production**: Use MySQL for performance and reliability

## Database Schema Conversion

### General Principles

1. **Table Names**: Keep original table names (BaseVehicle, Mfr, Parts, etc.)
2. **Column Names**: Maintain original column names and types
3. **Primary Keys**: Preserve existing primary key structures
4. **Indexes**: Add appropriate indexes for performance

### Access to MySQL Type Mapping

| Access Type | MySQL Type | Notes |
|-------------|------------|-------|
| AutoNumber | INT AUTO_INCREMENT | Primary keys |
| Number (Long) | INT | Integer values |
| Number (Integer) | SMALLINT | Smaller integers |
| Text (255) | VARCHAR(255) | Text fields |
| Text (>255) | TEXT | Long text fields |
| Memo | TEXT or LONGTEXT | Large text content |
| Date/Time | DATETIME | Date and time values |
| Yes/No | BOOLEAN or TINYINT(1) | Boolean values |

### Sample Schema Conversion

#### VCdb BaseVehicle Table
```sql
-- Access equivalent in MySQL
CREATE TABLE BaseVehicle (
    BaseVehicleID INT AUTO_INCREMENT PRIMARY KEY,
    MakeID INT NOT NULL,
    ModelID INT NOT NULL,
    Year INT NOT NULL,
    INDEX idx_make_model (MakeID, ModelID),
    INDEX idx_year (Year)
);
```

#### PCdb Parts Table
```sql
CREATE TABLE Parts (
    partterminologyid INT AUTO_INCREMENT PRIMARY KEY,
    partterminologyname VARCHAR(255) NOT NULL,
    INDEX idx_name (partterminologyname)
);
```

#### Qdb Qualifier Table
```sql
CREATE TABLE Qualifier (
    qualifierid INT AUTO_INCREMENT PRIMARY KEY,
    qualifiertext TEXT,
    qualifiertypeid INT,
    INDEX idx_type (qualifiertypeid)
);
```

## Data Migration Process

### Method 1: Using MySQL Workbench

1. Install MySQL Workbench
2. Use the Migration Wizard:
   - Connect to Access database via ODBC
   - Select target MySQL server
   - Map schemas and tables
   - Review and execute migration

### Method 2: Using Access Export

1. Open Access database
2. Use "External Data" → "Export" → "ODBC Database"
3. Configure MySQL ODBC connection
4. Export tables to MySQL

### Method 3: Using Custom Scripts

```python
# Sample migration script
import pyodbc
import pymysql

def migrate_table(access_conn, mysql_conn, table_name):
    # Read from Access
    access_cursor = access_conn.cursor()
    access_cursor.execute(f"SELECT * FROM {table_name}")
    
    # Get column info
    columns = [desc[0] for desc in access_cursor.description]
    placeholders = ', '.join(['%s'] * len(columns))
    
    # Insert into MySQL
    mysql_cursor = mysql_conn.cursor()
    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    batch_size = 1000
    while True:
        rows = access_cursor.fetchmany(batch_size)
        if not rows:
            break
        mysql_cursor.executemany(insert_sql, rows)
    
    mysql_conn.commit()
```

## Configuration Examples

### Development Environment (Mixed)
```bash
# Use MySQL for large VCdb, Access for others
python aces_inspector.py \
  -i input.xml \
  -o ./output \
  -t ./temp \
  -v "mysql://dev_user:dev_pass@localhost:3306/vcdb_dev" \
  -p "data/PCdb20230126.accdb" \
  -q "data/Qdb20230126.accdb" \
  --verbose
```

### Production Environment (Full MySQL)
```bash
# All databases in MySQL
python aces_inspector.py \
  -i production.xml \
  -o ./reports \
  -t ./temp \
  -v "mysql://aces_user:secure_pass@db.company.com:3306/vcdb_prod" \
  -p "mysql://aces_user:secure_pass@db.company.com:3306/pcdb_prod" \
  -q "mysql://aces_user:secure_pass@db.company.com:3306/qdb_prod" \
  --verbose
```

### High Availability Setup
```bash
# Using MySQL with connection pooling
python aces_inspector.py \
  -i input.xml \
  -o ./output \
  -t ./temp \
  -v "mysql://aces_user:pass@db-cluster.company.com:3306/vcdb?charset=utf8mb4" \
  -p "mysql://aces_user:pass@db-cluster.company.com:3306/pcdb?charset=utf8mb4" \
  -q "mysql://aces_user:pass@db-cluster.company.com:3306/qdb?charset=utf8mb4" \
  --verbose
```

## Performance Optimization

### MySQL Configuration

1. **Increase Buffer Pool Size**
   ```ini
   [mysqld]
   innodb_buffer_pool_size = 1G  # Adjust based on available RAM
   ```

2. **Optimize for Read-Heavy Workloads**
   ```ini
   [mysqld]
   query_cache_size = 128M
   query_cache_type = 1
   ```

3. **Connection Settings**
   ```ini
   [mysqld]
   max_connections = 200
   wait_timeout = 28800
   ```

### Indexing Strategy

```sql
-- VCdb performance indexes
CREATE INDEX idx_basevehicle_year_make ON BaseVehicle (Year, MakeID);
CREATE INDEX idx_basevehicle_make_model_year ON BaseVehicle (MakeID, ModelID, Year);

-- PCdb performance indexes
CREATE INDEX idx_parts_name ON Parts (partterminologyname);
CREATE INDEX idx_codemaster_part_pos ON codemaster (partterminologyid, positionid);

-- Qdb performance indexes
CREATE INDEX idx_qualifier_type_text ON Qualifier (qualifiertypeid, qualifiertext(50));
```

## Troubleshooting

### Common Issues

1. **Character Encoding**
   - Use UTF-8 (utf8mb4) in MySQL
   - Ensure proper character set conversion during migration

2. **Case Sensitivity**
   - MySQL on Linux is case-sensitive by default
   - Use lowercase table names or configure MySQL appropriately

3. **Connection Timeouts**
   - Increase MySQL timeout settings for large data operations
   - Use connection pooling for better resource management

4. **Data Type Mismatches**
   - Review and adjust data types during migration
   - Test with sample data before full migration

### Testing Migration

```python
# Test script to verify migration
def verify_migration(access_path, mysql_connection):
    # Compare record counts
    access_conn = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={access_path};")
    mysql_conn = pymysql.connect(**mysql_connection)
    
    tables = ['BaseVehicle', 'Mfr', 'Parts', 'Qualifier']
    
    for table in tables:
        access_count = access_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        mysql_count = mysql_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        
        if access_count == mysql_count:
            print(f"✓ {table}: {access_count} records")
        else:
            print(f"✗ {table}: Access={access_count}, MySQL={mysql_count}")
```

## Best Practices

1. **Backup Strategy**
   - Always backup original Access databases before migration
   - Implement regular MySQL backups
   - Test restore procedures

2. **Security**
   - Use dedicated database users with minimal required permissions
   - Enable SSL connections for remote access
   - Regularly update passwords

3. **Monitoring**
   - Monitor MySQL performance and resource usage
   - Set up alerts for connection issues
   - Log slow queries for optimization

4. **Version Control**
   - Document schema changes
   - Maintain migration scripts in version control
   - Track database versions alongside application versions

## Support and Migration Services

For organizations requiring assistance with database migration:

1. **Assessment Phase**
   - Current database analysis
   - Performance requirements evaluation
   - Migration strategy planning

2. **Migration Phase**
   - Schema conversion
   - Data migration and validation
   - Performance optimization

3. **Testing Phase**
   - Functionality verification
   - Performance benchmarking
   - Load testing

4. **Deployment Phase**
   - Production migration
   - Monitoring setup
   - Training and documentation

This migration approach ensures minimal disruption while providing enhanced performance and scalability for ACES processing workflows.