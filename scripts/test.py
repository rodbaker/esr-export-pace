#!/usr/bin/env python3
"""Test that everything is working"""

print("🌾 Testing ESR project setup...")

try:
    import requests
    import pandas as pd
    import yaml
    print("✅ All packages imported successfully!")
    print("🎯 Ready to start building the ESR tracker")
except ImportError as e:
    print(f"❌ Missing package: {e}")
