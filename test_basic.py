#!/usr/bin/env python3
"""
Basic test script for ACES Inspector CLI Python port
Demonstrates core functionality without requiring actual database files
"""

from autocare import ACES, VCdb, PCdb, Qdb, App, Asset, VCdbAttribute, QdbQualifier
import tempfile
import os


def test_basic_classes():
    """Test basic class instantiation and functionality"""
    print("Testing basic class instantiation...")
    
    # Test ACES class
    aces = ACES()
    assert aces.successful_import == False
    assert len(aces.apps) == 0
    assert len(aces.assets) == 0
    print("✓ ACES class initialized successfully")
    
    # Test VCdb class
    vcdb = VCdb()
    assert vcdb.import_success == False
    assert len(vcdb.vcdb_basevehicle_dict) == 0
    print("✓ VCdb class initialized successfully")
    
    # Test PCdb class
    pcdb = PCdb()
    assert pcdb.import_success == False
    assert len(pcdb.parttypes) == 0
    print("✓ PCdb class initialized successfully")
    
    # Test Qdb class
    qdb = Qdb()
    assert qdb.import_success == False
    assert len(qdb.qualifiers) == 0
    print("✓ Qdb class initialized successfully")


def test_app_functionality():
    """Test App class functionality"""
    print("\nTesting App class functionality...")
    
    app = App()
    app.id = 1
    app.action = "A"
    app.basevehicle_id = 12345
    app.parttype_id = 100
    app.position_id = 1
    app.quantity = 2
    app.part = "TEST-PART-123"
    app.mfr_label = "Test Manufacturer"
    
    # Test VCdb attributes
    attr1 = VCdbAttribute()
    attr1.name = "EngineBase"
    attr1.value = 456
    app.vcdb_attributes.append(attr1)
    
    attr2 = VCdbAttribute()
    attr2.name = "DriveType"
    attr2.value = 789
    app.vcdb_attributes.append(attr2)
    
    # Test Qdb qualifiers
    qual = QdbQualifier()
    qual.qualifier_id = 123
    qual.qualifier_parameters = ["param1", "param2"]
    app.qdb_qualifiers.append(qual)
    
    # Test notes
    app.notes.append("Test note 1")
    app.notes.append("Test note 2")
    
    # Test string methods
    name_val_pairs = app.name_val_pair_string(True)
    assert "EngineBase:456" in name_val_pairs
    assert "DriveType:789" in name_val_pairs
    assert "Test note 1" in name_val_pairs
    print("✓ App name_val_pair_string working")
    
    qdb_data = app.raw_qdb_data_string()
    assert "123:param1:param2;" == qdb_data
    print("✓ App raw_qdb_data_string working")
    
    app_hash = app.app_hash()
    assert len(app_hash) == 32  # MD5 hash length
    print("✓ App hash generation working")


def test_asset_functionality():
    """Test Asset class functionality"""
    print("\nTesting Asset class functionality...")
    
    asset = Asset()
    asset.id = 1
    asset.action = "A"
    asset.basevehicle_id = 12345
    asset.asset_name = "test_asset.jpg"
    
    # Test VCdb attributes
    attr = VCdbAttribute()
    attr.name = "SubModel"
    attr.value = 999
    asset.vcdb_attributes.append(attr)
    
    # Test notes
    asset.notes.append("Asset test note")
    
    print("✓ Asset class functionality working")


def test_xml_parsing():
    """Test basic XML parsing functionality"""
    print("\nTesting XML parsing functionality...")
    
    # Create a simple test ACES XML
    test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ACES version="4.2">
    <Header>
        <Company>Test Company</Company>
        <SenderName>Test Sender</SenderName>
        <SenderPhone>555-1234</SenderPhone>
        <TransferDate>2024-01-01</TransferDate>
        <DocumentTitle>Test Document</DocumentTitle>
        <EffectiveDate>2024-01-01</EffectiveDate>
        <SubmissionType>FULL</SubmissionType>
        <VcdbVersionDate>2024-01-01</VcdbVersionDate>
        <QdbVersionDate>2024-01-01</QdbVersionDate>
        <PcdbVersionDate>2024-01-01</PcdbVersionDate>
    </Header>
    <App action="A" id="1">
        <BaseVehicle id="12345"></BaseVehicle>
        <EngineBase id="456">V6 2.4L</EngineBase>
        <Qty>2</Qty>
        <PartType id="100">Air Filter</PartType>
        <Position id="1">Engine</Position>
        <Part>TEST-PART-123</Part>
        <Note>Test note</Note>
    </App>
    <Asset action="A" id="1">
        <BaseVehicle id="12345"></BaseVehicle>
        <AssetName>test_image.jpg</AssetName>
    </Asset>
    <Footer>
        <RecordCount>1</RecordCount>
    </Footer>
</ACES>'''
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(test_xml)
        temp_file = f.name
    
    try:
        aces = ACES()
        result = aces.import_xml(
            temp_file, 
            "",  # schema_string
            True,  # respect_validate_no_tag
            False,  # import_deletes
            {},  # note_translation
            {},  # note_qdb_transform
            "/tmp",  # cache_path
            True  # verbose
        )
        
        assert result == ""  # No error
        assert aces.successful_import == True
        assert len(aces.apps) == 1
        assert len(aces.assets) == 1
        assert aces.company == "Test Company"
        assert aces.sender_name == "Test Sender"
        assert aces.version == "4.2"
        
        # Check parsed app
        app = aces.apps[0]
        assert app.id == 1
        assert app.action == "A"
        assert app.basevehicle_id == 12345
        assert app.quantity == 2
        assert app.part == "TEST-PART-123"
        assert len(app.vcdb_attributes) == 1
        assert app.vcdb_attributes[0].name == "EngineBase"
        assert app.vcdb_attributes[0].value == 456
        assert len(app.notes) == 1
        assert app.notes[0] == "Test note"
        
        # Check parsed asset
        asset = aces.assets[0]
        assert asset.id == 1
        assert asset.action == "A"
        assert asset.asset_name == "test_image.jpg"
        
        print("✓ XML parsing working correctly")
        
    finally:
        # Clean up temp file
        os.unlink(temp_file)


def main():
    """Run all tests"""
    print("ACES Inspector CLI Python Port - Basic Tests")
    print("=" * 50)
    
    try:
        test_basic_classes()
        test_app_functionality()
        test_asset_functionality()
        test_xml_parsing()
        
        print("\n" + "=" * 50)
        print("✅ All basic tests passed!")
        print("\nNote: These are basic functionality tests.")
        print("Full testing requires actual VCdb/PCdb/Qdb database files.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())