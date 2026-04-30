import json
import os
import datetime
from typing import Any, Dict, Optional


def read_json_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_case_complete(data: Dict[str, Any]) -> bool:
    """
    Check if the case has minimal required financial data to proceed
    without manual input.
    """
    val_data = data.get("valuation_data", {})
    if not val_data:
        return False

    # Check DCF essentials
    dcf = val_data.get("income_dcf_data", {})
    # List of keys that must NOT be None
    required_dcf = [
        "noi_annual", 
        "cap_rate_percent", 
        "discount_rate_percent", 
        "growth_rate_percent", 
        "exit_yield_percent",
        "projection_years"
    ]
    for key in required_dcf:
        if dcf.get(key) is None:
            return False

    # Check Residual essentials
    res = val_data.get("residual_data", {})
    required_res = ["gdv", "dev_cost", "dev_profit_percent"]
    for key in required_res:
        if res.get(key) is None:
            return False
            
    return True


def ensure_timestamp(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data.get("timestamp"):
        data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data
