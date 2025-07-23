# ACES Inspector CLI - Python Port

A Python port of the ACES Inspector CLI tool for analyzing Automotive Catalog Exchange Standard (ACES) XML files.

## Overview

This is a complete Python conversion of the original C# ACES Inspector CLI application. It provides comprehensive analysis and validation of ACES XML files used in the automotive aftermarket industry.

## Features

- **ACES XML Import & Validation**: Parse and validate ACES XML files against multiple schema versions (1.08, 2.0, 3.0, 3.0.1, 3.1, 3.2, 4.2)
- **Multiple Database Support**: 
  - **Microsoft Access**: Connect to VCdb, PCdb, and Qdb Access database files (.accdb/.mdb)
  - **MySQL**: Connect to MySQL databases with flexible connection string formats
  - **Mixed Environments**: Use different database types for different data sources
- **Comprehensive Analysis**: 
  - Individual application error detection
  - Quantity outlier identification  
  - Fitment logic problem analysis
  - VCdb configuration validation
  - Part type/position validation
  - Qdb qualifier validation
- **Excel Report Generation**: Generate detailed assessment reports in Excel-compatible XML format
- **Export Capabilities**: Export applications in various formats (flat files, XML)
- **Logging**: Comprehensive logging with configurable verbosity

## Requirements

- Python 3.8+
- **For Access databases**: Microsoft Access ODBC Driver
- **For MySQL databases**: MySQL server and client libraries
- Required Python packages (see requirements.txt):
  - `lxml` - XML processing
  - `pyodbc` - Access database connectivity
  - `PyMySQL` - MySQL database connectivity
  - `mysql-connector-python` - Alternative MySQL connector
  - `xlsxwriter`, `openpyxl` - Excel report generation

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd aces-inspector-python
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Install database drivers as needed:
   - **For Access databases**: Microsoft Access ODBC Driver
   - **For MySQL databases**: MySQL client libraries (usually included with PyMySQL/mysql-connector-python)

## Usage

### Basic Usage

#### Access Databases
```bash
python aces_inspector.py -i "input.xml" -o ./output -t ./temp -v vcdb.accdb -p pcdb.accdb -q qdb.accdb
```

#### MySQL Databases
```bash
python aces_inspector.py -i "input.xml" -o ./output -t ./temp \
  -v "mysql://user:pass@localhost:3306/vcdb" \
  -p "mysql://user:pass@localhost:3306/pcdb" \
  -q "mysql://user:pass@localhost:3306/qdb"
```

#### Mixed Database Types
```bash
python aces_inspector.py -i "input.xml" -o ./output -t ./temp \
  -v "mysql://user:pass@localhost:3306/vcdb" \
  -p "pcdb.accdb" \
  -q "host=localhost;database=qdb;user=dbuser;password=dbpass"
```

### Full Command Line Options

```bash
python aces_inspector.py -i <ACES_XML_FILE> -o <OUTPUT_DIR> -t <TEMP_DIR> -v <VCDB_SOURCE> -p <PCDB_SOURCE> -q <QDB_SOURCE> [-l <LOGS_DIR>] [--verbose] [--delete]
```

#### Required Arguments
- `-i, --input`: Input ACES XML file path
- `-o, --output`: Output directory for assessment files
- `-t, --temp`: Temporary directory for processing
- `-v, --vcdb`: VCdb database (Access file path or MySQL connection string)
- `-p, --pcdb`: PCdb database (Access file path or MySQL connection string)  
- `-q, --qdb`: Qdb database (Access file path or MySQL connection string)

#### Optional Arguments
- `-l, --logs`: Logs directory (optional)
- `--verbose`: Enable verbose console output
- `--delete`: Delete input ACES file upon successful analysis
- `--version`: Show version information

### Database Connection Formats

#### Access Database Files
- **File Path**: `/path/to/database.accdb` or `C:\path\to\database.accdb`
- **ODBC String**: `DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=/path/to/database.accdb;`

#### MySQL Database Connections
- **URL Format**: `mysql://username:password@hostname:port/database_name`
- **PyMySQL Format**: `mysql+pymysql://username:password@hostname:port/database_name`
- **Parameter Format**: `host=hostname;port=3306;database=dbname;user=username;password=password`

### Examples

#### Traditional Access Databases
```bash
python aces_inspector.py \
  -i "ACES_file_with_spaces.xml" \
  -o ./myOutputDir \
  -t ./myTempDir \
  -l ./myLogsDir \
  -v VCdb20230126.accdb \
  -p PCdb20230126.accdb \
  -q Qdb20230126.accdb \
  --verbose \
  --delete
```

#### MySQL Production Environment
```bash
python aces_inspector.py \
  -i "production_aces.xml" \
  -o ./reports \
  -t ./temp \
  -l ./logs \
  -v "mysql://aces_user:secure_password@db.company.com:3306/vcdb_prod" \
  -p "mysql://aces_user:secure_password@db.company.com:3306/pcdb_prod" \
  -q "mysql://aces_user:secure_password@db.company.com:3306/qdb_prod" \
  --verbose
```

#### Mixed Environment (Development)
```bash
python aces_inspector.py \
  -i "test_aces.xml" \
  -o ./dev_output \
  -t ./dev_temp \
  -v "mysql://dev_user:dev_pass@localhost:3306/vcdb_dev" \
  -p "dev_databases/PCdb20230126.accdb" \
  -q "host=localhost;database=qdb_dev;user=dev_user;password=dev_pass" \
  --verbose
```

## Return Codes

The application returns the following exit codes:

- `0`: Successful analysis - Output spreadsheet and log file written
- `1`: Failure - Missing command line arguments
- `2`: Failure - Local filesystem problems reading input
- `3`: Failure - Local filesystem problems writing output
- `4`: Failure - Reference database (VCdb, PCdb, or Qdb) not found
- `5`: Failure - Reference database import error
- `6`: Failure - XML XSD validation error

## Output

The tool generates:

1. **Assessment Spreadsheet**: Excel-compatible XML file with multiple worksheets containing:
   - Summary information
   - Individual application errors
   - Quantity outliers
   - Fitment logic problems
   - VCdb configuration errors
   - Part type/position errors
   - Qdb errors
   - Base vehicle ID usage statistics

2. **Log File**: Detailed processing log (if logs directory specified)

## Project Structure

```
aces-inspector-python/
├── aces_inspector.py      # Main entry point
├── autocare.py           # Core classes and functionality
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── [temp directories]   # Created during processing
```

## Core Classes

### Main Classes
- **`ACES`**: Main container for ACES file data and analysis methods
- **`App`**: Represents an individual application from ACES XML
- **`Asset`**: Represents an asset from ACES XML
- **`VCdb`**: Vehicle Configuration Database interface
- **`PCdb`**: Part Configuration Database interface  
- **`Qdb`**: Qualifier Database interface

### Data Structures
- **`VCdbAttribute`**: Vehicle configuration attribute
- **`QdbQualifier`**: Qualifier with parameters
- **`BaseVehicle`**: Vehicle identification information
- **`FitmentNode`**: Node in fitment analysis tree
- **`ValidationProblem`**: Validation error details

## Version History

### Python Port v1.0.0.21
- Complete Python conversion of C# codebase
- Maintained all original functionality and features
- Improved cross-platform compatibility
- Enhanced error handling and logging

### Original C# Versions
- 1.0.0.21 (9/17/2024): Defaulted "allowGraceForWildcardConfigs" to true, fixed spelling error
- 1.0.0.20 (3/13/2024): Fixed bug in year-range style apps modelid vs make id
- [Previous versions documented in original project]

## Database Requirements

The tool requires three databases containing automotive industry standard data:

1. **VCdb (Vehicle Configuration Database)**: Contains vehicle configuration data
2. **PCdb (Part Configuration Database)**: Contains part type and position data  
3. **Qdb (Qualifier Database)**: Contains qualifier definitions

### Database Sources
- **Access Format**: Original Microsoft Access files (.accdb/.mdb) from Auto Care Association
- **MySQL Format**: Converted/migrated MySQL databases with equivalent schema and data
- **Mixed**: Can use different database types for different data sources as needed

These databases must be obtained separately from Auto Care Association or other authorized sources.

### Database Schema Compatibility
The tool expects standard Auto Care Association database schemas. When using MySQL:
- Table and column names should match the original Access database structure
- Data types should be compatible (text, integers, dates)
- For case-sensitive MySQL setups, table/column names may need adjustment
- Version information should be available in a `Version` table

## Limitations

- **Access databases**: Requires Microsoft Access ODBC driver
- **MySQL databases**: Requires MySQL server access and appropriate credentials
- Large ACES files may require significant memory and processing time
- Complex fitment logic analysis may be computationally intensive
- Network latency may affect performance when using remote MySQL databases

## Contributing

This is a faithful port of the original C# application. When making changes:

1. Maintain compatibility with original functionality
2. Follow existing code structure and patterns
3. Add comprehensive tests for new features
4. Update documentation accordingly

## License

This project maintains the same licensing as the original C# version.

## Support

For issues specific to the Python port, please create an issue in this repository.
For questions about ACES standards or database formats, refer to Auto Care Association documentation.

## Acknowledgments

- Original C# application by Luke Smith at AutoPartSource
- Auto Care Association for ACES standards
- Python conversion maintains full feature parity with original application



