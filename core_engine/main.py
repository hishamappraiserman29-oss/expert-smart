import os
import json
import time
import glob
import datetime
from typing import Dict, Tuple, Optional

from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Your existing modules
from engine.valuation_logic import calculate_dcf, calculate_residual
from integration.google_sheets_sync import GoogleSheetsClient, build_row_from_schema
from integration.google_drive import build_drive_service, upload_to_drive

load_dotenv()


# -------------------------
# Helpers
# -------------------------
def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: str = "0") -> bool:
    return _env(name, default) in ("1", "true", "True", "yes", "YES", "on", "ON")


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _now_ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_basename(path: str) -> str:
    return os.path.basename(path).replace(" ", "_")


def _is_temporary_file(path: str) -> bool:
    base = os.path.basename(path).lower()
    # ignore Office temp files, partial downloads, hidden temp
    return (
        base.startswith("~$")
        or base.endswith(".tmp")
        or base.endswith(".crdownload")
        or base.endswith(".part")
        or base.endswith(".download")
    )


def _wait_until_file_stable(path: str, timeout_s: int = 20, interval_s: float = 0.5) -> bool:
    """
    Wait until file size stops changing to avoid reading partial write.
    """
    start = time.time()
    last_size = -1
    same_count = 0

    while time.time() - start < timeout_s:
        try:
            size = os.path.getsize(path)
        except Exception:
            time.sleep(interval_s)
            continue

        if size == last_size:
            same_count += 1
            if same_count >= 3:
                return True
        else:
            same_count = 0
            last_size = size

        time.sleep(interval_s)

    return False


def _write_text(path: str, text: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text or "")


# -------------------------
# Text / Data Extraction
# -------------------------
def extract_text_from_pdf(filepath: str) -> str:
    """
    Robust-ish PDF text extraction using PyPDF2.
    Install: pip install pypdf2
    """
    try:
        import PyPDF2
    except Exception as e:
        return f"[PDF] PyPDF2 not installed. Install with: pip install PyPDF2. ({e})"

    text_parts = []
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    text_parts.append(page.extract_text() or "")
                except Exception:
                    text_parts.append("")
    except Exception as e:
        return f"[PDF] extraction failed: {e}"

    return "\n".join(text_parts).strip()


def extract_text_from_docx(filepath: str) -> str:
    """
    Word text extraction using python-docx.
    Install: pip install python-docx
    """
    try:
        import docx  # python-docx
    except Exception as e:
        return f"[DOCX] python-docx not installed. Install with: pip install python-docx. ({e})"

    try:
        d = docx.Document(filepath)
        paras = [p.text for p in d.paragraphs if p.text]
        return "\n".join(paras).strip()
    except Exception as e:
        return f"[DOCX] extraction failed: {e}"


def extract_from_image_to_case_json(filepath: str) -> Tuple[Optional[Dict], str]:
    """
    Uses processors/vision_ocr.py -> VisionProcessor to output strict Case JSON.
    Returns: (case_json_or_none, debug_text)
    """
    try:
        from processors.vision_ocr import VisionProcessor
    except Exception as e:
        return None, f"[IMAGE] vision_ocr.py not available/import failed: {e}"

    vp = VisionProcessor()
    result = vp.process_image(filepath)

    if isinstance(result, dict) and result.get("error"):
        return None, f"[IMAGE] Vision error: {result.get('error')}"

    # result should be a dict matching schema
    return result, "[IMAGE] VisionProcessor returned structured JSON."


def extract_text_from_audio(filepath: str) -> Tuple[str, str]:
    """
    Uses processors/speech_to_text.py -> SpeechProcessor to transcribe.
    Returns: (text, debug)
    """
    try:
        from processors.speech_to_text import SpeechProcessor
    except Exception as e:
        return "", f"[AUDIO] speech_to_text.py not available/import failed: {e}"

    sp = SpeechProcessor()
    try:
        txt = sp.transcribe(
            filepath,
            language=_env("AUDIO_LANGUAGE", "ar"),
            prompt=_env("AUDIO_PROMPT", ""),
            temperature=float(_env("AUDIO_TEMPERATURE", "0.0") or "0.0"),
        )
        return txt, "[AUDIO] Transcription OK."
    except Exception as e:
        return "", f"[AUDIO] Transcription failed: {e}"


def extract_text_from_file(filepath: str) -> Tuple[str, str]:
    """
    Returns: (text, source_kind)
    source_kind in: pdf, docx, image, audio, txt, json, unknown
    NOTE:
      - Images use VisionProcessor -> returns JSON directly, so text will be just a marker.
      - We'll handle images in process_input_file() specially.
    """
    ext = os.path.splitext(filepath)[1].lower()

    # JSON file dropped directly => treat as case JSON
    if ext == ".json":
        return "", "json"

    # Plain text
    if ext in [".txt", ".md"]:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), "txt"
        except Exception as e:
            return f"[TXT] read failed: {e}", "txt"

    # PDF
    if ext == ".pdf":
        return extract_text_from_pdf(filepath), "pdf"

    # Word
    if ext in [".docx"]:
        return extract_text_from_docx(filepath), "docx"
    if ext in [".doc"]:
        return f"[DOC] .doc legacy format. Convert to .docx then retry. File: {filepath}", "docx"

    # Images (we will process with VisionProcessor in process_input_file)
    if ext in [".png", ".jpg", ".jpeg", ".jfif", ".webp", ".tif", ".tiff"]:
        return f"[IMAGE detected: {filepath}]", "image"

    # Audio
    if ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".flac"]:
        text, _debug = extract_text_from_audio(filepath)
        return text, "audio"

    return f"[Unknown file type: {filepath}]", "unknown"


# -------------------------
# Naive Text -> Case JSON (Baseline)
# -------------------------
def naive_text_to_case_json(text: str, meta: Dict) -> Dict:
    """
    Baseline 'structural' JSON.
    It will NOT reliably produce NOI/GDV unless you implement parser or LLM extraction.
    """
    return {
        "timestamp": meta.get("inspection_date") or _now_ts(),
        "source_client": meta.get("source_client", ""),
        "property_type": meta.get("property_type", ""),
        "location_zone": meta.get("location_zone", ""),
        "area_sqm": meta.get("area_sqm", ""),
        "inspection": {
            "inspection_date": meta.get("inspection_date", ""),
            "finish_state": meta.get("finish_state", ""),
            "vacant": meta.get("vacant", ""),
            "notes": meta.get("notes", ""),
        },
        "raw_extracted_text": (text or "")[:20000],
        "valuation_data": {
            "market_approach_value": "",
            "cost_approach_value": "",
            "income_dcf_data": {
                "noi_annual": "",
                "cap_rate_percent": "",
                "discount_rate_percent": "",
                "growth_rate_percent": "",
                "exit_yield_percent": "",
                "projection_years": 5
            },
            "residual_data": {
                "gdv": "",
                "dev_cost": "",
                "dev_profit_percent": 20
            }
        },
        "ai_generative_benchmark": {},
        "final_reconciled_value": "",
        "ai_notes": "Generated by naive_text_to_case_json (needs parser/LLM for accurate numbers)."
    }


def _build_meta_from_env() -> Dict:
    # Read session_config to augment defaults
    session_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared_data', 'session_config.json')
    session_data = {}
    if os.path.exists(session_config_path):
        try:
            session_data = _load_json(session_config_path)
        except Exception as e:
            print(f"⚠️ Could not load session config: {e}")

    active_session = session_data.get('active_session', {})
    expert_name = active_session.get('expert_name', '')
    region = active_session.get('selected_region', '')
    currency = active_session.get('currency', 'EGP')
    val_standard = active_session.get('valuation_standard', 'EFSA')

    return {
        "inspection_date": _env("INSPECTION_DATE", ""),
        "finish_state": _env("FINISH_STATE", ""),
        "vacant": _env("VACANT", ""),
        "notes": _env("NOTES", ""),
        "source_client": expert_name or _env("SOURCE_CLIENT", ""),
        "property_type": _env("PROPERTY_TYPE", ""),
        "location_zone": _env("LOCATION_ZONE", f"Region: {region}" if region else ""),
        "area_sqm": _env("AREA_SQM", ""),
        "currency": currency,
        "valuation_standard": val_standard
    }


# -------------------------
# Core Case Processing (Valuation + Sheets + Drive + Report)
# -------------------------
def process_case_dict(case_data: Dict, config: Dict, origin_label: str = ""):
    valuation_data = case_data.get("valuation_data", {}) or {}
    income = valuation_data.get("income_dcf_data", {}) or {}
    residual = valuation_data.get("residual_data", {}) or {}

    print("🧮 إجراء الحسابات المالية (DCF & Residual)...")
    dcf_result = calculate_dcf(
        noi_annual=income.get("noi_annual"),
        discount_rate_percent=income.get("discount_rate_percent"),
        growth_rate_percent=income.get("growth_rate_percent"),
        exit_yield_percent=income.get("exit_yield_percent"),
        projection_years=income.get("projection_years", 5),
        cap_rate_percent=income.get("cap_rate_percent"),
    )

    residual_result = calculate_residual(
        gdv=residual.get("gdv"),
        dev_cost=residual.get("dev_cost"),
        dev_profit_percent=residual.get("dev_profit_percent", 20),
    )

    out = {
        "timestamp": case_data.get("timestamp") or _now_ts(),
        "source_client": case_data.get("source_client", ""),
        "property_type": case_data.get("property_type", ""),
        "location_zone": case_data.get("location_zone", ""),
        "area_sqm": case_data.get("area_sqm", ""),
        "inspection": case_data.get("inspection", {}) or {},
        "origin_label": origin_label,
        "valuation_data": {
            "market_approach_value": valuation_data.get("market_approach_value", ""),
            "cost_approach_value": valuation_data.get("cost_approach_value", ""),
            "income_dcf_data": {
                "noi_annual": income.get("noi_annual", ""),
                "cap_rate_percent": income.get("cap_rate_percent", ""),
                "discount_rate_percent": income.get("discount_rate_percent", ""),
                "growth_rate_percent": income.get("growth_rate_percent", ""),
                "exit_yield_percent": income.get("exit_yield_percent", ""),
                "projection_years": income.get("projection_years", 5),
                "dcf_value": dcf_result.get("dcf_value", ""),
            },
            "residual_data": {
                "gdv": residual.get("gdv", ""),
                "dev_cost": residual.get("dev_cost", ""),
                "dev_profit_percent": residual.get("dev_profit_percent", 20),
                "residual_land_value": residual_result.get("residual_land_value", ""),
            },
        },
        "ai_generative_benchmark": case_data.get("ai_generative_benchmark", {}) or {},
        "final_reconciled_value": case_data.get("final_reconciled_value", ""),
        "ai_notes": case_data.get("ai_notes", ""),
    }

    # Save local output JSON
    _save_json(config["INPUT_JSON_FILE"], out)
    print(f"💾 تم حفظ النتائج في: {config['INPUT_JSON_FILE']}")

    # Generate Markdown report
    os.makedirs(config["REPORTS_DIR"], exist_ok=True)
    report_name = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path = os.path.join(config["REPORTS_DIR"], report_name)

    insp = out.get("inspection", {}) or {}
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Property Valuation Report (Auto) - {case_data.get('currency', 'EGP')}\n\n")
        f.write(f"- Valuation Standard: {case_data.get('valuation_standard', 'EFSA')}\n")
        f.write(f"- Timestamp: {out['timestamp']}\n")
        f.write(f"- Origin: {origin_label}\n")
        f.write(f"- Source/Client: {out['source_client']}\n")
        f.write(f"- Property Type: {out['property_type']}\n")
        f.write(f"- Location/Zone: {out['location_zone']}\n")
        f.write(f"- Area (sqm): {out['area_sqm']}\n\n")

        f.write("## Inspection\n")
        f.write(f"- Inspection date: {insp.get('inspection_date','')}\n")
        f.write(f"- Finish state: {insp.get('finish_state','')}\n")
        f.write(f"- Vacant: {insp.get('vacant','')}\n")
        f.write(f"- Notes: {insp.get('notes','')}\n\n")

        f.write("## Valuation Inputs\n")
        inc = out["valuation_data"]["income_dcf_data"]
        res = out["valuation_data"]["residual_data"]
        f.write(f"- NOI (annual): {inc.get('noi_annual','')}\n")
        f.write(f"- Cap Rate (%): {inc.get('cap_rate_percent','')}\n")
        f.write(f"- Discount Rate (%): {inc.get('discount_rate_percent','')}\n")
        f.write(f"- Growth Rate (%): {inc.get('growth_rate_percent','')}\n")
        f.write(f"- Exit Yield (%): {inc.get('exit_yield_percent','')}\n")
        f.write(f"- Projection Years: {inc.get('projection_years','')}\n")
        f.write(f"- GDV: {res.get('gdv','')}\n")
        f.write(f"- Dev Cost: {res.get('dev_cost','')}\n")
        f.write(f"- Dev Profit (%): {res.get('dev_profit_percent','')}\n\n")

        f.write("## Results\n")
        f.write(f"- DCF Value: {inc.get('dcf_value','')}\n")
        f.write(f"- Residual Land Value: {res.get('residual_land_value','')}\n")

    print(f"📝 Report generated: {report_path}")

    # Drive upload (optional)
    file_link = ""
    report_link = ""
    if config["ENABLE_DRIVE_UPLOAD"]:
        print("☁️ جاري الرفع إلى Google Drive...")
        try:
            drive = build_drive_service("credentials.json", "token.json")

            _id1, file_link = upload_to_drive(drive, config["INPUT_JSON_FILE"], config["DRIVE_FOLDER_ID"] or None)
            _id2, report_link = upload_to_drive(drive, report_path, config["DRIVE_FOLDER_ID"] or None)

            if report_link:
                print(f"✅ Report uploaded: {report_link}")
            if file_link:
                print(f"✅ JSON uploaded: {file_link}")
        except Exception as e:
            print(f"⚠️ تحذير: فشل الرفع لـ Drive ({e}) - سيتم إكمال العملية بدونه.")
            file_link, report_link = "", ""

    # Sheets sync
    print(f"📊 جاري إضافة الصف إلى Google Sheets ({config['SHEET_ID']})...")
    try:
        sheets = GoogleSheetsClient(
            sheet_id=config["SHEET_ID"],
            sheet_tab=config["SHEET_TAB"],
            template_row=config["TEMPLATE_ROW"],
            credentials_file="credentials.json",
            token_file="token.json",
        )

        row = build_row_from_schema(out, file_link=report_link or file_link)
        new_row = sheets.append_row_and_copy_formulas(row, copy_formula_columns=("M", "Q"))
        print(f"✅✅ تم بنجاح! تمت الإضافة في الصف رقم: {new_row}")
        print("🏁 انتهت المعالجة بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء المزامنة مع Google Sheets: {e}")


# -------------------------
# File Processing Entry
# -------------------------
def process_input_file(filepath: str, config: Dict):
    if _is_temporary_file(filepath):
        return

    name = _safe_basename(filepath)
    print(f"\n📥 New input detected: {name}")

    if not _wait_until_file_stable(filepath):
        print("⚠️ الملف لم يستقر (قد يكون لسه بيتكتب). تجاهل/أعد المحاولة.")
        return

    ext = os.path.splitext(filepath)[1].lower()

    # 1) JSON provided directly
    if ext == ".json":
        try:
            case_data = _load_json(filepath)
            return process_case_dict(case_data, config, origin_label=name)
        except Exception as e:
            print(f"❌ Failed to load JSON: {e}")
            return

    # 2) Image => VisionProcessor returns full Case JSON
    if ext in [".png", ".jpg", ".jpeg", ".jfif", ".webp", ".tif", ".tiff"]:
        case_json, debug = extract_from_image_to_case_json(filepath)
        print(debug)

        if not isinstance(case_json, dict):
            # fallback: store marker + proceed naive
            text = f"[IMAGE] failed to extract structured JSON. File: {filepath}"
            kind = "image"
            _save_extracted_text(config, name, kind, text)
            meta = _build_meta_from_env()
            case_data = naive_text_to_case_json(text=text, meta=meta)
        else:
            # enrich inspection fields from env if missing
            meta = _build_meta_from_env()
            case_json.setdefault("inspection", {})
            # only fill if empty
            for k in ("inspection_date", "finish_state", "vacant", "notes"):
                case_json["inspection"].setdefault(k, meta.get(k, ""))
            case_json.setdefault("timestamp", meta.get("inspection_date") or _now_ts())
            case_data = case_json

        case_path = _save_case_json_sidecar(config, case_data, origin=name)
        print(f"🧩 Case JSON created: {case_path}")
        return process_case_dict(case_data, config, origin_label=name)

    # 3) Everything else => extract text then make Case JSON (structural)
    text, kind = extract_text_from_file(filepath)
    _save_extracted_text(config, name, kind, text)

    meta = _build_meta_from_env()
    case_data = naive_text_to_case_json(text=text, meta=meta)

    case_path = _save_case_json_sidecar(config, case_data, origin=name)
    print(f"🧩 Case JSON created: {case_path}")

    process_case_dict(case_data, config, origin_label=name)


def _save_extracted_text(config: Dict, origin_name: str, kind: str, text: str):
    extracted_dir = os.path.join(config["LOGS_DIR"], "extracted_text")
    os.makedirs(extracted_dir, exist_ok=True)
    extracted_path = os.path.join(extracted_dir, f"{os.path.splitext(origin_name)[0]}_{kind}.txt")
    _write_text(extracted_path, text)
    print(f"🧾 Extracted text saved: {extracted_path}")


def _save_case_json_sidecar(config: Dict, case_data: Dict, origin: str) -> str:
    os.makedirs(config["CASES_DIR"], exist_ok=True)
    case_json_path = os.path.join(
        config["CASES_DIR"],
        f"case_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.splitext(origin)[0]}.json"
    )
    _save_json(case_json_path, case_data)
    return case_json_path


# -------------------------
# Watchdog Handler
# -------------------------
class NewInputHandler(FileSystemEventHandler):
    def __init__(self, config: Dict):
        self.config = config
        self._processed_recent: Dict[str, float] = {}

    def _debounced(self, path: str, window_s: int = 5) -> bool:
        now = time.time()
        last = self._processed_recent.get(path, 0)
        if now - last < window_s:
            return True
        self._processed_recent[path] = now
        return False

    def on_created(self, event):
        if event.is_directory:
            return
        if self._debounced(event.src_path):
            return
        time.sleep(0.5)
        process_input_file(event.src_path, self.config)

    def on_moved(self, event):
        # Many apps write temp then move into place
        if getattr(event, "is_directory", False):
            return
        dest = getattr(event, "dest_path", None)
        if not dest:
            return
        if self._debounced(dest):
            return
        time.sleep(0.5)
        process_input_file(dest, self.config)


def _initial_scan(config: Dict):
    if not _env_bool("INITIAL_SCAN", "1"):
        return
    print("🔎 Initial scan enabled: scanning existing files in watch folder...")
    patterns = ["*.*"]
    for pat in patterns:
        for fp in glob.glob(os.path.join(config["WATCH_DIR"], pat)):
            if os.path.isfile(fp) and not _is_temporary_file(fp):
                process_input_file(fp, config)


def main():
    print("\n" + "=" * 60)
    print("🚀 بدء نظام التقييم العقاري (Workflow Automator)")
    print("=" * 60)

    config = {
        "SHEET_ID": _env("GOOGLE_SHEETS_ID"),
        "SHEET_TAB": _env("GOOGLE_SHEET_TAB", "Sheet1"),
        "TEMPLATE_ROW": int(_env("GOOGLE_TEMPLATE_ROW", "2") or "2"),
        "ENABLE_DRIVE_UPLOAD": _env_bool("ENABLE_DRIVE_UPLOAD", "0"),
        "DRIVE_FOLDER_ID": _env("GOOGLE_DRIVE_FOLDER_ID", ""),
        "INPUT_JSON_FILE": _env("INPUT_JSON_FILE", "input_data.json"),
        "WATCH_DIR": _env("WATCH_DIR", "inputs"),
        "CASES_DIR": _env("CASES_DIR", "inputs_case_json"),
        "REPORTS_DIR": _env("REPORTS_DIR", "outputsreports"),
        "LOGS_DIR": _env("LOGS_DIR", "outputslogs"),
    }

    if not config["SHEET_ID"]:
        raise SystemExit("❌ GOOGLE_SHEETS_ID مش موجود في .env")

    os.makedirs(config["WATCH_DIR"], exist_ok=True)
    os.makedirs(config["CASES_DIR"], exist_ok=True)
    os.makedirs(config["REPORTS_DIR"], exist_ok=True)
    os.makedirs(config["LOGS_DIR"], exist_ok=True)

    print(f"📡 Monitoring folder: {config['WATCH_DIR']}")
    print("ضع أي ملفات هنا: pdf/docx/jpg/png/mp3/wav/txt/json ... وسيتم التعامل معها.")
    print("🧠 Images: سيتم استخراج Case JSON تلقائياً عبر VisionProcessor.")
    print("🎙️ Audio: سيتم تحويله لنص عبر SpeechProcessor ثم Case JSON هيكلي.")

    # Optional initial scan
    _initial_scan(config)

    handler = NewInputHandler(config)
    observer = Observer()
    observer.schedule(handler, config["WATCH_DIR"], recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 تم إيقاف المراقبة.")
    observer.join()


if __name__ == "__main__":
    main()