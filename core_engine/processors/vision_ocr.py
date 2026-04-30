import os
import base64
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI


class VisionProcessor:
    """
    Level-3 extractor:
    - Extracts ONLY what is evidenced in the document/image.
    - Uses null for missing financial fields.
    - Adds evidence + confidence + warnings.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Strict schema keys we want
        self.system_prompt = """
ROLE:
You are an expert real-estate document analyst for Arabic (Egypt/Saudi) documents.

GOAL:
Extract verifiable facts from the image/document ONLY. Do NOT invent numbers.
If a value is missing, output null and add it to missing_fields.
For each extracted key field, provide:
- confidence: 0..1
- evidence: short quote/description of where it appears in the image.

LANGUAGE:
- Keep Arabic in: location_zone, ai_notes, evidence.quote (if the quote is Arabic).
- Keys are English.

OUTPUT:
Return STRICT JSON only.

JSON SHAPE:
{
  "timestamp": "DD/MM/YYYY|null",
  "source_client": "string|null",
  "property_type": "string|null",
  "location_zone": "string|null",
  "area_sqm": number|null,

  "inspection": {
    "inspection_date": "DD/MM/YYYY|null",
    "finish_state": "string|null",
    "vacant": true|false|null
  },

  "document_entities": {
    "project_name": "string|null",
    "unit_id": "string|null",
    "land_plot": "string|null",
    "city": "string|null",
    "developer": "string|null"
  },

  "valuation_data": {
    "market_approach_value": number|null,
    "cost_approach_value": number|null,

    "income_dcf_data": {
      "noi_annual": number|null,
      "cap_rate_percent": number|null,
      "discount_rate_percent": number|null,
      "growth_rate_percent": number|null,
      "exit_yield_percent": number|null,
      "projection_years": number|null
    },

    "residual_data": {
      "gdv": number|null,
      "dev_cost": number|null,
      "dev_profit_percent": number|null
    }
  },

  "extraction_meta": {
    "doc_type": "contract|license|letter|photo|unknown",
    "confidence_overall": number,
    "missing_fields": [ "string", ... ],
    "warnings": [ "string", ... ]
  },

  "evidence": {
    "fields": [
      {
        "path": "dot.notation.path",
        "confidence": number,
        "quote": "string",
        "note": "string|null"
      }
    ]
  },

  "ai_notes": "string|null"
}
"""

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def process_image(self, image_path: str) -> Dict[str, Any]:
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}

        base64_image = self._encode_image(image_path)

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Extract verifiable information from this document/photo. "
                                    "Do not invent values. Use null + missing_fields when unknown. "
                                    "Add evidence for each field."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    },
                ],
                temperature=0.0,
            )
            content = resp.choices[0].message.content
            data = json.loads(content)

            # Basic sanity normalization
            if "extraction_meta" not in data:
                data["extraction_meta"] = {
                    "doc_type": "unknown",
                    "confidence_overall": 0.5,
                    "missing_fields": [],
                    "warnings": ["Extractor returned without extraction_meta; pipeline should validate."],
                }

            return data

        except Exception as e:
            return {"error": f"Vision processing failed: {str(e)}"}