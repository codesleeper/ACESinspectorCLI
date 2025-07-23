# ACES Inspector CLI - Usage Examples

## Table of Contents

1. [Basic Usage Examples](#basic-usage-examples)
2. [Advanced Command Line Usage](#advanced-command-line-usage)
3. [Programmatic Usage](#programmatic-usage)
4. [Batch Processing](#batch-processing)
5. [Custom Analysis](#custom-analysis)
6. [Error Handling](#error-handling)
7. [Integration Examples](#integration-examples)
8. [Performance Optimization](#performance-optimization)

---

## Basic Usage Examples

### Example 1: Simple ACES File Analysis

```bash
# Basic analysis with minimum required parameters
python aces_inspector.py \
  -i "ACES_catalog.xml" \
  -o ./output \
  -t ./temp \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb
```

**Expected Output:**
```
Processing ACES file: ACES_catalog.xml
Loading VCdb database...
Loading PCdb database...
Loading Qdb database...
Importing ACES XML file...
Found 1234 applications
Starting analysis...
Analysis complete. Report saved to: output/assessment_ACES_catalog.xml
```

### Example 2: Analysis with Verbose Output

```bash
# Enable detailed console output
python aces_inspector.py \
  -i "ACES_catalog.xml" \
  -o ./output \
  -t ./temp \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb \
  --verbose
```

**Expected Verbose Output:**
```
[2024-01-15 10:30:15] Starting ACES Inspector CLI v1.0.0.21
[2024-01-15 10:30:15] Input file: ACES_catalog.xml
[2024-01-15 10:30:15] Output directory: ./output
[2024-01-15 10:30:15] Connecting to VCdb database...
[2024-01-15 10:30:16] VCdb connected successfully
[2024-01-15 10:30:16] Loading VCdb data...
[2024-01-15 10:30:18] VCdb data loaded: 15,234 base vehicles
[2024-01-15 10:30:18] Connecting to PCdb database...
[2024-01-15 10:30:18] PCdb connected successfully
[2024-01-15 10:30:18] Loading PCdb data...
[2024-01-15 10:30:19] PCdb data loaded: 456 part types, 789 positions
[2024-01-15 10:30:19] Connecting to Qdb database...
[2024-01-15 10:30:19] Qdb connected successfully
[2024-01-15 10:30:19] Loading Qdb data...
[2024-01-15 10:30:20] Qdb data loaded: 234 qualifiers
[2024-01-15 10:30:20] Parsing ACES XML file...
[2024-01-15 10:30:22] Found 1234 applications, 56 assets
[2024-01-15 10:30:22] Starting individual application analysis...
[2024-01-15 10:30:24] Found 12 part type errors
[2024-01-15 10:30:24] Starting quantity outlier analysis...
[2024-01-15 10:30:25] Found 3 quantity outliers
[2024-01-15 10:30:25] Starting fitment logic analysis...
[2024-01-15 10:30:27] Found 2 fitment logic problems
[2024-01-15 10:30:27] Generating assessment report...
[2024-01-15 10:30:28] Assessment report saved: output/assessment_ACES_catalog.xml
[2024-01-15 10:30:28] Processing completed successfully
```

### Example 3: Analysis with Logging

```bash
# Save detailed logs to file
python aces_inspector.py \
  -i "ACES_catalog.xml" \
  -o ./output \
  -t ./temp \
  -l ./logs \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb \
  --verbose
```

**Generated Files:**
```
output/
├── assessment_ACES_catalog.xml    # Main assessment report
logs/
├── aces_analysis_20240115_103028.log  # Detailed processing log
temp/
├── (temporary files - auto-cleaned)
```

---

## Advanced Command Line Usage

### Example 4: File with Spaces and Special Characters

```bash
# Handle files with spaces in names
python aces_inspector.py \
  -i "ACES Product Catalog (2024-Q1) [Final].xml" \
  -o "./Output Reports" \
  -t "./Temporary Files" \
  -l "./Log Files" \
  -v "databases/VCdb 2023-01-26.accdb" \
  -p "databases/PCdb 2023-01-26.accdb" \
  -q "databases/Qdb 2023-01-26.accdb" \
  --verbose
```

### Example 5: Auto-delete Source File After Processing

```bash
# Automatically delete input file after successful analysis
python aces_inspector.py \
  -i "processed/ACES_catalog.xml" \
  -o ./output \
  -t ./temp \
  -v databases/VCdb20230126.accdb \
  -p databases/PCdb20230126.accdb \
  -q databases/Qdb20230126.accdb \
  --delete \
  --verbose
```

**Note:** The `--delete` flag only removes the input file if analysis completes successfully (return code 0).

### Example 6: Using Absolute Paths

```bash
# Use absolute paths for better reliability in scripts
python aces_inspector.py \
  -i "/home/user/data/ACES_catalog.xml" \
  -o "/home/user/reports" \
  -t "/tmp/aces_temp" \
  -l "/var/log/aces" \
  -v "/opt/databases/VCdb20230126.accdb" \
  -p "/opt/databases/PCdb20230126.accdb" \
  -q "/opt/databases/Qdb20230126.accdb" \
  --verbose
```

---

## Programmatic Usage

### Example 7: Basic Programmatic Analysis

```python
#!/usr/bin/env python3
"""
Basic programmatic usage of ACES Inspector CLI
"""

from autocare import ACES, VCdb, PCdb, Qdb
import os
import tempfile

def analyze_aces_file(aces_file_path, database_paths):
    """Analyze ACES file programmatically."""
    
    # Initialize components
    aces = ACES()
    vcdb = VCdb()
    pcdb = PCdb()
    qdb = Qdb()
    
    try:
        # Connect to databases
        print("Connecting to databases...")
        vcdb_error = vcdb.connect_local_oledb(database_paths['vcdb'])
        if vcdb_error:
            print(f"VCdb connection error: {vcdb_error}")
            return False
            
        pcdb_error = pcdb.connect_local_oledb(database_paths['pcdb'])
        if pcdb_error:
            print(f"PCdb connection error: {pcdb_error}")
            return False
            
        qdb_error = qdb.connect_local_oledb(database_paths['qdb'])
        if qdb_error:
            print(f"Qdb connection error: {qdb_error}")
            return False
        
        # Import database data
        print("Loading database data...")
        vcdb.import_oledb_data()
        pcdb.import_oledb()
        qdb.import_oledb()
        
        # Import ACES XML file
        print(f"Importing ACES file: {aces_file_path}")
        with tempfile.TemporaryDirectory() as temp_dir:
            import_result = aces.import_xml(
                aces_file_path,
                "",  # Schema string (empty for auto-detection)
                True,  # Respect validate="no" tag
                False,  # Don't discard deletes
                {},  # Part interchange (empty)
                {},  # Asset name interchange (empty)
                temp_dir,  # Cache path
                True  # Use multi-threading
            )
            
            if import_result != "":
                print(f"Import failed: {import_result}")
                return False
            
            print(f"Successfully imported {len(aces.apps)} applications and {len(aces.assets)} assets")
            
            # Generate assessment report
            output_file = "assessment_report.xml"
            print(f"Generating assessment report: {output_file}")
            report_result = aces.generate_assessment_file(
                output_file,
                vcdb,
                pcdb,
                qdb,
                temp_dir,
                ""  # Log indent
            )
            
            if report_result == "":
                print("Assessment report generated successfully")
                return True
            else:
                print(f"Report generation failed: {report_result}")
                return False
                
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        # Clean up database connections
        vcdb.disconnect()
        pcdb.disconnect()
        qdb.disconnect()

# Usage
if __name__ == "__main__":
    database_paths = {
        'vcdb': 'databases/VCdb20230126.accdb',
        'pcdb': 'databases/PCdb20230126.accdb',
        'qdb': 'databases/Qdb20230126.accdb'
    }
    
    success = analyze_aces_file('sample_aces.xml', database_paths)
    if success:
        print("Analysis completed successfully")
    else:
        print("Analysis failed")
```

### Example 8: Application Data Analysis

```python
#!/usr/bin/env python3
"""
Example: Analyzing individual applications
"""

from autocare import ACES, VCdb, PCdb, Qdb
import tempfile

def analyze_applications(aces_file_path):
    """Analyze individual applications in ACES file."""
    
    aces = ACES()
    vcdb = VCdb()
    pcdb = PCdb()
    qdb = Qdb()
    
    # Setup and load data (abbreviated for brevity)
    vcdb.connect_local_oledb('databases/VCdb20230126.accdb')
    pcdb.connect_local_oledb('databases/PCdb20230126.accdb')
    qdb.connect_local_oledb('databases/Qdb20230126.accdb')
    
    vcdb.import_oledb_data()
    pcdb.import_oledb()
    qdb.import_oledb()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        aces.import_xml(aces_file_path, "", True, False, {}, {}, temp_dir, True)
        
        print(f"Analyzing {len(aces.apps)} applications...")
        
        # Analyze individual applications
        for i, app in enumerate(aces.apps[:10]):  # First 10 apps
            print(f"\nApplication {i+1}:")
            print(f"  ID: {app.id}")
            print(f"  Action: {app.action}")
            print(f"  Part: {app.part}")
            print(f"  Quantity: {app.quantity}")
            
            # Get vehicle information
            mmy = app.nice_mmy_string(vcdb)
            print(f"  Vehicle: {mmy}")
            
            # Get part type information
            parttype_desc = pcdb.nice_parttype(app.parttype_id)
            position_desc = pcdb.nice_position(app.position_id)
            print(f"  Part Type: {parttype_desc}")
            print(f"  Position: {position_desc}")
            
            # Get fitment string
            fitment = app.nice_full_fitment_string(vcdb, qdb)
            print(f"  Fitment: {fitment}")
            
            # Get attributes
            attributes = app.nice_attributes_string(vcdb, True)
            if attributes:
                print(f"  Attributes: {attributes}")

if __name__ == "__main__":
    analyze_applications('sample_aces.xml')
```

### Example 9: Custom Validation

```python
#!/usr/bin/env python3
"""
Example: Adding custom validation logic
"""

from autocare import ACES, VCdb, PCdb, Qdb, ValidationProblem
import tempfile

class CustomValidator:
    """Custom validation rules for ACES applications."""
    
    def validate_quantity_rules(self, app):
        """Custom quantity validation."""
        problems = []
        
        # Rule: Quantity should not exceed 10 for most parts
        if app.quantity > 10:
            problem = ValidationProblem()
            problem.description = f"High quantity: {app.quantity}"
            problem.app_id = app.id
            problem.severity = "Warning"
            problems.append(problem)
        
        # Rule: Quantity should not be zero
        if app.quantity == 0:
            problem = ValidationProblem()
            problem.description = "Zero quantity"
            problem.app_id = app.id
            problem.severity = "Error"
            problems.append(problem)
            
        return problems
    
    def validate_part_number_format(self, app):
        """Validate part number format."""
        problems = []
        
        # Rule: Part numbers should not contain spaces
        if ' ' in app.part:
            problem = ValidationProblem()
            problem.description = f"Part number contains spaces: '{app.part}'"
            problem.app_id = app.id
            problem.severity = "Warning"
            problems.append(problem)
        
        # Rule: Part numbers should not be too short
        if len(app.part) < 3:
            problem = ValidationProblem()
            problem.description = f"Part number too short: '{app.part}'"
            problem.app_id = app.id
            problem.severity = "Error"
            problems.append(problem)
            
        return problems

def analyze_with_custom_validation(aces_file_path):
    """Analyze ACES file with custom validation."""
    
    aces = ACES()
    vcdb = VCdb()
    pcdb = PCdb()
    qdb = Qdb()
    validator = CustomValidator()
    
    # Setup (abbreviated)
    vcdb.connect_local_oledb('databases/VCdb20230126.accdb')
    pcdb.connect_local_oledb('databases/PCdb20230126.accdb')
    qdb.connect_local_oledb('databases/Qdb20230126.accdb')
    
    vcdb.import_oledb_data()
    pcdb.import_oledb()
    qdb.import_oledb()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        aces.import_xml(aces_file_path, "", True, False, {}, {}, temp_dir, True)
        
        # Apply custom validation
        total_problems = 0
        for app in aces.apps:
            # Run custom validations
            qty_problems = validator.validate_quantity_rules(app)
            part_problems = validator.validate_part_number_format(app)
            
            all_problems = qty_problems + part_problems
            total_problems += len(all_problems)
            
            # Add problems to app
            app.problems_found.extend(all_problems)
            
            # Report problems
            if all_problems:
                print(f"App {app.id} ({app.part}):")
                for problem in all_problems:
                    print(f"  {problem.severity}: {problem.description}")
        
        print(f"\nTotal custom validation problems found: {total_problems}")

if __name__ == "__main__":
    analyze_with_custom_validation('sample_aces.xml')
```

---

## Batch Processing

### Example 10: Batch Processing Script

```bash
#!/bin/bash
# batch_process.sh - Process multiple ACES files

# Configuration
INPUT_DIR="input"
OUTPUT_DIR="output"
TEMP_DIR="temp"
LOGS_DIR="logs"
DATABASES_DIR="databases"

# Database files
VCDB_FILE="$DATABASES_DIR/VCdb20230126.accdb"
PCDB_FILE="$DATABASES_DIR/PCdb20230126.accdb"
QDB_FILE="$DATABASES_DIR/Qdb20230126.accdb"

# Create directories if they don't exist
mkdir -p "$OUTPUT_DIR" "$TEMP_DIR" "$LOGS_DIR"

# Process each XML file in input directory
for file in "$INPUT_DIR"/*.xml; do
    if [ ! -f "$file" ]; then
        echo "No XML files found in $INPUT_DIR"
        break
    fi
    
    echo "Processing: $file"
    
    # Extract filename without path and extension
    basename=$(basename "$file" .xml)
    
    # Run analysis
    python aces_inspector.py \
        -i "$file" \
        -o "$OUTPUT_DIR" \
        -t "$TEMP_DIR" \
        -l "$LOGS_DIR" \
        -v "$VCDB_FILE" \
        -p "$PCDB_FILE" \
        -q "$QDB_FILE" \
        --verbose
    
    # Check result
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "✓ Successfully processed: $file"
        # Move processed file to completed directory
        mkdir -p "$INPUT_DIR/completed"
        mv "$file" "$INPUT_DIR/completed/"
    else
        echo "✗ Failed to process: $file (exit code: $exit_code)"
        # Move failed file to error directory
        mkdir -p "$INPUT_DIR/errors"
        mv "$file" "$INPUT_DIR/errors/"
    fi
    
    echo "----------------------------------------"
done

echo "Batch processing complete"
```

### Example 11: Python Batch Processing

```python
#!/usr/bin/env python3
"""
Python batch processing script
"""

import os
import glob
import shutil
import subprocess
import datetime
from pathlib import Path

class BatchProcessor:
    """Batch process multiple ACES files."""
    
    def __init__(self, config):
        self.config = config
        self.processed_count = 0
        self.failed_count = 0
        self.results = []
    
    def process_files(self):
        """Process all XML files in input directory."""
        
        # Find all XML files
        pattern = os.path.join(self.config['input_dir'], '*.xml')
        xml_files = glob.glob(pattern)
        
        if not xml_files:
            print(f"No XML files found in {self.config['input_dir']}")
            return
        
        print(f"Found {len(xml_files)} files to process")
        
        # Process each file
        for file_path in xml_files:
            result = self.process_single_file(file_path)
            self.results.append(result)
            
            if result['success']:
                self.processed_count += 1
                self._move_file(file_path, 'completed')
            else:
                self.failed_count += 1
                self._move_file(file_path, 'errors')
        
        self._print_summary()
    
    def process_single_file(self, file_path):
        """Process a single ACES file."""
        filename = os.path.basename(file_path)
        print(f"Processing: {filename}")
        
        start_time = datetime.datetime.now()
        
        # Build command
        cmd = [
            'python', 'aces_inspector.py',
            '-i', file_path,
            '-o', self.config['output_dir'],
            '-t', self.config['temp_dir'],
            '-l', self.config['logs_dir'],
            '-v', self.config['vcdb_file'],
            '-p', self.config['pcdb_file'],
            '-q', self.config['qdb_file'],
            '--verbose'
        ]
        
        try:
            # Run analysis
            result = subprocess.run(cmd, capture_output=True, text=True)
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            success = result.returncode == 0
            
            return {
                'filename': filename,
                'success': success,
                'exit_code': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                'filename': filename,
                'success': False,
                'exit_code': -1,
                'duration': duration,
                'stdout': '',
                'stderr': str(e),
                'start_time': start_time,
                'end_time': end_time
            }
    
    def _move_file(self, file_path, subdirectory):
        """Move file to subdirectory."""
        input_dir = self.config['input_dir']
        target_dir = os.path.join(input_dir, subdirectory)
        os.makedirs(target_dir, exist_ok=True)
        
        filename = os.path.basename(file_path)
        target_path = os.path.join(target_dir, filename)
        shutil.move(file_path, target_path)
    
    def _print_summary(self):
        """Print processing summary."""
        total_files = len(self.results)
        
        print("\n" + "="*50)
        print("BATCH PROCESSING SUMMARY")
        print("="*50)
        print(f"Total files: {total_files}")
        print(f"Successfully processed: {self.processed_count}")
        print(f"Failed: {self.failed_count}")
        print(f"Success rate: {(self.processed_count/total_files)*100:.1f}%")
        
        # Show failed files
        if self.failed_count > 0:
            print("\nFailed files:")
            for result in self.results:
                if not result['success']:
                    print(f"  {result['filename']} (exit code: {result['exit_code']})")
        
        # Show timing statistics
        durations = [r['duration'] for r in self.results]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            print(f"\nTiming statistics:")
            print(f"  Average processing time: {avg_duration:.1f}s")
            print(f"  Fastest: {min_duration:.1f}s")
            print(f"  Slowest: {max_duration:.1f}s")

def main():
    """Main batch processing function."""
    config = {
        'input_dir': 'input',
        'output_dir': 'output',
        'temp_dir': 'temp',
        'logs_dir': 'logs',
        'vcdb_file': 'databases/VCdb20230126.accdb',
        'pcdb_file': 'databases/PCdb20230126.accdb',
        'qdb_file': 'databases/Qdb20230126.accdb'
    }
    
    # Create directories
    for dir_path in [config['output_dir'], config['temp_dir'], config['logs_dir']]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Process files
    processor = BatchProcessor(config)
    processor.process_files()

if __name__ == "__main__":
    main()
```

---

## Error Handling

### Example 12: Comprehensive Error Handling

```python
#!/usr/bin/env python3
"""
Example: Comprehensive error handling
"""

import sys
import os
import traceback
from autocare import ACES, VCdb, PCdb, Qdb

def analyze_with_error_handling(aces_file_path, database_paths):
    """Analyze ACES file with comprehensive error handling."""
    
    # Validate inputs
    if not os.path.exists(aces_file_path):
        print(f"Error: ACES file not found: {aces_file_path}")
        return 2  # File access error
    
    for db_name, db_path in database_paths.items():
        if not os.path.exists(db_path):
            print(f"Error: {db_name} database not found: {db_path}")
            return 4  # Database not found
    
    # Initialize components
    aces = ACES()
    vcdb = VCdb()
    pcdb = PCdb()
    qdb = Qdb()
    
    try:
        # Connect to databases with error handling
        print("Connecting to databases...")
        
        vcdb_error = vcdb.connect_local_oledb(database_paths['vcdb'])
        if vcdb_error:
            print(f"Error connecting to VCdb: {vcdb_error}")
            return 4  # Database connection error
        
        pcdb_error = pcdb.connect_local_oledb(database_paths['pcdb'])
        if pcdb_error:
            print(f"Error connecting to PCdb: {pcdb_error}")
            return 4  # Database connection error
        
        qdb_error = qdb.connect_local_oledb(database_paths['qdb'])
        if qdb_error:
            print(f"Error connecting to Qdb: {qdb_error}")
            return 4  # Database connection error
        
        # Import database data with error handling
        print("Loading database data...")
        
        vcdb_import = vcdb.import_oledb_data()
        if vcdb_import != "":
            print(f"Error importing VCdb data: {vcdb_import}")
            return 5  # Database import error
        
        pcdb_import = pcdb.import_oledb()
        if pcdb_import != "":
            print(f"Error importing PCdb data: {pcdb_import}")
            return 5  # Database import error
        
        qdb_import = qdb.import_oledb()
        if qdb_import != "":
            print(f"Error importing Qdb data: {qdb_import}")
            return 5  # Database import error
        
        # Import ACES XML with error handling
        print(f"Importing ACES file: {aces_file_path}")
        
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            import_result = aces.import_xml(
                aces_file_path,
                "",  # Schema string
                True,  # Respect validate="no"
                False,  # Don't discard deletes
                {},  # Part interchange
                {},  # Asset name interchange
                temp_dir,  # Cache path
                True  # Use multi-threading
            )
            
            if import_result != "":
                if "validation" in import_result.lower():
                    print(f"XML validation error: {import_result}")
                    return 6  # XML validation error
                else:
                    print(f"XML import error: {import_result}")
                    return 2  # File access error
            
            print(f"Successfully imported {len(aces.apps)} applications")
            
            # Generate report with error handling
            try:
                output_file = "assessment_report.xml"
                report_result = aces.generate_assessment_file(
                    output_file,
                    vcdb,
                    pcdb,
                    qdb,
                    temp_dir,
                    ""
                )
                
                if report_result != "":
                    print(f"Error generating report: {report_result}")
                    return 3  # Output error
                
                print(f"Assessment report generated: {output_file}")
                return 0  # Success
                
            except PermissionError:
                print(f"Error: Permission denied writing to output file")
                return 3  # Output error
            except OSError as e:
                print(f"Error: File system error: {e}")
                return 3  # Output error
                
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1  # User cancellation
    except MemoryError:
        print("Error: Out of memory - file too large or insufficient RAM")
        return 2  # Memory error
    except Exception as e:
        print(f"Unexpected error: {e}")
        print("Stack trace:")
        traceback.print_exc()
        return 1  # General error
    finally:
        # Always cleanup connections
        try:
            vcdb.disconnect()
            pcdb.disconnect()
            qdb.disconnect()
        except:
            pass  # Ignore cleanup errors

def main():
    """Main function with error handling."""
    if len(sys.argv) < 2:
        print("Usage: python error_handling_example.py <aces_file>")
        return 1
    
    aces_file = sys.argv[1]
    database_paths = {
        'vcdb': 'databases/VCdb20230126.accdb',
        'pcdb': 'databases/PCdb20230126.accdb',
        'qdb': 'databases/Qdb20230126.accdb'
    }
    
    exit_code = analyze_with_error_handling(aces_file, database_paths)
    
    # Print exit code meaning
    exit_meanings = {
        0: "Success",
        1: "General error",
        2: "File access error",
        3: "Output error",
        4: "Database not found",
        5: "Database import error",
        6: "XML validation error"
    }
    
    print(f"Exit code: {exit_code} ({exit_meanings.get(exit_code, 'Unknown')})")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
```

---

## Integration Examples

### Example 13: Web Service Integration

```python
#!/usr/bin/env python3
"""
Example: Simple web service for ACES analysis
"""

from flask import Flask, request, jsonify, send_file
import os
import tempfile
import uuid
from autocare import ACES, VCdb, PCdb, Qdb

app = Flask(__name__)

# Global database instances (loaded once)
vcdb = VCdb()
pcdb = PCdb()
qdb = Qdb()

def initialize_databases():
    """Initialize database connections."""
    vcdb.connect_local_oledb('databases/VCdb20230126.accdb')
    pcdb.connect_local_oledb('databases/PCdb20230126.accdb')
    qdb.connect_local_oledb('databases/Qdb20230126.accdb')
    
    vcdb.import_oledb_data()
    pcdb.import_oledb()
    qdb.import_oledb()

@app.route('/analyze', methods=['POST'])
def analyze_aces():
    """Analyze uploaded ACES file."""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as temp_file:
            file.save(temp_file.name)
            
            # Analyze file
            aces = ACES()
            
            with tempfile.TemporaryDirectory() as temp_dir:
                import_result = aces.import_xml(
                    temp_file.name,
                    "",
                    True,
                    False,
                    {},
                    {},
                    temp_dir,
                    True
                )
                
                if import_result != "":
                    return jsonify({
                        'job_id': job_id,
                        'status': 'error',
                        'error': import_result
                    }), 400
                
                # Generate report
                report_file = f"report_{job_id}.xml"
                report_result = aces.generate_assessment_file(
                    report_file,
                    vcdb,
                    pcdb,
                    qdb,
                    temp_dir,
                    ""
                )
                
                if report_result != "":
                    return jsonify({
                        'job_id': job_id,
                        'status': 'error',
                        'error': report_result
                    }), 500
                
                # Return summary
                return jsonify({
                    'job_id': job_id,
                    'status': 'success',
                    'summary': {
                        'total_apps': len(aces.apps),
                        'total_assets': len(aces.assets),
                        'parttype_errors': aces.parttype_position_errors_count,
                        'qdb_errors': aces.qdb_errors_count,
                        'quantity_outliers': aces.qty_outlier_count
                    },
                    'report_file': report_file
                })
                
    except Exception as e:
        return jsonify({
            'job_id': job_id,
            'status': 'error',
            'error': str(e)
        }), 500
    finally:
        # Clean up uploaded file
        try:
            os.unlink(temp_file.name)
        except:
            pass

@app.route('/report/<job_id>')
def download_report(job_id):
    """Download assessment report."""
    report_file = f"report_{job_id}.xml"
    
    if not os.path.exists(report_file):
        return jsonify({'error': 'Report not found'}), 404
    
    return send_file(report_file, as_attachment=True)

if __name__ == '__main__':
    print("Initializing databases...")
    initialize_databases()
    print("Starting web service...")
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### Example 14: Database Integration

```python
#!/usr/bin/env python3
"""
Example: Store analysis results in database
"""

import sqlite3
import json
from datetime import datetime
from autocare import ACES, VCdb, PCdb, Qdb

class AnalysisDatabase:
    """Store analysis results in SQLite database."""
    
    def __init__(self, db_path='analysis_results.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    total_apps INTEGER,
                    total_assets INTEGER,
                    parttype_errors INTEGER,
                    qdb_errors INTEGER,
                    quantity_outliers INTEGER,
                    processing_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS app_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_run_id INTEGER,
                    app_id INTEGER,
                    error_type TEXT,
                    error_description TEXT,
                    severity TEXT,
                    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (id)
                )
            ''')
    
    def save_analysis_results(self, filename, aces, success=True, error_message=None, processing_time=0):
        """Save analysis results to database."""
        
        metadata = {
            'version': aces.version,
            'company': aces.company,
            'transfer_date': aces.transfer_date,
            'file_md5_hash': aces.file_md5_hash
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert main analysis record
            cursor.execute('''
                INSERT INTO analysis_runs (
                    filename, timestamp, total_apps, total_assets,
                    parttype_errors, qdb_errors, quantity_outliers,
                    processing_time, success, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                filename,
                datetime.now(),
                len(aces.apps),
                len(aces.assets),
                aces.parttype_position_errors_count,
                aces.qdb_errors_count,
                aces.qty_outlier_count,
                processing_time,
                success,
                error_message,
                json.dumps(metadata)
            ))
            
            analysis_run_id = cursor.lastrowid
            
            # Insert individual app errors
            for app in aces.apps:
                for problem in app.problems_found:
                    cursor.execute('''
                        INSERT INTO app_errors (
                            analysis_run_id, app_id, error_type,
                            error_description, severity
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        analysis_run_id,
                        app.id,
                        'validation_error',
                        problem.description,
                        problem.severity
                    ))
            
            conn.commit()
            return analysis_run_id
    
    def get_analysis_history(self, limit=50):
        """Get recent analysis history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filename, timestamp, total_apps, parttype_errors,
                       qdb_errors, quantity_outliers, success
                FROM analysis_runs
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

def analyze_with_database_storage(aces_file_path):
    """Analyze ACES file and store results in database."""
    
    db = AnalysisDatabase()
    start_time = datetime.now()
    
    try:
        # Setup
        aces = ACES()
        vcdb = VCdb()
        pcdb = PCdb()
        qdb = Qdb()
        
        # Connect and load databases
        vcdb.connect_local_oledb('databases/VCdb20230126.accdb')
        pcdb.connect_local_oledb('databases/PCdb20230126.accdb')
        qdb.connect_local_oledb('databases/Qdb20230126.accdb')
        
        vcdb.import_oledb_data()
        pcdb.import_oledb()
        qdb.import_oledb()
        
        # Import and analyze
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            import_result = aces.import_xml(
                aces_file_path, "", True, False, {}, {}, temp_dir, True
            )
            
            if import_result != "":
                # Save failed analysis
                processing_time = (datetime.now() - start_time).total_seconds()
                db.save_analysis_results(
                    aces_file_path, aces, success=False, 
                    error_message=import_result, processing_time=processing_time
                )
                return False
            
            # Successful analysis
            processing_time = (datetime.now() - start_time).total_seconds()
            analysis_id = db.save_analysis_results(
                aces_file_path, aces, success=True, processing_time=processing_time
            )
            
            print(f"Analysis completed and saved with ID: {analysis_id}")
            return True
            
    except Exception as e:
        # Save error
        processing_time = (datetime.now() - start_time).total_seconds()
        db.save_analysis_results(
            aces_file_path, aces, success=False, 
            error_message=str(e), processing_time=processing_time
        )
        raise

if __name__ == "__main__":
    # Example usage
    success = analyze_with_database_storage('sample_aces.xml')
    
    # Show recent history
    db = AnalysisDatabase()
    history = db.get_analysis_history(10)
    
    print("\nRecent analysis history:")
    for record in history:
        status = "✓" if record['success'] else "✗"
        print(f"{status} {record['filename']} - {record['timestamp']} - {record['total_apps']} apps")
```

---

## Performance Optimization

### Example 15: Performance Monitoring

```python
#!/usr/bin/env python3
"""
Example: Performance monitoring and optimization
"""

import time
import psutil
import tracemalloc
from autocare import ACES, VCdb, PCdb, Qdb

class PerformanceMonitor:
    """Monitor performance during ACES analysis."""
    
    def __init__(self):
        self.start_time = None
        self.checkpoints = []
        self.process = psutil.Process()
    
    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        tracemalloc.start()
        self.checkpoint("Start")
    
    def checkpoint(self, name):
        """Record a performance checkpoint."""
        current_time = time.time()
        if self.start_time:
            elapsed = current_time - self.start_time
        else:
            elapsed = 0
        
        memory_info = self.process.memory_info()
        
        # Get memory trace if available
        try:
            current, peak = tracemalloc.get_traced_memory()
            traced_memory = {
                'current': current / 1024 / 1024,  # MB
                'peak': peak / 1024 / 1024  # MB
            }
        except:
            traced_memory = None
        
        checkpoint = {
            'name': name,
            'time': current_time,
            'elapsed': elapsed,
            'memory_rss': memory_info.rss / 1024 / 1024,  # MB
            'memory_vms': memory_info.vms / 1024 / 1024,  # MB
            'traced_memory': traced_memory
        }
        
        self.checkpoints.append(checkpoint)
        print(f"[{elapsed:.1f}s] {name} - Memory: {checkpoint['memory_rss']:.1f}MB")
    
    def stop(self):
        """Stop monitoring and print summary."""
        self.checkpoint("End")
        tracemalloc.stop()
        
        print("\nPerformance Summary:")
        print("="*50)
        
        total_time = self.checkpoints[-1]['elapsed']
        peak_memory = max(cp['memory_rss'] for cp in self.checkpoints)
        
        print(f"Total time: {total_time:.1f}s")
        print(f"Peak memory: {peak_memory:.1f}MB")
        
        print("\nCheckpoints:")
        for i, cp in enumerate(self.checkpoints):
            if i > 0:
                time_diff = cp['elapsed'] - self.checkpoints[i-1]['elapsed']
                print(f"  {cp['name']}: {time_diff:.1f}s (+{cp['memory_rss']:.1f}MB)")

def analyze_with_performance_monitoring(aces_file_path):
    """Analyze ACES file with performance monitoring."""
    
    monitor = PerformanceMonitor()
    monitor.start()
    
    try:
        # Initialize components
        aces = ACES()
        vcdb = VCdb()
        pcdb = PCdb()
        qdb = Qdb()
        
        monitor.checkpoint("Components initialized")
        
        # Connect to databases
        vcdb.connect_local_oledb('databases/VCdb20230126.accdb')
        pcdb.connect_local_oledb('databases/PCdb20230126.accdb')
        qdb.connect_local_oledb('databases/Qdb20230126.accdb')
        
        monitor.checkpoint("Database connections")
        
        # Import database data
        vcdb.import_oledb_data()
        monitor.checkpoint("VCdb imported")
        
        pcdb.import_oledb()
        monitor.checkpoint("PCdb imported")
        
        qdb.import_oledb()
        monitor.checkpoint("Qdb imported")
        
        # Import ACES XML
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            import_result = aces.import_xml(
                aces_file_path, "", True, False, {}, {}, temp_dir, True
            )
            
            monitor.checkpoint("ACES XML imported")
            
            if import_result != "":
                print(f"Import failed: {import_result}")
                return False
            
            # Generate report
            report_file = "performance_test_report.xml"
            report_result = aces.generate_assessment_file(
                report_file, vcdb, pcdb, qdb, temp_dir, ""
            )
            
            monitor.checkpoint("Report generated")
            
            if report_result != "":
                print(f"Report generation failed: {report_result}")
                return False
            
            print(f"Successfully processed {len(aces.apps)} applications")
            return True
            
    finally:
        monitor.stop()

if __name__ == "__main__":
    analyze_with_performance_monitoring('sample_aces.xml')
```

---

**Version**: 1.0.0.21 (Python Port)  
**Last Updated**: Current Date  
**Status**: Production Ready

These examples demonstrate the versatility and power of the ACES Inspector CLI Python port across different usage scenarios and integration patterns.