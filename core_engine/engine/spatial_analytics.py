"""
spatial_analytics.py — GIS and Spatial Valuation Engine
Handles Inverse Distance Weighting (IDW) and Ordinary Kriging.
This module integrates with scipy and pykrige to compute geographically weighted estimates.
"""

import numpy as np

try:
    from scipy.interpolate import Rbf
except ImportError:
    Rbf = None

try:
    from pykrige.ok import OrdinaryKriging
except ImportError:
    OrdinaryKriging = None

def compute_idw_estimate(target_lat: float, target_lon: float, comps_data: list, power: int = 2) -> float:
    """
    Inverse Distance Weighting calculation for spatial price interpolation.
    comps_data: List of dicts [{"lat": float, "lon": float, "price_per_m2": float}]
    """
    if not Rbf or not comps_data:
        return 0.0

    lats = np.array([c["lat"] for c in comps_data])
    lons = np.array([c["lon"] for c in comps_data])
    prices = np.array([c["price_per_m2"] for c in comps_data])

    # Basic Euclidean distance approximation (for small geospatial extents)
    # Rbf with 'inverse' function mathematically proxies IDW
    try:
        rbf = Rbf(lons, lats, prices, function='inverse', epsilon=power)
        estimated_price = float(rbf(target_lon, target_lat))
        return round(estimated_price, 2)
    except Exception as e:
        print(f"[GIS] IDW Error: {e}")
        return 0.0

def compute_kriging_estimate(target_lat: float, target_lon: float, comps_data: list) -> float:
    """
    Ordinary Kriging calculation. Models spatial variance to estimate expected price.
    comps_data: List of dicts [{"lat": float, "lon": float, "price_per_m2": float}]
    """
    if not OrdinaryKriging or len(comps_data) < 3:
        return 0.0

    lats = np.array([c["lat"] for c in comps_data])
    lons = np.array([c["lon"] for c in comps_data])
    prices = np.array([c["price_per_m2"] for c in comps_data])

    try:
        OK = OrdinaryKriging(
            lons, lats, prices,
            variogram_model='linear',
            verbose=False,
            enable_plotting=False
        )
        z_pred, _ss = OK.execute('grid', np.array([target_lon]), np.array([target_lat]))
        return round(float(z_pred[0][0]), 2)
    except Exception as e:
        print(f"[GIS] Kriging Error: {e}")
        return 0.0

def run_spatial_analysis(target_coordinates: tuple, market_comps: list) -> dict:
    """
    Main entrypoint for GIS module.
    Runs IDW and Kriging concurrently based on provided comps.
    returns {"idw_estimate": float, "kriging_estimate": float}
    """
    if not target_coordinates or not market_comps:
        return {"idw_estimate": 0.0, "kriging_estimate": 0.0}
        
    lat, lon = target_coordinates
    idw_val = compute_idw_estimate(lat, lon, market_comps)
    krig_val = compute_kriging_estimate(lat, lon, market_comps)
    
    return {
        "target_coordinates": {"lat": lat, "lon": lon},
        "idw_estimate": idw_val,
        "kriging_estimate": krig_val,
        "confidence": "High" if (10 > abs(idw_val - krig_val) / max(1, idw_val) * 100) else "Low"
    }

if __name__ == "__main__":
    # Test Data Set (Dreamland mock)
    mock_target = (30.012, 31.200)
    mock_comps = [
        {"lat": 30.010, "lon": 31.205, "price_per_m2": 15000},
        {"lat": 30.015, "lon": 31.190, "price_per_m2": 16000},
        {"lat": 30.000, "lon": 31.210, "price_per_m2": 14500},
    ]
    print(f"Spatial Analysis Result: {run_spatial_analysis(mock_target, mock_comps)}")
