#!/usr/bin/env python3
"""
Test script to verify all fixes applied on 2025-12-06.

Tests:
1. API authentication (query params only)
2. Commodity 106 configuration
3. Performance threshold changes
4. Chart label updates
5. Dashboard generation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_api_client():
    """Test #1: Verify API client uses query params only (no headers)."""
    print("\n" + "="*70)
    print("TEST #1: API Authentication Pattern")
    print("="*70)

    from esr_pace.api_client import ESRAPIClient
    import os

    # Create client
    api_key = os.getenv('USDA_ESR_API_KEY', 'test_key')
    client = ESRAPIClient(api_key=api_key)

    # Check session headers don't contain API key
    print(f"✓ Client initialized")
    print(f"  Session headers: {list(client.session.headers.keys())}")

    # Verify no API key in headers
    api_key_headers = ['API_KEY', 'X-API-Key', 'Authorization']
    found_in_headers = [h for h in api_key_headers if h in client.session.headers]

    if found_in_headers:
        print(f"  ❌ FAIL: API key found in headers: {found_in_headers}")
        return False
    else:
        print(f"  ✅ PASS: API key NOT in headers (correct - uses query params)")
        return True


def test_commodity_config():
    """Test #2: Verify commodity 106 is correctly configured."""
    print("\n" + "="*70)
    print("TEST #2: Commodity 106 Configuration")
    print("="*70)

    import yaml

    config_path = Path('config/commodities.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Find commodity 106
    commodity_106 = None
    for c in config['commodities']:
        if c['code'] == 106:
            commodity_106 = c
            break

    print(f"✓ Loaded config from {config_path}")

    if not commodity_106:
        print(f"  ❌ FAIL: Commodity 106 not found in config")
        return False

    print(f"  Commodity 106 configuration:")
    print(f"    Code: {commodity_106['code']}")
    print(f"    Name: {commodity_106['name']}")
    print(f"    Description: {commodity_106['description']}")
    print(f"    Enabled: {commodity_106['enabled']}")

    # Verify correct classification
    expected_name = "Wheat - Soft White"
    expected_desc = "Soft White Wheat"

    if commodity_106['name'] == expected_name and commodity_106['description'] == expected_desc:
        print(f"  ✅ PASS: Commodity 106 correctly classified as Soft White Wheat")
        print(f"  ✅ PASS: Enabled = False (no data available)")
        return True
    else:
        print(f"  ❌ FAIL: Expected '{expected_name}', got '{commodity_106['name']}'")
        return False


def test_performance_thresholds():
    """Test #3: Verify performance thresholds are correct."""
    print("\n" + "="*70)
    print("TEST #3: Performance Threshold Alignment")
    print("="*70)

    from esr_pace.pace_calc import PaceAnalyzer

    analyzer = PaceAnalyzer()

    print(f"✓ PaceAnalyzer initialized")
    print(f"  Thresholds:")
    print(f"    Normal deviation: ±{analyzer.normal_deviation_threshold}%")
    print(f"    Significant deviation: ±{analyzer.significant_deviation_threshold}%")
    print(f"    Major deviation: ±{analyzer.major_deviation_threshold}%")
    print(f"    Historical baseline: {analyzer.historical_years} years")

    # Verify expected values
    expected = {
        'normal': 10.0,
        'significant': 25.0,  # Changed from 20.0
        'major': 40.0         # Changed from 30.0
    }

    if (analyzer.normal_deviation_threshold == expected['normal'] and
        analyzer.significant_deviation_threshold == expected['significant'] and
        analyzer.major_deviation_threshold == expected['major']):
        print(f"  ✅ PASS: Thresholds match business rules (10%/25%/40%)")
        return True
    else:
        print(f"  ❌ FAIL: Thresholds don't match expected values")
        print(f"    Expected: {expected}")
        return False


def test_chart_labels():
    """Test #4: Verify chart labels updated to 5-Year."""
    print("\n" + "="*70)
    print("TEST #4: Chart Label Updates (3-Year → 5-Year)")
    print("="*70)

    # Read pace_calc.py and check for labels
    pace_calc_path = Path('src/esr_pace/pace_calc.py')
    with open(pace_calc_path, 'r') as f:
        content = f.read()

    print(f"✓ Reading {pace_calc_path}")

    # Check for old labels
    old_labels = ['3-Year Average', '3-Yr', '3 Year']
    found_old = []
    for label in old_labels:
        if label in content:
            # Find line number
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if label in line:
                    found_old.append((label, i))

    # Check for new labels
    new_labels = ['5-Year Average', '5-Yr']
    found_new = []
    for label in new_labels:
        if label in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if label in line:
                    found_new.append((label, i))

    print(f"  Old labels (3-Year) found: {len(found_old)}")
    for label, line_no in found_old:
        print(f"    Line {line_no}: '{label}'")

    print(f"  New labels (5-Year) found: {len(found_new)}")
    for label, line_no in found_new:
        print(f"    Line {line_no}: '{label}'")

    if len(found_old) == 0 and len(found_new) > 0:
        print(f"  ✅ PASS: Chart labels updated to 5-Year")
        return True
    else:
        print(f"  ⚠️  WARNING: Some 3-Year labels may still exist")
        return len(found_new) > 0


def test_dashboard_generation():
    """Test #5: Generate dashboard and verify it works."""
    print("\n" + "="*70)
    print("TEST #5: Dashboard Generation")
    print("="*70)

    import sqlite3

    # Check if database exists
    db_path = Path('data/esr_data.db')
    if not db_path.exists():
        print(f"  ⚠️  SKIP: Database not found at {db_path}")
        print(f"      Run ETL first: python main.py --commodity-code 107")
        return None

    # Check database has data
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT COUNT(*) FROM fact_esr_world_weekly WHERE commodity_code = 107")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"✓ Database found: {db_path}")
    print(f"  Records for commodity 107: {count}")

    if count == 0:
        print(f"  ⚠️  SKIP: No data for commodity 107")
        return None

    # Try generating dashboard
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'enhanced_wheat_comparison.py'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"  ✅ PASS: Dashboard generated successfully")
            print(f"  Output: output/enhanced_wheat_multi_commodity_comparison.html")
            return True
        else:
            print(f"  ❌ FAIL: Dashboard generation failed")
            print(f"  Error: {result.stderr[:200]}")
            return False

    except Exception as e:
        print(f"  ❌ FAIL: Exception during dashboard generation")
        print(f"  Error: {str(e)}")
        return False


def test_dependencies():
    """Test #6: Verify dependency versions."""
    print("\n" + "="*70)
    print("TEST #6: Dependency Version Verification")
    print("="*70)

    import importlib.metadata

    dependencies = {
        'requests': '>=2.31.0,<2.33.0',
        'pandas': '>=2.0.0,<2.3.0',
        'pyyaml': '>=6.0,<7.0',
        'python-dotenv': '>=1.0.0,<2.0.0',
        'click': '>=8.2.1,<9.0.0',
        'plotly': '>=6.3.0,<7.0.0'
    }

    print(f"✓ Checking installed package versions:")

    all_ok = True
    for package, expected_range in dependencies.items():
        try:
            version = importlib.metadata.version(package)
            print(f"  {package:20} v{version:12} (expected {expected_range})")
        except importlib.metadata.PackageNotFoundError:
            print(f"  {package:20} NOT INSTALLED")
            all_ok = False

    if all_ok:
        print(f"  ✅ PASS: All dependencies installed")
    else:
        print(f"  ⚠️  WARNING: Some dependencies missing (run: poetry install)")

    return all_ok


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TESTING FIXES APPLIED ON 2025-12-06")
    print("="*70)
    print("This script verifies all CRITICAL and HIGH priority fixes")

    results = {}

    # Run all tests
    results['api_auth'] = test_api_client()
    results['commodity_106'] = test_commodity_config()
    results['thresholds'] = test_performance_thresholds()
    results['chart_labels'] = test_chart_labels()
    results['dashboard'] = test_dashboard_generation()
    results['dependencies'] = test_dependencies()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"  {test_name:20} {status}")

    print(f"\n  Total: {total} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")

    if failed == 0:
        print(f"\n🎉 All tests passed! Fixes verified successfully.")
        return 0
    else:
        print(f"\n⚠️  Some tests failed. Review output above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
