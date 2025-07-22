# ACES Inspector CLI - System Architecture

## Overview

The ACES Inspector CLI Python port is a command-line tool for analyzing Automotive Catalog Exchange Standard (ACES) XML files. This document provides a comprehensive overview of the system architecture, component relationships, and data flow.

## High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Command Line  │───▶│   Main Process   │───▶│   File Output   │
│   Interface     │    │   (aces_inspector│    │   (Excel/Logs)  │
│                 │    │    .py)          │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Analysis Engine                          │
│                     (autocare.py)                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│     ACES        │      VCdb       │         PCdb/Qdb             │
│   Container     │   (Vehicle      │      (Part/Qualifier        │
│                 │  Configuration) │       Databases)            │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Database Layer                              │
│              (Microsoft Access via ODBC)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Entry Point Layer

#### aces_inspector.py
**Purpose**: Command-line interface and main program flow orchestration.

**Responsibilities**:
- Parse command-line arguments
- Validate input parameters
- Initialize core components
- Orchestrate analysis workflow
- Handle errors and return appropriate exit codes
- Generate output files

**Key Functions**:
- `main()` - Primary entry point
- `escape_xml_special_chars()` - XML encoding utilities
- Argument parsing and validation
- File path handling

### 2. Core Analysis Engine

#### autocare.py
**Purpose**: Contains all core business logic and data structures.

**Main Classes**:

#### 2.1 Data Structure Classes

##### VCdbAttribute
```python
@dataclass
class VCdbAttribute:
    name: str = ""
    value: int = 0
```
**Purpose**: Represents vehicle configuration attributes from VCdb.

##### QdbQualifier  
```python
@dataclass
class QdbQualifier:
    qualifier_id: int = 0
    qualifier_parameters: List[str] = field(default_factory=list)
```
**Purpose**: Represents qualifiers with parameters from Qdb.

##### BaseVehicle
```python
@dataclass
class BaseVehicle:
    id: int = 0
    make_id: int = 0
    model_id: int = 0
    year: int = 0
```
**Purpose**: Vehicle identification information.

##### ValidationProblem
```python
@dataclass
class ValidationProblem:
    description: str = ""
    app_id: int = 0
    severity: str = ""
```
**Purpose**: Represents validation errors found during analysis.

#### 2.2 Business Logic Classes

##### App Class
**Purpose**: Represents individual ACES applications.

**Key Properties**:
- `id`, `action`, `basevehicle_id` - Basic identification
- `parttype_id`, `position_id`, `quantity` - Part information
- `vcdb_attributes` - Vehicle configuration attributes
- `qdb_qualifiers` - Applied qualifiers
- `notes` - Application notes

**Key Methods**:
- `nice_attributes_string()` - Human-readable attribute formatting
- `clear()` - Reset application data

##### Asset Class
**Purpose**: Represents ACES assets (digital assets like images).

**Key Properties**:
- Asset identification and metadata
- Base vehicle associations
- VCdb attributes and Qdb qualifiers

##### ACES Class
**Purpose**: Main container and analysis orchestrator.

**Core Data Structures**:
```python
# Main collections
self.apps: List[App] = []
self.assets: List[Asset] = []

# Analysis results
self.parts_app_counts: Dict[str, int] = {}
self.basevid_occurrences: Dict[int, int] = {}
self.qdbid_occurrences: Dict[int, int] = {}

# Error tracking
self.qty_outlier_count = 0
self.parttype_position_errors_count = 0
self.qdb_errors_count = 0
```

**Key Methods**:
- `import_xml()` - Parse ACES XML files
- `find_individual_app_errors()` - Validate individual applications
- `analyze_qty_outliers()` - Statistical quantity analysis
- `analyze_fitment_logic()` - Fitment validation
- `generate_assessment_report()` - Excel report generation

#### 2.3 Database Interface Classes

##### VCdb Class
**Purpose**: Vehicle Configuration Database interface.

**Key Properties**:
```python
self.vcdb_basevehicle_dict: Dict[int, BaseVehicle] = {}
self.basevehicle_make_dict: Dict[int, str] = {}
self.basevehicle_model_dict: Dict[int, str] = {}
self.basevehicle_year_dict: Dict[int, int] = {}
```

**Key Methods**:
- `import_from_access()` - Load VCdb data from Access database
- `nice_make_of_basevid()` - Get vehicle make name
- `nice_model_of_basevid()` - Get vehicle model name
- `nice_year_of_basevid()` - Get vehicle year

##### PCdb Class
**Purpose**: Part Configuration Database interface.

**Key Properties**:
```python
self.parttypes: Dict[int, str] = {}
self.positions: Dict[int, str] = {}
self.codemaster_parttype_positions: Dict[str, bool] = {}
```

**Key Methods**:
- `import_from_access()` - Load PCdb data
- `nice_parttype()` - Get part type description
- `nice_position()` - Get position description

##### Qdb Class
**Purpose**: Qualifier Database interface.

**Key Properties**:
```python
self.qualifiers: Dict[int, str] = {}
self.qualifier_groups: Dict[int, List[int]] = {}
```

**Key Methods**:
- `import_from_access()` - Load Qdb data
- `nice_qualifier()` - Get qualifier description

## Data Flow Architecture

### 1. Initialization Phase
```
Command Line Args → Validation → Database Loading → ACES Object Creation
```

### 2. Import Phase
```
XML File → XML Parser → App/Asset Objects → ACES Container → Hash Generation
```

### 3. Analysis Phase
```
Apps Collection → Individual Validation → Quantity Analysis → Fitment Analysis → Error Collection
```

### 4. Output Phase
```
Analysis Results → Excel Spreadsheet Generation → Log File Writing → Cache File Cleanup
```

## Analysis Pipeline

### Individual Application Analysis
1. **Part Type/Position Validation**
   - Validate part type IDs against PCdb
   - Validate position IDs against PCdb
   - Check part type/position combinations

2. **VCdb Configuration Validation**
   - Validate base vehicle IDs
   - Check vehicle attribute combinations
   - Verify configuration completeness

3. **Qdb Qualifier Validation**
   - Validate qualifier IDs
   - Check parameter requirements
   - Verify qualifier applicability

### Statistical Analysis
1. **Quantity Outlier Detection**
   - Calculate statistical thresholds
   - Identify quantity anomalies
   - Flag potential data entry errors

2. **Usage Statistics**
   - Track base vehicle ID usage
   - Monitor qualifier utilization
   - Generate coverage reports

### Fitment Logic Analysis
1. **Tree Construction**
   - Build fitment hierarchy
   - Identify logical relationships
   - Detect contradictions

2. **Permutation Mining**
   - Generate possible configurations
   - Identify missing combinations
   - Flag logical inconsistencies

## Threading and Performance

### Multi-Threading Strategy
- **Analysis Chunks**: Large datasets divided into manageable chunks
- **Parallel Processing**: Independent analysis tasks run concurrently
- **Thread Pool**: Managed via `concurrent.futures.ThreadPoolExecutor`

### Memory Management
- **In-Memory Caching**: Database lookups cached for performance
- **Temporary Files**: Large analysis results written to disk
- **Cleanup**: Automatic temporary file removal

## File I/O Architecture

### Input Processing
- **XML Parsing**: `xml.etree.ElementTree` and `lxml` for validation
- **Database Access**: `pyodbc` for Microsoft Access files
- **Schema Validation**: Multiple ACES schema versions supported

### Output Generation
- **Excel XML Format**: Compatible spreadsheet generation
- **Log Files**: Structured logging with timestamps
- **Cache Files**: Temporary analysis results storage

## Error Handling Strategy

### Exception Categories
1. **File Access Errors** (Return Code 2/3)
2. **Database Errors** (Return Code 4/5)
3. **XML Validation Errors** (Return Code 6)
4. **Analysis Errors** (Logged, processing continues)

### Error Recovery
- **Graceful Degradation**: Continue analysis when possible
- **Detailed Logging**: Comprehensive error reporting
- **Cleanup**: Ensure temporary files are removed

## Configuration Management

### Database Configuration
- **VCdb**: Vehicle configuration data
- **PCdb**: Part type and position data
- **Qdb**: Qualifier definitions

### Analysis Parameters
- **Quantity Thresholds**: Configurable outlier detection
- **Validation Settings**: Strict vs. permissive modes
- **Performance Settings**: Thread counts, chunk sizes

## Extensibility Points

### Custom Analysis
- **Validation Rules**: Add new validation logic
- **Statistical Methods**: Implement new outlier detection
- **Report Formats**: Additional output formats

### Database Support
- **Alternative Databases**: SQLite, PostgreSQL support
- **Cloud Integration**: Remote database connectivity
- **Caching Strategies**: Redis, Memcached integration

## Security Considerations

### File Access
- **Path Validation**: Prevent directory traversal
- **Permission Checks**: Verify read/write access
- **Temporary Files**: Secure temporary directory usage

### Database Security
- **Connection Strings**: Secure credential handling
- **SQL Injection**: Parameterized queries
- **Access Control**: Minimum required permissions

## Dependencies

### Core Dependencies
- **lxml**: XML processing and validation
- **pyodbc**: Database connectivity
- **xlsxwriter/openpyxl**: Excel file generation

### System Dependencies
- **Microsoft Access ODBC Driver**: Database connectivity
- **Python 3.8+**: Modern Python features

## Future Architecture Enhancements

### Scalability Improvements
- **Microservices**: Break into independent services
- **Message Queues**: Async processing pipelines
- **Horizontal Scaling**: Multiple worker processes

### Cloud Integration
- **Container Support**: Docker deployment
- **Cloud Storage**: S3, Azure Blob integration
- **Managed Databases**: Cloud database services

### API Development
- **REST API**: Web service interface
- **GraphQL**: Flexible query interface
- **WebSocket**: Real-time analysis updates

---

**Last Updated**: Current Date  
**Version**: 1.0.0.21 (Python Port)  
**Status**: Production Ready