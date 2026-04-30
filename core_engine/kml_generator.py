"""
kml_generator.py
================
Generates a Google Earth KML file + standalone HTML price heatmap
from the spatial comparables database used in valuation_logic.py.

Usage:
    from kml_generator import generate_kml, generate_html_map
    kml_path  = generate_kml(subject_coords, comps, output_dir)
    html_path = generate_html_map(subject_coords, comps, output_dir)
"""
from __future__ import annotations
import os
import math
from datetime import datetime
from typing import List, Dict, Tuple

# ─── Color scale helpers ──────────────────────────────────────────────────────

def _price_to_kml_color(ppm: float, min_ppm: float, max_ppm: float) -> str:
    """
    Maps price/m² to a KML ABGR hex color string.
    Low  → Green  (#FF00B050)
    Mid  → Yellow (#FF00D4FF)
    High → Red    (#FF0000FF)
    """
    ratio = (ppm - min_ppm) / max((max_ppm - min_ppm), 1)
    ratio = max(0.0, min(1.0, ratio))
    if ratio < 0.5:
        r = int(255 * ratio * 2)
        g = 200
        b = 50
    else:
        r = 220
        g = int(200 * (1 - (ratio - 0.5) * 2))
        b = 50
    # KML uses AABBGGRR
    return f"FF{b:02X}{g:02X}{r:02X}"


def _price_to_rgb(ppm: float, min_ppm: float, max_ppm: float) -> str:
    """Returns CSS rgb() string for HTML heatmap."""
    ratio = (ppm - min_ppm) / max((max_ppm - min_ppm), 1)
    ratio = max(0.0, min(1.0, ratio))
    if ratio < 0.5:
        r = int(255 * ratio * 2)
        g = 180
        b = 60
    else:
        r = 230
        g = int(180 * (1 - (ratio - 0.5) * 2))
        b = 60
    return f"rgb({r},{g},{b})"


# ─── KML Generator ────────────────────────────────────────────────────────────

def generate_kml(
    subject: Tuple[float, float],      # (lat, lon)
    comps: List[Dict],                  # list of {id, loc, x, y, ppm, area, floor}
    output_dir: str = "",
    report_id: str = "",
    subject_label: str = "العقار موضوع التقييم",
) -> str:
    """
    Generates a .kml file viewable in Google Earth.
    Returns the absolute path to the generated file.
    """
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "outputs", "reports")
    os.makedirs(output_dir, exist_ok=True)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    rid = report_id or f"VAL-{ts}"
    out = os.path.join(output_dir, f"price_map_{ts}.kml")

    prices = [c.get("ppm", 0) for c in comps if c.get("ppm", 0) > 0]
    min_p  = min(prices) if prices else 10000
    max_p  = max(prices) if prices else 30000

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'  <name>خريطة أسعار العقارات — {rid}</name>',
        f'  <description>تقرير تقييم عقاري — {datetime.now().strftime("%Y/%m/%d")}</description>',
        # Subject property style
        '  <Style id="subject">',
        '    <IconStyle><color>FF0000FF</color><scale>1.6</scale>',
        '      <Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-stars.png</href></Icon>',
        '    </IconStyle>',
        '    <LabelStyle><color>FF0000FF</color><scale>1.2</scale></LabelStyle>',
        '  </Style>',
    ]

    # Comparable styles (one per unique color bucket)
    for i, c in enumerate(comps):
        ppm   = c.get("ppm", min_p)
        color = _price_to_kml_color(ppm, min_p, max_p)
        lines += [
            f'  <Style id="comp{i}">',
            f'    <IconStyle><color>{color}</color><scale>1.2</scale>',
            '      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/homegardenbusiness.png</href></Icon>',
            '    </IconStyle>',
            f'    <LabelStyle><scale>0.8</scale></LabelStyle>',
            '  </Style>',
        ]

    # Subject placemark
    s_lat, s_lon = subject
    lines += [
        '  <Placemark>',
        f'    <name>{subject_label}</name>',
        f'    <description><![CDATA[<b>العقار موضوع التقييم</b><br/>الموقع: {subject_label}]]></description>',
        '    <styleUrl>#subject</styleUrl>',
        '    <Point>',
        f'      <coordinates>{s_lon},{s_lat},0</coordinates>',
        '    </Point>',
        '  </Placemark>',
    ]

    # Comparable placemarks
    for i, c in enumerate(comps):
        lat = c.get("x", s_lat + 0.001 * i)
        lon = c.get("y", s_lon + 0.001 * i)
        ppm = c.get("ppm", 0)
        loc = c.get("loc", c.get("id", f"مقارنة {i+1}"))
        area_c = c.get("area", c.get("ar", 0))
        floor  = c.get("floor", 1)
        lines += [
            '  <Placemark>',
            f'    <name>{ppm:,.0f} EGP/م²</name>',
            f'    <description><![CDATA[',
            f'<b>{loc}</b><br/>',
            f'السعر/م²: <b>{ppm:,.0f} EGP</b><br/>',
            f'المساحة: {area_c} م² | الدور: {floor}',
            '    ]]></description>',
            f'    <styleUrl>#comp{i}</styleUrl>',
            '    <Point>',
            f'      <coordinates>{lon},{lat},0</coordinates>',
            '    </Point>',
            '  </Placemark>',
        ]

    lines += ['</Document>', '</kml>']

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return out


# ─── HTML Price Heatmap ────────────────────────────────────────────────────────

def generate_html_map(
    subject: Tuple[float, float],
    comps: List[Dict],
    output_dir: str = "",
    report_id: str = "",
    subject_label: str = "العقار موضوع التقييم",
) -> str:
    """
    Generates a self-contained HTML file using Leaflet.js
    with color-coded price markers and a legend.
    Returns the absolute path to the generated file.
    """
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "outputs", "reports")
    os.makedirs(output_dir, exist_ok=True)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    rid = report_id or f"VAL-{ts}"
    out = os.path.join(output_dir, f"price_map_{ts}.html")

    prices = [c.get("ppm", 0) for c in comps if c.get("ppm", 0) > 0]
    min_p  = min(prices) if prices else 10000
    max_p  = max(prices) if prices else 30000
    s_lat, s_lon = subject

    # Build JS markers
    markers_js = []
    for c in comps:
        lat   = c.get("x", s_lat)
        lon   = c.get("y", s_lon)
        ppm   = c.get("ppm", 0)
        loc   = c.get("loc", c.get("id", "مقارنة"))
        area_c = c.get("area", c.get("ar", 0))
        color = _price_to_rgb(ppm, min_p, max_p)
        popup = (f"<b>{loc}</b><br/>"
                 f"السعر/م²: <b>{ppm:,.0f} EGP</b><br/>"
                 f"المساحة: {area_c} م²")
        markers_js.append(
            f'L.circleMarker([{lat}, {lon}], '
            f'{{radius: 10, fillColor: "{color}", color: "#333", weight:1, fillOpacity:0.85}})'
            f'.bindPopup(`{popup}`).addTo(map);'
        )

    markers_str = "\n    ".join(markers_js)

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>خريطة أسعار العقارات — {rid}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; font-family: 'Simplified Arabic', Arial, sans-serif; background:#0d1117; color:#e6edf3; }}
  #map  {{ height: 70vh; width: 100%; border-radius: 10px; }}
  .header {{ padding: 18px 24px; background: linear-gradient(135deg,#1F4E78,#2E74B5);
             text-align:center; }}
  .header h2 {{ margin:0; font-size:1.4rem; color:#FFD700; }}
  .header p  {{ margin:4px 0 0; font-size:.9rem; color:#BDD7EE; }}
  .legend {{ background:#161b22; border:1px solid #30363d; border-radius:8px;
             padding:12px 18px; position:absolute; bottom:40px; left:20px;
             z-index:1000; font-size:.85rem; }}
  .legend-bar {{ height:14px; width:160px; border-radius:4px;
                 background: linear-gradient(to right, rgb(60,180,60), rgb(255,200,0), rgb(230,50,50));
                 margin:6px 0; }}
  .legend-labels {{ display:flex; justify-content:space-between; font-size:.75rem; color:#8b949e; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; padding:14px 24px;
            background:#161b22; }}
  .stat  {{ background:#0d1117; border:1px solid #30363d; border-radius:8px;
            padding:10px; text-align:center; }}
  .stat .val {{ font-size:1.3rem; font-weight:700; color:#FFD700; }}
  .stat .lbl {{ font-size:.75rem; color:#8b949e; margin-top:4px; }}
</style>
</head>
<body>
<div class="header">
  <h2>خريطة تحليل أسعار السوق العقاري</h2>
  <p>رقم التقرير: {rid} | تاريخ: {datetime.now().strftime("%Y/%m/%d")}</p>
</div>

<div class="stats">
  <div class="stat"><div class="val">{len(comps)}</div><div class="lbl">عدد المقارنات</div></div>
  <div class="stat"><div class="val">{min_p:,.0f}</div><div class="lbl">أدنى سعر/م²</div></div>
  <div class="stat"><div class="val">{max_p:,.0f}</div><div class="lbl">أعلى سعر/م²</div></div>
  <div class="stat"><div class="val">{(sum(prices) // max(len(prices), 1)):,.0f}</div><div class="lbl">متوسط السعر/م²</div></div>
</div>

<div style="position:relative">
  <div id="map"></div>
  <div class="legend">
    <b>مقياس السعر (EGP/م²)</b>
    <div class="legend-bar"></div>
    <div class="legend-labels">
      <span>{min_p:,.0f}</span>
      <span>{(min_p+max_p)//2:,.0f}</span>
      <span>{max_p:,.0f}</span>
    </div>
    <div style="margin-top:8px;color:#8b949e;font-size:.75rem;">
      ★ = العقار موضوع التقييم
    </div>
  </div>
</div>

<script>
  var map = L.map('map').setView([{s_lat}, {s_lon}], 14);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap',
    maxZoom: 19
  }}).addTo(map);

  // Subject property marker
  var starIcon = L.divIcon({{
    html: '<div style="font-size:28px;line-height:1">★</div>',
    className:'', iconAnchor:[14,14]
  }});
  L.marker([{s_lat}, {s_lon}], {{icon: starIcon}})
    .bindPopup('<b>{subject_label}</b><br/>العقار موضوع التقييم')
    .addTo(map);

  // Comparable markers
  {markers_str}
</script>
</body>
</html>
"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    return out


# ─── Convenience: generate both from valuation result ─────────────────────────

def generate_maps_from_result(
    ivs_result: dict,
    output_dir: str = "",
    report_id: str = "",
) -> dict:
    """
    Accepts the dict from advanced_valuation() and generates both KML + HTML maps.
    Returns {"kml": path, "html": path}
    """
    from valuation_logic import _get_target_coords, _SPATIAL_COMPS

    location  = ivs_result.get("location", "القاهرة")
    subject   = _get_target_coords(location)

    # Merge RAG comparables (with real coords from _SPATIAL_COMPS as fallback)
    rag_comps = ivs_result.get("market", {}).get("comparables", [])
    spatial_c = [
        {
            "id":    c["id"] if "id" in c else f"comp{i}",
            "loc":   c.get("name", c.get("location", f"مقارنة {i+1}")),
            "x":     c.get("x",    subject[0] + 0.001 * (i - len(_SPATIAL_COMPS)//2)),
            "y":     c.get("y",    subject[1] + 0.001 * (i - len(_SPATIAL_COMPS)//2)),
            "ppm":   c.get("adj_price", c.get("base_price", 0)),
            "area":  c.get("area", 100),
            "floor": c.get("floor", 1),
        }
        for i, c in enumerate(_SPATIAL_COMPS[:10])
    ]

    rid = report_id or ivs_result.get("report_id", "")

    kml_path  = generate_kml(subject,  spatial_c, output_dir, rid, location)
    html_path = generate_html_map(subject, spatial_c, output_dir, rid, location)

    return {"kml": kml_path, "html": html_path}


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    from valuation_logic import _SPATIAL_COMPS
    subject = (29.978, 31.049)   # دريم لاند
    comps   = [
        {"id": c["id"], "loc": "دريم لاند", "x": c["x"], "y": c["y"],
         "ppm": c["ppm"], "area": c["area"], "floor": c["floor"]}
        for c in _SPATIAL_COMPS[:10]
    ]
    kml  = generate_kml(subject, comps)
    html = generate_html_map(subject, comps)
    print(f"KML  : {kml}")
    print(f"HTML : {html}")
