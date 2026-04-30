import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI
from valuation_logic import calculate_property_valuation, get_estimated_price, advanced_valuation

_openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class RealEstateRAGWorkflow:
    def __init__(self):
        print("Initializing Real Estate RAG Workflow...")
        # Mock database connection
        self.db = []
        self.vector_store = []
        
    def run_daily_pipeline(self):
        print(f"\n--- Starting Daily Run: {datetime.now().isoformat()} ---")
        
        # Step 1: HTTP Request Node
        raw_data = self.step_1_http_request()
        
        # Step 2: Data Cleaning Node
        cleaned_data = self.step_2_data_cleaning(raw_data)
        
        # Step 3: Data Processing Node
        processed_data = self.step_3_data_processing(cleaned_data)
        
        # Step 4: Duplicate Detection Node
        unique_data = self.step_4_duplicate_detection(processed_data)
        
        # Step 5: Storage Node
        self.step_5_storage(unique_data)
        
        # Step 6: Embedding Node
        embedded_data = self.step_6_embedding(unique_data)
        
        # Step 7: Vector Database Node
        self.step_7_vector_database(embedded_data)
        
        print("--- Daily Pipeline Completed Successfully ---\n")
        
    def handle_user_query(self, user_input: str, target_location: str) -> str:
        print(f"\n--- Processing User Query: '{user_input}' ---")
        
        # Step 8: Retrieval Node
        retrieved_records = self.step_8_retrieval(user_input, top_k=20)
        
        # Step 9: Context Builder Node
        context = self.step_9_context_builder(retrieved_records, target_location)
        
        # Step 10: AI Model Node
        report = self.step_10_ai_model(user_input, context)
        
        return report

    # --- NODE IMPLEMENTATIONS ---

    def step_1_http_request(self) -> List[Any]:
        """Step 1: HTTP Request Node
        Fetch property listings (JSON or HTML). Run daily.
        """
        print("[Node 1] Fetching property listings via HTTP Request...")
        # Mocking incoming raw data (could be messy)
        return [
            {"loc": "Cairo", "prc": "2,000,000", "size": 100, "status": "New", "listed_date": "2026-03-01"},
            {"loc": "Giza", "prc": "1500000", "size": 80, "status": "Good", "listed_date": "2026-03-02"},
            {"loc": "حي النرجس بالرياض", "prc": "4,500,000", "size": 300, "status": "New", "listed_date": "2026-04-01"},
            {"loc": "حي النرجس بالرياض", "prc": "6,000,000", "size": 400, "status": "Excellent", "listed_date": "2026-04-05"},
            {"loc": "حي النرجس بالرياض", "prc": "7,500,000", "size": 500, "status": "New", "listed_date": "2026-04-08"},
        ]

    def step_2_data_cleaning(self, raw_data: List[Any]) -> List[Dict[str, Any]]:
        """Step 2: Data Cleaning Node
        Extract: location, price, area, condition, date. Output structured JSON.
        """
        print(f"[Node 2] Cleaning {len(raw_data)} records...")
        cleaned = []
        for item in raw_data:
            price = str(item.get("prc", "0")).replace(",", "").strip()
            cleaned.append({
                "location": item.get("loc"),
                "price": float(price) if price.isdigit() else 0.0,
                "area": float(item.get("size", 0)),
                "condition": item.get("status"),
                "date": item.get("listed_date")
            })
        return cleaned

    def step_3_data_processing(self, cleaned_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 3: Data Processing Node
        Calculate: price_per_m2 = price / area
        """
        print(f"[Node 3] Processing data (calculating price_per_m2)...")
        for item in cleaned_data:
            if item["area"] > 0:
                item["price_per_m2"] = item["price"] / item["area"]
            else:
                item["price_per_m2"] = 0.0
        return cleaned_data

    def step_4_duplicate_detection(self, processed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 4: Duplicate Detection Node
        Check duplicates using: location + price + area
        """
        print(f"[Node 4] Detecting and removing duplicates...")
        seen = set()
        unique_data = []
        for item in processed_data:
            # Create a unique fingerprint
            fingerprint = f"{item['location']}_{item['price']}_{item['area']}"
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique_data.append(item)
        print(f"         Removed {len(processed_data) - len(unique_data)} duplicates.")
        return unique_data

    def step_5_storage(self, unique_data: List[Dict[str, Any]]):
        """Step 5: Storage Node
        Save cleaned data to a shared folder or database
        """
        print(f"[Node 5] Saving {len(unique_data)} records to main database...")
        for item in unique_data:
            record = item.copy()
            record["id"] = str(uuid.uuid4())
            self.db.append(record)

    def step_6_embedding(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 6: Embedding Node
        Generate real embeddings using OpenAI text-embedding-3-small
        """
        print(f"[Node 6] Generating vector embeddings for {len(records)} records...")
        texts = []
        for item in records:
            text_repr = f"{item['condition']} property in {item['location']}, {item['area']} sq m, price: {item['price']}."
            item["text_repr"] = text_repr
            texts.append(text_repr)

        try:
            response = _openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            for i, item in enumerate(records):
                item["embedding"] = response.data[i].embedding
        except Exception as e:
            print(f"⚠️ Embedding API failed ({e}). Falling back to zero vectors.")
            for item in records:
                item["embedding"] = [0.0] * 1536

        return records

    def step_7_vector_database(self, embedded_data: List[Dict[str, Any]]):
        """Step 7: Vector Database Node
        Store embeddings in Qdrant
        """
        print(f"[Node 7] Upserting records into Qdrant Vector Database...")
        for item in embedded_data:
            self.vector_store.append({
                "id": str(uuid.uuid4()),
                "embedding": item["embedding"],
                "metadata": item
            })

    def step_8_retrieval(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Step 8: Retrieval Node
        Encode the query and return top_k records ranked by cosine similarity.
        """
        print(f"[Node 8] Retrieving top {top_k} similar properties for query...")

        if not self.vector_store:
            return []

        # Embed the query
        try:
            resp = _openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=[query]
            )
            query_vec = resp.data[0].embedding
        except Exception as e:
            print(f"⚠️ Query embedding failed ({e}). Returning all records unranked.")
            return [r["metadata"] for r in self.vector_store][:top_k]

        # Cosine similarity
        def cosine_sim(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x ** 2 for x in a) ** 0.5
            norm_b = sum(x ** 2 for x in b) ** 0.5
            return dot / (norm_a * norm_b + 1e-9)

        ranked = sorted(
            self.vector_store,
            key=lambda r: cosine_sim(query_vec, r["embedding"]),
            reverse=True
        )
        return [r["metadata"] for r in ranked[:top_k]]

    def step_9_context_builder(self, retrieved_records: List[Dict[str, Any]], target_location: str) -> Dict[str, Any]:
        """Step 9: Context Builder Node
        Calculate: average price, median, trend
        """
        print(f"[Node 9] Building context metadata from retrieved records...")
        prices = [r["price"] for r in retrieved_records if r["location"] == target_location]
        
        if not prices:
            return {"average_price": 0, "median_price": 0, "trend": "Unknown", "count": 0}
            
        prices.sort()
        avg_price = sum(prices) / len(prices)
        median_price = prices[len(prices)//2]
        
        context = {
            "average_price": round(avg_price, 2),
            "median_price": round(median_price, 2),
            "trend": "Stable (Mock Trend)",
            "count": len(prices),
            "comparables": retrieved_records
        }
        return context

    def step_10_ai_model(self, user_input: str, context: Dict[str, Any]) -> str:
        """Step 10: AI Model Node
        Send: user input + context. Generate valuation report.
        """
        print(f"[Node 10] Generating AI Valuation Report...")
        
        # استخراج المساحة من الإدخال للحساب التلقائي (محاكاة)
        import re
        area_sqm = 0
        match = re.search(r'(\d+)\s*(m|sqm|متر|m2)', user_input.lower())
        if match:
            area_sqm = float(match.group(1))
            
        # استخراج الحي وجلب السعر من القاموس
        match_loc = re.search(r'(الملقا|النرجس|الياسمين)', user_input)
        extracted_neighborhood = match_loc.group(1) if match_loc else "غير محدد"
        
        if extracted_neighborhood != "غير محدد":
            price_per_meter = get_estimated_price(extracted_neighborhood)
        else:
            price_per_meter = context.get('median_price', 0)
            
        if area_sqm > 0 and price_per_meter > 0:
            # محاكاة سحب البيانات من Train Data
            # حيث تتوفر بيانات الإيجارات والتكلفة كمعطيات مساعدة
            simulated_rent = 400 if extracted_neighborhood == 'الملقا' else 350
            simulated_build_cost = 2500
            
            valuation_data = {
                "area": area_sqm,
                "price_per_meter": price_per_meter,
                "location": extracted_neighborhood if extracted_neighborhood != "غير محدد" else "منطقة مسح السوق",
                "building_area": area_sqm * 0.6,
                "building_cost_sqm": simulated_build_cost,
                "building_age": 5,
                "rent_per_sqm": simulated_rent,
                "cap_rate": 0.08,
                "comparables": [
                    {'location': extracted_neighborhood, 'price_per_meter': price_per_meter + 200},
                    {'location': extracted_neighborhood, 'price_per_meter': price_per_meter - 100},
                    {'location': extracted_neighborhood, 'price_per_meter': price_per_meter}
                ]
            }
            
            ivs_result = advanced_valuation(valuation_data)
            
            # 💡 الاعتماد على المُولد الأساسي لتقارير الـ Word المتوافقة مع IVS
            word_path = ""
            try:
                import sys
                # Ensure core_engine directory is in path
                _core_dir = os.path.dirname(os.path.abspath(__file__))
                if _core_dir not in sys.path:
                    sys.path.insert(0, _core_dir)

                from report_generator import generate_professional_report
                word_path = generate_professional_report(ivs_result)
            except Exception as e:
                import traceback
                word_path = f"(خطأ في توليد الإخراج: {e}\n{traceback.format_exc()})"
            
            report = f"""
        ==================================================
                 AI REAL ESTATE VALUATION REPORT (IVS)
        ==================================================
        Query: {user_input}
        
        تم إتمام التقييم بنجاح بالاعتماد على معايير IVS.
        القيمة المرجحة النهائية المستنتجة: {ivs_result['reconciled_value']:,.2f} ريال سعودي
        
        ✅ تم إنشاء تقرير Word شامل لكافة الفصول والأساليب بشكل آلي.
        📥 مسار الملف:
        {word_path}
        ==================================================
        """
        else:
            # القالب الافتراضي إذا لم يتم العثور على مساحة أو أسعار
            report = f"""
        ==================================================
                 AI REAL ESTATE VALUATION REPORT
        ==================================================
        Query: {user_input}
        
        Based on our RAG database analysis of {context['count']} comparable 
        properties in the requested area:
        
        - Market Average Price: {context['average_price']:,.2f}
        - Market Median Price:  {context['median_price']:,.2f}
        - Market Trend:         {context['trend']}
        
        Estimated Valuation Summary:
        Considering the current market dynamics alongside your input, 
        we predict an optimal valuation aligning with the market median 
        of {context.get('median_price', 0):,.2f}, pending physical condition checks.
        ==================================================
        """
        return report

if __name__ == "__main__":
    workflow = RealEstateRAGWorkflow()
    # 1. Simulate the automated daily data ingestion pipeline
    workflow.run_daily_pipeline()
    
    # 2. Simulate a User Request triggering the retrieval side
    final_report = workflow.handle_user_query(
        user_input="قيم لي الآن فيلا مساحتها 600 متر في حي النرجس بالرياض، وطلع لي ملف الـ Word النهائي.", 
        target_location="حي النرجس بالرياض"
    )
    print(final_report)
