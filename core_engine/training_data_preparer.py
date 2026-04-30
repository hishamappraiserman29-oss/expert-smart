import os
import json
import PyPDF2
import docx2txt

class TrainingDataPreparer:
    """
    Scans raw documents (PDF/DOCX) in language-specific folders 
    and converts them into an Alpaca-formatted training dataset.
    """
    def __init__(self, raw_docs_base='core_engine/inputs/raw_docs', output_file='shared_data/train_ready.jsonl'):
        self.raw_docs_base = raw_docs_base
        self.output_file = output_file

    def extract_text_from_pdf(self, file_path):
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"❌ Error extracting PDF {file_path}: {e}")
        return text.strip()

    def extract_text_from_docx(self, file_path):
        try:
            return docx2txt.process(file_path).strip()
        except Exception as e:
            print(f"❌ Error extracting DOCX {file_path}: {e}")
            return ""

    def process_document(self, file_path, lang):
        """
        Process a single document and return an Alpaca entry.
        """
        ext = os.path.splitext(file_path)[1].lower()
        content = ""
        
        if ext == '.pdf':
            content = self.extract_text_from_pdf(file_path)
        elif ext == '.docx':
            content = self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
        if not content:
            return None

        # Improved extraction for "Expert Tone" output
        output_text = ""
        input_text = ""
        
        if lang == 'ar':
            instruction = "قم بتقييم العقار التالي بناءً على المعايير المعتمدة"
            # Search for Arabic valuation conclusion markers
            markers = ["ﺍﻟﻘﻴﻤﺔ ﺍﻟﺴﻮﻗﻴﺔ", "ﺇﺟﻤﺎﻟﻲ ﺍﻟﺘﻘﻴﻴﻢ", "ﺧﻼﺻﺔ ﺍﻟﺘﻘﻴﻴﻢ", "ﻭﻗﺪ ﻭﺻﻠﺖ ﻧﺘﻴﺠﺔ"]
            found = False
            for marker in markers:
                if marker in content:
                    parts = content.split(marker, 1)
                    input_text = parts[0].strip()
                    # Take the next few lines/paragraphs as the output to capture the "Tone"
                    output_text = marker + parts[1][:500].strip() 
                    found = True
                    break
            if not found:
                input_text = content[:2000].strip()
                output_text = "Professional Valuation: Analysis of technical specs and market comparison required."
                
        else:
            instruction = "Perform a valuation for the following asset based on approved standards"
            # Search for English valuation conclusion markers
            markers = ["Market Value", "Opinion of Value", "Conclusion of Value", "Final Value Estimate"]
            found = False
            for marker in markers:
                if marker in content:
                    parts = content.split(marker, 1)
                    input_text = parts[0].strip()
                    output_text = marker + parts[1][:500].strip()
                    found = True
                    break
            if not found:
                input_text = content[:2000].strip()
                output_text = "Professional Valuation: Analysis of technical specs and market comparison required."

        return {
            "instruction": instruction,
            "input": input_text,
            "output": output_text
        }

    def run(self):
        records = []
        langs = ['ar', 'en']
        
        for lang in langs:
            lang_dir = os.path.join(self.raw_docs_base, lang)
            if not os.path.exists(lang_dir):
                print(f"⚠️ Directory {lang_dir} does not exist.")
                continue
            
            for filename in os.listdir(lang_dir):
                file_path = os.path.join(lang_dir, filename)
                if os.path.isfile(file_path):
                    entry = self.process_document(file_path, lang)
                    if entry:
                        records.append(entry)
                        print(f"✅ Processed: {filename} ({lang})")

        if not records:
             # Fallback/Dummy data if no files found for verification
             print("ℹ️ No source files found. Generating dummy records to verify structure.")
             records = [
                 {
                     "instruction": "قم بتقييم هذا العرض بناءً على المواصفات الفنية المرفقة.",
                     "input": "شقة سكنية - المعادي - 200م - تشطيب فاخر.",
                     "output": "يُقدر سعر المتر في هذه المنطقة بـ 15000 جنيه، الإجمالي 3,000,000 جنيه مصري."
                 },
                 {
                     "instruction": "Evaluate this property based on the provided specifications.",
                     "input": "Office space - Riyadh - 300sqm - Near Metro station.",
                     "output": "The estimated market value is 4,000,000 SAR justified by strategic location and high accessibility."
                 }
             ]

        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"🚀 Final dataset saved to: {self.output_file}")
        return records

if __name__ == "__main__":
    preparer = TrainingDataPreparer()
    preparer.run()
