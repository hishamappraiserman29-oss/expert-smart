"""
seed_data.py — Phase 22 Initial Knowledge Base Entries

Covers EGVS (residential, commercial), IVSC (fair value), CBE (LTV, Basel III),
market insights (Cairo 2024), methodology (comparable sales), and case studies.

Usage:
    from knowledge.seed_data import get_seed_entries
    entries = get_seed_entries()
"""

from __future__ import annotations

from typing import List

from .knowledge_base import KnowledgeCategory, KnowledgeEntry, LanguageCode


def get_seed_entries() -> List[KnowledgeEntry]:
    """Return the initial list of domain knowledge entries."""

    return [
        # ── EGVS ─────────────────────────────────────────────────────────────

        KnowledgeEntry(
            id="egvs_001",
            title="EGVS Residential Property Valuation",
            category=KnowledgeCategory.EGVS,
            content=(
                "Egyptian Valuation Standards (EGVS) Part 1 covers residential property valuation.\n\n"
                "Key principles:\n"
                "1. Comparative approach: Use recent comparable sales in the same area.\n"
                "2. Market conditions adjustment: Reflect current market supply and demand.\n"
                "3. Property characteristics: Account for size, condition, and location.\n"
                "4. Comparable selection: Use properties sold within 12 months.\n"
                "5. Adjustment methodology: Apply percentage adjustments for differences.\n\n"
                "For residential properties in Cairo:\n"
                "- Weight comparable approach: 60-70%.\n"
                "- Use 5-10 comparable properties.\n"
                "- Adjust for location within district.\n"
                "- Account for parking, utilities, and view.\n"
                "- Final value should be within 10% of the comparable range."
            ),
            language=LanguageCode.ENGLISH,
            tags=["residential", "comparable", "cairo", "adjustment"],
            source="EGVS 2023",
            version="1.0",
        ),

        KnowledgeEntry(
            id="egvs_002",
            title="EGVS Commercial Property Valuation",
            category=KnowledgeCategory.EGVS,
            content=(
                "Egyptian Valuation Standards (EGVS) commercial property valuation.\n\n"
                "Approaches for commercial properties:\n"
                "1. Comparative Approach (60-70%): Recent sales of similar commercial properties.\n"
                "2. Income Approach (20-30%): Rental income capitalisation.\n"
                "3. Cost Approach (10-20%): Replacement cost of building.\n\n"
                "For commercial properties in Cairo:\n"
                "- Compare with recent office/retail sales.\n"
                "- Consider rental yield (typically 4-6% in Cairo).\n"
                "- Account for location (CBD vs. suburban).\n"
                "- Evaluate tenant quality and lease terms.\n"
                "- Final value = Annual NOI / Cap Rate.\n\n"
                "Commercial property premiums:\n"
                "- Prime location (Heliopolis, Zamalek): 20-30% premium.\n"
                "- Secondary location (Nasr City, October City): standard rates.\n"
                "- Remote location: 10-20% discount."
            ),
            language=LanguageCode.ENGLISH,
            tags=["commercial", "income", "cairo"],
            source="EGVS 2023",
            version="1.0",
        ),

        KnowledgeEntry(
            id="egvs_003",
            title="EGVS Land Valuation Guidelines",
            category=KnowledgeCategory.EGVS,
            content=(
                "EGVS guidelines for land and development site valuation.\n\n"
                "Land valuation approaches:\n"
                "1. Comparative approach: Sales of similar parcels in the same area.\n"
                "2. Residual method: Gross Development Value minus development costs.\n"
                "3. Capitalisation of ground rent: For leasehold land.\n\n"
                "Key factors for land valuation:\n"
                "- Planning permissions and zoning.\n"
                "- Infrastructure availability (utilities, roads).\n"
                "- Topography and soil conditions.\n"
                "- Access and frontage.\n"
                "- Permitted floor-area ratio (FAR).\n\n"
                "Residual method formula:\n"
                "Land Value = GDV - (Construction Costs + Developer Profit + Finance Costs)\n\n"
                "GDV = Gross Development Value based on comparable completed projects."
            ),
            language=LanguageCode.ENGLISH,
            tags=["land", "residual", "development", "zoning"],
            source="EGVS 2023",
            version="1.0",
        ),

        # ── IVSC ─────────────────────────────────────────────────────────────

        KnowledgeEntry(
            id="ivsc_001",
            title="IVSC Fair Value Definition",
            category=KnowledgeCategory.IVSC,
            content=(
                "International Valuation Standards Committee (IVSC) Fair Value Definition.\n\n"
                "Fair value is the estimated price for an asset or liability in an orderly "
                "transaction between market participants at the measurement date.\n\n"
                "Fair Value Hierarchy (IAS 13 / IFRS 13):\n"
                "1. Level 1 (Highest priority): Quoted prices in active markets.\n"
                "2. Level 2: Observable market data (comparables, rental evidence).\n"
                "3. Level 3 (Lowest priority): Unobservable data (entity assumptions).\n\n"
                "For Egyptian real estate valuations:\n"
                "- Residential: Usually Level 2 (comparable sales).\n"
                "- Commercial: Level 2-3 (mix of comparables and income).\n"
                "- Development land: Level 3 (valuation models).\n\n"
                "Fair value vs. Market value:\n"
                "- Fair value: Theoretical/accounting basis.\n"
                "- Market value: Practical transaction basis.\n"
                "- Difference can be 5-15% depending on market.\n\n"
                "IVSC requires:\n"
                "- Detailed valuation basis disclosure.\n"
                "- Assumptions clearly stated.\n"
                "- Uncertainty quantification.\n"
                "- Compliance with local standards."
            ),
            language=LanguageCode.ENGLISH,
            tags=["fair_value", "ifrs13", "standards"],
            source="IVSC Standards 2022",
            version="1.0",
        ),

        KnowledgeEntry(
            id="ivsc_002",
            title="IVSC Market Value Definition and Basis",
            category=KnowledgeCategory.IVSC,
            content=(
                "IVSC definition of Market Value (IVS 104).\n\n"
                "Market Value: The estimated amount for which an asset or liability should "
                "exchange on the valuation date between a willing buyer and a willing seller "
                "in an arm's-length transaction, after proper marketing, where the parties had "
                "each acted knowledgeably, prudently, and without compulsion.\n\n"
                "Key conditions:\n"
                "1. Willing buyer and willing seller — no compulsion.\n"
                "2. Arm's-length transaction — independent parties.\n"
                "3. Proper marketing — adequate exposure to the market.\n"
                "4. Knowledgeable parties — both aware of relevant facts.\n"
                "5. Specific valuation date.\n\n"
                "For Egyptian residential properties:\n"
                "- Market exposure: Minimum 3-6 months.\n"
                "- Marketing method: Listing on major portals (Aqarmap, Property Finder).\n"
                "- Evidence: Signed sale contracts, not asking prices."
            ),
            language=LanguageCode.ENGLISH,
            tags=["market_value", "ivs104", "definition"],
            source="IVSC Standards 2022",
            version="1.0",
        ),

        # ── CBE ──────────────────────────────────────────────────────────────

        KnowledgeEntry(
            id="cbe_001",
            title="CBE Real Estate Financing Regulations",
            category=KnowledgeCategory.CBE,
            content=(
                "Central Bank of Egypt (CBE) Regulations for Real Estate Financing (2023).\n\n"
                "Loan-to-Value (LTV) Limits:\n"
                "- Residential: Max 80% LTV.\n"
                "- Commercial: Max 70% LTV.\n"
                "- Land: Max 60% LTV.\n\n"
                "Valuation Requirements for Mortgage:\n"
                "1. Licensed appraiser must conduct valuation.\n"
                "2. Valuation valid for 6 months maximum.\n"
                "3. Update required if property condition changes.\n"
                "4. Consider market conditions at time of appraisal.\n"
                "5. Conservative approach — use lower of appraised/purchase price.\n\n"
                "Risk Weights (Basel III):\n"
                "- Residential (LTV <= 80%): 35% risk weight.\n"
                "- Residential (LTV > 80%): 100% risk weight.\n"
                "- Commercial (LTV <= 60%): 50% risk weight.\n"
                "- Commercial (LTV > 60%): 100% risk weight.\n\n"
                "CBE reporting requirements:\n"
                "- Quarterly reporting of real estate portfolio.\n"
                "- Mark-to-market for investment properties.\n"
                "- Disclosures required for concentration risk.\n"
                "- Provision for impairment on distressed properties."
            ),
            language=LanguageCode.ENGLISH,
            tags=["cbe", "mortgage", "ltv", "regulation"],
            source="CBE Circular 208/2023",
            version="1.0",
        ),

        KnowledgeEntry(
            id="cbe_002",
            title="CBE Basel III Capital Requirements for Real Estate",
            category=KnowledgeCategory.CBE,
            content=(
                "CBE implementation of Basel III capital requirements affecting real estate.\n\n"
                "Capital adequacy ratios:\n"
                "- CET1 (Common Equity Tier 1): Minimum 4.5%.\n"
                "- Tier 1 Capital: Minimum 6.0%.\n"
                "- Total Capital Ratio: Minimum 8.0%.\n"
                "- Capital Conservation Buffer: 2.5%.\n\n"
                "Real estate concentration limits:\n"
                "- Residential mortgage book: Max 20% of total loan portfolio.\n"
                "- Commercial real estate: Max 15% of total loan portfolio.\n"
                "- Single borrower limit: Max 15% of Tier 1 capital.\n\n"
                "Stress testing requirements:\n"
                "- Annual stress test of real estate portfolio.\n"
                "- Scenario: 30% price decline in residential.\n"
                "- Scenario: 40% price decline in commercial.\n"
                "- Banks must maintain capital adequacy under stress scenarios."
            ),
            language=LanguageCode.ENGLISH,
            tags=["cbe", "basel3", "capital", "stress_test"],
            source="CBE Basel III Implementation 2023",
            version="1.0",
        ),

        # ── Market Insights ───────────────────────────────────────────────────

        KnowledgeEntry(
            id="market_cairo_001",
            title="Cairo Real Estate Market Insights (2024)",
            category=KnowledgeCategory.MARKET_INSIGHT,
            content=(
                "Cairo Real Estate Market Overview (Q1 2024).\n\n"
                "Market Conditions:\n"
                "- Residential prices: EGP 25,000-50,000 per sqm (prime locations).\n"
                "- Commercial rents: $400-800 per sqm per year.\n"
                "- Capitalisation rates: 5-7% for stabilised assets.\n"
                "- Vacancy rates: 8-12% in commercial spaces.\n\n"
                "Location Premiums (vs. average):\n"
                "- Zamalek: +40-50%.\n"
                "- Heliopolis: +25-35%.\n"
                "- New Cairo: +15-25%.\n"
                "- Nasr City: +5-10%.\n"
                "- October City: Comparable baseline.\n"
                "- Giza: -5-15%.\n\n"
                "Price Trends:\n"
                "- Residential: +8-12% YoY growth.\n"
                "- Commercial: +3-5% YoY growth.\n"
                "- Land: +5-8% YoY growth.\n\n"
                "Market Drivers:\n"
                "1. Currency fluctuations (EGP/USD).\n"
                "2. Interest rate changes (CBE policy).\n"
                "3. New developments and infrastructure.\n"
                "4. Expatriate demand.\n"
                "5. Domestic savings growth.\n\n"
                "Forecast: Steady growth expected with some volatility in 2024-2025."
            ),
            language=LanguageCode.ENGLISH,
            tags=["market", "cairo", "prices", "trends"],
            source="Market Report Q1 2024",
            version="1.0",
        ),

        KnowledgeEntry(
            id="market_cairo_002",
            title="New Cairo and October City Residential Market (2024)",
            category=KnowledgeCategory.MARKET_INSIGHT,
            content=(
                "New Cairo and 6th October City Residential Market Analysis (2024).\n\n"
                "New Cairo:\n"
                "- Average price: EGP 30,000-45,000 per sqm in compounds.\n"
                "- Annual price growth: 10-15%.\n"
                "- Key developments: Madinaty, Hyde Park, Mountain View.\n"
                "- Demand drivers: Young professionals, suburban lifestyle.\n"
                "- Rental yield: 3.5-4.5%.\n\n"
                "6th October City:\n"
                "- Average price: EGP 18,000-28,000 per sqm.\n"
                "- Annual price growth: 5-8%.\n"
                "- Key developments: Westown, Zed, Palm Hills.\n"
                "- Demand drivers: Affordable alternative to central Cairo.\n"
                "- Rental yield: 4.0-5.0%.\n\n"
                "Comparison:\n"
                "- New Cairo commands 20-30% premium over October City.\n"
                "- Infrastructure quality drives the premium.\n"
                "- Both markets show strong demand from end-users."
            ),
            language=LanguageCode.ENGLISH,
            tags=["new_cairo", "october_city", "residential", "market"],
            source="Market Report Q1 2024",
            version="1.0",
        ),

        # ── Case Studies ──────────────────────────────────────────────────────

        KnowledgeEntry(
            id="case_residential_001",
            title="Case Study: Residential Valuation in New Cairo",
            category=KnowledgeCategory.CASE_STUDY,
            content=(
                "Case Study: 200 sqm Apartment in New Cairo.\n\n"
                "Subject Property:\n"
                "- Type: Apartment.\n"
                "- Location: New Cairo compound development.\n"
                "- Area: 200 sqm.\n"
                "- Bedrooms: 3, Bathrooms: 2.\n"
                "- Year Built: 2018. Condition: Good.\n\n"
                "Comparable Properties:\n"
                "1. Same compound: EGP 9,000/sqm.\n"
                "2. Nearby compound (premium): EGP 9,500/sqm.\n"
                "3. Nearby compound (standard): EGP 8,500/sqm.\n"
                "4. Older unit: EGP 8,000/sqm.\n\n"
                "Adjustments:\n"
                "- Base: EGP 8,750/sqm.\n"
                "- Age (+5%): EGP 9,188/sqm.\n"
                "- Condition (-2%): EGP 9,004/sqm.\n"
                "- Location (+3%): EGP 9,274/sqm.\n\n"
                "Final Value: EGP 1,854,800 (EGP 9,274 x 200 sqm).\n"
                "Rental yield: 3.5-4%. Cap rate: 4.2%."
            ),
            language=LanguageCode.ENGLISH,
            tags=["case_study", "residential", "new_cairo"],
            source="Expert Smart Database",
            version="1.0",
        ),

        KnowledgeEntry(
            id="case_commercial_001",
            title="Case Study: Commercial Office Valuation in Heliopolis",
            category=KnowledgeCategory.CASE_STUDY,
            content=(
                "Case Study: 500 sqm Office in Heliopolis Business District.\n\n"
                "Subject Property:\n"
                "- Type: Office space. Location: Heliopolis Business Center.\n"
                "- Area: 500 sqm. Tenant: 3-year lease at EGP 2,000/sqm/year.\n"
                "- Condition: Class A.\n\n"
                "Income Approach:\n"
                "- Annual Rent: 2,000 x 500 = EGP 1,000,000.\n"
                "- Operating Expenses (20%): EGP 200,000.\n"
                "- NOI: EGP 800,000.\n"
                "- Cap rate (Heliopolis premium): 5.5%.\n"
                "- Value = 800,000 / 0.055 = EGP 14,545,455.\n\n"
                "Comparable check: EGP 28,000/sqm in area vs EGP 29,091/sqm implied.\n"
                "Final Value: EGP 14,545,455. Confidence: High."
            ),
            language=LanguageCode.ENGLISH,
            tags=["case_study", "commercial", "heliopolis", "income"],
            source="Expert Smart Database",
            version="1.0",
        ),

        # ── Methodology ──────────────────────────────────────────────────────

        KnowledgeEntry(
            id="methodology_comparable_001",
            title="Comparable Sales Approach - Methodology",
            category=KnowledgeCategory.METHODOLOGY,
            content=(
                "Comparable Sales Approach - Step-by-Step Methodology.\n\n"
                "Step 1: Market Analysis\n"
                "- Define competitive market for subject property.\n"
                "- Analyse recent transactions (6-12 months).\n"
                "- Identify supply/demand trends.\n\n"
                "Step 2: Comparable Selection\n"
                "- Find 5-10 recently sold properties.\n"
                "- Similar type, size (+-20%), location, condition.\n\n"
                "Step 3: Adjustments\n"
                "- Financing terms: +/-3-5%.\n"
                "- Market conditions (time): +5-8% per year.\n"
                "- Location: 5-15%.\n"
                "- Size: +/-5% per 10% size difference.\n"
                "- Condition: +/-10% for major differences.\n\n"
                "Step 4: Reconciliation\n"
                "- Weight most similar comparables.\n"
                "- Final value within comparable range.\n"
                "- Document outliers and assumptions.\n\n"
                "Example:\n"
                "Comp 1: EGP 8,500/sqm. Comp 2: EGP 8,750/sqm. Comp 3: EGP 9,000/sqm.\n"
                "Weighted average: EGP 8,750/sqm."
            ),
            language=LanguageCode.ENGLISH,
            tags=["methodology", "comparable", "adjustment"],
            source="Expert Smart Standards",
            version="1.0",
        ),

        KnowledgeEntry(
            id="methodology_income_001",
            title="Income Capitalisation Approach - Methodology",
            category=KnowledgeCategory.METHODOLOGY,
            content=(
                "Income Capitalisation Approach for Commercial Real Estate.\n\n"
                "Direct Capitalisation:\n"
                "Value = NOI / Capitalisation Rate.\n\n"
                "Discounted Cash Flow (DCF):\n"
                "Value = Sum of (NOI_t / (1+r)^t) + Terminal Value / (1+r)^n.\n\n"
                "Net Operating Income calculation:\n"
                "- Gross Potential Rent (GPR).\n"
                "- Less: Vacancy and credit loss (5-10%).\n"
                "- Equals: Effective Gross Income (EGI).\n"
                "- Less: Operating expenses (15-25% of EGI).\n"
                "- Equals: Net Operating Income (NOI).\n\n"
                "Capitalisation rates by asset class (Cairo 2024):\n"
                "- Prime offices: 5.0-6.0%.\n"
                "- Retail (high street): 5.5-6.5%.\n"
                "- Industrial/logistics: 7.0-8.5%.\n"
                "- Residential (rental): 3.5-4.5%.\n\n"
                "DCF assumptions:\n"
                "- Holding period: 5-10 years.\n"
                "- Discount rate: Cap rate + 100-200 bps risk premium.\n"
                "- Terminal cap rate: Entry cap rate + 25-50 bps."
            ),
            language=LanguageCode.ENGLISH,
            tags=["methodology", "income", "dcf", "capitalisation"],
            source="Expert Smart Standards",
            version="1.0",
        ),
    ]
