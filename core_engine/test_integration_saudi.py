import json
import os
import sys

# Add the current directory to sys.path so we can import from main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import _build_meta_from_env

def run_saudi_integration_test():
    print("\n" + "="*60)
    print("🚀 Running Integration Test: Saudi Arabia Setup")
    print("="*60)
    
    # 1. Verify Platform (Usually hardcoded or in config)
    # Based on session_config.json created by the user
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared_data', 'session_config.json')
    
    if not os.path.exists(config_path):
        print(f"❌ Error: session_config.json not found at {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    platform_name = config_data.get("system_info", {}).get("platform_name", "Expert_Smart")
    
    # 2. Get Metadata via the bridge logic in main.py
    # This calls the actual logic that the core engine uses
    meta = _build_meta_from_env()
    
    currency = meta.get("currency")
    standard = meta.get("valuation_standard")
    region = meta.get("location_zone")
    
    # 3. Print the Mock Valuation Report as requested
    print(f"\n[MOCK VALUATION REPORT]")
    print(f"------------------------------------------------------------")
    print(f"Platform Name: {platform_name}")
    print(f"Currency:      {currency}")
    print(f"Standard:      {standard}")
    print(f"Region:        {region}")
    print(f"Status:        ✅ Verified for {region}")
    print(f"------------------------------------------------------------")
    
    # Final Validation Check
    if currency == "SAR" and standard == "TAQEEM":
        print("\n✅ SUCCESS: Python Engine is correctly utilizing Saudi standards.")
    else:
        print(f"\n❌ FAILURE: Expected SAR/TAQEEM but got {currency}/{standard}")

if __name__ == "__main__":
    run_saudi_integration_test()
