#!/usr/bin/env python3
"""
ACES Inspector CLI - Python Port
A command-line program to analyze ACES XML files

Version: 1.0.0.21 (Python port)
Author: Luke Smith (Original C#), Python Port

Changes:
1.0.0.21 (9/17/2024) defaulted "allowGraceForWildcardConfigs" to true. Fixed spelling error in output spreadsheet "Vehiclce"
[Previous versions documented in original C# project]

Example command line call:
python aces_inspector.py -i "input/ACES file with spaces.xml" -o myOutputDir -t myTempDir -l myLogsDir -v VCdb20230126.accdb -p PCdb20230126.accdb -q Qdb20230126.accdb --delete --verbose

Return values (int) from the command call:
 - 0 successful analysis. Output spreadsheet and log file written 
 - 1 failure - missing command line args
 - 2 failure - local filesystem problems reading input
 - 3 failure - local filesystem problems writing output
 - 4 failure - reference database (vcdb, pcdb or qdb) not found
 - 5 failure - reference database import (vcdb, pcdb or qdb)
 - 6 failure - xml xsd validation
"""

import sys
import os
import argparse
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path
import traceback
from concurrent.futures import ThreadPoolExecutor

from autocare import ACES, VCdb, PCdb, Qdb
from database_adapter import DatabaseConfig


def escape_xml_special_chars(input_string: str) -> str:
    """Escape XML special characters in string"""
    if not input_string:
        return ""
    
    output_string = input_string
    output_string = output_string.replace("&", "&amp;")
    output_string = output_string.replace("<", "&lt;")
    output_string = output_string.replace(">", "&gt;")
    output_string = output_string.replace("'", "&apos;")
    output_string = output_string.replace('"', "&quot;")
    return output_string


def get_version():
    """Get version string"""
    return "1.0.0.21"


def is_database_connection_string(path: str) -> bool:
    """Check if path is a database connection string rather than a file path"""
    path_lower = path.lower()
    return (
        path_lower.startswith(('mysql://', 'mysql+pymysql://')) or
        'host=' in path_lower or
        ('driver=' in path_lower and 'dbq=' in path_lower)
    )


def validate_database_source(db_path: str, db_name: str, verbose: bool = False) -> int:
    """Validate database source (file or connection string). Returns 0 on success, 4 on failure."""
    try:
        if is_database_connection_string(db_path):
            # This is a connection string - try to parse it
            config = DatabaseConfig.from_connection_string(db_path)
            if config.db_type == "unknown":
                print(f"{db_name} connection string format not recognized: {db_path}")
                return 4
            if verbose:
                print(f"{db_name} using {config.db_type} database connection")
            return 0
        else:
            # This should be a file path
            if not os.path.exists(db_path):
                print(f"{db_name} database file ({db_path}) does not exist")
                return 4
            if verbose:
                print(f"{db_name} using Access database file")
            return 0
    except Exception as ex:
        print(f"Error validating {db_name} database source: {ex}")
        return 4


def main():
    """Main entry point"""
    starting_datetime = datetime.now()
    
    parser = argparse.ArgumentParser(
        description='ACES XML file analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  Access databases:
    python aces_inspector.py -i "ACES.xml" -o ./output -t ./temp -v vcdb.accdb -p pcdb.accdb -q qdb.accdb -l ./logs --verbose
  
  MySQL databases:
    python aces_inspector.py -i "ACES.xml" -o ./output -t ./temp -v "mysql://user:pass@localhost/vcdb" -p "mysql://user:pass@localhost/pcdb" -q "mysql://user:pass@localhost/qdb" --verbose

Return codes:
  0 - Successful analysis
  1 - Missing command line arguments
  2 - Input file access problems
  3 - Output directory access problems
  4 - Reference database not found
  5 - Reference database import failure
  6 - XML XSD validation failure
        """
    )
    
    parser.add_argument('-i', '--input', required=True, help='Input ACES XML file')
    parser.add_argument('-o', '--output', required=True, help='Output directory for assessment files')
    parser.add_argument('-t', '--temp', required=True, help='Temporary directory')
    parser.add_argument('-v', '--vcdb', required=True, help='VCdb database (Access file path or MySQL connection string)')
    parser.add_argument('-p', '--pcdb', required=True, help='PCdb database (Access file path or MySQL connection string)')
    parser.add_argument('-q', '--qdb', required=True, help='Qdb database (Access file path or MySQL connection string)')
    parser.add_argument('-l', '--logs', help='Logs directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose console output')
    parser.add_argument('--delete', action='store_true', help='Delete input ACES file upon successful analysis')
    parser.add_argument('--version', action='version', version=f'Version: {get_version()}')
    
    if len(sys.argv) == 1:
        print(f"Version: {get_version()}")
        print("usage: python aces_inspector.py -i <ACES xml file> -v <VCdb database> -p <PCdb database> -q <Qdb database> -o <assessment file> -t <temp directory> [-l <logs directory>]")
        print("\nDatabase options:")
        print("  Access files: path/to/database.accdb")
        print("  MySQL: mysql://user:pass@host:port/dbname")
        print("  MySQL params: host=localhost;user=user;password=pass;database=dbname")
        print("\noptional switches")
        print("  --verbose    verbose console output")
        print("  --delete     delete input ACES file upon successful analysis")
        return 1  # failure - missing command line args

    args = parser.parse_args()
    
    verbose = args.verbose
    delete_aces_file_on_success = args.delete
    input_file = args.input
    vcdb_file = args.vcdb
    pcdb_file = args.pcdb
    qdb_file = args.qdb
    log_file = args.logs if args.logs else ""
    assessments_path = args.output
    cache_path = args.temp

    # Validate input file exists
    if not os.path.exists(input_file):
        print(f"input ACES file ({input_file}) does not exist")
        return 2  # failure - local filesystem problems reading input

    # Validate output directory exists
    if not os.path.exists(assessments_path):
        print(f"output directory ({assessments_path}) does not exist")
        return 3  # failure - local filesystem problems writing output

    # Ensure temp directory and AiFragments folder exist
    if os.path.exists(cache_path):
        ai_fragments_path = os.path.join(cache_path, "AiFragments")
        if not os.path.exists(ai_fragments_path):
            try:
                os.makedirs(ai_fragments_path)
            except Exception as ex:
                print(f"failed to create AiFragments directory inside temp folder: {ex}")
                return 3  # failure - local filesystem problems writing output
    else:
        print(f"temp directory ({cache_path}) does not exist")
        return 3  # failure - local filesystem problems writing output

    # Validate database sources (files or connection strings)
    result = validate_database_source(vcdb_file, "VCdb", verbose)
    if result != 0:
        return result

    result = validate_database_source(pcdb_file, "PCdb", verbose)
    if result != 0:
        return result

    result = validate_database_source(qdb_file, "Qdb", verbose)
    if result != 0:
        return result

    if verbose:
        print(f"version {get_version()}")

    cache_files_to_delete_on_exit = []

    use_assets_as_fitment = True  # changed from false to true in v 1.0.0.19
    report_all_apps_in_problem_group = False
    concern_for_disparate = False
    respect_qdb_type = False
    macro_problems_description = ""
    thread_count = 20
    tree_config_limit = 1000

    note_translation_dictionary = {}
    note_to_qdb_transform_dictionary = {}

    # Initialize main objects
    aces = ACES()  # this instance will hold all the data imported from our "primary" ACES xml file
    vcdb = VCdb()  # this class will hold all the contents of the imported VCdb Access file
    pcdb = PCdb()
    qdb = Qdb()

    aces.allow_grace_for_wildcard_configs = True

    # Hash the input file - temp fragment files are named including this hash
    try:
        with open(input_file, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest().upper()
            aces.file_md5_hash = file_hash
    except Exception as ex:
        if verbose:
            print(f"error opening input ACES file: {ex}")
        return 2  # failure - local filesystem problems reading input

    # Setup logging
    if log_file:
        log_file_path = os.path.join(log_file, f"{Path(input_file).stem}_{aces.file_md5_hash}.log")
        try:
            with open(log_file_path, 'w') as f:
                f.write(f"{datetime.now()}\tVersion {get_version()} started\n")
        except Exception as ex:
            if verbose:
                print(f"failed to create log file: {ex}")

    # Connect to databases
    try:
        if verbose:
            print("connecting to VCdb")
        result = vcdb.connect_local_oledb(vcdb_file)
        if result:
            print(f"VCdb connection failed: {result}")
            return 4

        if verbose:
            print("connecting to PCdb")
        result = pcdb.connect_local_oledb(pcdb_file)
        if result:
            print(f"PCdb connection failed: {result}")
            return 4

        if verbose:
            print("connecting to Qdb")
        result = qdb.connect_local_oledb(qdb_file)
        if result:
            print(f"Qdb connection failed: {result}")
            return 4

    except Exception as ex:
        if verbose:
            print(f"database connection error: {ex}")
        return 4

    # Import database data
    try:
        if verbose:
            print("importing VCdb data")
        result = vcdb.import_oledb_data()
        if result:
            print(f"VCdb import failed: {result}")
            return 5

        if verbose:
            print("importing PCdb data")
        result = pcdb.import_oledb()
        if result:
            print(f"PCdb import failed: {result}")
            return 5

        if verbose:
            print("importing Qdb data")
        result = qdb.import_oledb()
        if result:
            print(f"Qdb import failed: {result}")
            return 5

    except Exception as ex:
        if verbose:
            print(f"database import error: {ex}")
        return 5

    # Import and analyze ACES XML
    try:
        if verbose:
            print("importing ACES XML data")
        
        # Get appropriate schema string based on XML version
        schema_string = ""  # Will be determined during import
        
        result = aces.import_xml(
            input_file, 
            schema_string,
            True,  # respect_validate_no_tag
            False,  # import_deletes
            note_translation_dictionary,
            note_to_qdb_transform_dictionary,
            cache_path,
            verbose
        )
        
        if not aces.successful_import:
            if verbose:
                print("ACES XML import failed")
            return 6  # XML validation failure

        if verbose:
            print(f"imported {len(aces.apps)} applications")

    except Exception as ex:
        if verbose:
            print(f"ACES XML import error: {ex}")
            traceback.print_exc()
        return 6

    # Perform comprehensive analysis
    try:
        if verbose:
            print("performing analysis")
        
        # Set analysis running flag
        aces.analysis_running = True
        
        # Set analysis parameters
        aces.qty_outlier_threshold = 1
        aces.qty_outlier_sample_size = 1000
        
        # Establish fitment tree roots
        aces.establish_fitment_tree_roots(use_assets_as_fitment)
        
        # Clear previous analysis results
        aces.clear_analysis_results()
        
        # Divide apps into analysis chunks for parallel processing
        number_of_sections = thread_count
        if (number_of_sections * 5) > len(aces.apps):
            number_of_sections = 1  # Ensure at least 5 apps per section
        
        section_size = len(aces.apps) // number_of_sections if number_of_sections > 0 else len(aces.apps)
        
        # Create individual analysis chunks
        chunk_id = 1
        current_chunk = None
        
        for i, app in enumerate(aces.apps):
            if not current_chunk or len(current_chunk.apps_list) >= section_size:
                from autocare import AnalysisChunk
                current_chunk = AnalysisChunk()
                current_chunk.id = chunk_id
                current_chunk.cache_file = os.path.join(cache_path, "AiFragments", aces.file_md5_hash)
                current_chunk.apps_list = []
                aces.individual_analysis_chunks_list.append(current_chunk)
                
                # Add cache files to deletion list
                cache_files_to_delete_on_exit.extend([
                    f"{current_chunk.cache_file}_parttypePositionErrors{chunk_id}.txt",
                    f"{current_chunk.cache_file}_QdbErrors{chunk_id}.txt",
                    f"{current_chunk.cache_file}_questionableNotes{chunk_id}.txt",
                    f"{current_chunk.cache_file}_invalidBasevehicles{chunk_id}.txt",
                    f"{current_chunk.cache_file}_invalidVCdbCodes{chunk_id}.txt",
                    f"{current_chunk.cache_file}_configurationErrors{chunk_id}.txt"
                ])
                chunk_id += 1
            
            current_chunk.apps_list.append(app)
        
        # Run individual app analysis in parallel
        if verbose:
            print("analyzing individual applications...")
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Individual app errors analysis
            individual_futures = []
            for chunk in aces.individual_analysis_chunks_list:
                future = executor.submit(aces.find_individual_app_errors, chunk, vcdb, pcdb, qdb)
                individual_futures.append(future)
            
            # Outlier analysis (single threaded)
            from autocare import AnalysisChunk
            outlier_chunk = AnalysisChunk()
            outlier_chunk.cache_file = os.path.join(cache_path, "AiFragments", aces.file_md5_hash)
            outlier_chunk.apps_list = aces.apps
            aces.outlier_analysis_chunks_list.append(outlier_chunk)
            cache_files_to_delete_on_exit.extend([
                f"{outlier_chunk.cache_file}_qtyOutliers.txt",
                f"{outlier_chunk.cache_file}_parttypeDisagreements.txt",
                f"{outlier_chunk.cache_file}_assetProblems.txt"
            ])
            
            outlier_future = executor.submit(aces.find_individual_app_outliers, outlier_chunk, vcdb, pcdb, qdb)
            
            # Fitment logic analysis
            if verbose:
                print("analyzing fitment logic...")
            
            # Create fitment analysis chunk groups
            fitment_sections = thread_count
            if (fitment_sections * 5) > len(aces.fitment_analysis_chunks_list):
                fitment_sections = 1
            
            fitment_section_size = len(aces.fitment_analysis_chunks_list) // fitment_sections if fitment_sections > 0 else len(aces.fitment_analysis_chunks_list)
            
            from autocare import AnalysisChunkGroup
            chunk_group_id = 1
            current_group = None
            
            for chunk in aces.fitment_analysis_chunks_list:
                if not current_group or len(current_group.chunks) >= fitment_section_size:
                    current_group = AnalysisChunkGroup()
                    current_group.id = chunk_group_id
                    current_group.chunks = []
                    aces.fitment_analysis_chunks_groups.append(current_group)
                    chunk_group_id += 1
                
                current_group.chunks.append(chunk)
            
            # Submit fitment logic analysis tasks
            fitment_futures = []
            for chunk_group in aces.fitment_analysis_chunks_groups:
                future = executor.submit(
                    aces.find_fitment_logic_problems,
                    chunk_group, vcdb, pcdb, qdb,
                    os.path.join(cache_path, "ACESinspector-fitment_permutations.txt"),
                    tree_config_limit, cache_path,
                    concern_for_disparate, respect_qdb_type,
                    True, thread_count, verbose
                )
                fitment_futures.append(future)
            
            # Wait for all analyses to complete
            for future in individual_futures + [outlier_future] + fitment_futures:
                future.result()  # This will raise any exceptions that occurred
        
        if verbose:
            print("  analysis complete")
        
        # Compile total error and warning counts
        aces.parttype_position_errors_count = 0
        aces.qdb_errors_count = 0
        aces.questionable_notes_count = 0
        aces.basevehicleids_errors_count = 0
        aces.vcdb_codes_errors_count = 0
        aces.vcdb_configurations_errors_count = 0
        aces.parttype_disagreement_count = 0
        aces.qty_outlier_count = 0
        aces.asset_problems_count = 0
        
        # Sum up individual analysis results
        for chunk in aces.individual_analysis_chunks_list:
            aces.parttype_position_errors_count += chunk.parttype_position_errors_count
            aces.qdb_errors_count += chunk.qdb_errors_count
            aces.questionable_notes_count += chunk.questionable_notes_count
            aces.basevehicleids_errors_count += chunk.basevehicleids_errors_count
            aces.vcdb_codes_errors_count += chunk.vcdb_codes_errors_count
            aces.vcdb_configurations_errors_count += chunk.vcdb_configurations_errors_count
        
        # Sum up outlier analysis results
        for chunk in aces.outlier_analysis_chunks_list:
            aces.parttype_disagreement_count += chunk.parttype_disagreement_errors_count
            aces.qty_outlier_count += chunk.qty_outlier_count
            aces.asset_problems_count += chunk.asset_problems_count
        
        # Sum up fitment logic problems
        aces.fitment_logic_problems_count = 0
        problem_group_number = 0
        
        for chunk_group in aces.fitment_analysis_chunks_groups:
            for chunk in chunk_group.chunks:
                if len(chunk.problem_apps_list) > 0:
                    aces.fitment_logic_problems_count += len(chunk.problem_apps_list)
                    problem_group_number += 1
                    
                    if report_all_apps_in_problem_group:
                        aces.fitment_problem_groups_app_lists[str(problem_group_number)] = chunk.apps_list
                    else:
                        aces.fitment_problem_groups_app_lists[str(problem_group_number)] = chunk.problem_apps_list
                    
                    aces.fitment_problem_groups_best_permutations[str(problem_group_number)] = chunk.lowest_badness_permutation
        
        # Calculate total errors and problems
        total_errors = (aces.basevehicleids_errors_count + aces.vcdb_codes_errors_count + 
                       aces.vcdb_configurations_errors_count + aces.qdb_errors_count + 
                       aces.parttype_position_errors_count)
        
        if verbose:
            print(f"{total_errors} errors")
        
        # Build problems summary
        problems_list = []
        if aces.fitment_logic_problems_count > 0:
            problems_list.append(f"{aces.fitment_logic_problems_count} logic flaws")
        if aces.qty_outlier_count > 0:
            problems_list.append(f"{aces.qty_outlier_count} qty outliers")
        if aces.parttype_disagreement_count > 0:
            problems_list.append(f"{aces.parttype_disagreement_count} type disagreements")
        if aces.asset_problems_count > 0:
            problems_list.append(f"{aces.asset_problems_count} asset problems")
        
        macro_problems_description = "0 problems" if not problems_list else ", ".join(problems_list)
        
        if verbose:
            print(macro_problems_description)
            print("writing assessment file")
        
        # Create comprehensive assessment file
        assessment_filename = f"{Path(input_file).stem}_{aces.file_md5_hash}_assessment.xml"
        assessment_path = os.path.join(assessments_path, assessment_filename)
        
        # Calculate base vehicle coverage
        basevehicle_hit_count = 0
        modern_basevehicle_hit_count = 0
        modern_basevehicles_available = 0
        
        for base_vid, base_vehicle in vcdb.vcdb_basevehicle_dict.items():
            if base_vehicle.year >= 1990:
                modern_basevehicles_available += 1
            
            if base_vid in aces.basevid_occurrences:
                basevehicle_hit_count += 1
                if base_vehicle.year >= 1990:
                    modern_basevehicle_hit_count += 1
        
        total_basevehicles = len(vcdb.vcdb_basevehicle_dict)
        all_coverage = round((basevehicle_hit_count * 100) / (total_basevehicles + 1), 1) if total_basevehicles > 0 else 0
        modern_coverage = round((modern_basevehicle_hit_count * 100) / (modern_basevehicles_available + 1), 1) if modern_basevehicles_available > 0 else 0
        
        # Generate comprehensive Excel-format XML assessment file
        aces.generate_assessment_file(
            assessment_path, vcdb, pcdb, qdb, 
            all_coverage, modern_coverage,
            basevehicle_hit_count, total_basevehicles,
            modern_basevehicle_hit_count, modern_basevehicles_available,
            starting_datetime, cache_path
        )
        
        if verbose:
            print(f"assessment file created: {assessment_filename}")

    except Exception as ex:
        if verbose:
            print(f"assessment file NOT created: {ex}")
            traceback.print_exc()

    # Cleanup
    if verbose:
        print("deleting temp files")

    for cache_file in cache_files_to_delete_on_exit:
        try:
            os.remove(cache_file)
        except:
            pass

    # Delete input file if requested
    if delete_aces_file_on_success:
        if verbose:
            print("deleting input file")
        try:
            os.remove(input_file)
        except Exception as ex:
            if verbose:
                print(f"failed to delete input file: {ex}")

    # Disconnect databases
    try:
        vcdb.disconnect()
        pcdb.disconnect()
        qdb.disconnect()
    except:
        pass

    runtime = datetime.now() - starting_datetime
    if verbose:
        print(f"analysis completed in {runtime.total_seconds():.1f} seconds")

    return 0  # successful analysis


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)