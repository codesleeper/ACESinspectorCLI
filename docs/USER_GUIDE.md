# ACES Inspector CLI - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Requirements](#requirements)
4. [Quick Start](#quick-start)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Command Line Reference](#command-line-reference)
8. [Understanding Output](#understanding-output)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Introduction

The ACES Inspector CLI is a powerful command-line tool for analyzing Automotive Catalog Exchange Standard (ACES) XML files. It provides comprehensive validation, error detection, and reporting capabilities for automotive aftermarket applications.

### What is ACES?

ACES (Automotive Catalog Exchange Standard) is an XML-based standard used in the automotive aftermarket industry to describe vehicle applications for parts and accessories. ACES files contain:

- **Applications**: Descriptions of which parts fit which vehicles
- **Assets**: Digital content like images and documents
- **Vehicle Configuration**: Detailed vehicle specifications
- **Qualifiers**: Additional fitment criteria

### What the Tool Does

The ACES Inspector CLI:
- ✅ **Validates** ACES XML files against multiple schema versions
- ✅ **Analyzes** applications for errors and inconsistencies
- ✅ **Detects** quantity outliers and fitment logic problems
- ✅ **Generates** comprehensive Excel reports
- ✅ **Integrates** with VCdb, PCdb, and Qdb databases
- ✅ **Provides** detailed logging and error reporting

---

## Installation

### Method 1: Using pip (Recommended)

```bash
# Install from source
pip install -e .

# Or install specific version
pip install aces-inspector-cli==1.0.0.21
```

### Method 2: Manual Installation

```bash
# Clone the repository
git clone <repository-url>
cd aces-inspector-python

# Install dependencies
pip install -r requirements.txt

# Verify installation
python aces_inspector.py --version
```

### Method 3: Virtual Environment (Recommended for Development)

```bash
# Create virtual environment
python -m venv aces_env

# Activate virtual environment
# On Windows:
aces_env\Scripts\activate
# On Linux/Mac:
source aces_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Requirements

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, Linux, or macOS
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large files)
- **Disk Space**: Sufficient space for temporary files and output reports

### Database Requirements

The tool requires three Microsoft Access database files:

1. **VCdb (Vehicle Configuration Database)**: Contains vehicle data
2. **PCdb (Part Configuration Database)**: Contains part type and position data  
3. **Qdb (Qualifier Database)**: Contains qualifier definitions

These databases must be obtained from Auto Care Association or authorized sources.

### Python Dependencies

```
lxml>=4.9.3         # XML processing and validation
pyodbc>=4.0.39      # Microsoft Access database connectivity
xlsxwriter>=3.1.9   # Excel file generation
openpyxl>=3.1.2     # Excel file manipulation
```

### ODBC Driver

**Microsoft Access ODBC Driver** is required for database connectivity:

- **Windows**: Usually pre-installed
- **Linux**: Install `mdbtools` and `unixodbc`
- **macOS**: Install via Homebrew or download from Microsoft

---

## Quick Start

### 1. Prepare Your Environment

```bash
# Check Python version
python --version

# Verify ODBC driver
python -c "import pyodbc; print('ODBC drivers:', pyodbc.drivers())"
```

### 2. Basic Analysis

```bash
python aces_inspector.py \
  -i "sample_aces.xml" \
  -o ./output \
  -t ./temp \
  -v VCdb20230126.accdb \
  -p PCdb20230126.accdb \
  -q Qdb20230126.accdb \
  --verbose
```

### 3. Check Results

After successful execution, you'll find:
- **Assessment report**: Excel-compatible XML file in output directory
- **Log file**: Detailed processing log (if specified)
- **Return code**: 0 for success, non-zero for errors

---

## Configuration

### Database Configuration

#### Database File Locations
Store database files in an accessible location:

```
project/
├── databases/
│   ├── VCdb20230126.accdb
│   ├── PCdb20230126.accdb
│   └── Qdb20230126.accdb
├── input/
│   └── sample_aces.xml
└── output/
```

#### Database Versions
Always use the latest available database versions for best results:
- VCdb versions are typically released quarterly
- PCdb and Qdb versions follow similar schedules
- Version dates are usually in YYYYMMDD format

### Directory Configuration

#### Input Directory
```bash
mkdir -p input
# Place ACES XML files here
```

#### Output Directory  
```bash
mkdir -p output
# Assessment reports will be generated here
```

#### Temporary Directory
```bash
mkdir -p temp
# Temporary processing files (automatically cleaned up)
```

#### Logs Directory (Optional)
```bash
mkdir -p logs
# Detailed processing logs
```

### Performance Configuration

#### Memory Management
For large ACES files:
```bash
# Set Python memory limits if needed
export PYTHONHASHSEED=0
```

#### Multi-threading
The tool automatically uses multi-threading for better performance on large files.

---

## Usage Examples

### Example 1: Basic Analysis

```bash
python aces_inspector.py \
  -i "ACES_Product_Catalog.xml" \
  -o ./reports \
  -t ./temp \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb
```

### Example 2: Verbose Output with Logging

```bash
python aces_inspector.py \
  -i "ACES_Product_Catalog.xml" \
  -o ./reports \
  -t ./temp \
  -l ./logs \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb \
  --verbose
```

### Example 3: Auto-delete Input File After Processing

```bash
python aces_inspector.py \
  -i "ACES_Product_Catalog.xml" \
  -o ./reports \
  -t ./temp \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb \
  --delete \
  --verbose
```

### Example 4: Batch Processing Script

```bash
#!/bin/bash
# Process multiple ACES files

for file in input/*.xml; do
    echo "Processing $file..."
    python aces_inspector.py \
      -i "$file" \
      -o ./output \
      -t ./temp \
      -v databases/VCdb20230126.accdb \
      -p databases/PCdb20230126.accdb \
      -q databases/Qdb20230126.accdb \
      --verbose
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully processed $file"
    else
        echo "✗ Failed to process $file"
    fi
done
```

---

## Command Line Reference

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `-i, --input` | Input ACES XML file | `"ACES_catalog.xml"` |
| `-o, --output` | Output directory | `./reports` |
| `-t, --temp` | Temporary directory | `./temp` |
| `-v, --vcdb` | VCdb database file | `VCdb20230126.accdb` |
| `-p, --pcdb` | PCdb database file | `PCdb20230126.accdb` |
| `-q, --qdb` | Qdb database file | `Qdb20230126.accdb` |

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-l, --logs` | Logs directory | None |
| `--verbose` | Verbose console output | False |
| `--delete` | Delete input file after success | False |
| `--version` | Show version information | - |

### File Path Handling

#### Spaces in Filenames
Use quotes for paths with spaces:
```bash
python aces_inspector.py -i "ACES file with spaces.xml" ...
```

#### Relative vs Absolute Paths
Both are supported:
```bash
# Relative paths
python aces_inspector.py -i ./input/file.xml -o ./output

# Absolute paths  
python aces_inspector.py -i /home/user/aces/file.xml -o /home/user/reports
```

---

## Understanding Output

### Assessment Report Structure

The tool generates an Excel-compatible XML file with multiple worksheets:

#### 1. Summary Worksheet
- **File Information**: Input file details, processing statistics
- **Error Counts**: Summary of all error types found
- **Processing Time**: Analysis duration and performance metrics

#### 2. Individual Application Errors
- **Part Type Errors**: Invalid part type IDs
- **Position Errors**: Invalid position IDs
- **Part Type-Position Combinations**: Invalid combinations

#### 3. VCdb Configuration Errors
- **Base Vehicle Errors**: Invalid base vehicle IDs
- **Configuration Violations**: Invalid attribute combinations
- **Attribute Errors**: Missing or invalid vehicle attributes

#### 4. Qdb Errors
- **Invalid Qualifiers**: Qualifier IDs not found in Qdb
- **Parameter Errors**: Missing or invalid qualifier parameters
- **Logic Errors**: Conflicting qualifier applications

#### 5. Quantity Outliers
- **Statistical Outliers**: Quantities that deviate significantly from norms
- **Threshold Analysis**: Configurable outlier detection

#### 6. Fitment Logic Problems
- **Logical Contradictions**: Conflicting fitment specifications
- **Missing Combinations**: Incomplete fitment coverage
- **Redundant Applications**: Duplicate or overlapping applications

#### 7. Base Vehicle Usage Statistics
- **Usage Frequency**: How often each base vehicle ID is used
- **Coverage Analysis**: Vehicle coverage patterns

### Log File Structure

When logging is enabled (`-l` option), detailed logs include:

```
[Timestamp] Processing started
[Timestamp] Loading VCdb database...
[Timestamp] Loading PCdb database...
[Timestamp] Loading Qdb database...
[Timestamp] Importing ACES XML file...
[Timestamp] Found 1234 applications
[Timestamp] Found 56 assets
[Timestamp] Starting individual application analysis...
[Timestamp] Found 12 part type errors
[Timestamp] Starting quantity outlier analysis...
[Timestamp] Found 3 quantity outliers
[Timestamp] Starting fitment logic analysis...
[Timestamp] Found 2 fitment logic problems
[Timestamp] Generating assessment report...
[Timestamp] Processing completed successfully
```

### Return Codes

| Code | Meaning | Action Required |
|------|---------|-----------------|
| 0 | Success | None - review report |
| 1 | Missing arguments | Check command line syntax |
| 2 | Input file problems | Verify file exists and is readable |
| 3 | Output problems | Check output directory permissions |
| 4 | Database not found | Verify database file paths |
| 5 | Database import error | Check database file integrity |
| 6 | XML validation error | Verify ACES XML format |

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Problems

**Error**: "Could not connect to database"

**Solutions**:
```bash
# Check if ODBC driver is installed
python -c "import pyodbc; print(pyodbc.drivers())"

# Verify database file exists
ls -la VCdb20230126.accdb

# Check file permissions
chmod 644 VCdb20230126.accdb
```

#### 2. Memory Issues with Large Files

**Error**: "Out of memory" or slow processing

**Solutions**:
```bash
# Increase Python memory limit
export PYTHONUNBUFFERED=1

# Use 64-bit Python for large files
python --version  # Check architecture

# Split large ACES files if possible
```

#### 3. XML Parsing Errors

**Error**: "XML validation failed"

**Solutions**:
```bash
# Validate XML structure
xmllint --noout sample.xml

# Check for encoding issues
file sample.xml

# Verify ACES schema compliance
```

#### 4. Path Issues

**Error**: "File not found"

**Solutions**:
```bash
# Use absolute paths
python aces_inspector.py -i /full/path/to/file.xml

# Escape special characters
python aces_inspector.py -i "file with spaces.xml"

# Check current working directory
pwd
```

### Performance Optimization

#### For Large Files (>100MB):
- Use SSD storage for temporary files
- Ensure adequate RAM (8GB+ recommended)
- Close other applications during processing
- Use the latest database versions

#### For Batch Processing:
- Process files sequentially to avoid resource conflicts
- Monitor disk space for temporary files
- Use logging to track progress
- Implement error handling in scripts

### Debug Mode

For troubleshooting, enable maximum verbosity:

```bash
python aces_inspector.py \
  -i sample.xml \
  -o ./output \
  -t ./temp \
  -l ./logs \
  -v VCdb.accdb \
  -p PCdb.accdb \
  -q Qdb.accdb \
  --verbose
```

---

## Best Practices

### File Organization

```
project/
├── databases/           # Keep database files here
│   ├── VCdb20230126.accdb
│   ├── PCdb20230126.accdb
│   └── Qdb20230126.accdb
├── input/              # Input ACES files
│   ├── processed/      # Move completed files here
│   └── pending/        # Files awaiting processing
├── output/             # Assessment reports
│   ├── 2024-01/       # Organize by date
│   └── 2024-02/
├── temp/               # Temporary files (auto-cleaned)
├── logs/               # Processing logs
└── scripts/            # Automation scripts
```

### Database Management

1. **Keep databases updated**: Use the latest versions available
2. **Backup databases**: Store copies in multiple locations
3. **Version control**: Track which database versions were used
4. **Access control**: Protect database files from corruption

### Processing Workflow

1. **Validate input**: Check ACES file before processing
2. **Use staging area**: Process files in dedicated directories
3. **Monitor resources**: Watch disk space and memory usage
4. **Archive results**: Keep assessment reports for reference
5. **Document issues**: Log problems and solutions

### Quality Assurance

1. **Review reports**: Always examine assessment results
2. **Validate findings**: Cross-check errors with business rules
3. **Track trends**: Monitor error patterns over time
4. **Automate checks**: Use scripts for routine validations

### Security Considerations

1. **File permissions**: Restrict access to database files
2. **Temporary files**: Ensure proper cleanup
3. **Sensitive data**: Handle part numbers and vehicle data appropriately
4. **Backup strategy**: Implement secure backup procedures

---

**Version**: 1.0.0.21 (Python Port)  
**Last Updated**: Current Date  
**Status**: Production Ready

For additional support, refer to the [API Reference](API_REFERENCE.md) and [Architecture Documentation](ARCHITECTURE.md).