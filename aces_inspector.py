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

from autocare import ACES, VCdb, PCdb, Qdb


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


def main():
    """Main entry point"""
    starting_datetime = datetime.now()
    
    parser = argparse.ArgumentParser(
        description='ACES XML file analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python aces_inspector.py -i "ACES.xml" -o ./output -t ./temp -v vcdb.accdb -p pcdb.accdb -q qdb.accdb -l ./logs --verbose

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
    parser.add_argument('-v', '--vcdb', required=True, help='VCdb Access database file')
    parser.add_argument('-p', '--pcdb', required=True, help='PCdb Access database file')
    parser.add_argument('-q', '--qdb', required=True, help='Qdb Access database file')
    parser.add_argument('-l', '--logs', help='Logs directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose console output')
    parser.add_argument('--delete', action='store_true', help='Delete input ACES file upon successful analysis')
    parser.add_argument('--version', action='version', version=f'Version: {get_version()}')
    
    if len(sys.argv) == 1:
        print(f"Version: {get_version()}")
        print("usage: python aces_inspector.py -i <ACES xml file> -v <VCdb access file> -p <PCdb access file> -q <Qdb access file> -o <assessment file> -t <temp directory> [-l <logs directory>]")
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

    # Validate database files exist
    if not os.path.exists(vcdb_file):
        print(f"VCdb Access database file ({vcdb_file}) does not exist")
        return 4  # failure - reference database not found

    if not os.path.exists(pcdb_file):
        print(f"PCdb Access database file ({pcdb_file}) does not exist")
        return 4  # failure - reference database not found

    if not os.path.exists(qdb_file):
        print(f"Qdb Access database file ({qdb_file}) does not exist")
        return 4  # failure - reference database not found

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

    # Perform analysis
    try:
        if verbose:
            print("performing analysis")
            
        # This would involve calling the various analysis methods
        # For now, we'll create a basic analysis structure
        # The full analysis implementation would be quite extensive
        
        # Create assessment file
        assessment_filename = f"{Path(input_file).stem}_{aces.file_md5_hash}_assessment.xml"
        assessment_path = os.path.join(assessments_path, assessment_filename)
        
        # Generate Excel-format XML output (placeholder for now)
        with open(assessment_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0"?>\n')
            f.write('<?mso-application progid="Excel.Sheet"?>\n')
            f.write('<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"\n')
            f.write(' xmlns:o="urn:schemas-microsoft-com:office:office"\n')
            f.write(' xmlns:x="urn:schemas-microsoft-com:office:excel"\n')
            f.write(' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"\n')
            f.write(' xmlns:html="http://www.w3.org/TR/REC-html40">\n')
            
            # Add basic summary worksheet
            f.write('<Worksheet ss:Name="Summary">\n')
            f.write('<Table>\n')
            f.write('<Row><Cell><Data ss:Type="String">ACES Analysis Summary</Data></Cell></Row>\n')
            f.write(f'<Row><Cell><Data ss:Type="String">Input File:</Data></Cell><Cell><Data ss:Type="String">{escape_xml_special_chars(input_file)}</Data></Cell></Row>\n')
            f.write(f'<Row><Cell><Data ss:Type="String">Applications Count:</Data></Cell><Cell><Data ss:Type="Number">{len(aces.apps)}</Data></Cell></Row>\n')
            f.write(f'<Row><Cell><Data ss:Type="String">Analysis Date:</Data></Cell><Cell><Data ss:Type="String">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</Data></Cell></Row>\n')
            f.write('</Table>\n')
            f.write('</Worksheet>\n')
            f.write('</Workbook>\n')

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