#!/usr/bin/env python3
"""Quick test of ESR API connectivity."""

import os
import sys

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

from src.esr_pace.api_client import ESRAPIClient, ESRAPIError

def test_api():
    # Get API key from environment variable or command line
    api_key = os.getenv('ESR_API_KEY')
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
        
    if not api_key:
        print("❌ API key required. Set ESR_API_KEY environment variable or pass as argument")
        return False
        
    print(f"Using API key: {api_key[:8]}{'*' * (len(api_key) - 8)}")
    client = ESRAPIClient(api_key=api_key)
    
    try:
        print("Testing ESR API connectivity...")
        
        # Test basic connectivity with commodities endpoint
        commodities = client.get_commodities()
        print(f"✅ Commodities endpoint: {len(commodities)} commodities found")
        
        # Find All Wheat
        all_wheat = None
        for commodity in commodities:
            if commodity.get('commodityCode') == 107:
                all_wheat = commodity
                break
                
        if all_wheat:
            print(f"✅ Found All Wheat: {all_wheat}")
        else:
            print("❌ All Wheat (107) not found")
            
        # Test data release dates
        releases = client.get_data_release_dates()
        print(f"✅ Data release dates: {len(releases)} commodities with release info")
        
        # Find release info for All Wheat
        wheat_release = client.get_release_info_for_commodity(107)
        if wheat_release:
            print(f"✅ All Wheat release info: {wheat_release}")
        else:
            print("❌ No release info for All Wheat")
            
        print("API test completed successfully!")
        return True
        
    except ESRAPIError as e:
        print(f"❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = test_api()
    exit(0 if success else 1)