#!/usr/bin/env python3
"""
Autocare module - Python port of Autocare.cs
Contains all the main classes for ACES XML analysis: Asset, App, ACES, VCdb, PCdb, Qdb

Author: Luke Smith (Original C#), Python Port
"""

import os
import sys
import re
import hashlib
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pyodbc
from lxml import etree
import itertools
from concurrent.futures import ThreadPoolExecutor
import tempfile
import traceback
from database_adapter import create_database_adapter, DatabaseAdapter, DatabaseQueryBuilder


@dataclass
class VCdbAttribute:
    """Represents a VCdb attribute with name and value"""
    name: str = ""
    value: int = 0
    
    def __lt__(self, other):
        """For sorting VCdbAttribute objects"""
        if self.name != other.name:
            return self.name < other.name
        return self.value < other.value


@dataclass
class QdbQualifier:
    """Represents a Qdb qualifier with ID and parameters"""
    qualifier_id: int = 0
    qualifier_parameters: List[str] = field(default_factory=list)
    
    def __init__(self):
        self.qualifier_id = 0
        self.qualifier_parameters = []


@dataclass
class ValidationProblem:
    """Represents a validation problem found during analysis"""
    description: str = ""
    app_id: int = 0
    severity: str = ""


@dataclass
class BaseVehicle:
    """Represents a base vehicle with make, model, year information"""
    id: int = 0
    make_id: int = 0
    model_id: int = 0
    year: int = 0


@dataclass
class FitmentNode:
    """Represents a node in the fitment tree"""
    id: int = 0
    parent_id: int = 0
    level: int = 0
    fitment_element: str = ""
    fitment_element_string: str = ""
    app_count: int = 0
    marked_as_cosmetic: bool = False
    
    def is_complementary_to(self, other_node: 'FitmentNode') -> bool:
        """Check if this node is complementary to another node"""
        return False  # Placeholder implementation
    
    def is_equal_to(self, other_node: 'FitmentNode') -> bool:
        """Check if this node is equal to another node"""
        return (self.fitment_element == other_node.fitment_element and 
                self.fitment_element_string == other_node.fitment_element_string)
    
    def node_hash(self) -> str:
        """Generate hash for this node"""
        content = f"{self.fitment_element}{self.fitment_element_string}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class AnalysisChunk:
    """Represents a chunk of applications for analysis"""
    id: int = 0
    app_count: int = 0
    qty_outlier_count: int = 0
    asset_problems_count: int = 0
    parttype_position_errors_count: int = 0
    qdb_errors_count: int = 0
    questionable_notes_count: int = 0
    vcdb_configurations_errors_count: int = 0
    fitment_logic_problems_count: int = 0
    parttype_disagreement_count: int = 0
    parttype_disagreement_errors_count: int = 0
    vcdb_codes_errors_count: int = 0
    basevehicleids_errors_count: int = 0
    cache_file: str = ""
    apps_list: List['App'] = field(default_factory=list)
    problem_apps_list: List['App'] = field(default_factory=list)
    lowest_badness_permutation: List[str] = field(default_factory=list)


@dataclass
class AnalysisChunkGroup:
    """Represents a group of analysis chunks"""
    id: int = 0
    chunks: List[AnalysisChunk] = field(default_factory=list)


class Asset:
    """Represents an asset from ACES XML"""
    
    def __init__(self):
        self.id = 0
        self.action = ""
        self.basevehicle_id = 0
        self.asset_name = ""
        self.vcdb_attributes: List[VCdbAttribute] = []
        self.qdb_qualifiers: List[QdbQualifier] = []
        self.notes: List[str] = []
    
    def nice_full_fitment_string(self, vcdb: 'VCdb', qdb: 'Qdb') -> str:
        """Returns human-readable fitment string"""
        string_list = []
        if self.vcdb_attributes:
            string_list.append(self.nice_attributes_string(vcdb, False))
        if self.qdb_qualifiers:
            string_list.append(self.nice_qdb_qualifier_string(qdb))
        if self.notes:
            string_list.extend(self.notes)
        return ";".join(string_list)
    
    def nice_attributes_string(self, vcdb: 'VCdb', include_notes: bool) -> str:
        """Returns human-readable attributes string"""
        string_list = []
        for attribute in self.vcdb_attributes:
            string_list.append(vcdb.nice_attribute(attribute))
        if include_notes:
            string_list.extend(self.notes)
        return ";".join(string_list)
    
    def nice_qdb_qualifier_string(self, qdb: 'Qdb') -> str:
        """Returns human-readable Qdb qualifier string"""
        result = ""
        for qualifier in self.qdb_qualifiers:
            result += qdb.nice_qdb_qualifier(qualifier.qualifier_id, qualifier.qualifier_parameters)
        return result


class App:
    """Represents an application from ACES XML"""
    
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
    
    def clear(self):
        """Clear all app data"""
        self.id = 0
        self.action = ""
        self.basevehicle_id = 0
        self.parttype_id = 0
        self.position_id = 0
        self.quantity = 0
        self.part = ""
        self.notes.clear()
        self.mfr_label = ""
        self.asset = ""
        self.asset_item_order = 0
        self.asset_item_ref = ""
        self.contains_vcdb_violation = False
        self.vcdb_attributes.clear()
        self.qdb_qualifiers.clear()
    
    def nice_attributes_string(self, vcdb: 'VCdb', include_notes: bool) -> str:
        """Returns human-readable attributes string"""
        string_list = []
        for attribute in self.vcdb_attributes:
            string_list.append(vcdb.nice_attribute(attribute))
        if include_notes:
            string_list.extend(self.notes)
        return ";".join(string_list)
    
    def name_val_pair_string(self, include_notes: bool) -> str:
        """Returns CSS-style name:value pairs"""
        string_list = []
        for attribute in self.vcdb_attributes:
            string_list.append(f"{attribute.name}:{attribute.value}")
        if include_notes:
            string_list.extend(self.notes)
        return ";".join(string_list)
    
    def raw_qdb_data_string(self) -> str:
        """Returns raw Qdb data string"""
        result = ""
        for qualifier in self.qdb_qualifiers:
            result += str(qualifier.qualifier_id)
            for param in qualifier.qualifier_parameters:
                result += f":{param}"
            result += ";"
        return result
    
    def nice_qdb_qualifier_string(self, qdb: 'Qdb') -> str:
        """Returns human-readable Qdb qualifier string"""
        string_list = []
        for qualifier in self.qdb_qualifiers:
            string_list.append(qdb.nice_qdb_qualifier(qualifier.qualifier_id, qualifier.qualifier_parameters))
        return ";".join(string_list)
    
    def nice_full_fitment_string(self, vcdb: 'VCdb', qdb: 'Qdb') -> str:
        """Returns complete human-readable fitment string"""
        string_list = []
        if self.vcdb_attributes:
            string_list.append(self.nice_attributes_string(vcdb, False))
        if self.qdb_qualifiers:
            string_list.append(self.nice_qdb_qualifier_string(qdb))
        if self.notes:
            string_list.extend(self.notes)
        return ";".join(string_list)
    
    def nice_mmy_string(self, vcdb: 'VCdb') -> str:
        """Returns Make/Model/Year string"""
        return f"{vcdb.nice_make_of_basevid(self.basevehicle_id)}, {vcdb.nice_model_of_basevid(self.basevehicle_id)}, {vcdb.nice_year_of_basevid(self.basevehicle_id)}"
    
    def app_hash(self) -> str:
        """Generate hash for this app"""
        content = (f"{self.basevehicle_id}{self.parttype_id}{self.position_id}{self.quantity}"
                  f"{self.name_val_pair_string(True)}{self.raw_qdb_data_string()}"
                  f"{self.mfr_label}{self.part}{self.asset}{self.asset_item_order}{self.brand}{self.subbrand}")
        return hashlib.md5(content.encode()).hexdigest()
    
    def __lt__(self, other):
        """For sorting App objects"""
        if self.basevehicle_id != other.basevehicle_id:
            return self.basevehicle_id < other.basevehicle_id
        if self.parttype_id != other.parttype_id:
            return self.parttype_id < other.parttype_id
        if self.position_id != other.position_id:
            return self.position_id < other.position_id
        if self.part != other.part:
            return self.part < other.part
        if self.mfr_label != other.mfr_label:
            return self.mfr_label < other.mfr_label
        name_val_cmp = self.name_val_pair_string(True) < other.name_val_pair_string(True)
        if self.name_val_pair_string(True) != other.name_val_pair_string(True):
            return name_val_cmp
        if self.asset != other.asset:
            return self.asset < other.asset
        return self.asset_item_order < other.asset_item_order


class VCdb:
    """Vehicle Configuration Database interface"""
    
    def __init__(self):
        self.import_vcdb_config_data = False
        self.connection_oledb = None
        self.db_adapter: Optional[DatabaseAdapter] = None
        self.vcdb_versions_on_server_list: List[str] = []
        self.import_success = False
        self.import_exception_message = ""
        self.file_path = ""
        self.version = ""
        self.import_progress = 0
        self.import_is_running = False
        
        # Dictionary mappings for fast lookup
        self.vcdb_basevehicle_dict: Dict[int, BaseVehicle] = {}
        self.vcdb_reverse_basevehicle_dict: Dict[str, int] = {}
        self.enginebase_dict: Dict[int, str] = {}
        self.engineblock_dict: Dict[int, str] = {}
        self.submodel_dict: Dict[int, str] = {}
        self.drivetype_dict: Dict[int, str] = {}
        self.aspiration_dict: Dict[int, str] = {}
        self.fueltype_dict: Dict[int, str] = {}
        self.braketype_dict: Dict[int, str] = {}
        self.brakeabs_dict: Dict[int, str] = {}
        self.mfrbodycode_dict: Dict[int, str] = {}
        self.bodynumdoors_dict: Dict[int, str] = {}
        self.bodytype_dict: Dict[int, str] = {}
        self.enginedesignation_dict: Dict[int, str] = {}
        self.enginevin_dict: Dict[int, str] = {}
        self.engineversion_dict: Dict[int, str] = {}
        self.mfr_dict: Dict[int, str] = {}
        self.fueldeliverytype_dict: Dict[int, str] = {}
        self.fueldeliverysubtype_dict: Dict[int, str] = {}
        self.fuelsystemcontroltype_dict: Dict[int, str] = {}
        self.fuelsystemdesign_dict: Dict[int, str] = {}
        self.cylinderheadtype_dict: Dict[int, str] = {}
        self.ignitionsystemtype_dict: Dict[int, str] = {}
        self.transmissionmfrcode_dict: Dict[int, str] = {}
        self.transmissionbase_dict: Dict[int, str] = {}
        self.transmissiontype_dict: Dict[int, str] = {}
        self.transmissioncontroltype_dict: Dict[int, str] = {}
        self.transmissionnumspeeds_dict: Dict[int, str] = {}
        self.transmission_elec_controlled_dict: Dict[int, str] = {}
        self.bedlength_dict: Dict[int, str] = {}
        self.bedtype_dict: Dict[int, str] = {}
        self.wheelbase_dict: Dict[int, str] = {}
        self.brakesystem_dict: Dict[int, str] = {}
        self.region_dict: Dict[int, str] = {}
        self.springtype_dict: Dict[int, str] = {}
        self.steeringsystem_dict: Dict[int, str] = {}
        self.steeringtype_dict: Dict[int, str] = {}
        self.valves_dict: Dict[int, str] = {}
        self.poweroutput_dict: Dict[int, str] = {}
        
        self.deleted_engine_base_dict: Dict[int, List[Tuple[str, str]]] = {}
    
    def connect_local_oledb(self, path: str) -> str:
        """Connect to local OLEDB database"""
        result = ""
        self.file_path = path
        try:
            # Disconnect existing connections
            if self.connection_oledb:
                self.connection_oledb.close()
            if self.db_adapter:
                self.db_adapter.disconnect()
            
            # Create new database adapter
            self.db_adapter = create_database_adapter(path)
            result = self.db_adapter.connect()
            
            # Maintain backward compatibility with existing code
            if not result:  # Success
                self.connection_oledb = self.db_adapter.connection
            
        except Exception as ex:
            result = str(ex)
        return result
    
    def disconnect(self):
        """Disconnect from database"""
        self.file_path = ""
        if self.db_adapter:
            self.db_adapter.disconnect()
            self.db_adapter = None
        if self.connection_oledb:
            self.connection_oledb.close()
            self.connection_oledb = None
    
    def clear(self):
        """Clear all data"""
        self.vcdb_basevehicle_dict.clear()
        self.vcdb_reverse_basevehicle_dict.clear()
        # Clear all other dictionaries...
        self.import_success = False
        self.import_exception_message = ""
    
    def nice_attribute(self, attribute: VCdbAttribute) -> str:
        """Return human-readable attribute string"""
        if attribute.name == "EngineBase" and attribute.value in self.enginebase_dict:
            return self.enginebase_dict[attribute.value]
        elif attribute.name == "SubModel" and attribute.value in self.submodel_dict:
            return self.submodel_dict[attribute.value]
        elif attribute.name == "DriveType" and attribute.value in self.drivetype_dict:
            return self.drivetype_dict[attribute.value]
        # Add more attribute type mappings...
        else:
            return f"{attribute.name}:{attribute.value}"
    
    def valid_attribute(self, attribute: VCdbAttribute) -> bool:
        """Check if attribute is valid"""
        if attribute.name == "EngineBase":
            return attribute.value in self.enginebase_dict
        elif attribute.name == "SubModel":
            return attribute.value in self.submodel_dict
        # Add more validation logic...
        return True
    
    def nice_make_of_basevid(self, base_vid: int) -> str:
        """Get make name for base vehicle ID"""
        if base_vid in self.vcdb_basevehicle_dict:
            make_id = self.vcdb_basevehicle_dict[base_vid].make_id
            return self.mfr_dict.get(make_id, "Unknown")
        return "Unknown"
    
    def nice_model_of_basevid(self, base_vid: int) -> str:
        """Get model name for base vehicle ID"""
        if base_vid in self.vcdb_basevehicle_dict:
            # Implementation would require model lookup table
            return "Unknown Model"
        return "Unknown"
    
    def nice_year_of_basevid(self, base_vid: int) -> str:
        """Get year for base vehicle ID"""
        if base_vid in self.vcdb_basevehicle_dict:
            return str(self.vcdb_basevehicle_dict[base_vid].year)
        return "Unknown"
    
    def basevids_from_year_range(self, make_id: int, model_id: int, start_year: int, end_year: int) -> List[int]:
        """Get base vehicle IDs for year range"""
        result = []
        for base_vid, vehicle in self.vcdb_basevehicle_dict.items():
            if (vehicle.make_id == make_id and vehicle.model_id == model_id and 
                start_year <= vehicle.year <= end_year):
                result.append(base_vid)
        return result
    
    def config_is_valid_memory_based(self, app: App) -> bool:
        """Check if configuration is valid using memory-based lookup"""
        # Implementation would check if the combination of attributes is valid
        # for the given base vehicle
        return True  # Placeholder
    
    def import_oledb_data(self) -> str:
        """Import data from OLEDB database"""
        try:
            self.import_success = False
            
            # Use database adapter if available, otherwise fall back to direct connection
            if self.db_adapter and self.db_adapter.is_connected():
                cursor = self.db_adapter.get_cursor()
            else:
                cursor = self.connection_oledb.cursor()
            
            # Import version - use database-agnostic query
            if self.db_adapter:
                db_type = self.db_adapter.config.db_type
                version_query = DatabaseQueryBuilder.get_version_query(db_type)
                if db_type == "mysql":
                    cursor.execute("SELECT version_date FROM version LIMIT 1")
                else:
                    cursor.execute("SELECT VersionDate FROM Version")
            else:
                cursor.execute("SELECT VersionDate FROM Version")
            
            row = cursor.fetchone()
            if row:
                self.version = str(row[0])
            
            # Import base vehicles
            cursor.execute("SELECT BaseVehicleID, MakeID, ModelID, Year FROM BaseVehicle")
            for row in cursor.fetchall():
                base_vehicle = BaseVehicle()
                base_vehicle.id = row[0]
                base_vehicle.make_id = row[1]
                base_vehicle.model_id = row[2]
                base_vehicle.year = row[3]
                self.vcdb_basevehicle_dict[base_vehicle.id] = base_vehicle
            
            # Import manufacturers
            cursor.execute("SELECT MfrID, MfrName FROM Mfr")
            for row in cursor.fetchall():
                self.mfr_dict[row[0]] = row[1]
            
            # Import engine bases
            cursor.execute("SELECT EngineBaseID, EngineBaseName FROM EngineBase")
            for row in cursor.fetchall():
                self.enginebase_dict[row[0]] = row[1]
            
            # Import submodels
            cursor.execute("SELECT SubModelID, SubModelName FROM SubModel")
            for row in cursor.fetchall():
                self.submodel_dict[row[0]] = row[1]
            
            # Import drive types
            cursor.execute("SELECT DriveTypeID, DriveTypeName FROM DriveType")
            for row in cursor.fetchall():
                self.drivetype_dict[row[0]] = row[1]
            
            # Add more imports for other lookup tables...
            
            self.import_success = True
            return ""
            
        except Exception as ex:
            self.import_exception_message = str(ex)
            self.import_success = False
            return str(ex)


class PCdb:
    """Part Configuration Database interface"""
    
    def __init__(self):
        self.connection_oledb = None
        self.db_adapter: Optional[DatabaseAdapter] = None
        self.pcdb_versions_on_server_list: List[str] = []
        self.import_success = False
        self.import_exception_message = ""
        self.file_path = ""
        self.version = ""
        
        self.parttypes: Dict[int, str] = {}
        self.positions: Dict[int, str] = {}
        self.codemaster_parttype_positions: List[str] = []
    
    def import_oledb(self) -> str:
        """Import data from OLEDB database"""
        try:
            self.import_success = False
            
            # Use database adapter if available, otherwise fall back to direct connection
            if self.db_adapter and self.db_adapter.is_connected():
                cursor = self.db_adapter.get_cursor()
            else:
                cursor = self.connection_oledb.cursor()
            
            # Import version - use database-agnostic query
            if self.db_adapter and self.db_adapter.config.db_type == "mysql":
                cursor.execute("SELECT version_date FROM version LIMIT 1")
            else:
                cursor.execute("SELECT VersionDate FROM Version")
            row = cursor.fetchone()
            if row:
                self.version = str(row[0])
            
            # Import part types
            cursor.execute("SELECT partterminologyid, partterminologyname FROM Parts")
            for row in cursor.fetchall():
                self.parttypes[row[0]] = row[1]
            
            # Import positions - handle column name quoting for different databases
            if self.db_adapter and self.db_adapter.config.db_type == "mysql":
                cursor.execute("SELECT PositionID, `Position` FROM Positions")
            else:
                cursor.execute("SELECT PositionID, [Position] FROM Positions")
            for row in cursor.fetchall():
                self.positions[row[0]] = row[1]
            
            # Import codemaster combinations
            cursor.execute("SELECT partterminologyid, positionid FROM codemaster")
            for row in cursor.fetchall():
                self.codemaster_parttype_positions.append(f"{row[0]}_{row[1]}")
            
            self.import_success = True
            return ""
            
        except Exception as ex:
            self.import_exception_message = str(ex)
            self.import_success = False
            return str(ex)
    
    def connect_local_oledb(self, path: str) -> str:
        """Connect to local OLEDB database"""
        result = ""
        self.file_path = path
        try:
            if self.connection_oledb:
                self.connection_oledb.close()
            
            connection_string = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={path};"
            self.connection_oledb = pyodbc.connect(connection_string)
        except Exception as ex:
            result = str(ex)
        return result
    
    def disconnect(self):
        """Disconnect from database"""
        self.file_path = ""
        if self.connection_oledb:
            self.connection_oledb.close()
            self.connection_oledb = None
    
    def clear(self):
        """Clear all data"""
        self.parttypes.clear()
        self.positions.clear()
        self.codemaster_parttype_positions.clear()
        self.import_success = False
        self.import_exception_message = ""
    
    def nice_parttype(self, parttype_id: int) -> str:
        """Get part type name"""
        return self.parttypes.get(parttype_id, "Unknown")
    
    def nice_position(self, position_id: int) -> str:
        """Get position name"""
        return self.positions.get(position_id, "Unknown")


class Qdb:
    """Qualifier Database interface"""
    
    def __init__(self):
        self.connection_oledb = None
        self.db_adapter: Optional[DatabaseAdapter] = None
        self.qdb_versions_on_server_list: List[str] = []
        self.file_path = ""
        self.version = ""
        self.import_success = False
        self.import_exception_message = ""
        self.qualifiers: Dict[int, str] = {}
        self.qualifiers_types: Dict[int, int] = {}
    
    def import_oledb(self) -> str:
        """Import data from OLEDB database"""
        try:
            self.import_success = False
            cursor = self.connection_oledb.cursor()
            
            # Import version
            cursor.execute("SELECT versiondate FROM Version")
            row = cursor.fetchone()
            if row:
                self.version = str(row[0])
            
            # Import qualifiers
            cursor.execute("SELECT qualifierid, qualifiertext, qualifiertypeid FROM Qualifier ORDER BY qualifierid")
            for row in cursor.fetchall():
                qualifier_id = row[0]
                self.qualifiers[qualifier_id] = row[1]
                qualifier_type_id = 0
                try:
                    qualifier_type_id = int(row[2]) if row[2] else 0
                except:
                    pass
                self.qualifiers_types[qualifier_id] = qualifier_type_id
            
            self.import_success = True
            return ""
            
        except Exception as ex:
            self.import_exception_message = str(ex)
            self.import_success = False
            return str(ex)
    
    def connect_local_oledb(self, path: str) -> str:
        """Connect to local OLEDB database"""
        result = ""
        self.file_path = path
        try:
            if self.connection_oledb:
                self.connection_oledb.close()
            
            connection_string = f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={path};"
            self.connection_oledb = pyodbc.connect(connection_string)
        except Exception as ex:
            result = str(ex)
        return result
    
    def disconnect(self):
        """Disconnect from database"""
        self.file_path = ""
        if self.connection_oledb:
            self.connection_oledb.close()
            self.connection_oledb = None
    
    def clear(self):
        """Clear all data"""
        self.qualifiers.clear()
        self.qualifiers_types.clear()
        self.import_success = False
        self.import_exception_message = ""
    
    def nice_qdb_qualifier(self, qualifier_id: int, parameters: List[str]) -> str:
        """Get human-readable qualifier string"""
        if qualifier_id in self.qualifiers:
            qualifier_text = self.qualifiers[qualifier_id]
            # Replace parameters in qualifier text if any
            for i, param in enumerate(parameters):
                qualifier_text = qualifier_text.replace(f"{{{i}}}", param)
            return qualifier_text
        return f"Unknown Qualifier {qualifier_id}"


class ACES:
    """Main ACES file container and analysis engine"""
    
    def __init__(self):
        # Basic properties
        self.successful_import = False
        self.analysis_running = False
        self.discarded_deletes_on_import = 0
        self.analysis_time = 0
        self.file_path = ""
        self.file_md5_hash = ""
        self.version = ""
        self.company = ""
        self.sender_name = ""
        self.sender_phone = ""
        self.transfer_date = ""
        self.brand_aaiaid = ""
        self.document_title = ""
        self.effective_date = ""
        self.submission_type = ""
        self.vcdb_version_date = ""
        self.qdb_version_date = ""
        self.pcdb_version_date = ""
        self.differentials_summary = ""
        self.footer_record_count = 0
        self.added_to_fitment_permutation_mining_cache = False
        self.qty_outlier_threshold = 0.0
        self.qty_outlier_sample_size = 0.0
        self.allow_grace_for_wildcard_configs = True
        self.ignore_na_items = False
        self.xml_app_node_count = 0
        self.xml_asset_node_count = 0
        self.qdb_utilization_score = 0.0
        
        # Error counts
        self.qty_outlier_count = 0
        self.asset_problems_count = 0
        self.parttype_position_errors_count = 0
        self.qdb_errors_count = 0
        self.questionable_notes_count = 0
        self.vcdb_configurations_errors_count = 0
        self.fitment_logic_problems_count = 0
        self.parttype_disagreement_count = 0
        self.vcdb_codes_errors_count = 0
        self.basevehicleids_errors_count = 0
        
        # Cache file lists
        self.qty_outlier_cachefiles_list: List[str] = []
        self.parttype_position_errors_cachefiles_list: List[str] = []
        self.qdb_errors_cachefiles_list: List[str] = []
        self.vcdb_configurations_errors_cachefiles_list: List[str] = []
        self.fitment_logic_problems_cachefiles_list: List[str] = []
        self.parttype_disagreement_cachefiles_list: List[str] = []
        self.vcdb_codes_errors_cachefiles_list: List[str] = []
        self.basevehicleids_errors_cachefiles_list: List[str] = []
        
        # Main data structures
        self.apps: List[App] = []
        self.assets: List[Asset] = []
        
        # Dictionary collections
        self.parts_app_counts: Dict[str, int] = {}
        self.interchange: Dict[str, str] = {}
        self.asset_name_interchange: Dict[str, str] = {}
        self.parts_part_types: Dict[str, List[int]] = {}
        self.parts_positions: Dict[str, List[int]] = {}
        self.note_counts: Dict[str, int] = {}
        self.basevid_occurrences: Dict[int, int] = {}
        self.qdbid_occurrences: Dict[int, int] = {}
        self.distinct_assets: List[str] = []
        self.distinct_mfr_labels: List[str] = []
        self.distinct_part_types: List[int] = []
        self.distinct_asset_names: List[str] = []
        
        # Analysis structures
        self.differential_parts: List[str] = []
        self.differential_vehicles: List[str] = []
        self.xml_validation_errors: List[str] = []
        self.aces_schemas: Dict[str, str] = {}
        self.fitment_node_list: List[FitmentNode] = []
        self.fitment_problem_groups_app_lists: Dict[str, List[App]] = {}
        self.fitment_problem_groups_best_permutations: Dict[str, List[str]] = {}
        self.app_hashes_flagged_as_cosmetic: Dict[str, str] = {}
        self.fitment_nodes_flagged_as_cosmetic: Dict[str, List[str]] = {}
        
        self.fitment_permutation_mining_cache: Dict[str, str] = {}
        self.individual_analysis_chunks_list: List[AnalysisChunk] = []
        self.outlier_analysis_chunks_list: List[AnalysisChunk] = []
        self.fitment_analysis_chunks_list: List[AnalysisChunk] = []
        self.fitment_analysis_chunks_groups: List[AnalysisChunkGroup] = []
        self.vcdb_usage_stats_dict: Dict[str, int] = {}
        self.vcdb_usage_stats_total_apps = 0
        self.vcdb_usage_stats_file_list: List[str] = []
        self.note_blacklist: Dict[str, bool] = {}
        self.analysis_history: List[str] = []
        self.log_level = 0
        self.log_to_file = False
        
        # Initialize schemas
        self._initialize_schemas()
    
    def _initialize_schemas(self):
        """Initialize ACES schema definitions"""
        # Schema definitions from original C# code
        self.aces_schemas["1.08"] = '<?xml version ="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">...'
        self.aces_schemas["2.0"] = '<?xml version ="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">...'
        self.aces_schemas["3.0"] = '<?xml version ="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" xml:lang="en" version="3.0">...'
        self.aces_schemas["3.0.1"] = '<? xml version ="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" version="3.0.1" xml:lang="en">...'
        self.aces_schemas["3.1"] = '<?xml version="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" version="3.1" xml:lang="en">...'
        self.aces_schemas["3.2"] = '<?xml version="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" version="3.2" xml:lang="en">...'
        self.aces_schemas["4.2"] = '<?xml version="1.0" encoding="UTF-8"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" version="4.2" xml:lang="en">...'
    
    def clear(self):
        """Clear all ACES data"""
        self.successful_import = False
        self.analysis_running = False
        self.apps.clear()
        self.assets.clear()
        # Clear all other collections...
    
    def clear_analysis_results(self):
        """Clear analysis results"""
        self.qty_outlier_count = 0
        self.asset_problems_count = 0
        self.parttype_position_errors_count = 0
        # Reset all other counts...
    
    def log_history_event(self, path: str, line: str):
        """Log an event to history"""
        self.analysis_history.append(f"{datetime.now()}: {line}")
        if self.log_to_file and path:
            try:
                with open(path, 'a') as f:
                    f.write(f"{datetime.now()}\t{line}\n")
            except:
                pass
    
    def parse_attribute_pairs_string(self, name_value_pairs_string: str) -> List[VCdbAttribute]:
        """Parse CSS-style name:value attribute pairs"""
        attributes = []
        if not name_value_pairs_string:
            return attributes
        
        pairs = name_value_pairs_string.split(';')
        for pair in pairs:
            if ':' in pair:
                name, value = pair.split(':', 1)
                try:
                    attr = VCdbAttribute()
                    attr.name = name.strip()
                    attr.value = int(value.strip())
                    attributes.append(attr)
                except ValueError:
                    continue
        
        return attributes
    
    def import_xml(self, file_path: str, schema_string: str, respect_validate_no_tag: bool,
                   import_deletes: bool, note_translation: Dict[str, str],
                   note_qdb_transform: Dict[str, QdbQualifier], cache_path: str, verbose: bool) -> str:
        """Import ACES XML file"""
        try:
            self.file_path = file_path
            self.clear()
            
            # Parse XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Get version
            self.version = root.get('version', '')
            
            # Parse header
            header = root.find('Header')
            if header is not None:
                self.company = header.findtext('Company', '')
                self.sender_name = header.findtext('SenderName', '')
                self.sender_phone = header.findtext('SenderPhone', '')
                self.transfer_date = header.findtext('TransferDate', '')
                self.document_title = header.findtext('DocumentTitle', '')
                self.effective_date = header.findtext('EffectiveDate', '')
                self.submission_type = header.findtext('SubmissionType', '')
                self.vcdb_version_date = header.findtext('VcdbVersionDate', '')
                self.qdb_version_date = header.findtext('QdbVersionDate', '')
                self.pcdb_version_date = header.findtext('PcdbVersionDate', '')
            
            # Parse applications
            app_nodes = root.findall('App')
            self.xml_app_node_count = len(app_nodes)
            
            for app_node in app_nodes:
                app = self._parse_app_node(app_node)
                if app:
                    self.apps.append(app)
            
            # Parse assets
            asset_nodes = root.findall('Asset')
            self.xml_asset_node_count = len(asset_nodes)
            
            for asset_node in asset_nodes:
                asset = self._parse_asset_node(asset_node)
                if asset:
                    self.assets.append(asset)
            
            # Parse footer
            footer = root.find('Footer')
            if footer is not None:
                record_count = footer.findtext('RecordCount', '0')
                try:
                    self.footer_record_count = int(record_count)
                except ValueError:
                    self.footer_record_count = 0
            
            self.successful_import = True
            
            if verbose:
                print(f"Successfully imported {len(self.apps)} applications and {len(self.assets)} assets")
            
            return ""
            
        except Exception as ex:
            self.successful_import = False
            error_msg = f"Failed to import ACES XML: {str(ex)}"
            if verbose:
                print(error_msg)
                traceback.print_exc()
            return error_msg
    
    def _parse_app_node(self, app_node) -> Optional[App]:
        """Parse an App XML node"""
        try:
            app = App()
            
            # Parse attributes
            app.id = int(app_node.get('id', '0'))
            app.action = app_node.get('action', 'A')
            app.reference = app_node.get('ref', '')
            validate_attr = app_node.get('validate', 'yes')
            app.validate = validate_attr.lower() == 'yes'
            
            # Parse base vehicle or year range
            base_vehicle = app_node.find('BaseVehicle')
            if base_vehicle is not None:
                app.basevehicle_id = int(base_vehicle.get('id', '0'))
                app.type = 1  # basevehicle type
            else:
                # Handle year range style
                years = app_node.find('Years')
                make = app_node.find('Make')
                if years is not None and make is not None:
                    app.type = 1  # Will be converted to basevehicle type
                    # Implementation would convert year range to basevehicle IDs
            
            # Parse part information
            qty_node = app_node.find('Qty')
            if qty_node is not None:
                try:
                    app.quantity = int(qty_node.text or '0')
                except ValueError:
                    app.quantity = 0
            
            parttype_node = app_node.find('PartType')
            if parttype_node is not None:
                app.parttype_id = int(parttype_node.get('id', '0'))
            
            position_node = app_node.find('Position')
            if position_node is not None:
                app.position_id = int(position_node.get('id', '0'))
            
            part_node = app_node.find('Part')
            if part_node is not None:
                app.part = part_node.text or ''
                app.brand = part_node.get('BrandAAIAID', '')
            
            mfr_label_node = app_node.find('MfrLabel')
            if mfr_label_node is not None:
                app.mfr_label = mfr_label_node.text or ''
            
            # Parse asset information
            asset_name_node = app_node.find('AssetName')
            if asset_name_node is not None:
                app.asset = asset_name_node.text or ''
            
            asset_order_node = app_node.find('AssetItemOrder')
            if asset_order_node is not None:
                try:
                    app.asset_item_order = int(asset_order_node.text or '0')
                except ValueError:
                    app.asset_item_order = 0
            
            asset_ref_node = app_node.find('AssetItemRef')
            if asset_ref_node is not None:
                app.asset_item_ref = asset_ref_node.text or ''
            
            # Parse VCdb attributes (all the vehicle attribute nodes)
            vcdb_attribute_names = [
                'SubModel', 'MfrBodyCode', 'BodyNumDoors', 'BodyType', 'DriveType',
                'EngineBase', 'EngineDesignation', 'EngineVIN', 'EngineVersion', 'EngineMfr',
                'PowerOutput', 'ValvesPerEngine', 'FuelDeliveryType', 'FuelDeliverySubType',
                'FuelSystemControlType', 'FuelSystemDesign', 'Aspiration', 'CylinderHeadType',
                'FuelType', 'IgnitionSystemType', 'TransmissionMfrCode', 'TransmissionBase',
                'TransmissionType', 'TransmissionControlType', 'TransmissionNumSpeeds',
                'TransElecControlled', 'TransmissionMfr', 'BedLength', 'BedType', 'WheelBase',
                'BrakeSystem', 'FrontBrakeType', 'RearBrakeType', 'BrakeABS', 'FrontSpringType',
                'RearSpringType', 'SteeringSystem', 'SteeringType', 'Region'
            ]
            
            for attr_name in vcdb_attribute_names:
                attr_node = app_node.find(attr_name)
                if attr_node is not None:
                    attr_id = attr_node.get('id')
                    if attr_id:
                        try:
                            vcdb_attr = VCdbAttribute()
                            vcdb_attr.name = attr_name
                            vcdb_attr.value = int(attr_id)
                            app.vcdb_attributes.append(vcdb_attr)
                        except ValueError:
                            continue
            
            # Parse Qdb qualifiers
            qual_nodes = app_node.findall('Qual')
            for qual_node in qual_nodes:
                qual_id = qual_node.get('id')
                if qual_id:
                    try:
                        qdb_qual = QdbQualifier()
                        qdb_qual.qualifier_id = int(qual_id)
                        
                        # Parse parameters
                        param_nodes = qual_node.findall('param')
                        for param_node in param_nodes:
                            value = param_node.get('value', '')
                            qdb_qual.qualifier_parameters.append(value)
                        
                        app.qdb_qualifiers.append(qdb_qual)
                    except ValueError:
                        continue
            
            # Parse notes
            note_nodes = app_node.findall('Note')
            for note_node in note_nodes:
                if note_node.text:
                    app.notes.append(note_node.text)
            
            return app
            
        except Exception as ex:
            print(f"Error parsing app node: {ex}")
            return None
    
    def _parse_asset_node(self, asset_node) -> Optional[Asset]:
        """Parse an Asset XML node"""
        try:
            asset = Asset()
            
            # Parse attributes
            asset.id = int(asset_node.get('id', '0'))
            asset.action = asset_node.get('action', 'A')
            
            # Parse asset name
            asset_name_node = asset_node.find('AssetName')
            if asset_name_node is not None:
                asset.asset_name = asset_name_node.text or ''
            
            # Parse base vehicle
            base_vehicle = asset_node.find('BaseVehicle')
            if base_vehicle is not None:
                asset.basevehicle_id = int(base_vehicle.get('id', '0'))
            
            # Parse VCdb attributes (similar to app parsing)
            # ... (implementation similar to app node parsing)
            
            # Parse Qdb qualifiers
            # ... (implementation similar to app node parsing)
            
            # Parse notes
            note_nodes = asset_node.findall('Note')
            for note_node in note_nodes:
                if note_node.text:
                    asset.notes.append(note_node.text)
            
            return asset
            
        except Exception as ex:
            print(f"Error parsing asset node: {ex}")
            return None
    
    def find_individual_app_errors(self, chunk: AnalysisChunk, vcdb: VCdb, pcdb: PCdb, qdb: Qdb):
        """Find individual application errors"""
        
        # PartType/Position errors
        self.log_history_event("", "Looking for parttype/position errors")
        cache_filename = f"{chunk.cache_file}_parttypePositionErrors{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":  # Ignore "Delete" apps
                        continue
                    
                    error_string = ""
                    
                    # Check if parttype ID is valid
                    if pcdb.nice_parttype(app.parttype_id) == str(app.parttype_id):
                        error_string = "Invalid Parttype"
                    
                    # Check if position ID is valid
                    if app.position_id != 0 and pcdb.nice_position(app.position_id) == str(app.position_id):
                        error_string += " Invalid Position"
                    
                    # Check if parttype-position combination is valid
                    if (error_string == "" and app.position_id != 0 and 
                        f"{app.parttype_id}_{app.position_id}" not in pcdb.codemaster_parttype_positions):
                        error_string = "Invalid Parttype-Position"
                    
                    if error_string:
                        chunk.parttype_position_errors_count += 1
                        problem_data = (f"{error_string}\t{app.id}\t{app.basevehicle_id}\t"
                                      f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                      f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                      f"{pcdb.nice_position(app.position_id)}\t"
                                      f"{app.quantity}\t{app.part}\t"
                                      f"{app.nice_full_fitment_string(vcdb, qdb)}")
                        f.write(problem_data + "\n")
            
            if chunk.parttype_position_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.parttype_position_errors_count} invalid parttypes or parttype/positions combinations (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in parttype/position analysis: {ex}")
        
        # Qdb errors
        self.log_history_event("", "Looking for Qdb errors")
        cache_filename = f"{chunk.cache_file}_QdbErrors{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    for qdb_qualifier in app.qdb_qualifiers:
                        if qdb.nice_qdb_qualifier(qdb_qualifier.qualifier_id, qdb_qualifier.qualifier_parameters) == str(qdb_qualifier.qualifier_id):
                            chunk.qdb_errors_count += 1
                            problem_data = (f"Invalid Qdb id ({qdb_qualifier.qualifier_id})\t{app.id}\t"
                                          f"{app.basevehicle_id}\t{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                          f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                          f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                          f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                          f"{pcdb.nice_position(app.position_id)}\t"
                                          f"{app.quantity}\t{app.part}\t"
                                          f"{app.nice_attributes_string(vcdb, False)}\t"
                                          f"{';'.join(app.notes)}")
                            f.write(problem_data + "\n")
            
            if chunk.qdb_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.qdb_errors_count} invalid Qdb references (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in Qdb analysis: {ex}")
        
        # Questionable Notes
        self.log_history_event("", "Looking for Questionable Notes")
        cache_filename = f"{chunk.cache_file}_questionableNotes{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    for search_term, exact_match in self.note_blacklist.items():
                        for note in app.notes:
                            if (exact_match and note == search_term) or (not exact_match and search_term in note):
                                chunk.questionable_notes_count += 1
                                problem_data = (f"Questionable note ({note})\t{app.id}\t{app.basevehicle_id}\t"
                                              f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                              f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                              f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                              f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                              f"{pcdb.nice_position(app.position_id)}\t"
                                              f"{app.quantity}\t{app.part}\t"
                                              f"{app.nice_attributes_string(vcdb, False)}\t"
                                              f"{';'.join(app.notes)}")
                                f.write(problem_data + "\n")
            
            if chunk.questionable_notes_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.questionable_notes_count} questionable notes (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in questionable notes analysis: {ex}")
        
        # Invalid Base Vehicles
        self.log_history_event("", "Looking for invalid basevehicles")
        cache_filename = f"{chunk.cache_file}_invalidBasevehicles{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    if app.basevehicle_id not in vcdb.vcdb_basevehicle_dict:
                        chunk.basevehicleids_errors_count += 1
                        problem_data = (f"Invalid BaseVehicle ID\t{app.id}\t{app.basevehicle_id}\t"
                                      f"Unknown\tUnknown\tUnknown\t"
                                      f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                      f"{pcdb.nice_position(app.position_id)}\t"
                                      f"{app.quantity}\t{app.part}\t"
                                      f"{app.nice_full_fitment_string(vcdb, qdb)}")
                        f.write(problem_data + "\n")
            
            if chunk.basevehicleids_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.basevehicleids_errors_count} invalid basevehicle IDs (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in basevehicle analysis: {ex}")
        
        # Invalid VCdb Codes
        self.log_history_event("", "Looking for invalid VCdb codes")
        cache_filename = f"{chunk.cache_file}_invalidVCdbCodes{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    for attribute in app.vcdb_attributes:
                        if not vcdb.valid_attribute(attribute):
                            chunk.vcdb_codes_errors_count += 1
                            problem_data = (f"Invalid VCdb Code ({attribute.name}:{attribute.value})\t"
                                          f"{app.id}\t{app.basevehicle_id}\t"
                                          f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                          f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                          f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                          f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                          f"{pcdb.nice_position(app.position_id)}\t"
                                          f"{app.quantity}\t{app.part}\t"
                                          f"{app.nice_attributes_string(vcdb, False)}\t"
                                          f"{';'.join(app.notes)}")
                            f.write(problem_data + "\n")
            
            if chunk.vcdb_codes_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.vcdb_codes_errors_count} invalid VCdb codes (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in VCdb codes analysis: {ex}")
        
        # Configuration Errors
        self.log_history_event("", "Looking for configuration errors")
        cache_filename = f"{chunk.cache_file}_configurationErrors{chunk.id}.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    if not vcdb.config_is_valid_memory_based(app):
                        chunk.vcdb_configurations_errors_count += 1
                        problem_data = (f"Invalid Configuration\t{app.id}\t{app.basevehicle_id}\t"
                                      f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                      f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                      f"{pcdb.nice_position(app.position_id)}\t"
                                      f"{app.quantity}\t{app.part}\t"
                                      f"{app.nice_attributes_string(vcdb, False)}\t"
                                      f"{';'.join(app.notes)}")
                        f.write(problem_data + "\n")
            
            if chunk.vcdb_configurations_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Error: {chunk.vcdb_configurations_errors_count} invalid configurations (task {chunk.id})")
        
        except Exception as ex:
            self.log_history_event("", f"Error in configuration analysis: {ex}")
    
    def find_individual_app_outliers(self, chunk: AnalysisChunk, vcdb: VCdb, pcdb: PCdb, qdb: Qdb):
        """Find application outliers"""
        
        # Quantity outliers
        self.log_history_event("", "Looking for quantity outliers")
        cache_filename = f"{chunk.cache_file}_qtyOutliers.txt"
        
        try:
            # Group apps by part type and position to analyze quantities
            part_qty_groups = defaultdict(list)
            for app in chunk.apps_list:
                if app.action == "D":
                    continue
                key = f"{app.parttype_id}_{app.position_id}"
                part_qty_groups[key].append(app)
            
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for group_key, apps in part_qty_groups.items():
                    if len(apps) < self.qty_outlier_sample_size:
                        continue
                    
                    quantities = [app.quantity for app in apps]
                    if not quantities:
                        continue
                    
                    # Calculate statistical outliers (simple implementation)
                    quantities.sort()
                    q1_index = len(quantities) // 4
                    q3_index = 3 * len(quantities) // 4
                    
                    if q1_index < len(quantities) and q3_index < len(quantities):
                        q1 = quantities[q1_index]
                        q3 = quantities[q3_index]
                        iqr = q3 - q1
                        
                        if iqr > 0:
                            lower_bound = q1 - 1.5 * iqr
                            upper_bound = q3 + 1.5 * iqr
                            
                            for app in apps:
                                if app.quantity < lower_bound or app.quantity > upper_bound:
                                    chunk.qty_outlier_count += 1
                                    problem_data = (f"Quantity outlier ({app.quantity})\t{app.id}\t{app.basevehicle_id}\t"
                                                  f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                                  f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                                  f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                                  f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                                  f"{pcdb.nice_position(app.position_id)}\t"
                                                  f"{app.quantity}\t{app.part}\t"
                                                  f"{app.nice_full_fitment_string(vcdb, qdb)}")
                                    f.write(problem_data + "\n")
            
            if chunk.qty_outlier_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Warning: {chunk.qty_outlier_count} quantity outliers")
        
        except Exception as ex:
            self.log_history_event("", f"Error in quantity outlier analysis: {ex}")
        
        # Part type disagreements
        self.log_history_event("", "Looking for part type disagreements")
        cache_filename = f"{chunk.cache_file}_parttypeDisagreements.txt"
        
        try:
            # Group by part number and check for different part types
            part_groups = defaultdict(set)
            for app in chunk.apps_list:
                if app.action == "D":
                    continue
                part_groups[app.part].add(app.parttype_id)
            
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for part, parttype_ids in part_groups.items():
                    if len(parttype_ids) > 1:
                        # This part appears with multiple part types
                        for app in chunk.apps_list:
                            if app.part == part and app.action != "D":
                                chunk.parttype_disagreement_errors_count += 1
                                problem_data = (f"Part type disagreement\t{app.id}\t{app.basevehicle_id}\t"
                                              f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                              f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                              f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                              f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                              f"{pcdb.nice_position(app.position_id)}\t"
                                              f"{app.quantity}\t{app.part}\t"
                                              f"{app.nice_full_fitment_string(vcdb, qdb)}")
                                f.write(problem_data + "\n")
            
            if chunk.parttype_disagreement_errors_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Warning: {chunk.parttype_disagreement_errors_count} part type disagreements")
        
        except Exception as ex:
            self.log_history_event("", f"Error in part type disagreement analysis: {ex}")
        
        # Asset problems
        self.log_history_event("", "Looking for asset problems")
        cache_filename = f"{chunk.cache_file}_assetProblems.txt"
        
        try:
            with open(cache_filename, 'w', encoding='utf-8') as f:
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    # Check for asset-related issues
                    if app.asset and not app.asset.strip():
                        chunk.asset_problems_count += 1
                        problem_data = (f"Empty asset name\t{app.id}\t{app.basevehicle_id}\t"
                                      f"{vcdb.nice_make_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_model_of_basevid(app.basevehicle_id)}\t"
                                      f"{vcdb.nice_year_of_basevid(app.basevehicle_id)}\t"
                                      f"{pcdb.nice_parttype(app.parttype_id)}\t"
                                      f"{pcdb.nice_position(app.position_id)}\t"
                                      f"{app.quantity}\t{app.part}\t"
                                      f"{app.nice_full_fitment_string(vcdb, qdb)}")
                        f.write(problem_data + "\n")
            
            if chunk.asset_problems_count == 0:
                try:
                    os.remove(cache_filename)
                except:
                    pass
            else:
                self.log_history_event("", f"Warning: {chunk.asset_problems_count} asset problems")
        
        except Exception as ex:
            self.log_history_event("", f"Error in asset problems analysis: {ex}")
    
    def find_fitment_logic_problems(self, chunk_group: AnalysisChunkGroup, vcdb: VCdb, pcdb: PCdb, qdb: Qdb,
                                   permutation_cache_file_path: str, iteration_limit: int, cache_directory: str,
                                   concern_for_disparates: bool, respect_qdb_type: bool, use_threads: bool,
                                   thread_count: int, verbose: bool):
        """Find fitment logic problems"""
        # Simplified fitment logic analysis - the full implementation would be very complex
        # This provides basic overlap detection
        
        for chunk in chunk_group.chunks:
            try:
                # Group applications by fitment criteria
                fitment_groups = defaultdict(list)
                
                for app in chunk.apps_list:
                    if app.action == "D":
                        continue
                    
                    # Create fitment key from base vehicle and attributes
                    fitment_key = f"{app.basevehicle_id}_{app.parttype_id}_{app.position_id}"
                    for attr in app.vcdb_attributes:
                        fitment_key += f"_{attr.name}:{attr.value}"
                    
                    fitment_groups[fitment_key].append(app)
                
                # Check for overlapping fitments (simplified logic)
                for fitment_key, apps in fitment_groups.items():
                    if len(apps) > 1:
                        # Multiple apps with same fitment - potential overlap
                        unique_parts = set(app.part for app in apps)
                        if len(unique_parts) > 1:
                            # Different parts with same fitment - this is a logic problem
                            chunk.problem_apps_list.extend(apps)
                            chunk.lowest_badness_permutation = ["Fitment_Overlap"]
                
            except Exception as ex:
                self.log_history_event("", f"Error in fitment logic analysis: {ex}")
    
    def establish_fitment_tree_roots(self, treat_assets_as_fitment: bool):
        """Establish fitment tree roots for analysis"""
        # Create analysis chunks based on MMY/parttype/position/mfrlabel/asset groupings
        fitment_groups = defaultdict(list)
        
        for app in self.apps:
            if app.action == "D":
                continue
            
            # Create grouping key
            group_key = f"{app.basevehicle_id}_{app.parttype_id}_{app.position_id}_{app.mfr_label}_{app.asset}"
            fitment_groups[group_key].append(app)
        
        # Create analysis chunks for each group
        chunk_id = 1
        for group_key, apps in fitment_groups.items():
            if len(apps) > 1:  # Only analyze groups with multiple apps
                chunk = AnalysisChunk()
                chunk.id = chunk_id
                chunk.apps_list = apps
                chunk.problem_apps_list = []
                chunk.lowest_badness_permutation = []
                self.fitment_analysis_chunks_list.append(chunk)
                chunk_id += 1
    
    def build_fitment_tree_from_app_list(self, app_list: List[App], fitment_element_prevalence: Dict[str, int],
                                        size_to_beat: int, human_readable: bool, truncate_long_notes: bool,
                                        vcdb: VCdb, qdb: Qdb) -> List[FitmentNode]:
        """Build fitment tree from application list"""
        # Implementation would construct a fitment tree for analysis
        return []
    
    def export_flat_apps(self, file_path: str, vcdb: VCdb, pcdb: PCdb, qdb: Qdb, delimiter: str, format_type: str) -> str:
        """Export applications in flat format"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header
                header = delimiter.join([
                    "AppID", "Action", "BaseVehicleID", "Make", "Model", "Year",
                    "PartType", "Position", "Quantity", "Part", "MfrLabel",
                    "VCdbAttributes", "QdbQualifiers", "Notes"
                ])
                f.write(header + "\n")
                
                # Write apps
                for app in self.apps:
                    row = delimiter.join([
                        str(app.id), app.action, str(app.basevehicle_id),
                        vcdb.nice_make_of_basevid(app.basevehicle_id),
                        vcdb.nice_model_of_basevid(app.basevehicle_id),
                        vcdb.nice_year_of_basevid(app.basevehicle_id),
                        pcdb.nice_parttype(app.parttype_id),
                        pcdb.nice_position(app.position_id),
                        str(app.quantity), app.part, app.mfr_label,
                        app.nice_attributes_string(vcdb, False),
                        app.nice_qdb_qualifier_string(qdb),
                        ";".join(app.notes)
                    ])
                    f.write(row + "\n")
            
            return ""
        except Exception as ex:
            return str(ex)
    
    def export_xml_apps(self, file_path: str, submission_type: str, cipher_file_path: str, anonymize: bool) -> str:
        """Export applications as ACES XML"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(f'<ACES version="{self.version}">\n')
                
                # Write header
                f.write('  <Header>\n')
                f.write(f'    <Company>{self.company}</Company>\n')
                f.write(f'    <SenderName>{self.sender_name}</SenderName>\n')
                f.write(f'    <SenderPhone>{self.sender_phone}</SenderPhone>\n')
                f.write(f'    <TransferDate>{self.transfer_date}</TransferDate>\n')
                f.write(f'    <DocumentTitle>{self.document_title}</DocumentTitle>\n')
                f.write(f'    <EffectiveDate>{self.effective_date}</EffectiveDate>\n')
                f.write(f'    <SubmissionType>{submission_type}</SubmissionType>\n')
                f.write(f'    <VcdbVersionDate>{self.vcdb_version_date}</VcdbVersionDate>\n')
                f.write(f'    <QdbVersionDate>{self.qdb_version_date}</QdbVersionDate>\n')
                f.write(f'    <PcdbVersionDate>{self.pcdb_version_date}</PcdbVersionDate>\n')
                f.write('  </Header>\n')
                
                # Write applications
                for app in self.apps:
                    self._write_app_xml(f, app)
                
                # Write assets
                for asset in self.assets:
                    self._write_asset_xml(f, asset)
                
                # Write footer
                f.write('  <Footer>\n')
                f.write(f'    <RecordCount>{len(self.apps)}</RecordCount>\n')
                f.write('  </Footer>\n')
                f.write('</ACES>\n')
            
            return ""
        except Exception as ex:
            return str(ex)
    
    def _write_app_xml(self, f, app: App):
        """Write application XML"""
        f.write(f'  <App action="{app.action}" id="{app.id}"')
        if app.reference:
            f.write(f' ref="{app.reference}"')
        if not app.validate:
            f.write(' validate="no"')
        f.write('>\n')
        
        # Write base vehicle
        if app.basevehicle_id:
            f.write(f'    <BaseVehicle id="{app.basevehicle_id}"></BaseVehicle>\n')
        
        # Write VCdb attributes
        for attr in app.vcdb_attributes:
            f.write(f'    <{attr.name} id="{attr.value}"></{attr.name}>\n')
        
        # Write Qdb qualifiers
        for qual in app.qdb_qualifiers:
            f.write(f'    <Qual id="{qual.qualifier_id}">\n')
            for param in qual.qualifier_parameters:
                f.write(f'      <param value="{param}"></param>\n')
            f.write('      <text></text>\n')
            f.write('    </Qual>\n')
        
        # Write notes
        for note in app.notes:
            f.write(f'    <Note>{note}</Note>\n')
        
        # Write part information
        f.write(f'    <Qty>{app.quantity}</Qty>\n')
        f.write(f'    <PartType id="{app.parttype_id}"></PartType>\n')
        if app.mfr_label:
            f.write(f'    <MfrLabel>{app.mfr_label}</MfrLabel>\n')
        if app.position_id:
            f.write(f'    <Position id="{app.position_id}"></Position>\n')
        f.write(f'    <Part')
        if app.brand:
            f.write(f' BrandAAIAID="{app.brand}"')
        f.write(f'>{app.part}</Part>\n')
        
        if app.asset:
            f.write(f'    <AssetName>{app.asset}</AssetName>\n')
            if app.asset_item_order:
                f.write(f'    <AssetItemOrder>{app.asset_item_order}</AssetItemOrder>\n')
            if app.asset_item_ref:
                f.write(f'    <AssetItemRef>{app.asset_item_ref}</AssetItemRef>\n')
        
        f.write('  </App>\n')
    
    def _write_asset_xml(self, f, asset: Asset):
        """Write asset XML"""
        f.write(f'  <Asset action="{asset.action}" id="{asset.id}">\n')
        
        # Write base vehicle
        if asset.basevehicle_id:
            f.write(f'    <BaseVehicle id="{asset.basevehicle_id}"></BaseVehicle>\n')
        
        # Write VCdb attributes
        for attr in asset.vcdb_attributes:
            f.write(f'    <{attr.name} id="{attr.value}"></{attr.name}>\n')
        
        # Write Qdb qualifiers
        for qual in asset.qdb_qualifiers:
            f.write(f'    <Qual id="{qual.qualifier_id}">\n')
            for param in qual.qualifier_parameters:
                f.write(f'      <param value="{param}"></param>\n')
            f.write('      <text></text>\n')
            f.write('    </Qual>\n')
        
        # Write notes
        for note in asset.notes:
            f.write(f'    <Note>{note}</Note>\n')
        
        # Write asset name
        f.write(f'    <AssetName>{asset.asset_name}</AssetName>\n')
        
        f.write('  </Asset>\n')
    
    def generate_assessment_file(self, file_path: str, vcdb: 'VCdb', pcdb: 'PCdb', qdb: 'Qdb',
                                all_coverage: float, modern_coverage: float,
                                basevehicle_hit_count: int, total_basevehicles: int,
                                modern_basevehicle_hit_count: int, modern_basevehicles_available: int,
                                start_time: datetime, cache_path: str):
        """Generate comprehensive assessment file in Excel XML format"""
        
        def escape_xml(text):
            """Escape XML special characters"""
            if not text:
                return ""
            return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;")
        
        runtime = datetime.now() - start_time
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write Excel XML header
                f.write('<?xml version="1.0"?>'
                       '<?mso-application progid="Excel.Sheet"?>'
                       '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
                       'xmlns:o="urn:schemas-microsoft-com:office:office" '
                       'xmlns:x="urn:schemas-microsoft-com:office:excel" '
                       'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" '
                       'xmlns:html="http://www.w3.org/TR/REC-html40">')
                
                # Document properties
                f.write('<DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">'
                       '<Author>ACESinspector</Author>'
                       '<LastAuthor>ACESinspector</LastAuthor>'
                       f'<Created>{datetime.now().isoformat()}Z</Created>'
                       '<Version>14.00</Version>'
                       '</DocumentProperties>')
                
                # Styles
                f.write('<Styles>'
                       '<Style ss:ID="Default" ss:Name="Normal">'
                       '<Alignment ss:Vertical="Bottom"/>'
                       '<Borders/>'
                       '<Font ss:FontName="Calibri" x:Family="Swiss" ss:Size="11" ss:Color="#000000"/>'
                       '<Interior/>'
                       '<NumberFormat/>'
                       '<Protection/>'
                       '</Style>'
                       '<Style ss:ID="s62"><NumberFormat ss:Format="Short Date"/></Style>'
                       '<Style ss:ID="s64" ss:Name="Hyperlink">'
                       '<Font ss:FontName="Calibri" x:Family="Swiss" ss:Size="11" ss:Color="#0000FF" ss:Underline="Single"/>'
                       '</Style>'
                       '<Style ss:ID="s65">'
                       '<Font ss:FontName="Calibri" x:Family="Swiss" ss:Size="11" ss:Color="#000000" ss:Bold="1"/>'
                       '<Interior ss:Color="#D9D9D9" ss:Pattern="Solid"/>'
                       '</Style>'
                       '</Styles>')
                
                # Stats worksheet
                f.write('<Worksheet ss:Name="Stats">'
                       '<Table ss:ExpandedColumnCount="3" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                       '<Column ss:Width="170"/>'
                       '<Column ss:Width="171"/>'
                       '<Column ss:Width="144"/>')
                
                # Stats content
                f.write(f'<Row><Cell><Data ss:Type="String">Input Filename</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{escape_xml(os.path.basename(self.file_path))}</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">Title</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{escape_xml(self.document_title)}</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">Brand</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{escape_xml(self.brand_aaiaid)}</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">ACES version</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{escape_xml(self.version)}</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">Application count</Data></Cell>'
                       f'<Cell><Data ss:Type="Number">{len(self.apps)}</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">Unique Part count</Data></Cell>'
                       f'<Cell><Data ss:Type="Number">{len(self.parts_app_counts)}</Data></Cell></Row>')
                
                # Result
                total_errors = (self.basevehicleids_errors_count + self.vcdb_codes_errors_count + 
                               self.vcdb_configurations_errors_count + self.qdb_errors_count + 
                               self.parttype_position_errors_count)
                
                if total_errors > 0:
                    failure_reasons = []
                    if self.parttype_position_errors_count > 0:
                        failure_reasons.append(f"{self.parttype_position_errors_count} partType-position pairings")
                    if self.vcdb_codes_errors_count > 0:
                        failure_reasons.append(f"{self.vcdb_codes_errors_count} invalid VCdb codes")
                    if self.vcdb_configurations_errors_count > 0:
                        failure_reasons.append(f"{self.vcdb_configurations_errors_count} invalid VCdb configs")
                    if self.basevehicleids_errors_count > 0:
                        failure_reasons.append(f"{self.basevehicleids_errors_count} invalid basevehicles")
                    if self.qdb_errors_count > 0:
                        failure_reasons.append(f"{self.qdb_errors_count} Qdb errors")
                    if self.fitment_logic_problems_count > 0:
                        failure_reasons.append(f"{self.fitment_logic_problems_count} fitment logic problems")
                    
                    f.write(f'<Row><Cell><Data ss:Type="String">Result</Data></Cell>'
                           f'<Cell><Data ss:Type="String">Fail</Data></Cell>'
                           f'<Cell><Data ss:Type="String">{escape_xml(", ".join(failure_reasons))}</Data></Cell></Row>')
                else:
                    f.write('<Row><Cell><Data ss:Type="String">Result</Data></Cell>'
                           '<Cell><Data ss:Type="String">Pass</Data></Cell></Row>')
                
                f.write(f'<Row><Cell><Data ss:Type="String">All BaseVehicle Coverage (%)</Data></Cell>'
                       f'<Cell><Data ss:Type="Number">{all_coverage:.2f}</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{basevehicle_hit_count} used, {total_basevehicles} available</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">1990+ BaseVehicle Coverage (%)</Data></Cell>'
                       f'<Cell><Data ss:Type="Number">{modern_coverage:.2f}</Data></Cell>'
                       f'<Cell><Data ss:Type="String">{modern_basevehicle_hit_count} used, {modern_basevehicles_available} available</Data></Cell></Row>')
                f.write(f'<Row><Cell><Data ss:Type="String">Processing Time (Seconds)</Data></Cell>'
                       f'<Cell><Data ss:Type="Number">{runtime.total_seconds():.1f}</Data></Cell></Row>')
                
                f.write('</Table></Worksheet>')
                
                # Parts worksheet
                f.write('<Worksheet ss:Name="Parts">'
                       '<Table ss:ExpandedColumnCount="4" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                       '<Row>'
                       '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                       '<Cell ss:StyleID="s65"><Data ss:Type="String">Applications Count</Data></Cell>'
                       '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Types</Data></Cell>'
                       '<Cell ss:StyleID="s65"><Data ss:Type="String">Positions</Data></Cell>'
                       '</Row>')
                
                for part, count in self.parts_app_counts.items():
                    part_types = []
                    positions = []
                    
                    if part in self.parts_part_types:
                        part_types = [pcdb.nice_parttype(pt_id) for pt_id in self.parts_part_types[part]]
                    if part in self.parts_positions:
                        positions = [pcdb.nice_position(pos_id) for pos_id in self.parts_positions[part]]
                    
                    f.write(f'<Row>'
                           f'<Cell><Data ss:Type="String">{escape_xml(part)}</Data></Cell>'
                           f'<Cell><Data ss:Type="Number">{count}</Data></Cell>'
                           f'<Cell><Data ss:Type="String">{escape_xml(",".join(part_types))}</Data></Cell>'
                           f'<Cell><Data ss:Type="String">{escape_xml(",".join(positions))}</Data></Cell>'
                           f'</Row>')
                
                f.write('</Table></Worksheet>')
                
                # Error worksheets - add individual error worksheets based on analysis results
                self._write_error_worksheets(f, vcdb, pcdb, qdb, cache_path, escape_xml)
                
                f.write('</Workbook>')
                
        except Exception as ex:
            self.log_history_event("", f"Error generating assessment file: {ex}")
            raise
    
    def _write_error_worksheets(self, f, vcdb: 'VCdb', pcdb: 'PCdb', qdb: 'Qdb', cache_path: str, escape_xml):
        """Write error worksheets to assessment file"""
        
        # Part Type Position Errors
        if self.parttype_position_errors_count > 0:
            f.write('<Worksheet ss:Name="PartType-Position Errors">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            # Read error files and write data
            for chunk in self.individual_analysis_chunks_list:
                if chunk.parttype_position_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_parttypePositionErrors{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 11:
                                        f.write('<Row>')
                                        for field in fields[:11]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Qdb Errors
        if self.qdb_errors_count > 0:
            f.write('<Worksheet ss:Name="Qdb Errors">'
                   '<Table ss:ExpandedColumnCount="12" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Attributes</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Notes</Data></Cell>'
                   '</Row>')
            
            for chunk in self.individual_analysis_chunks_list:
                if chunk.qdb_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_QdbErrors{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 12:
                                        f.write('<Row>')
                                        for field in fields[:12]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Questionable Notes
        if self.questionable_notes_count > 0:
            f.write('<Worksheet ss:Name="Questionable Notes">'
                   '<Table ss:ExpandedColumnCount="12" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Attributes</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Notes</Data></Cell>'
                   '</Row>')
            
            for chunk in self.individual_analysis_chunks_list:
                if chunk.questionable_notes_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_questionableNotes{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 12:
                                        f.write('<Row>')
                                        for field in fields[:12]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Invalid BaseVehicles
        if self.basevehicleids_errors_count > 0:
            f.write('<Worksheet ss:Name="Invalid BaseVehicles">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            for chunk in self.individual_analysis_chunks_list:
                if chunk.basevehicleids_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_invalidBasevehicles{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 11:
                                        f.write('<Row>')
                                        for field in fields[:11]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Invalid VCdb Codes
        if self.vcdb_codes_errors_count > 0:
            f.write('<Worksheet ss:Name="Invalid VCdb Codes">'
                   '<Table ss:ExpandedColumnCount="12" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Attributes</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Notes</Data></Cell>'
                   '</Row>')
            
            for chunk in self.individual_analysis_chunks_list:
                if chunk.vcdb_codes_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_invalidVCdbCodes{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 12:
                                        f.write('<Row>')
                                        for field in fields[:12]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Configuration Errors
        if self.vcdb_configurations_errors_count > 0:
            f.write('<Worksheet ss:Name="Configuration Errors">'
                   '<Table ss:ExpandedColumnCount="12" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Error</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Attributes</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Notes</Data></Cell>'
                   '</Row>')
            
            for chunk in self.individual_analysis_chunks_list:
                if chunk.vcdb_configurations_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_configurationErrors{chunk.id}.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 12:
                                        f.write('<Row>')
                                        for field in fields[:12]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Quantity Outliers
        if self.qty_outlier_count > 0:
            f.write('<Worksheet ss:Name="Quantity Outliers">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Warning</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            for chunk in self.outlier_analysis_chunks_list:
                if chunk.qty_outlier_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_qtyOutliers.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 11:
                                        f.write('<Row>')
                                        for field in fields[:11]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Part Type Disagreements
        if self.parttype_disagreement_count > 0:
            f.write('<Worksheet ss:Name="Part Type Disagreements">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Warning</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            for chunk in self.outlier_analysis_chunks_list:
                if chunk.parttype_disagreement_errors_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_parttypeDisagreements.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 11:
                                        f.write('<Row>')
                                        for field in fields[:11]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Asset Problems
        if self.asset_problems_count > 0:
            f.write('<Worksheet ss:Name="Asset Problems">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Warning</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            for chunk in self.outlier_analysis_chunks_list:
                if chunk.asset_problems_count > 0:
                    try:
                        error_file = f"{chunk.cache_file}_assetProblems.txt"
                        if os.path.exists(error_file):
                            with open(error_file, 'r', encoding='utf-8') as ef:
                                for line in ef:
                                    fields = line.strip().split('\t')
                                    if len(fields) >= 11:
                                        f.write('<Row>')
                                        for field in fields[:11]:
                                            f.write(f'<Cell><Data ss:Type="String">{escape_xml(field)}</Data></Cell>')
                                        f.write('</Row>')
                    except:
                        pass
            
            f.write('</Table></Worksheet>')
        
        # Fitment Logic Problems
        if self.fitment_logic_problems_count > 0:
            f.write('<Worksheet ss:Name="Fitment Logic Problems">'
                   '<Table ss:ExpandedColumnCount="11" x:FullColumns="1" x:FullRows="1" ss:DefaultRowHeight="15">'
                   '<Row>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Problem Group</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">App Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Base Vehicle Id</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Make</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Model</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Year</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part Type</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Position</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Quantity</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Part</Data></Cell>'
                   '<Cell ss:StyleID="s65"><Data ss:Type="String">Fitment</Data></Cell>'
                   '</Row>')
            
            for group_id, apps in self.fitment_problem_groups_app_lists.items():
                for app in apps:
                    f.write('<Row>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(group_id)}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(str(app.id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(str(app.basevehicle_id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(vcdb.nice_make_of_basevid(app.basevehicle_id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(vcdb.nice_model_of_basevid(app.basevehicle_id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(str(vcdb.nice_year_of_basevid(app.basevehicle_id)))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(pcdb.nice_parttype(app.parttype_id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(pcdb.nice_position(app.position_id))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(str(app.quantity))}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(app.part)}</Data></Cell>')
                    f.write(f'<Cell><Data ss:Type="String">{escape_xml(app.nice_full_fitment_string(vcdb, qdb))}</Data></Cell>')
                    f.write('</Row>')
            
            f.write('</Table></Worksheet>')