# ACES Inspector CLI - Developer Guide

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Code Architecture](#code-architecture)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [Code Quality](#code-quality)
7. [Contributing Guidelines](#contributing-guidelines)
8. [Extending the System](#extending-the-system)
9. [Release Process](#release-process)
10. [Troubleshooting Development Issues](#troubleshooting-development-issues)

---

## Development Environment Setup

### Prerequisites

- **Python 3.8+** with development headers
- **Git** for version control
- **Microsoft Access ODBC Driver** for database connectivity
- **IDE/Editor** with Python support (VS Code, PyCharm, etc.)

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd aces-inspector-python

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Install in development mode
pip install -e .
```

### Development Dependencies

Create `requirements-dev.txt`:
```
# Testing
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0

# Code Quality
black>=22.0.0
flake8>=5.0.0
mypy>=1.0.0
isort>=5.10.0

# Documentation
sphinx>=5.0.0
sphinx-rtd-theme>=1.2.0

# Development Tools
pre-commit>=2.20.0
tox>=4.0.0
```

### IDE Configuration

#### VS Code Settings
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true
}
```

#### PyCharm Configuration
- Set project interpreter to virtual environment
- Enable code inspections for Python
- Configure Black as code formatter
- Set up pytest as test runner

---

## Project Structure

### Directory Layout

```
aces-inspector-python/
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── USER_GUIDE.md
│   └── DEVELOPER_GUIDE.md
├── tests/                  # Test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── fixtures/          # Test data
│   └── conftest.py        # Pytest configuration
├── scripts/               # Utility scripts
│   ├── setup_dev.sh       # Development setup
│   └── run_tests.sh       # Test runner
├── examples/              # Usage examples
│   ├── basic_usage.py
│   └── batch_processing.py
├── aces_inspector.py      # Main entry point
├── autocare.py           # Core business logic
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── setup.py             # Package setup
├── pyproject.toml       # Modern Python project config
├── .gitignore           # Git ignore rules
├── .pre-commit-config.yaml  # Pre-commit hooks
├── README.md            # Project overview
└── plan.md             # Documentation plan
```

### Key Files

#### Core Modules
- **`aces_inspector.py`**: Command-line interface and main orchestration
- **`autocare.py`**: Core classes and business logic

#### Configuration Files
- **`pyproject.toml`**: Modern Python project configuration
- **`setup.py`**: Package setup and metadata
- **`requirements.txt`**: Production dependencies

#### Development Files
- **`.pre-commit-config.yaml`**: Code quality hooks
- **`tox.ini`**: Testing across Python versions
- **`mypy.ini`**: Type checking configuration

---

## Code Architecture

### Design Principles

1. **Separation of Concerns**: Clear boundaries between modules
2. **Single Responsibility**: Each class has one primary purpose
3. **Open/Closed Principle**: Extensible without modification
4. **Dependency Injection**: Configurable dependencies
5. **Error Handling**: Graceful degradation and recovery

### Module Dependencies

```
aces_inspector.py
    ↓
autocare.py
    ├── ACES (main container)
    ├── App (application data)
    ├── Asset (asset data)
    ├── VCdb (vehicle database)
    ├── PCdb (part database)
    └── Qdb (qualifier database)
```

### Class Relationships

```python
# Main container aggregates all components
class ACES:
    apps: List[App]
    assets: List[Asset]
    
    def analyze(self, vcdb: VCdb, pcdb: PCdb, qdb: Qdb):
        # Orchestrate analysis using database interfaces
        pass

# Database interfaces provide data access
class VCdb:
    def nice_make_of_basevid(self, base_vid: int) -> str:
        # Vehicle data lookup
        pass

# Data structures represent domain entities
class App:
    vcdb_attributes: List[VCdbAttribute]
    qdb_qualifiers: List[QdbQualifier]
```

---

## Development Workflow

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-analysis-algorithm

# Make changes and commit
git add .
git commit -m "Add quantity outlier detection algorithm"

# Push and create pull request
git push origin feature/new-analysis-algorithm
```

### Code Style

#### Python Style Guide
- Follow **PEP 8** conventions
- Use **Black** for automatic formatting
- Use **isort** for import sorting
- Maximum line length: 88 characters

#### Naming Conventions
```python
# Classes: PascalCase
class VehicleConfigurationDatabase:
    pass

# Functions/methods: snake_case
def analyze_fitment_logic():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_ANALYSIS_THREADS = 4

# Private methods: leading underscore
def _parse_xml_node():
    pass
```

#### Type Hints
```python
from typing import List, Dict, Optional, Union

def analyze_applications(
    apps: List[App], 
    vcdb: VCdb,
    config: Optional[Dict[str, str]] = None
) -> Tuple[int, List[ValidationProblem]]:
    """Analyze applications for errors."""
    pass
```

### Pre-commit Hooks

Setup `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

Install hooks:
```bash
pre-commit install
```

---

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_app.py           # App class tests
│   ├── test_aces.py          # ACES class tests
│   ├── test_vcdb.py          # VCdb class tests
│   └── test_utilities.py     # Utility function tests
├── integration/
│   ├── test_full_workflow.py # End-to-end tests
│   └── test_database_integration.py
├── fixtures/
│   ├── sample_aces.xml       # Test ACES files
│   ├── test_vcdb.accdb       # Test databases
│   └── expected_outputs/     # Expected results
└── conftest.py              # Shared test configuration
```

### Unit Testing

```python
# tests/unit/test_app.py
import pytest
from autocare import App, VCdbAttribute

class TestApp:
    def test_app_initialization(self):
        """Test App class initialization."""
        app = App()
        assert app.id == 0
        assert app.action == ""
        assert len(app.vcdb_attributes) == 0

    def test_app_clear(self):
        """Test App clear method."""
        app = App()
        app.id = 123
        app.part = "ABC123"
        app.clear()
        assert app.id == 0
        assert app.part == ""

    def test_app_hash_generation(self):
        """Test App hash generation."""
        app = App()
        app.id = 123
        app.part = "ABC123"
        hash_value = app.app_hash()
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
```

### Integration Testing

```python
# tests/integration/test_full_workflow.py
import tempfile
import os
from autocare import ACES, VCdb, PCdb, Qdb

class TestFullWorkflow:
    def test_complete_analysis_workflow(self):
        """Test complete analysis workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup test data
            aces = ACES()
            vcdb = VCdb()
            pcdb = PCdb()
            qdb = Qdb()
            
            # Load test databases (mock or test files)
            # Import test ACES file
            # Run analysis
            # Verify results
            pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=autocare --cov-report=html

# Run specific test file
pytest tests/unit/test_app.py

# Run tests with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_app"
```

### Test Configuration

`conftest.py`:
```python
import pytest
import tempfile
import os
from autocare import ACES, VCdb, PCdb, Qdb

@pytest.fixture
def temp_directory():
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sample_aces():
    """Provide sample ACES instance."""
    aces = ACES()
    # Setup with test data
    return aces

@pytest.fixture
def mock_databases():
    """Provide mock database instances."""
    vcdb = VCdb()
    pcdb = PCdb()
    qdb = Qdb()
    # Setup with test data
    return vcdb, pcdb, qdb
```

---

## Code Quality

### Static Analysis

#### MyPy Configuration
`mypy.ini`:
```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
```

#### Flake8 Configuration
`.flake8`:
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    venv,
    build,
    dist
```

### Documentation Standards

#### Docstring Format
```python
def analyze_applications(
    apps: List[App], 
    vcdb: VCdb,
    threshold: float = 0.1
) -> Tuple[int, List[ValidationProblem]]:
    """Analyze applications for validation errors.
    
    Args:
        apps: List of applications to analyze
        vcdb: Vehicle Configuration Database interface
        threshold: Error threshold for analysis (default: 0.1)
        
    Returns:
        Tuple containing error count and list of problems found
        
    Raises:
        ValueError: If threshold is negative
        DatabaseError: If VCdb connection fails
        
    Example:
        >>> apps = [App(), App()]
        >>> vcdb = VCdb()
        >>> error_count, problems = analyze_applications(apps, vcdb)
        >>> print(f"Found {error_count} errors")
    """
    pass
```

### Performance Monitoring

#### Profiling
```python
import cProfile
import pstats

def profile_analysis():
    """Profile analysis performance."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run analysis code
    aces = ACES()
    # ... analysis logic
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('tottime')
    stats.print_stats(20)
```

#### Memory Monitoring
```python
import tracemalloc

def monitor_memory():
    """Monitor memory usage during analysis."""
    tracemalloc.start()
    
    # Run analysis
    # ... analysis logic
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
    tracemalloc.stop()
```

---

## Contributing Guidelines

### Pull Request Process

1. **Fork the repository** and create feature branch
2. **Write tests** for new functionality
3. **Update documentation** as needed
4. **Ensure all tests pass** and code quality checks pass
5. **Submit pull request** with clear description

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No breaking changes (or clearly documented)
- [ ] Performance impact is acceptable
- [ ] Security considerations are addressed

### Issue Reporting

When reporting issues:
1. **Provide clear description** of the problem
2. **Include reproduction steps** with minimal example
3. **Specify environment details** (Python version, OS, etc.)
4. **Attach relevant files** (logs, sample data if possible)

---

## Extending the System

### Adding New Analysis Types

```python
# Example: Adding new validation rule
class CustomValidator:
    def validate_custom_rule(self, app: App) -> List[ValidationProblem]:
        """Implement custom validation logic."""
        problems = []
        
        # Custom validation logic
        if self._check_custom_condition(app):
            problem = ValidationProblem()
            problem.description = "Custom validation failed"
            problem.app_id = app.id
            problem.severity = "Warning"
            problems.append(problem)
            
        return problems
    
    def _check_custom_condition(self, app: App) -> bool:
        # Implement condition check
        return False

# Integrate into main analysis
class ACES:
    def find_individual_app_errors(self, chunk, vcdb, pcdb, qdb):
        # Existing validation logic...
        
        # Add custom validation
        custom_validator = CustomValidator()
        for app in chunk.apps_list:
            custom_problems = custom_validator.validate_custom_rule(app)
            app.problems_found.extend(custom_problems)
```

### Adding New Database Interfaces

```python
class CustomDatabase:
    """Interface to custom database source."""
    
    def __init__(self):
        self.import_success = False
        self.custom_data: Dict[int, str] = {}
    
    def connect_database(self, connection_string: str) -> str:
        """Connect to custom database."""
        try:
            # Implement database connection
            self.import_success = True
            return ""
        except Exception as e:
            return str(e)
    
    def import_data(self) -> str:
        """Import data from connected database."""
        try:
            # Implement data import
            return ""
        except Exception as e:
            return str(e)
    
    def get_custom_info(self, id: int) -> str:
        """Get custom information by ID."""
        return self.custom_data.get(id, str(id))
```

### Adding New Output Formats

```python
class JSONReporter:
    """Generate JSON format assessment reports."""
    
    def generate_report(self, aces: ACES, vcdb: VCdb, pcdb: PCdb, qdb: Qdb) -> str:
        """Generate JSON assessment report."""
        import json
        
        report = {
            "summary": {
                "total_apps": len(aces.apps),
                "total_errors": aces.parttype_position_errors_count,
                "processing_time": aces.analysis_time
            },
            "errors": self._collect_errors(aces, vcdb, pcdb, qdb),
            "statistics": self._generate_statistics(aces)
        }
        
        return json.dumps(report, indent=2)
    
    def _collect_errors(self, aces, vcdb, pcdb, qdb):
        # Implement error collection
        pass
    
    def _generate_statistics(self, aces):
        # Implement statistics generation
        pass
```

---

## Release Process

### Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Checklist

1. [ ] Update version in `setup.py` and `aces_inspector.py`
2. [ ] Update CHANGELOG.md
3. [ ] Run full test suite
4. [ ] Update documentation
5. [ ] Create release tag
6. [ ] Build and test package
7. [ ] Deploy to package repository

### Release Commands

```bash
# Update version
python setup.py --version

# Run tests
pytest

# Build package
python setup.py sdist bdist_wheel

# Check package
twine check dist/*

# Upload to test PyPI
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Upload to PyPI
twine upload dist/*
```

---

## Troubleshooting Development Issues

### Common Development Problems

#### Import Errors
```bash
# Fix Python path issues
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall in development mode
pip install -e .
```

#### Database Connection Issues
```python
# Test ODBC connectivity
import pyodbc
print("Available drivers:", pyodbc.drivers())

# Test database file access
import os
print("File exists:", os.path.exists("test.accdb"))
print("File permissions:", oct(os.stat("test.accdb").st_mode))
```

#### Memory Issues During Development
```bash
# Monitor memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

### Debugging Tips

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In ACES class
def log_history_event(self, path: str, line: str):
    logging.debug(f"[{path}] {line}")
```

#### Use Debugger
```python
import pdb

def problematic_function():
    pdb.set_trace()  # Set breakpoint
    # Debug problematic code
    pass
```

#### Profile Performance
```python
import time

def timed_function():
    start_time = time.time()
    # Function code
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")
```

---

**Version**: 1.0.0.21 (Python Port)  
**Last Updated**: Current Date  
**Status**: Production Ready

For additional development resources, see:
- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [User Guide](USER_GUIDE.md)