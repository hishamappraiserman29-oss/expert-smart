from datetime import datetime
from typing import Dict, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from adapters.asset import AssetValuationResult


# ── Style constants ────────────────────────────────────────────────────────────

_FILL_HEADER   = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
_FILL_SUBHEAD  = PatternFill(start_color="D6E4F7", end_color="D6E4F7", fill_type="solid")
_FILL_SECTION  = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
_FILL_CB         = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
_FILL_PORTFOLIO  = PatternFill(start_color="203864", end_color="203864", fill_type="solid")
_FILL_PORT_COL   = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
_FILL_ERROR      = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
_FILL_WARNING  = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")

_FONT_HEADER   = Font(bold=True, color="FFFFFF", size=12)
_FONT_TITLE    = Font(bold=True, size=14)
_FONT_SECTION  = Font(bold=True, size=12)
_FONT_BOLD     = Font(bold=True)
_FONT_ERR_LBL  = Font(color="FFFFFF", bold=True)
_FONT_MUTED    = Font(italic=True, color="888888")

_ALIGN_CENTER  = Alignment(horizontal="center", vertical="center", wrap_text=True)
_ALIGN_WRAP    = Alignment(wrap_text=True, vertical="top")
_BORDER_THIN   = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"),  bottom=Side(style="thin"),
)

_FMT_CURRENCY  = '#,##0.00'
_FMT_PCT       = '0.00%'

# ── Advanced-analytics sheets excluded from the legacy export ─────────────────
# Match is performed on sheet_name.strip().lower() so both Arabic variants
# (ي / ى endings, hamza variants) and English names are covered.
_LEGACY_EXCLUDED_SHEETS: frozenset = frozenset({
    "التحليل المكاني", "التحليل المكانى",
    "الإنحدار المتعدد", "الانحدار المتعدد",
    "الخيارات الحقيقية",
    "لوحة القيادة التنفيذية",
    "الشبكات العصبية",
    "السلاسل الزمنية",
    "إستخبارات السوق", "استخبارات السوق",
    "spatial analysis",
    "multiple regression",
    "real options",
    "executive dashboard",
    "neural networks",
    "time series",
    "market intelligence",
})

# EGVS / IFRS reference descriptions
_DISCLOSURE_DESCRIPTIONS: dict[str, str] = {
    "EGVS_1.0":  "Definition of Market Value",
    "EGVS_1.1":  "Basis of Valuation",
    "EGVS_2.0":  "Assumptions and Limiting Conditions",
    "EGVS_2.1":  "Market Conditions and Valuation Date",
    "EGVS_2.2":  "Special Assumptions",
    "EGVS_2.3":  "Valuation Date and Purpose",
    "EGVS_2.4":  "Insurance Valuation Purpose",
    "EGVS_2.5":  "Underwriting Assumptions",
    "EGVS_3.0":  "Three Approaches to Value",
    "EGVS_3.1":  "Sales Comparison Approach",
    "EGVS_3.2":  "Cost Approach",
    "EGVS_3.3":  "Income Capitalisation Approach",
    "EGVS_4.0":  "Replacement Cost Basis",
    "IFRS_13-1":  "Scope and Objective of Fair Value",
    "IFRS_13-54": "Definition of Fair Value",
    "IFRS_13-55": "Market Participant Assumption",
    "IFRS_13-72": "Fair Value Hierarchy (Introduction)",
    "IFRS_13-73": "Level 1 — Quoted Prices",
    "IFRS_13-74": "Level 2 — Observable Inputs",
    "IFRS_13-75": "Level 3 — Unobservable Inputs",
    "IFRS_13-89": "Non-Performance Risk",
    "IFRS_13-90": "Valuation Adjustments",
    "CBE_Circular_Mortgage_Rules": "Central Bank of Egypt Mortgage Rules",
    "Basel_III_LGD":               "Basel III Loss Given Default",
    "Egyptian_Lender_Standards":   "Egyptian Lender Standards",
    "Insurance_Industry_Standards":"Egyptian Insurance Industry Standards",
    "AssetAdapter_RESIDENTIAL":    "Residential Asset Adapter (80/15/5 weighting)",
    "AssetAdapter_COMMERCIAL":     "Commercial Asset Adapter (income-focused weighting)",
}


class ExcelReportBuilder:
    """
    Generate an EGVS-compliant Excel workbook from an AssetValuationResult.

    Sheet order
    -----------
    0  Summary            — executive overview
    1  Three Approaches   — Phase 4 raw values
    2  Weights Analysis   — weighted reconciliation table
    3  Audit Trail        — full step-by-step log
    4  Property Details   — all metadata fields
    5  Disclosures        — EGVS + IFRS compliance refs
    6  Issues & Warnings  — validation issues
    7  Certification      — appraiser signature block
    8  IVSC Compliance    — optional; added when ivsc_disclosure is provided
    """

    def __init__(self, result: Optional[AssetValuationResult] = None) -> None:
        self.result      = result
        self.workbook    = Workbook()
        self.workbook.remove(self.workbook.active)   # remove default blank sheet
        self.report_date = datetime.now().strftime("%Y-%m-%d")

    # ──────────────────────────────────────────────────────────────────────────
    # Shared styling helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _apply_header_style(self, ws, row: int, cols: int) -> None:
        """Dark-blue fill, white bold text, thin border on every cell in the row."""
        for col in range(1, cols + 1):
            cell             = ws.cell(row=row, column=col)
            cell.fill        = _FILL_HEADER
            cell.font        = _FONT_HEADER
            cell.alignment   = _ALIGN_CENTER
            cell.border      = _BORDER_THIN

    def _apply_currency_format(self, ws, start_row: int, end_row: int, col: int) -> None:
        for row in range(start_row, end_row + 1):
            ws.cell(row=row, column=col).number_format = _FMT_CURRENCY

    def _apply_percentage_format(self, ws, start_row: int, end_row: int, col: int) -> None:
        for row in range(start_row, end_row + 1):
            ws.cell(row=row, column=col).number_format = _FMT_PCT

    # ──────────────────────────────────────────────────────────────────────────
    # Sheet builders
    # ──────────────────────────────────────────────────────────────────────────

    def sheet_summary(self) -> None:
        ws = self.workbook.create_sheet("Summary", 0)
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 22

        ws["A1"]      = "VALUATION REPORT SUMMARY"
        ws["A1"].font = _FONT_TITLE

        row = 3
        def _row(label, value, *, currency=False, pct=False):
            nonlocal row
            ws.cell(row=row, column=1).value = label
            ws.cell(row=row, column=2).value = value
            if currency:
                self._apply_currency_format(ws, row, row, 2)
            if pct:
                self._apply_percentage_format(ws, row, row, 2)
            row += 1

        _row("Report Date",    self.report_date)
        _row("Asset Type",     self.result.asset_type)
        _row("Primary Purpose",self.result.primary_purpose)
        _row("Final Value (EGP)",
             float(self.result.primary_value) if self.result.primary_value else 0,
             currency=True)
        _row("Confidence",     self.result.confidence)

        row += 1
        ws.cell(row=row, column=1).value = "COMPARABLE ANALYSIS"
        ws.cell(row=row, column=1).font  = _FONT_SECTION
        row += 1

        md = self.result.metadata
        _row("Comparable Value", md.get("comparable", 0), currency=True)
        _row("Cost Value",       md.get("cost",       0), currency=True)
        _row("Income Value",     md.get("income",     0), currency=True)

        row += 1
        ws.cell(row=row, column=1).value = "WEIGHTS APPLIED"
        ws.cell(row=row, column=1).font  = _FONT_SECTION
        row += 1

        w = self.result.weights_applied
        _row("Comparable", w.get("comparable", 0), pct=True)
        _row("Cost",        w.get("cost",       0), pct=True)
        _row("Income",      w.get("income",     0), pct=True)

        if self.result.alternative_values:
            row += 1
            ws.cell(row=row, column=1).value = "ALTERNATIVE VALUES"
            ws.cell(row=row, column=1).font  = _FONT_SECTION
            row += 1
            for purpose, value in self.result.alternative_values.items():
                _row(purpose.replace("_", " ").title(),
                     float(value) if value else 0, currency=True)

    def sheet_three_approaches(self) -> None:
        ws = self.workbook.create_sheet("Three Approaches", 1)
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 16

        headers = ["Approach", "Value (EGP)", "% of Total"]
        self._apply_header_style(ws, 1, len(headers))
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col).value = h

        md  = self.result.metadata
        comp = md.get("comparable", 0)
        cost = md.get("cost",       0)
        inc  = md.get("income",     0)
        total = comp + cost + inc

        rows = [
            ("Comparable Sales", comp),
            ("Cost Approach",    cost),
            ("Income Approach",  inc),
        ]
        for r, (label, val) in enumerate(rows, 2):
            ws.cell(row=r, column=1).value = label
            ws.cell(row=r, column=2).value = val
            self._apply_currency_format(ws, r, r, 2)
            if total > 0:
                ws.cell(row=r, column=3).value = val / total
                self._apply_percentage_format(ws, r, r, 3)

        # Total row
        tr = len(rows) + 2
        ws.cell(row=tr, column=1).value = "TOTAL"
        ws.cell(row=tr, column=1).font  = _FONT_BOLD
        ws.cell(row=tr, column=2).value = total
        ws.cell(row=tr, column=2).font  = _FONT_BOLD
        self._apply_currency_format(ws, tr, tr, 2)

    def sheet_weights_analysis(self) -> None:
        ws = self.workbook.create_sheet("Weights Analysis", 2)
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 14
        ws.column_dimensions["C"].width = 22

        headers = ["Approach", "Weight %", "Weighted Value (EGP)"]
        self._apply_header_style(ws, 1, len(headers))
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col).value = h

        md      = self.result.metadata
        weights = self.result.weights_applied
        entries = [
            ("Comparable", md.get("comparable", 0), weights.get("comparable", 0)),
            ("Cost",        md.get("cost",       0), weights.get("cost",       0)),
            ("Income",      md.get("income",     0), weights.get("income",     0)),
        ]
        for r, (label, val, wt) in enumerate(entries, 2):
            ws.cell(row=r, column=1).value = label
            ws.cell(row=r, column=2).value = wt
            self._apply_percentage_format(ws, r, r, 2)
            ws.cell(row=r, column=3).value = val * wt
            self._apply_currency_format(ws, r, r, 3)

        # Reconciled value row
        tr = len(entries) + 2
        ws.cell(row=tr, column=1).value = "RECONCILED VALUE"
        ws.cell(row=tr, column=1).font  = _FONT_BOLD
        ws.cell(row=tr, column=3).value = float(self.result.primary_value) if self.result.primary_value else 0
        ws.cell(row=tr, column=3).font  = _FONT_BOLD
        self._apply_currency_format(ws, tr, tr, 3)

    def sheet_audit_trail(self) -> None:
        ws = self.workbook.create_sheet("Audit Trail", 3)
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 40
        ws.column_dimensions["C"].width = 40
        ws.column_dimensions["D"].width = 50
        ws.column_dimensions["E"].width = 22

        headers = ["Step Name", "Inputs", "Outputs", "Formula", "References"]
        self._apply_header_style(ws, 1, len(headers))
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col).value = h

        for r, entry in enumerate(self.result.audit_trail, 2):
            ws.cell(row=r, column=1).value = entry.step_name
            ws.cell(row=r, column=2).value = str(entry.inputs)
            ws.cell(row=r, column=3).value = str(entry.outputs)
            ws.cell(row=r, column=4).value = entry.formula
            ws.cell(row=r, column=5).value = ", ".join(entry.references)
            for col in range(1, 6):
                ws.cell(row=r, column=col).alignment = _ALIGN_WRAP

    def sheet_property_details(self) -> None:
        ws = self.workbook.create_sheet("Property Details", 4)
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 40

        ws["A1"]      = "SUBJECT PROPERTY DETAILS"
        ws["A1"].font = _FONT_SECTION

        row = 3
        for key, value in self.result.metadata.items():
            ws.cell(row=row, column=1).value = key.replace("_", " ").title()
            is_value_field = "value" in key.lower() and isinstance(value, (int, float))
            is_weight_dict = "weight" in key.lower() and isinstance(value, dict)

            if is_value_field:
                ws.cell(row=row, column=2).value = value
                self._apply_currency_format(ws, row, row, 2)
            elif is_weight_dict:
                ws.cell(row=row, column=2).value = str(value)
            else:
                ws.cell(row=row, column=2).value = str(value)
            row += 1

    def sheet_disclosures(self) -> None:
        ws = self.workbook.create_sheet("Disclosures", 5)
        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 60

        ws["A1"]      = "STANDARDS & COMPLIANCE REFERENCES"
        ws["A1"].font = _FONT_SECTION

        row = 3
        for disc in self.result.disclosures:
            ws.cell(row=row, column=1).value = disc
            ws.cell(row=row, column=1).font  = _FONT_BOLD
            ws.cell(row=row, column=2).value = _DISCLOSURE_DESCRIPTIONS.get(disc, "See standards documentation")
            row += 1

    def sheet_issues_warnings(self) -> None:
        ws = self.workbook.create_sheet("Issues & Warnings", 6)
        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 55

        headers = ["Severity", "Code", "Message"]
        self._apply_header_style(ws, 1, len(headers))
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col).value = h

        if not self.result.issues:
            cell = ws.cell(row=2, column=1)
            cell.value = "No issues"
            cell.font  = _FONT_MUTED
            return

        for r, issue in enumerate(self.result.issues, 2):
            sev_cell = ws.cell(row=r, column=1)
            sev_cell.value = issue.severity
            if issue.severity == "error":
                sev_cell.fill = _FILL_ERROR
                sev_cell.font = _FONT_ERR_LBL
            elif issue.severity == "warning":
                sev_cell.fill = _FILL_WARNING

            ws.cell(row=r, column=2).value = issue.code
            msg_cell = ws.cell(row=r, column=3)
            msg_cell.value     = issue.message
            msg_cell.alignment = _ALIGN_WRAP

    def sheet_certification(self) -> None:
        ws = self.workbook.create_sheet("Certification", 7)
        ws.column_dimensions["A"].width = 80

        ws["A1"]      = "APPRAISER CERTIFICATION"
        ws["A1"].font = _FONT_TITLE

        cert_text = (
            "I certify that, to the best of my knowledge and belief, the statements of fact "
            "contained in this appraisal are true and correct, and the reported analyses, "
            "conclusions, and recommendations are limited only by the reported assumptions "
            "and limiting conditions and are my personal, impartial, and unbiased professional "
            "analysis, opinions, and conclusions.\n\n"
            "I have no present or prospective interest in the property that is the subject of "
            "this report, and I have performed no services, as an appraiser or in any other "
            "capacity, regarding the subject property that would create a conflict of interest.\n\n"
            "The value opinion in this appraisal was developed independently and in accordance "
            "with the Egyptian Valuation Standard (EgVS) and International Financial Reporting "
            "Standard (IFRS) 13 Fair Value Measurement."
        )

        row = 3
        cert_cell           = ws.cell(row=row, column=1)
        cert_cell.value     = cert_text
        cert_cell.alignment = _ALIGN_WRAP
        ws.row_dimensions[row].height = 130

        row += 10
        for line in (
            "Appraiser Name: ___________________________",
            "License No.:    ___________________________",
            f"Date:           {self.report_date}",
            "Signature:      ___________________________",
        ):
            ws.cell(row=row, column=1).value = line
            row += 2

    def sheet_ivsc_compliance(self, ivsc_disclosure) -> None:
        ws = self.workbook.create_sheet("IVSC Compliance", 8)
        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 70

        def _section(row: int, title: str) -> None:
            cell = ws.cell(row=row, column=1)
            cell.value     = title
            cell.fill      = _FILL_SECTION
            cell.font      = Font(bold=True, color="FFFFFF", size=11)
            cell.alignment = _ALIGN_WRAP
            ws.cell(row=row, column=2).fill = _FILL_SECTION

        def _row(row: int, label: str, value) -> None:
            lc = ws.cell(row=row, column=1)
            lc.value     = label
            lc.font      = _FONT_BOLD
            lc.alignment = _ALIGN_WRAP
            vc = ws.cell(row=row, column=2)
            vc.value     = value if value is not None else "—"
            vc.alignment = _ALIGN_WRAP

        # ── Title row ─────────────────────────────────────────────────────────
        ws.merge_cells("A1:B1")
        title_cell           = ws["A1"]
        title_cell.value     = "IVSC COMPLIANCE DISCLOSURE"
        title_cell.fill      = _FILL_HEADER
        title_cell.font      = Font(bold=True, color="FFFFFF", size=14)
        title_cell.alignment = _ALIGN_CENTER
        ws.row_dimensions[1].height = 28

        ws.merge_cells("A2:B2")
        ws["A2"].value     = f"Report Date: {self.report_date}"
        ws["A2"].alignment = Alignment(horizontal="right")
        ws["A2"].font      = _FONT_MUTED

        r = 4
        # ── Scope of Work ─────────────────────────────────────────────────────
        _section(r, "SCOPE OF WORK (IVS 101)"); r += 1
        _row(r, "Scope of Work",        ivsc_disclosure.scope_of_work);        r += 1
        _row(r, "Purpose of Valuation", ivsc_disclosure.purpose_of_valuation); r += 1
        _row(r, "Effective Date",
             ivsc_disclosure.effective_date.isoformat()
             if ivsc_disclosure.effective_date else "—");                       r += 2

        # ── Basis of Valuation ────────────────────────────────────────────────
        _section(r, "BASIS OF VALUATION (IVS 102)"); r += 1
        _row(r, "Basis",      ivsc_disclosure.basis_of_valuation); r += 1
        _row(r, "Definition", ivsc_disclosure.definition);         r += 2

        # ── Valuation Approaches ──────────────────────────────────────────────
        _section(r, "VALUATION APPROACHES (IVS 103-105)"); r += 1
        _row(r, "Approaches Used",
             ", ".join(ivsc_disclosure.approaches_used)
             if ivsc_disclosure.approaches_used else "—");         r += 1
        _row(r, "Methodology Summary", ivsc_disclosure.methodology_summary)
        ws.row_dimensions[r].height = 72;                          r += 2

        # ── Key Assumptions ───────────────────────────────────────────────────
        _section(r, "KEY ASSUMPTIONS (IVS 105)"); r += 1
        for assumption in ivsc_disclosure.key_assumptions:
            _row(r, "", f"• {assumption}"); r += 1
        r += 1

        # ── Limiting Conditions ───────────────────────────────────────────────
        _section(r, "LIMITING CONDITIONS"); r += 1
        for condition in ivsc_disclosure.limiting_conditions:
            _row(r, "", f"• {condition}"); r += 1
        r += 1

        # ── Market Conditions ─────────────────────────────────────────────────
        _section(r, "MARKET CONDITIONS (IVS 104)"); r += 1
        _row(r, "Market Conditions",  ivsc_disclosure.market_conditions_summary); r += 1
        _row(r, "Economic Conditions", ivsc_disclosure.economic_conditions);       r += 1
        _row(r, "Currency",            ivsc_disclosure.currency);                  r += 1
        if ivsc_disclosure.exchange_rate_basis:
            _row(r, "Exchange Rate Basis", ivsc_disclosure.exchange_rate_basis);   r += 1
        r += 1

        # ── Inspection ────────────────────────────────────────────────────────
        _section(r, "INSPECTION (IVS 105)"); r += 1
        _row(r, "Inspection Date",
             ivsc_disclosure.inspection_date.isoformat()
             if ivsc_disclosure.inspection_date else "—");           r += 1
        _row(r, "Inspection Notes", ivsc_disclosure.inspection_notes); r += 2

        # ── Appraiser Credentials ─────────────────────────────────────────────
        _section(r, "APPRAISER CREDENTIALS"); r += 1
        _row(r, "Appraiser Name",           ivsc_disclosure.appraiser_name);           r += 1
        _row(r, "Qualifications",           ivsc_disclosure.appraiser_qualifications); r += 1
        _row(r, "Declaration",              ivsc_disclosure.appraiser_declaration)
        ws.row_dimensions[r].height = 60;                                               r += 2

        # ── Standards Applied ─────────────────────────────────────────────────
        _section(r, "STANDARDS APPLIED"); r += 1
        ivsc_vals = [s.value for s in ivsc_disclosure.ivsc_standards_applied]
        _row(r, "IVSC Standards",
             "\n".join(f"• {v}" for v in ivsc_vals) if ivsc_vals else "—")
        ws.row_dimensions[r].height = max(15 * len(ivsc_vals), 15);  r += 1
        national = ivsc_disclosure.national_standards_applied
        _row(r, "National Standards",
             ", ".join(national) if national else "—");               r += 2

        # ── Certification ─────────────────────────────────────────────────────
        _section(r, "CERTIFICATION"); r += 1
        _row(r, "Certification Statement", ivsc_disclosure.certification_statement)
        ws.row_dimensions[r].height = 80;                             r += 1
        _row(r, "Date Certified",
             ivsc_disclosure.date_certified.isoformat()
             if ivsc_disclosure.date_certified else "—");             r += 1

    def sheet_cross_border(self, cb_disclosure) -> None:
        ws = self.workbook.create_sheet("Cross-Border", 9)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 25
        ws.column_dimensions["D"].width = 25

        _cb_section_font = Font(bold=True, color="FFFFFF", size=11)

        def _section(row: int, title: str) -> None:
            ws.merge_cells(f"A{row}:D{row}")
            cell            = ws.cell(row=row, column=1)
            cell.value      = title
            cell.fill       = _FILL_CB
            cell.font       = _cb_section_font
            cell.alignment  = _ALIGN_WRAP

        def _row(row: int, label: str, value, merge_value: bool = False) -> None:
            lc            = ws.cell(row=row, column=1)
            lc.value      = label
            lc.font       = _FONT_BOLD
            lc.alignment  = _ALIGN_WRAP
            if merge_value:
                ws.merge_cells(f"B{row}:D{row}")
            vc            = ws.cell(row=row, column=2)
            vc.value      = value if value is not None else "—"
            vc.alignment  = _ALIGN_WRAP

        # ── Title ─────────────────────────────────────────────────────────────
        ws.merge_cells("A1:D1")
        title_cell           = ws["A1"]
        title_cell.value     = "CROSS-BORDER COMPLIANCE DISCLOSURE"
        title_cell.fill      = _FILL_CB
        title_cell.font      = Font(bold=True, color="FFFFFF", size=14)
        title_cell.alignment = _ALIGN_CENTER
        ws.row_dimensions[1].height = 28

        ws.merge_cells("A2:D2")
        ws["A2"].value     = f"Report Date: {self.report_date}"
        ws["A2"].alignment = Alignment(horizontal="right")
        ws["A2"].font      = _FONT_MUTED

        r = 4
        # ── Currencies & Locations ────────────────────────────────────────────
        _section(r, "CURRENCIES & LOCATIONS"); r += 1
        _row(r, "Subject Property Currency",
             cb_disclosure.subject_property_currency.value);   r += 1
        _row(r, "Reporting Currency",
             cb_disclosure.reporting_currency.value);          r += 1
        _row(r, "Property Location Country",
             cb_disclosure.property_location_country);         r += 1
        _row(r, "Valuation Purpose Country",
             cb_disclosure.valuation_purpose_country);         r += 2

        # ── Exchange Rate Assumptions ─────────────────────────────────────────
        if cb_disclosure.exchange_rate_assumption:
            era = cb_disclosure.exchange_rate_assumption
            _section(r, "EXCHANGE RATE ASSUMPTIONS"); r += 1
            _row(r, "Exchange Rate",   era.format_rate());              r += 1
            _row(r, "Effective Date",  era.effective_date.isoformat()); r += 1
            _row(r, "Source",          era.source);                     r += 1
            _row(r, "Currency Risk",   era.currency_risk_disclosure,
                 merge_value=True)
            ws.row_dimensions[r].height = 48;                           r += 2

        # ── Currency Risk Statement ───────────────────────────────────────────
        _section(r, "CURRENCY RISK STATEMENT"); r += 1
        ws.merge_cells(f"A{r}:D{r}")
        risk_cell           = ws.cell(row=r, column=1)
        risk_cell.value     = cb_disclosure.currency_risk_statement
        risk_cell.alignment = _ALIGN_WRAP
        ws.row_dimensions[r].height = 60;                               r += 2

        # ── Multi-Currency Values ─────────────────────────────────────────────
        _section(r, "VALUATION IN MULTIPLE CURRENCIES"); r += 1
        _row(r, "Value (EGP)",
             f"EGP {cb_disclosure.primary_value_egp:,.0f}");   r += 1
        if cb_disclosure.primary_value_usd > 0:
            _row(r, "Value (USD)",
                 f"USD {cb_disclosure.primary_value_usd:,.0f}"); r += 1
        if cb_disclosure.primary_value_eur > 0:
            _row(r, "Value (EUR)",
                 f"EUR {cb_disclosure.primary_value_eur:,.0f}"); r += 1
        r += 1

        # ── Reporting Assumptions ─────────────────────────────────────────────
        _section(r, "REPORTING ASSUMPTIONS"); r += 1
        for idx, assumption in enumerate(cb_disclosure.reporting_assumptions, 1):
            ws.cell(row=r, column=1).value      = f"{idx}."
            ws.cell(row=r, column=1).font       = _FONT_BOLD
            ws.merge_cells(f"B{r}:D{r}")
            vc                 = ws.cell(row=r, column=2)
            vc.value           = assumption
            vc.alignment       = _ALIGN_WRAP
            ws.row_dimensions[r].height = 30;  r += 1
        r += 1

        # ── Certification ─────────────────────────────────────────────────────
        _section(r, "CERTIFICATION"); r += 1
        ws.merge_cells(f"A{r}:D{r}")
        cert_cell           = ws.cell(row=r, column=1)
        cert_cell.value     = cb_disclosure.certification_statement
        cert_cell.alignment = _ALIGN_WRAP
        ws.row_dimensions[r].height = 72

    def sheet_portfolio_summary(self, ps: Dict) -> None:
        """Portfolio Summary sheet — overview of all properties in a portfolio."""
        ws = self.workbook.create_sheet("Portfolio Summary")
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 22
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 15

        _port_sect_font = Font(bold=True, color="FFFFFF", size=11)

        def _section(row: int, title: str) -> None:
            ws.merge_cells(f"A{row}:D{row}")
            cell           = ws.cell(row=row, column=1)
            cell.value     = title
            cell.fill      = _FILL_PORTFOLIO
            cell.font      = _port_sect_font
            cell.alignment = _ALIGN_WRAP

        def _row(row: int, label: str, value, col_b: int = 2, merge_cd: bool = False) -> None:
            lc           = ws.cell(row=row, column=1)
            lc.value     = label
            lc.font      = _FONT_BOLD
            lc.alignment = _ALIGN_WRAP
            if merge_cd:
                ws.merge_cells(f"B{row}:D{row}")
            vc           = ws.cell(row=row, column=col_b)
            vc.value     = value if value is not None else "—"
            vc.alignment = _ALIGN_WRAP

        metrics = ps.get("metrics", {})

        # ── Title ─────────────────────────────────────────────────────────────
        ws.merge_cells("A1:D1")
        title_cell           = ws["A1"]
        title_cell.value     = "PORTFOLIO SUMMARY"
        title_cell.fill      = _FILL_PORTFOLIO
        title_cell.font      = Font(bold=True, color="FFFFFF", size=14)
        title_cell.alignment = _ALIGN_CENTER
        ws.row_dimensions[1].height = 28

        ws.merge_cells("A2:D2")
        ws["A2"].value     = f"Report Date: {self.report_date}"
        ws["A2"].alignment = Alignment(horizontal="right")
        ws["A2"].font      = _FONT_MUTED

        r = 4
        # ── Portfolio Overview ────────────────────────────────────────────────
        _section(r, "PORTFOLIO OVERVIEW"); r += 1
        _row(r, "Portfolio Name",
             ps.get("portfolio_name", "Unnamed"));                          r += 1
        _row(r, "Total Portfolio Value",
             f"EGP {metrics.get('total_portfolio_value', 0):,.0f}");        r += 1
        _row(r, "Number of Properties",
             metrics.get("number_of_properties", 0));                       r += 1
        _row(r, "Portfolio Cap Rate",
             f"{metrics.get('portfolio_cap_rate', 0) * 100:.2f}%");         r += 2

        # ── Value Distribution by Type ────────────────────────────────────────
        _section(r, "VALUE DISTRIBUTION BY TYPE"); r += 1
        type_vals = metrics.get("value_by_type", {})
        type_pcts = metrics.get("type_percentages", {})
        for pt in sorted(type_vals):
            ws.cell(row=r, column=1).value = f"{pt.title()}:"
            ws.cell(row=r, column=1).font  = _FONT_BOLD
            ws.cell(row=r, column=2).value = f"EGP {type_vals[pt]:,.0f}"
            ws.cell(row=r, column=3).value = f"{type_pcts.get(pt, 0) * 100:.1f}%"
            r += 1
        r += 1

        # ── Income Analysis ───────────────────────────────────────────────────
        _section(r, "INCOME ANALYSIS"); r += 1
        _row(r, "Total Annual Gross Income",
             f"EGP {metrics.get('total_annual_gross_income', 0):,.0f}");    r += 1
        _row(r, "Total Annual NOI",
             f"EGP {metrics.get('total_annual_noi', 0):,.0f}");             r += 1
        _row(r, "Portfolio NOI Margin",
             f"{metrics.get('portfolio_noi_margin', 0) * 100:.2f}%");       r += 2

        # ── Risk & Diversification ────────────────────────────────────────────
        _section(r, "RISK & DIVERSIFICATION"); r += 1
        cr = metrics.get("concentration_ratio", 0)
        hi = metrics.get("herfindahl_index", 0)
        ds = round(1 - hi, 4)
        _row(r, "Concentration Ratio",      f"{cr * 100:.2f}%");            r += 1
        ws.cell(row=r - 1, column=3).value = "(Lower = more diversified)"
        _row(r, "Herfindahl Index",         f"{hi:.4f}");                   r += 1
        _row(r, "Diversification Score",    f"{ds:.4f}");                   r += 1
        ws.cell(row=r - 1, column=3).value = "(1.0 = perfectly diversified)"
        r += 1

        # ── Valuation Confidence ──────────────────────────────────────────────
        _section(r, "VALUATION CONFIDENCE"); r += 1
        high_val = metrics.get("high_confidence_value", 0)
        _row(r, "High Confidence",
             f"{metrics.get('high_confidence_count', 0)} properties  "
             f"(EGP {high_val:,.0f})");                                     r += 1
        _row(r, "Medium Confidence",
             f"{metrics.get('medium_confidence_count', 0)} properties");    r += 1
        _row(r, "Low Confidence",
             f"{metrics.get('low_confidence_count', 0)} properties");       r += 2

        # ── Property Listing ──────────────────────────────────────────────────
        _section(r, "PROPERTY LISTING"); r += 1
        for col, hdr in enumerate(("Property Name", "Type", "Value (EGP)", "Weight %"), 1):
            cell       = ws.cell(row=r, column=col)
            cell.value = hdr
            cell.font  = _FONT_BOLD
            cell.fill  = _FILL_PORT_COL
        r += 1
        for prop in ps.get("properties", []):
            ws.cell(row=r, column=1).value = prop.get("property_name", "")
            ws.cell(row=r, column=2).value = prop.get("property_type",  "")
            ws.cell(row=r, column=3).value = f"{prop.get('valuation_value', 0):,.0f}"
            ws.cell(row=r, column=4).value = f"{prop.get('portfolio_weight', 0) * 100:.2f}%"
            r += 1

    def sheet_portfolio_performance(self, perf: Dict) -> None:
        """Portfolio Performance sheet — scenario comparison + risk summary (Phase 11.3)."""
        ws = self.workbook.create_sheet("Portfolio Performance")

        for col, width in zip("ABCDEFGH", (24, 22, 14, 22, 14, 16, 14, 14)):
            ws.column_dimensions[col].width = width

        _port_sect_font = Font(bold=True, color="FFFFFF", size=12)

        def _section(row: int, title: str) -> None:
            ws.merge_cells(f"A{row}:H{row}")
            cell           = ws.cell(row=row, column=1)
            cell.value     = title
            cell.fill      = _FILL_PORTFOLIO
            cell.font      = _port_sect_font
            cell.alignment = _ALIGN_WRAP

        def _kv(row: int, label: str, value) -> None:
            lc           = ws.cell(row=row, column=1)
            lc.value     = label
            lc.font      = _FONT_BOLD
            lc.alignment = _ALIGN_WRAP
            vc           = ws.cell(row=row, column=2)
            vc.value     = value if value is not None else "—"
            vc.alignment = _ALIGN_WRAP

        # Safe accessor — conditional keys may be absent when no scenarios ran
        def _g(key, default=None):
            return perf.get(key, default)

        # ── Title ─────────────────────────────────────────────────────────────
        ws.merge_cells("A1:H1")
        tc           = ws["A1"]
        tc.value     = "PORTFOLIO PERFORMANCE ANALYSIS"
        tc.fill      = _FILL_PORTFOLIO
        tc.font      = Font(bold=True, color="FFFFFF", size=14)
        tc.alignment = _ALIGN_CENTER
        ws.row_dimensions[1].height = 28

        ws.merge_cells("A2:H2")
        ws["A2"].value     = f"Report Date: {self.report_date}"
        ws["A2"].alignment = Alignment(horizontal="right")
        ws["A2"].font      = _FONT_MUTED

        r = 4

        # ── Section 1: Baseline Metrics ───────────────────────────────────────
        _section(r, "BASELINE METRICS"); r += 1
        _kv(r, "Portfolio Name",        _g("portfolio_name", "—"));                   r += 1
        _kv(r, "Base Portfolio Value",  f"EGP {_g('base_portfolio_value', 0):,.0f}");     r += 1
        _kv(r, "Base Total NOI",        f"EGP {_g('base_total_noi', 0):,.0f}");           r += 1
        _kv(r, "Base Cap Rate",         f"{_g('base_cap_rate', 0) * 100:.2f}%");          r += 1
        _kv(r, "Diversification Score", f"{_g('diversification_score', 0):.4f}");        r += 1
        _kv(r, "Scenario Count",        _g("scenario_count", 0));                         r += 2

        # ── Section 2: Scenario Table ─────────────────────────────────────────
        _section(r, "SCENARIO ANALYSIS"); r += 1

        col_headers = [
            "Scenario", "Stressed Value (EGP)", "Value Δ%",
            "Stressed NOI (EGP)", "NOI Δ%", "Stressed Cap Rate",
            "NOI Margin", "IRR Estimate",
        ]
        for col_i, hdr in enumerate(col_headers, 1):
            cell           = ws.cell(row=r, column=col_i)
            cell.value     = hdr
            cell.font      = _FONT_BOLD
            cell.fill      = _FILL_PORT_COL
            cell.alignment = _ALIGN_WRAP
            cell.border    = _BORDER_THIN
        r += 1

        scenarios = _g("scenarios") or []
        if scenarios:
            for sc in scenarios:
                row_vals = [
                    sc.get("scenario_label", ""),
                    f"EGP {sc.get('stressed_portfolio_value', 0):,.0f}",
                    f"{sc.get('value_change_pct', 0) * 100:.2f}%",
                    f"EGP {sc.get('stressed_total_noi', 0):,.0f}",
                    f"{sc.get('noi_change_pct', 0) * 100:.2f}%",
                    f"{sc.get('stressed_cap_rate', 0) * 100:.2f}%",
                    f"{sc.get('stressed_noi_margin', 0) * 100:.2f}%",
                    f"{sc.get('irr_estimate', 0) * 100:.2f}%",
                ]
                for col_i, v in enumerate(row_vals, 1):
                    cell           = ws.cell(row=r, column=col_i)
                    cell.value     = v
                    cell.alignment = _ALIGN_WRAP
                    cell.border    = _BORDER_THIN
                r += 1
        else:
            ws.merge_cells(f"A{r}:H{r}")
            cell           = ws.cell(row=r, column=1)
            cell.value     = "No scenario data available"
            cell.font      = _FONT_MUTED
            cell.alignment = _ALIGN_CENTER
            r += 1

        r += 1  # gap before risk section

        # ── Section 3: Risk Summary ────────────────────────────────────────────
        _section(r, "RISK SUMMARY"); r += 1

        min_val = _g("min_stressed_value")
        max_val = _g("max_stressed_value")
        min_noi = _g("min_stressed_noi")
        max_noi = _g("max_stressed_noi")
        var_pct = _g("value_at_risk_pct")

        _kv(r, "Min Stressed Value",
            f"EGP {min_val:,.0f}" if min_val is not None else "—");   r += 1
        _kv(r, "Max Stressed Value",
            f"EGP {max_val:,.0f}" if max_val is not None else "—");   r += 1
        _kv(r, "Min Stressed NOI",
            f"EGP {min_noi:,.0f}" if min_noi is not None else "—");   r += 1
        _kv(r, "Max Stressed NOI",
            f"EGP {max_noi:,.0f}" if max_noi is not None else "—");   r += 1
        _kv(r, "Scenario-Implied Downside %",
            f"{var_pct * 100:.2f}%" if var_pct is not None else "—"); r += 1

    # ──────────────────────────────────────────────────────────────────────────
    # Style helper
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _should_include_sheet(sheet_name: str, report_style: str) -> bool:
        """Return False for advanced-analytics sheets when report_style == 'legacy'."""
        if report_style == "legacy":
            return sheet_name.strip().lower() not in _LEGACY_EXCLUDED_SHEETS
        return True

    # ──────────────────────────────────────────────────────────────────────────
    # Advanced-analytics sheets (detailed only — excluded from legacy)
    # ──────────────────────────────────────────────────────────────────────────

    def _adv_sheet(self, ar_title: str, en_title: str, description: str) -> None:
        """Create an advanced-analytics sheet with a standard header."""
        ws = self.workbook.create_sheet(ar_title)
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 55
        ws.merge_cells("A1:B1")
        tc           = ws["A1"]
        tc.value     = f"{ar_title}  —  {en_title}"
        tc.font      = _FONT_TITLE
        tc.fill      = _FILL_HEADER
        tc.font      = Font(bold=True, color="FFFFFF", size=13)
        tc.alignment = _ALIGN_CENTER
        ws.row_dimensions[1].height = 26

        ws.merge_cells("A2:B2")
        ws["A2"].value     = f"Report Date: {self.report_date}"
        ws["A2"].font      = _FONT_MUTED
        ws["A2"].alignment = Alignment(horizontal="right")

        ws.merge_cells("A4:B4")
        desc_cell           = ws["A4"]
        desc_cell.value     = description
        desc_cell.alignment = _ALIGN_WRAP
        ws.row_dimensions[4].height = 45

        if self.result is not None:
            md = self.result.metadata or {}
            ws.cell(row=6, column=1).value = "Asset Type"
            ws.cell(row=6, column=1).font  = _FONT_BOLD
            ws.cell(row=6, column=2).value = self.result.asset_type
            ws.cell(row=7, column=1).value = "Primary Value (EGP)"
            ws.cell(row=7, column=1).font  = _FONT_BOLD
            ws.cell(row=7, column=2).value = float(self.result.primary_value) if self.result.primary_value else 0
            self._apply_currency_format(ws, 7, 7, 2)
            ws.cell(row=8, column=1).value = "Confidence"
            ws.cell(row=8, column=1).font  = _FONT_BOLD
            ws.cell(row=8, column=2).value = self.result.confidence
            ws.cell(row=9, column=1).value = "Location"
            ws.cell(row=9, column=1).font  = _FONT_BOLD
            ws.cell(row=9, column=2).value = md.get("location") or md.get("address") or "—"

    def sheet_spatial_analysis(self) -> None:
        self._adv_sheet(
            "التحليل المكاني", "Spatial Analysis",
            "يحتوي هذا القسم على التحليل المكاني للعقارات المقارنة والموقع الجغرافي "
            "للأصل. يشمل خرائط الكثافة السعرية، نصف قطر البحث، وتأثير الموقع على القيمة.",
        )

    def sheet_multiple_regression(self) -> None:
        ws_name = "الانحدار المتعدد"
        self._adv_sheet(
            ws_name, "Multiple Regression",
            "يحتوي هذا القسم على نموذج الانحدار المتعدد لتقدير القيمة. يشمل المتغيرات "
            "المستقلة (المساحة، الموقع، العمر)، معاملات الانحدار، ومعامل التحديد R².",
        )
        if self.result is not None:
            ws  = self.workbook[ws_name]
            md  = self.result.metadata or {}
            row = 11
            ws.cell(row=row, column=1).value = "Inputs (Three Approaches)"; row += 1
            for key, label in (("comparable", "Comparable"), ("cost", "Cost"), ("income", "Income")):
                ws.cell(row=row, column=1).value = label
                ws.cell(row=row, column=1).font  = _FONT_BOLD
                ws.cell(row=row, column=2).value = float(md.get(key) or 0)
                self._apply_currency_format(ws, row, row, 2)
                row += 1

    def sheet_real_options(self) -> None:
        self._adv_sheet(
            "الخيارات الحقيقية", "Real Options",
            "يحتوي هذا القسم على تحليل الخيارات الحقيقية للأصل. يشمل قيمة خيار التطوير، "
            "خيار التأخير، خيار التوسع، وخيار التخلي مع التقلبات الضمنية في السوق.",
        )

    def sheet_executive_dashboard(self) -> None:
        ws_name = "لوحة القيادة التنفيذية"
        self._adv_sheet(
            ws_name, "Executive Dashboard",
            "لوحة القيادة التنفيذية — ملخص المؤشرات الرئيسية للتقرير للإطلاع السريع.",
        )
        if self.result is not None:
            ws  = self.workbook[ws_name]
            md  = self.result.metadata or {}
            row = 11
            headers = ["Metric", "Value"]
            self._apply_header_style(ws, row, 2)
            for col, h in enumerate(headers, 1):
                ws.cell(row=row, column=col).value = h
            row += 1
            for label, val in (
                ("Asset Type",      self.result.asset_type),
                ("Primary Purpose", self.result.primary_purpose),
                ("Confidence",      self.result.confidence),
                ("Comparable (EGP)", float(md.get("comparable") or 0)),
                ("Cost (EGP)",       float(md.get("cost")       or 0)),
                ("Income (EGP)",     float(md.get("income")     or 0)),
                ("Final Value (EGP)", float(self.result.primary_value) if self.result.primary_value else 0),
            ):
                ws.cell(row=row, column=1).value = label
                ws.cell(row=row, column=1).font  = _FONT_BOLD
                ws.cell(row=row, column=2).value = val
                if "EGP" in label:
                    self._apply_currency_format(ws, row, row, 2)
                row += 1

    def sheet_neural_networks(self) -> None:
        self._adv_sheet(
            "الشبكات العصبية", "Neural Networks",
            "يحتوي هذا القسم على نموذج الشبكة العصبية الاصطناعية لتقدير القيمة السوقية. "
            "يشمل البنية المعمارية للنموذج، الطبقات المخفية، دالة التفعيل، ومقاييس الأداء.",
        )

    def sheet_time_series(self) -> None:
        ws_name = "السلاسل الزمنية"
        self._adv_sheet(
            ws_name, "Time Series",
            "يحتوي هذا القسم على تحليل السلاسل الزمنية لأسعار العقارات في المنطقة. "
            "يشمل اتجاهات الأسعار التاريخية، نماذج ARIMA، والتنبؤ بالأسعار المستقبلية.",
        )
        if self.result is not None:
            ws  = self.workbook[ws_name]
            row = 11
            ws.cell(row=row, column=1).value = "Valuation Date"
            ws.cell(row=row, column=1).font  = _FONT_BOLD
            ws.cell(row=row, column=2).value = self.report_date

    def sheet_market_intelligence(self) -> None:
        self._adv_sheet(
            "استخبارات السوق", "Market Intelligence",
            "يحتوي هذا القسم على تقرير استخبارات السوق العقاري. يشمل مؤشرات الطلب والعرض، "
            "متوسطات أسعار المنطقة، حجم الصفقات، وتحليل المنافسين.",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    def build(self, filename: str, ivsc_disclosure=None,
              cross_border_disclosure=None, portfolio_summary=None,
              portfolio_performance=None,
              report_style: str = "legacy") -> str:
        """Build all sheets and save to filename. Returns the filename."""
        # ── Try professional template export (individual valuation) ───────────
        # Only attempted when report_style == "professional_template".
        # Any failure silently falls through to the existing builder below.
        if self.result is not None and report_style == "professional_template":
            try:
                from pathlib import Path as _Path
                try:
                    from reports.excel_template_renderer import (
                        INDIVIDUAL_VALUATION_TEMPLATE as _TPL,
                        build_individual_valuation_report as _build_tpl,
                    )
                except ImportError:
                    from core_engine.reports.excel_template_renderer import (  # type: ignore
                        INDIVIDUAL_VALUATION_TEMPLATE as _TPL,
                        build_individual_valuation_report as _build_tpl,
                    )
                if _TPL.is_file():
                    _r    = self.result
                    _meta = _r.metadata or {}
                    _context = {
                        "report_date":       self.report_date,
                        "valuation_date":    _meta.get("valuation_date") or self.report_date,
                        "client_name":       _meta.get("client_name") or _meta.get("borrower_name") or "N/A",
                        "property_type":     _r.asset_type,
                        "location":          _meta.get("location") or _meta.get("address") or "N/A",
                        "area":              _meta.get("area") or _meta.get("floor_area_m2") or "",
                        "valuation_purpose": _r.primary_purpose,
                        "market_value":      float(_r.primary_value) if _r.primary_value else 0,
                        "comparative_value": float(_meta.get("comparable") or 0),
                        "cost_value":        float(_meta.get("cost") or 0),
                        "income_value":      float(_meta.get("income") or 0),
                        "final_value":       float(_r.primary_value) if _r.primary_value else 0,
                        "confidence":        _r.confidence,
                        "reviewer_name":     _meta.get("reviewer_name") or _meta.get("appraiser_name") or "N/A",
                        "report_id":         _meta.get("report_id") or "N/A",
                    }
                    _tables: Dict[str, list] = {}
                    if _r.audit_trail:
                        _tables["audit_trail"] = [
                            {
                                "Step":       e.step_name,
                                "Formula":    e.formula or "",
                                "References": ", ".join(e.references or []),
                            }
                            for e in _r.audit_trail
                        ]
                    if _r.issues:
                        _tables["issues"] = [
                            {"Severity": i.severity, "Code": i.code, "Message": i.message}
                            for i in _r.issues
                        ]
                    _methods = [
                        {
                            "Approach":    label,
                            "Value (EGP)": float(_meta.get(key) or 0),
                            "Weight":      (_r.weights_applied or {}).get(key, ""),
                        }
                        for key, label in (
                            ("comparable", "Comparable Sales"),
                            ("cost",       "Cost Approach"),
                            ("income",     "Income Approach"),
                        )
                        if _meta.get(key)
                    ]
                    if _methods:
                        _tables["valuation_methods"] = _methods
                    _comps = _meta.get("comparables") or _meta.get("comparable_sales") or []
                    if _comps:
                        _tables["comparables"] = [
                            dict(c) if isinstance(c, dict) else {"Value": str(c)}
                            for c in _comps[:20]
                        ]
                    if _r.disclosures:
                        _tables["assumptions"] = [{"Reference": d} for d in _r.disclosures]

                    # Use .xlsm extension when the template is .xlsm but
                    # the requested filename was .xlsx (bridge_api default).
                    _req   = _Path(filename)
                    _out_path = (
                        _req.with_suffix(".xlsm")
                        if _TPL.suffix.lower() == ".xlsm"
                        and _req.suffix.lower() == ".xlsx"
                        else _req
                    )
                    _out = _build_tpl(
                        output_path=str(_out_path),
                        context=_context,
                        tables=_tables,
                    )
                    if _out is not None and _out_path.is_file():
                        return str(_out_path)
            except Exception:
                pass
        # ─────────────────────────────────────────────────────────────────────

        if self.result is not None:
            self.sheet_summary()
            self.sheet_three_approaches()
            self.sheet_weights_analysis()
            self.sheet_audit_trail()
            self.sheet_property_details()
            self.sheet_disclosures()
            self.sheet_issues_warnings()
            self.sheet_certification()
            if ivsc_disclosure is not None:
                self.sheet_ivsc_compliance(ivsc_disclosure)
            if cross_border_disclosure is not None:
                self.sheet_cross_border(cross_border_disclosure)
            # ── Advanced-analytics sheets (detailed only) ─────────────────────
            _inc = self._should_include_sheet
            if _inc("التحليل المكاني", report_style):
                self.sheet_spatial_analysis()
            if _inc("الانحدار المتعدد", report_style):
                self.sheet_multiple_regression()
            if _inc("الخيارات الحقيقية", report_style):
                self.sheet_real_options()
            if _inc("لوحة القيادة التنفيذية", report_style):
                self.sheet_executive_dashboard()
            if _inc("الشبكات العصبية", report_style):
                self.sheet_neural_networks()
            if _inc("السلاسل الزمنية", report_style):
                self.sheet_time_series()
            if _inc("استخبارات السوق", report_style):
                self.sheet_market_intelligence()
        if portfolio_summary is not None:
            self.sheet_portfolio_summary(portfolio_summary)
        if portfolio_performance is not None:
            self.sheet_portfolio_performance(portfolio_performance)
        self.workbook.save(filename)
        return filename
