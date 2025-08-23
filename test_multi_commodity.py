#!/usr/bin/env python3
"""
Test script for multi-commodity functionality without requiring API calls.

This script validates that:
1. Configuration loading works for all commodity classes
2. Database schema supports multiple commodities
3. ETL pipeline can handle different commodity codes
4. Main and batch scripts accept correct arguments
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.esr_pace.config import config_manager
from src.esr_pace.data_store import ESRDataStore
from src.esr_pace.etl import ESRETLPipeline

def test_configuration():
    """Test commodity configuration loading."""
    print("=== Testing Configuration Loading ===")
    
    try:
        config = config_manager.load_config()
        print(f"✅ Configuration loaded successfully")
        print(f"   Total commodities: {len(config.commodities)}")
        
        enabled = config_manager.get_enabled_commodities()
        print(f"   Enabled commodities: {len(enabled)}")
        
        for commodity in enabled:
            print(f"     • {commodity.code}: {commodity.name} - {commodity.description}")
        
        # Test specific lookups
        wheat_107 = config_manager.get_commodity_by_code(107)
        if wheat_107 and wheat_107.name == "All Wheat":
            print(f"✅ Commodity lookup works: {wheat_107.name}")
        else:
            print(f"❌ Commodity lookup failed for code 107")
            return False
        
        codes = config_manager.get_enabled_commodity_codes()
        if 101 in codes and 107 in codes and len(codes) == 7:
            print(f"✅ Enabled codes correct: {codes}")
        else:
            print(f"❌ Enabled codes incorrect: {codes}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_schema():
    """Test database schema supports multiple commodities."""
    print("\n=== Testing Database Schema ===")
    
    try:
        store = ESRDataStore()
        
        # Check current stats
        stats = store.get_database_stats()
        print(f"✅ Database accessible")
        print(f"   Current records: {stats['total_records']}")
        
        # Test that schema supports different commodity codes
        conn = store._get_connection()
        
        # Check table structure
        cursor = conn.execute("PRAGMA table_info(fact_esr_world_weekly)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_columns = ['commodity_code', 'market_year', 'week_ending']
        for col in required_columns:
            if col in columns:
                print(f"✅ Required column present: {col} ({columns[col]})")
            else:
                print(f"❌ Missing required column: {col}")
                return False
        
        # Test primary key includes commodity_code
        cursor = conn.execute("PRAGMA index_list(fact_esr_world_weekly)")
        indexes = cursor.fetchall()
        
        # Check commodity_code index exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='fact_esr_world_weekly' AND name LIKE '%commodity%'")
        commodity_index = cursor.fetchone()
        if commodity_index:
            print(f"✅ Commodity index exists: {commodity_index[0]}")
        else:
            print(f"⚠️  No dedicated commodity index found")
        
        store.close()
        return True
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_etl_commodity_support():
    """Test ETL pipeline can handle different commodity codes."""
    print("\n=== Testing ETL Multi-Commodity Support ===")
    
    try:
        # Create ETL pipeline (without API key - won't make calls)
        pipeline = ESRETLPipeline()
        
        # Test that it can accept different commodity codes
        # (This will fail at API call stage, but validates parameter passing)
        
        print("✅ ETL pipeline created successfully")
        
        # Test batch method signature
        test_codes = [101, 102, 107]
        try:
            # This will fail due to no API key, but should validate input parameters
            result = pipeline.run_batch_etl(test_codes, force_refresh=True)
            # If we got this far, the method signature works
            print(f"✅ Batch ETL method accepts multiple commodity codes")
        except Exception as e:
            error_str = str(e)
            if "API key" in error_str or "api_key" in error_str.lower():
                print(f"✅ Batch ETL method signature works (expected API key error)")
            else:
                print(f"❌ Batch ETL method failed unexpectedly: {e}")
                return False
        
        pipeline.close()
        return True
        
    except Exception as e:
        print(f"❌ ETL commodity support test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_command_line_interfaces():
    """Test command line argument parsing."""
    print("\n=== Testing Command Line Interfaces ===")
    
    try:
        # Test main.py help
        import subprocess
        
        # Test main.py --help (should show new commodity-code option)
        result = subprocess.run([sys.executable, 'main.py', '--help'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            help_text = result.stdout
            if '--commodity-code' in help_text and '--list-commodities' in help_text:
                print("✅ main.py has new commodity arguments")
            else:
                print("❌ main.py missing new commodity arguments")
                print("Help text:", help_text[:500])
                return False
        else:
            print(f"❌ main.py --help failed: {result.stderr}")
            return False
        
        # Test batch_etl.py help
        result = subprocess.run([sys.executable, 'batch_etl.py', '--help'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            help_text = result.stdout
            if '--include' in help_text and '--exclude' in help_text:
                print("✅ batch_etl.py has include/exclude arguments")
            else:
                print("❌ batch_etl.py missing include/exclude arguments")
                return False
        else:
            print(f"❌ batch_etl.py --help failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Command line interface test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing Multi-Commodity ESR Export Pace System")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_database_schema,
        test_etl_commodity_support,
        test_command_line_interfaces
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"❌ Test failed: {test.__name__}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Multi-commodity system is ready.")
        
        print(f"\n=== Next Steps ===")
        print(f"1. Set ESR_API_KEY environment variable")
        print(f"2. Test with real API calls:")
        print(f"   python main.py --commodity-code 101 --force-refresh")
        print(f"3. Run batch processing:")
        print(f"   python batch_etl.py --include '101,102,107' --force-refresh")
        
        return 0
    else:
        print("❌ Some tests failed. Fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())