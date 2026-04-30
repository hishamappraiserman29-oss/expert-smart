import re
from typing import Any, Dict, List, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from integration.google_oauth import get_oauth_credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _safe_get(d: Dict[str, Any], path: str, default=None):
    cur: Any = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _num_or_blank(x: Any):
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return x
    try:
        s = str(x).strip().replace(",", "")
        if s == "":
            return ""
        return float(s) if ("." in s) else int(s)
    except Exception:
        return ""


def _percent_to_fraction_or_blank(pct: Any):
    """
    Scenario A:
    JSON يخزن 7.5 (percent) لكن الشيت عمود Percent => لازم نرسل 0.075
    """
    if pct is None or pct == "":
        return ""
    try:
        if isinstance(pct, str):
            s = pct.strip().replace("%", "").replace(",", "")
            if s == "":
                return ""
            val = float(s)
        else:
            val = float(pct)
        return val / 100.0
    except Exception:
        return ""


def build_row_from_schema(data: Dict[str, Any], file_link: str = "") -> List[Any]:
    """
    ترتيب الأعمدة A..V (22 عمود) مطابق للشيت:
    A Timestamp
    B Source/Client
    C Property Type
    D Location/Zone
    E Area
    F Market
    G Cost
    H NOI
    I Cap Rate (%)      -> fraction
    J Discount Rate (%) -> fraction
    K Growth Rate (%)   -> fraction
    L Exit Yield (%)    -> fraction
    M DCF Value (Calc)  -> formula copied
    N GDV (Sales)
    O Dev Cost & Fees
    P Developer Profit (%) -> fraction
    Q Residual Land Value -> formula copied
    R AI Benchmark Value
    S AI Reasoning
    T Final Reconciled Value
    U AI Notes
    V File Link
    """
    ts = _safe_get(data, "timestamp", "")
    source_client = _safe_get(data, "source_client", "")
    property_type = _safe_get(data, "property_type", "")
    location_zone = _safe_get(data, "location_zone", "")
    area_sqm = _num_or_blank(_safe_get(data, "area_sqm", ""))

    market = _num_or_blank(_safe_get(data, "valuation_data.market_approach_value", ""))
    cost = _num_or_blank(_safe_get(data, "valuation_data.cost_approach_value", ""))

    noi = _num_or_blank(_safe_get(data, "valuation_data.income_dcf_data.noi_annual", ""))

    cap = _percent_to_fraction_or_blank(_safe_get(data, "valuation_data.income_dcf_data.cap_rate_percent", None))
    disc = _percent_to_fraction_or_blank(_safe_get(data, "valuation_data.income_dcf_data.discount_rate_percent", None))
    growth = _percent_to_fraction_or_blank(_safe_get(data, "valuation_data.income_dcf_data.growth_rate_percent", None))
    exit_y = _percent_to_fraction_or_blank(_safe_get(data, "valuation_data.income_dcf_data.exit_yield_percent", None))

    dcf_calc = ""  # M formula copied

    gdv = _num_or_blank(_safe_get(data, "valuation_data.residual_data.gdv", ""))
    dev_cost = _num_or_blank(_safe_get(data, "valuation_data.residual_data.dev_cost", ""))
    dev_profit = _percent_to_fraction_or_blank(_safe_get(data, "valuation_data.residual_data.dev_profit_percent", None))

    residual_land = ""  # Q formula copied

    ai_value = _num_or_blank(_safe_get(data, "ai_generative_benchmark.ai_suggested_value", ""))
    ai_reason = _safe_get(data, "ai_generative_benchmark.ai_benchmark_reasoning", "")
    final_val = _num_or_blank(_safe_get(data, "final_reconciled_value", ""))
    ai_notes = _safe_get(data, "ai_notes", "")

    return [
        ts,                 # A
        source_client,      # B
        property_type,      # C
        location_zone,      # D
        area_sqm,           # E
        market,             # F
        cost,               # G
        noi,                # H
        cap,                # I
        disc,               # J
        growth,             # K
        exit_y,             # L
        dcf_calc,           # M
        gdv,                # N
        dev_cost,           # O
        dev_profit,         # P
        residual_land,      # Q
        ai_value,           # R
        ai_reason,          # S
        final_val,          # T
        ai_notes,           # U
        file_link or "",    # V
    ]


class GoogleSheetsClient:
    def __init__(
        self,
        sheet_id: str,
        sheet_tab: str,
        template_row: int = 2,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
    ):
        self.sheet_id = sheet_id
        self.sheet_tab = sheet_tab
        self.template_row = template_row

        creds = get_oauth_credentials(credentials_file, token_file)
        self.service = build("sheets", "v4", credentials=creds)
        self._tab_gid = self._get_tab_gid(sheet_tab)

    def _get_tab_gid(self, tab_name: str) -> int:
        meta = self.service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
        for sh in meta.get("sheets", []):
            props = sh.get("properties", {})
            if props.get("title") == tab_name:
                return int(props.get("sheetId"))
        raise RuntimeError(f"Sheet tab not found: {tab_name}")

    def append_row_and_copy_formulas(
        self,
        row_values: List[Any],
        copy_formula_columns: Tuple[str, ...] = ("M", "Q"),
    ) -> int:
        """
        1) Append row values (A..V)
        2) Copy formulas from template_row (مثلاً M2 و Q2) لنفس الأعمدة في الصف الجديد
        """
        try:
            append_range = f"{self.sheet_tab}!A:V"
            resp = (
                self.service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.sheet_id,
                    range=append_range,
                    valueInputOption="USER_ENTERED",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [row_values]},
                )
                .execute()
            )
        except HttpError as e:
            raise RuntimeError(f"Google Sheets append failed: {e}")

        updated_range = resp.get("updates", {}).get("updatedRange", "")
        # مثال: Sheet1!A23:V23
        m = re.search(r"!(?:[A-Z]+)(\d+):", updated_range)
        if not m:
            raise RuntimeError(f"Could not detect appended row from updatedRange: {updated_range}")
        new_row = int(m.group(1))

        requests = []
        for col_letter in copy_formula_columns:
            start_col = self._col_letter_to_index(col_letter)
            requests.append(
                {
                    "copyPaste": {
                        "source": {
                            "sheetId": self._tab_gid,
                            "startRowIndex": self.template_row - 1,
                            "endRowIndex": self.template_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": start_col + 1,
                        },
                        "destination": {
                            "sheetId": self._tab_gid,
                            "startRowIndex": new_row - 1,
                            "endRowIndex": new_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": start_col + 1,
                        },
                        "pasteType": "PASTE_FORMULA",
                        "pasteOrientation": "NORMAL",
                    }
                }
            )

        if requests:
            try:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.sheet_id,
                    body={"requests": requests},
                ).execute()
            except HttpError as e:
                print(f"⚠️ تحذير: فشل نسخ المعادلات (M/Q): {e}")

        return new_row

    @staticmethod
    def _col_letter_to_index(letter: str) -> int:
        """
        A -> 0, B -> 1, ... Z -> 25, AA -> 26 ...
        """
        letter = letter.strip().upper()
        idx = 0
        for ch in letter:
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
        return idx - 1
