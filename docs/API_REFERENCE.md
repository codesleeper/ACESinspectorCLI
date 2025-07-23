# ACES Inspector CLI - API Reference

## Overview

This document provides a comprehensive API reference for all classes, methods, and data structures in the ACES Inspector CLI Python project.

## Table of Contents

1. [Data Structure Classes](#data-structure-classes)
2. [Main Business Logic Classes](#main-business-logic-classes)
3. [Database Interface Classes](#database-interface-classes)
4. [Analysis and Processing Classes](#analysis-and-processing-classes)
5. [Utility Functions](#utility-functions)

---

## Data Structure Classes

### VCdbAttribute

Represents a vehicle configuration attribute from the VCdb database.

```python
@dataclass
class VCdbAttribute:
    name: str = ""
    value: int = 0
```

#### Properties
- **name** (`str`): The attribute name (e.g., "SubModel", "EngineBase")
- **value** (`int`): The attribute value ID

#### Methods

##### `__lt__(self, other) -> bool`
Comparison method for sorting VCdbAttribute objects.

**Parameters:**
- `other` (`VCdbAttribute`): Another VCdbAttribute to compare against

**Returns:**
- `bool`: True if this attribute should sort before the other

**Usage:**
```python
attr1 = VCdbAttribute("EngineBase", 123)
attr2 = VCdbAttribute("SubModel", 456)
sorted_attrs = sorted([attr1, attr2])
```

---

### QdbQualifier

Represents a qualifier from the Qdb database with associated parameters.

```python
@dataclass
class QdbQualifier:
    qualifier_id: int = 0
    qualifier_parameters: List[str] = field(default_factory=list)
```

#### Properties
- **qualifier_id** (`int`): The unique qualifier ID
- **qualifier_parameters** (`List[str]`): List of parameter values for the qualifier

#### Methods

##### `__init__(self)`
Initialize a new QdbQualifier instance.

**Usage:**
```python
qualifier = QdbQualifier()
qualifier.qualifier_id = 123
qualifier.qualifier_parameters = ["value1", "value2"]
```

---

### ValidationProblem

Represents a validation error or warning found during analysis.

```python
@dataclass
class ValidationProblem:
    description: str = ""
    app_id: int = 0
    severity: str = ""
```

#### Properties
- **description** (`str`): Human-readable problem description
- **app_id** (`int`): ID of the application with the problem
- **severity** (`str`): Problem severity level

---

### BaseVehicle

Represents basic vehicle identification information.

```python
@dataclass
class BaseVehicle:
    id: int = 0
    make_id: int = 0
    model_id: int = 0
    year: int = 0
```

#### Properties
- **id** (`int`): Unique base vehicle ID
- **make_id** (`int`): Vehicle make ID
- **model_id** (`int`): Vehicle model ID
- **year** (`int`): Vehicle year

---

### FitmentNode

Represents a node in the fitment analysis tree structure.

```python
@dataclass
class FitmentNode:
    id: int = 0
    parent_id: int = 0
    level: int = 0
    fitment_element: str = ""
    fitment_element_string: str = ""
    app_count: int = 0
    marked_as_cosmetic: bool = False
```

#### Methods

##### `is_complementary_to(self, other_node: 'FitmentNode') -> bool`
Check if this node is complementary to another node in fitment logic.

##### `is_equal_to(self, other_node: 'FitmentNode') -> bool`
Check if this node is equal to another node.

##### `node_hash(self) -> str`
Generate a unique hash for this fitment node.

---

## Main Business Logic Classes

### App

Represents an individual ACES application with all associated data.

```python
class App:
    def __init__(self):
        self.id = 0
        self.type = 1  # 1=basevehicle, 2=equipmentbase, 3=Mfr/Equipment Model/Vehicle Type
        self.reference = ""
        self.action = ""
        self.validate = True
        self.basevehicle_id = 0
        self.parttype_id = 0
        self.position_id = 0
        self.quantity = 0
        self.part = ""
        self.mfr_label = ""
        self.asset = ""
        self.asset_item_order = 0
        self.asset_item_ref = ""
        self.vcdb_attributes: List[VCdbAttribute] = []
        self.qdb_qualifiers: List[QdbQualifier] = []
        self.notes: List[str] = []
        self.contains_vcdb_violation = False
        self.has_been_validated = False
        self.problems_found: List[ValidationProblem] = []
        self.hash = ""
        self.brand = ""
        self.subbrand = ""
```

#### Core Properties
- **id** (`int`): Unique application ID
- **action** (`str`): Application action ("A" for add, "D" for delete)
- **basevehicle_id** (`int`): Associated base vehicle ID
- **parttype_id** (`int`): Part type identifier
- **position_id** (`int`): Position identifier
- **quantity** (`int`): Quantity of parts
- **part** (`str`): Part number
- **vcdb_attributes** (`List[VCdbAttribute]`): Vehicle configuration attributes
- **qdb_qualifiers** (`List[QdbQualifier]`): Applied qualifiers

#### Methods

##### `clear(self)`
Reset all application data to default values.

**Usage:**
```python
app = App()
app.id = 123
app.clear()  # Resets all properties
```

##### `nice_attributes_string(self, vcdb: 'VCdb', include_notes: bool) -> str`
Generate human-readable attributes string.

**Parameters:**
- `vcdb` (`VCdb`): VCdb instance for attribute lookups
- `include_notes` (`bool`): Whether to include notes in output

**Returns:**
- `str`: Formatted attribute string

##### `name_val_pair_string(self, include_notes: bool) -> str`
Generate CSS-style name:value pairs string.

##### `raw_qdb_data_string(self) -> str`
Generate raw qualifier data string.

##### `nice_qdb_qualifier_string(self, qdb: 'Qdb') -> str`
Generate human-readable qualifier string.

##### `nice_full_fitment_string(self, vcdb: 'VCdb', qdb: 'Qdb') -> str`
Generate complete fitment description string.

##### `nice_mmy_string(self, vcdb: 'VCdb') -> str`
Generate Make/Model/Year string from base vehicle ID.

##### `app_hash(self) -> str`
Generate unique hash for this application.

---

### Asset

Represents an ACES asset (digital content like images, documents).

```python
class Asset:
    def __init__(self):
        self.id = 0
        self.action = ""
        self.asset_name = ""
        self.basevehicle_id = 0
        self.vcdb_attributes: List[VCdbAttribute] = []
        self.qdb_qualifiers: List[QdbQualifier] = []
        self.notes: List[str] = []
```

#### Methods

##### `nice_full_fitment_string(self, vcdb: 'VCdb', qdb: 'Qdb') -> str`
Generate complete fitment description for the asset.

##### `nice_attributes_string(self, vcdb: 'VCdb', include_notes: bool) -> str`
Generate human-readable attributes string for the asset.

##### `nice_qdb_qualifier_string(self, qdb: 'Qdb') -> str`
Generate human-readable qualifier string for the asset.

---

### ACES

Main container class that orchestrates all ACES file operations and analysis.

```python
class ACES:
    def __init__(self):
        # Initialization of all properties and collections
```

#### Core Collections
- **apps** (`List[App]`): All applications in the ACES file
- **assets** (`List[Asset]`): All assets in the ACES file
- **parts_app_counts** (`Dict[str, int]`): Part number usage statistics
- **basevid_occurrences** (`Dict[int, int]`): Base vehicle ID usage counts

#### Key Methods

##### `import_xml(self, file_path: str, schema_string: str, respect_validate_no_tag: bool, discard_deletes: bool, interchange: Dict[str, str], asset_name_interchange: Dict[str, str], cache_path: str, use_multi_threading: bool) -> str`

Import and parse an ACES XML file.

**Parameters:**
- `file_path` (`str`): Path to the ACES XML file
- `schema_string` (`str`): XSD schema for validation
- `respect_validate_no_tag` (`bool`): Whether to respect validate="no" attributes
- `discard_deletes` (`bool`): Whether to discard delete applications
- `interchange` (`Dict[str, str]`): Part number interchange mapping
- `asset_name_interchange` (`Dict[str, str]`): Asset name mapping
- `cache_path` (`str`): Path for temporary cache files
- `use_multi_threading` (`bool`): Enable multi-threaded processing

**Returns:**
- `str`: Error message if import fails, empty string on success

**Usage:**
```python
aces = ACES()
result = aces.import_xml(
    "sample.xml", 
    "", 
    True, 
    False, 
    {}, 
    {}, 
    "/tmp", 
    True
)
if result == "":
    print("Import successful")
else:
    print(f"Import failed: {result}")
```

##### `find_individual_app_errors(self, chunk: AnalysisChunk, vcdb: VCdb, pcdb: PCdb, qdb: Qdb)`

Analyze individual applications for validation errors.

**Parameters:**
- `chunk` (`AnalysisChunk`): Chunk of applications to analyze
- `vcdb` (`VCdb`): Vehicle Configuration Database interface
- `pcdb` (`PCdb`): Part Configuration Database interface
- `qdb` (`Qdb`): Qualifier Database interface

##### `find_individual_app_outliers(self, chunk: AnalysisChunk, vcdb: VCdb, pcdb: PCdb, qdb: Qdb)`

Find quantity outliers and other statistical anomalies.

##### `find_fitment_logic_problems(self, chunk_group: AnalysisChunkGroup, vcdb: VCdb, pcdb: PCdb, qdb: Qdb, cache_path: str)`

Analyze fitment logic for contradictions and problems.

##### `export_flat_apps(self, file_path: str, vcdb: VCdb, pcdb: PCdb, qdb: Qdb, delimiter: str, format_type: str) -> str`

Export applications to flat file format.

**Parameters:**
- `file_path` (`str`): Output file path
- `vcdb`, `pcdb`, `qdb`: Database interfaces
- `delimiter` (`str`): Field delimiter (tab, comma, etc.)
- `format_type` (`str`): Output format type

##### `export_xml_apps(self, file_path: str, submission_type: str, cipher_file_path: str, anonymize: bool) -> str`

Export applications to ACES XML format.

##### `generate_assessment_file(self, file_path: str, vcdb: 'VCdb', pcdb: 'PCdb', qdb: 'Qdb', cache_path: str, log_indent: str) -> str`

Generate comprehensive assessment report in Excel XML format.

---

## Database Interface Classes

### VCdb

Interface to Vehicle Configuration Database.

```python
class VCdb:
    def __init__(self):
        self.import_success = False
        self.vcdb_basevehicle_dict: Dict[int, BaseVehicle] = {}
        self.basevehicle_make_dict: Dict[int, str] = {}
        self.basevehicle_model_dict: Dict[int, str] = {}
        self.basevehicle_year_dict: Dict[int, int] = {}
        # ... other properties
```

#### Methods

##### `connect_local_oledb(self, path: str) -> str`
Connect to local Microsoft Access database file.

**Parameters:**
- `path` (`str`): Path to Access database file

**Returns:**
- `str`: Error message if connection fails, empty string on success

##### `import_oledb_data(self) -> str`
Import all VCdb data from connected database.

##### `nice_make_of_basevid(self, base_vid: int) -> str`
Get human-readable make name for base vehicle ID.

##### `nice_model_of_basevid(self, base_vid: int) -> str`
Get human-readable model name for base vehicle ID.

##### `nice_year_of_basevid(self, base_vid: int) -> str`
Get year string for base vehicle ID.

##### `nice_attribute(self, attribute: VCdbAttribute) -> str`
Get human-readable attribute description.

##### `valid_attribute(self, attribute: VCdbAttribute) -> bool`
Check if attribute is valid in VCdb.

##### `config_is_valid_memory_based(self, app: App) -> bool`
Validate vehicle configuration using in-memory data.

---

### PCdb

Interface to Part Configuration Database.

```python
class PCdb:
    def __init__(self):
        self.import_success = False
        self.parttypes: Dict[int, str] = {}
        self.positions: Dict[int, str] = {}
        self.codemaster_parttype_positions: Dict[str, bool] = {}
```

#### Methods

##### `import_oledb(self) -> str`
Import PCdb data from connected Access database.

##### `nice_parttype(self, parttype_id: int) -> str`
Get human-readable part type description.

##### `nice_position(self, position_id: int) -> str`
Get human-readable position description.

---

### Qdb

Interface to Qualifier Database.

```python
class Qdb:
    def __init__(self):
        self.import_success = False
        self.qualifiers: Dict[int, str] = {}
        self.qualifier_groups: Dict[int, List[int]] = {}
```

#### Methods

##### `import_oledb(self) -> str`
Import Qdb data from connected Access database.

##### `nice_qdb_qualifier(self, qualifier_id: int, parameters: List[str]) -> str`
Get human-readable qualifier description with parameters.

---

## Analysis and Processing Classes

### AnalysisChunk

Represents a chunk of applications for parallel processing.

```python
@dataclass
class AnalysisChunk:
    id: int = 0
    app_count: int = 0
    qty_outlier_count: int = 0
    parttype_position_errors_count: int = 0
    qdb_errors_count: int = 0
    vcdb_configurations_errors_count: int = 0
    vcdb_codes_errors_count: int = 0
    basevehicleids_errors_count: int = 0
    cache_file: str = ""
    apps_list: List[App] = field(default_factory=list)
```

### AnalysisChunkGroup

Groups related analysis chunks for fitment logic analysis.

```python
@dataclass
class AnalysisChunkGroup:
    id: int = 0
    chunk_count: int = 0
    fitment_logic_problems_count: int = 0
    cache_path: str = ""
```

---

## Utility Functions

### Module-Level Functions

#### `escape_xml_special_chars(input_string: str) -> str`
**Location**: `aces_inspector.py`

Escape XML special characters in a string.

**Parameters:**
- `input_string` (`str`): String to escape

**Returns:**
- `str`: XML-escaped string

**Usage:**
```python
from aces_inspector import escape_xml_special_chars
escaped = escape_xml_special_chars("R&D <test>")
# Returns: "R&amp;D &lt;test&gt;"
```

#### `get_version() -> str`
**Location**: `aces_inspector.py`

Get the current version string.

**Returns:**
- `str`: Version string

---

## Error Handling

### Return Codes
All main functions return standardized error codes:

- **0**: Successful operation
- **1**: Missing command line arguments
- **2**: Input file access problems
- **3**: Output directory access problems
- **4**: Reference database not found
- **5**: Reference database import failure
- **6**: XML XSD validation failure

### Exception Handling
Most methods handle exceptions gracefully and return error messages rather than raising exceptions. Always check return values for error conditions.

---

## Usage Examples

### Basic Usage Pattern

```python
from autocare import ACES, VCdb, PCdb, Qdb

# Initialize components
aces = ACES()
vcdb = VCdb()
pcdb = PCdb()
qdb = Qdb()

# Connect to databases
vcdb_error = vcdb.connect_local_oledb("VCdb.accdb")
pcdb_error = pcdb.connect_local_oledb("PCdb.accdb") 
qdb_error = qdb.connect_local_oledb("Qdb.accdb")

if not any([vcdb_error, pcdb_error, qdb_error]):
    # Import database data
    vcdb.import_oledb_data()
    pcdb.import_oledb()
    qdb.import_oledb()
    
    # Import ACES XML
    import_result = aces.import_xml(
        "sample.xml", "", True, False, {}, {}, "/tmp", True
    )
    
    if import_result == "":
        # Generate assessment report
        report_result = aces.generate_assessment_file(
            "assessment.xml", vcdb, pcdb, qdb, "/tmp", ""
        )
        print(f"Assessment complete: {report_result}")
```

### Application Analysis

```python
# Analyze individual applications
for app in aces.apps:
    # Get formatted vehicle info
    mmy = app.nice_mmy_string(vcdb)
    
    # Get part type description
    parttype_desc = pcdb.nice_parttype(app.parttype_id)
    
    # Get fitment string
    fitment = app.nice_full_fitment_string(vcdb, qdb)
    
    print(f"App {app.id}: {mmy} - {parttype_desc} - {fitment}")
```

---

**Version**: 1.0.0.21 (Python Port)  
**Last Updated**: Current Date  
**Status**: Production Ready