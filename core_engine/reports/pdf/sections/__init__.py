"""
PDF report sections — composed from pdf_components primitives.

Each section module exposes a single render_<name>(pdf, *, ...) function
that draws its content onto an existing FPDF page, advancing the cursor.
Sections never create FPDF or call output(); the pdf_engine orchestrates.
"""
