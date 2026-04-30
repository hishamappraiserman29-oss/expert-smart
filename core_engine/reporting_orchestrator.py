import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from report_generator import generate_professional_report
from master_report_generator import generate_report as generate_excel_report
from integration.google_drive import build_drive_service, upload_to_drive

def execute_full_report_package(valuation_data: dict, enable_drive_sync: bool = False):
    """
    Agentic Orchestrator for Full Valuation Reporting.
    1. Reads parsed JSON data.
    2. Calls Word Generation.
    3. Calls Excel Generation.
    4. Syncs to Google Drive if authorized.
    5. Returns dict of deterministic paths and URLs.
    """
    print(f"\n[Agent] Creating reporting package for {valuation_data.get('location', 'Unknown')}...")

    # 1. Generate Word Report
    print(f"[Agent] Generating narrative Word report (.docx)...")
    try:
        word_path = generate_professional_report(valuation_data)
        print(f"[Agent] -> Word report saved to: {word_path}")
    except Exception as e:
        print(f"[Agent] -> Error generating Word report: {str(e)}")
        word_path = None

    # 2. Generate Excel Report
    print(f"[Agent] Generating executive Excel report (.xlsx)...")
    try:
        excel_path = generate_excel_report(
            client_name=valuation_data.get("client_name", "عميل افتراضي"),
            property_type=valuation_data.get("property_type", "عقار"),
            location=valuation_data.get("location", "موقع"),
            area=valuation_data.get("area", 150),
            floor=valuation_data.get("floor", 1),
            rooms=valuation_data.get("rooms", 3),
            year_built=valuation_data.get("year_built", 2010),
            price_per_m2=valuation_data.get("market", {}).get("value", 18000) / valuation_data.get("area", 150) if valuation_data.get("market", {}).get("value") else 18000,
            rent_per_sqm=valuation_data.get("income", {}).get("rent_per_sqm", 350),
            cap_rate=valuation_data.get("income", {}).get("cap_rate", 0.08),
        )
        print(f"[Agent] -> Excel report saved to: {excel_path}")
    except Exception as e:
        print(f"[Agent] -> Error generating Excel report: {str(e)}")
        excel_path = None

    drive_links = {"word": None, "excel": None}

    # 3. Google Drive Sync
    if enable_drive_sync:
        print("\n[Agent] Uploading reports to Google Drive...")
        try:
            drive_service = build_drive_service(
                credentials_file=os.path.join(os.path.dirname(__file__), "credentials.json"),
                token_file=os.path.join(os.path.dirname(__file__), "token.json")
            )
            
            if word_path and os.path.exists(word_path):
                file_id, web_link = upload_to_drive(drive_service, word_path)
                drive_links["word"] = web_link
                print(f"[Agent] -> Word report uploaded to: {web_link}")
                
            if excel_path and os.path.exists(excel_path):
                file_id, web_link = upload_to_drive(drive_service, excel_path)
                drive_links["excel"] = web_link
                print(f"[Agent] -> Excel report uploaded to: {web_link}")
                
        except Exception as e:
            print(f"[Agent] -> Google Drive upload skipped or failed: {str(e)}")
            
    print("\n[Agent] Reporting workflow fully completed!")
    
    return {
        "word_local": word_path,
        "excel_local": excel_path,
        "word_drive": drive_links["word"],
        "excel_drive": drive_links["excel"]
    }

if __name__ == "__main__":
    # Test Agent Mock Data
    mock_data = {
        "client_name": "السيد / أحمد محمود",
        "property_type": "فيلا دريم لاند",
        "location": "دريم لاند، 6 أكتوبر",
        "area": 430,
        "floor": 0,
        "rooms": 6,
        "year_built": 2016,
        "market": {"value": 8500000},
        "income": {"rent_per_sqm": 450, "cap_rate": 0.08},
        "cost": {"value": 8200000},
        "reconciled_value": 8400000
    }
    
    execute_full_report_package(mock_data, enable_drive_sync=False)
