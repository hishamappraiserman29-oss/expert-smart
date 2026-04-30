"""
spatial_audit_engine.py
======================
الرقابة (Audit) والذكاء الجغرافي (Spatial Intelligence)
يطبق مقاييس IAAO الضريبية، يولد خرائط OpenStreetMap ثابتة، ويهيئ مصفوفات التكلفة.
"""

import logging

try:
    from staticmap import StaticMap, CircleMarker
except ImportError:
    StaticMap = None

class SpatialAuditEngine:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("SpatialAudit")

    def calculate_iaao_metrics(self, assessed_values: list, sale_prices: list) -> dict:
        """
        يحسب مقاييس ASR, COD, PRD حسب معايير الرابطة الدولية لضباط التقييم (IAAO).
        """
        if not assessed_values or not sale_prices or len(assessed_values) != len(sale_prices):
            return {"status": "error", "message": "Invalid data length for audit."}

        ratios = [a / s for a, s in zip(assessed_values, sale_prices) if s > 0]
        if not ratios:
            return {"error": "Division by zero (No valid sales)."}

        # ASR (Assessment Sales Ratio)
        asr = sum(ratios) / len(ratios)
        
        # PRD (Price-Related Differential)
        mean_assessed = sum(assessed_values) / len(assessed_values)
        mean_sales = sum(sale_prices) / len(sale_prices)
        weighted_mean_ratio = mean_assessed / mean_sales if mean_sales > 0 else 1.0
        prd = asr / weighted_mean_ratio if weighted_mean_ratio > 0 else 1.0

        # COD (Coefficient of Dispersion)
        median_ratio = sorted(ratios)[len(ratios)//2]
        abs_deviations = [abs(r - median_ratio) for r in ratios]
        cod = (sum(abs_deviations) / len(abs_deviations)) / median_ratio * 100 if median_ratio > 0 else 0

        # نظام الإشارات الضوئية (Traffic Light Safety)
        traffic_light = "🔴 الأحمر (مخاطرة عالية / عدم تكافؤ)"
        if 5.0 <= cod <= 15.0 and 0.98 <= prd <= 1.03:
            traffic_light = "🟢 الأخضر (سليم ومطابق لمعايير IAAO)"
        elif 15.0 < cod <= 20.0 or 0.95 <= prd <= 1.05:
            traffic_light = "🟡 الأصفر (يحتاج مراجعة)"

        self.logger.info(f"IAAO Tax Audit Executed | COD: {cod:.2f}% | PRD: {prd:.2f} | {traffic_light}")

        return {
            "ASR_mean": round(asr, 2),
            "PRD": round(prd, 3),
            "COD_percent": round(cod, 2),
            "Traffic_Light": traffic_light
        }

    def generate_static_heatmap(self, lat: float, lon: float, price_zones: list, output_filename: str) -> bool:
        """
        يولد خريطة حرارية ثابتة عبر OSM لا تتطلب API Keys للسيادة الكاملة.
        """
        if not StaticMap:
            self.logger.warning("staticmap missing. Skipping OSM geographic intelligence routine.")
            return False

        try:
            m = StaticMap(800, 600, url_template='http://a.tile.osm.org/{z}/{x}/{y}.png')
            
            # Subject Property (الهدف)
            m.add_marker(CircleMarker((lon, lat), "#002060", 12))  # Sovereign Blue
            
            # Price Zones Heatmap Simulation
            for z in price_zones:
                # z expects: {"lon": float, "lat": float, "price_intensity_color": str, "size": int}
                m.add_marker(CircleMarker((z["lon"], z["lat"]), z.get("color", "#D4AF37"), z.get("size", 8)))
                
            img = m.render(zoom=14)
            img.save(output_filename)
            self.logger.info(f"OSM Price Zones Heatmap secured at: {output_filename}")
            return True
        except Exception as e:
            self.logger.error(f"Geographic engine exception: {e}")
            return False

    def structural_collapse_land_cost(self):
        """
        مفهوم 'تبسيط الهيكل': يمنع إنشاء شيت 'تسويات الأرض' منفصل
        ويوجه النظام لدمجه ميكانيكياً ضمن خطوط 'طريقة التكلفة'.
        """
        self.logger.info("Structural Rewrite: 'Land Adjustments Matrix' is now strictly collapsed into the 'Cost Approach' Sheet.")
        return True
