"""
translations.py — Phase 23 Translation Strings
English, Arabic, and French UI/API strings for Expert Smart.
"""

from __future__ import annotations

ENGLISH_TRANSLATIONS: dict = {
    # Navigation
    "nav.home": "Home",
    "nav.valuations": "Valuations",
    "nav.reports": "Reports",
    "nav.portfolio": "Portfolio",
    "nav.settings": "Settings",
    "nav.language": "Language",
    # Buttons
    "button.submit": "Submit",
    "button.cancel": "Cancel",
    "button.save": "Save",
    "button.download": "Download",
    "button.evaluate": "Evaluate",
    "button.search": "Search",
    "button.clear": "Clear",
    "button.generate_report": "Generate Report",
    # Titles
    "title.property_valuation": "Property Valuation",
    "title.portfolio_analysis": "Portfolio Analysis",
    "title.batch_valuation": "Batch Valuation",
    "title.report_generation": "Report Generation",
    # Form Labels
    "form.area_sqm": "Area (sqm)",
    "form.location": "Location",
    "form.property_type": "Property Type",
    "form.property_type.residential": "Residential",
    "form.property_type.commercial": "Commercial",
    "form.property_type.land": "Land",
    "form.primary_purpose": "Valuation Purpose",
    "form.primary_purpose.market_value": "Market Value",
    "form.primary_purpose.insurance": "Insurance",
    "form.primary_purpose.mortgage": "Mortgage",
    # Messages
    "message.loading": "Loading...",
    "message.processing": "Processing...",
    "message.success": "Operation completed successfully",
    "message.error": "An error occurred",
    "message.validation_error": "Please check your input",
    "message.no_data": "No data available",
    # Results
    "result.primary_value": "Primary Value",
    "result.confidence": "Confidence Level",
    "result.comparable_count": "Number of Comparables",
    "result.unit_value": "Unit Value (EGP/sqm)",
    "result.methodology": "Valuation Methodology",
    # Confidence
    "confidence.high": "High",
    "confidence.medium": "Medium",
    "confidence.low": "Low",
    # Errors
    "error.invalid_area": "Area must be between 1 and 100,000 sqm",
    "error.invalid_location": "Please enter a valid location",
    "error.invalid_property_type": "Please select a valid property type",
    "error.no_comparables": "No comparable properties found",
    "error.valuation_failed": "Valuation failed",
    # Reports
    "report.title": "Property Valuation Report",
    "report.summary": "Summary",
    "report.details": "Property Details",
    "report.methodology": "Valuation Methodology",
    "report.comparables": "Comparable Properties",
    "report.reconciliation": "Reconciliation",
    "report.conclusion": "Conclusion",
    # Portfolio
    "portfolio.total_value": "Total Portfolio Value",
    "portfolio.diversification": "Diversification Score",
    "portfolio.properties": "Number of Properties",
    "portfolio.concentration": "Concentration Ratio",
    # Help
    "help.area_help": "Enter property area in square meters",
    "help.location_help": "Select governorate or district",
    "help.property_type_help": "Choose property type",
    "info.powered_by": "Powered by Expert Smart",
    "info.version": "Version {version}",
}

ARABIC_TRANSLATIONS: dict = {
    # Navigation
    "nav.home": "الرئيسية",
    "nav.valuations": "التقييمات",
    "nav.reports": "التقارير",
    "nav.portfolio": "المحفظة",
    "nav.settings": "الإعدادات",
    "nav.language": "اللغة",
    # Buttons
    "button.submit": "إرسال",
    "button.cancel": "إلغاء",
    "button.save": "حفظ",
    "button.download": "تنزيل",
    "button.evaluate": "تقييم",
    "button.search": "بحث",
    "button.clear": "مسح",
    "button.generate_report": "إنشاء تقرير",
    # Titles
    "title.property_valuation": "تقييم العقار",
    "title.portfolio_analysis": "تحليل المحفظة",
    "title.batch_valuation": "تقييم دفعات",
    "title.report_generation": "إنشاء التقرير",
    # Form Labels
    "form.area_sqm": "المساحة (متر مربع)",
    "form.location": "الموقع",
    "form.property_type": "نوع العقار",
    "form.property_type.residential": "سكني",
    "form.property_type.commercial": "تجاري",
    "form.property_type.land": "أرض",
    "form.primary_purpose": "الغرض من التقييم",
    "form.primary_purpose.market_value": "القيمة السوقية",
    "form.primary_purpose.insurance": "التأمين",
    "form.primary_purpose.mortgage": "الرهن العقاري",
    # Messages
    "message.loading": "جاري التحميل...",
    "message.processing": "جاري المعالجة...",
    "message.success": "تمت العملية بنجاح",
    "message.error": "حدث خطأ",
    "message.validation_error": "يرجى التحقق من البيانات المدخلة",
    "message.no_data": "لا توجد بيانات",
    # Results
    "result.primary_value": "القيمة الأساسية",
    "result.confidence": "مستوى الثقة",
    "result.comparable_count": "عدد العقارات المقارنة",
    "result.unit_value": "القيمة الموحدة (جنيه/متر مربع)",
    "result.methodology": "منهجية التقييم",
    # Confidence
    "confidence.high": "عالي",
    "confidence.medium": "متوسط",
    "confidence.low": "منخفض",
    # Errors
    "error.invalid_area": "يجب أن تكون المساحة بين 1 و 100,000 متر مربع",
    "error.invalid_location": "يرجى إدخال موقع صحيح",
    "error.invalid_property_type": "يرجى اختيار نوع عقار صحيح",
    "error.no_comparables": "لم يتم العثور على عقارات مقارنة",
    "error.valuation_failed": "فشل التقييم",
    # Reports
    "report.title": "تقرير تقييم العقار",
    "report.summary": "الملخص",
    "report.details": "تفاصيل العقار",
    "report.methodology": "منهجية التقييم",
    "report.comparables": "العقارات المقارنة",
    "report.reconciliation": "التوفيق",
    "report.conclusion": "الخلاصة",
    # Portfolio
    "portfolio.total_value": "إجمالي قيمة المحفظة",
    "portfolio.diversification": "درجة التنويع",
    "portfolio.properties": "عدد العقارات",
    "portfolio.concentration": "نسبة التركيز",
    # Help
    "help.area_help": "أدخل مساحة العقار بالمتر المربع",
    "help.location_help": "اختر المحافظة أو المنطقة",
    "help.property_type_help": "اختر نوع العقار",
    "info.powered_by": "مدعوم من Expert Smart",
    "info.version": "الإصدار {version}",
}

FRENCH_TRANSLATIONS: dict = {
    # Navigation
    "nav.home": "Accueil",
    "nav.valuations": "Evaluations",
    "nav.reports": "Rapports",
    "nav.portfolio": "Portefeuille",
    "nav.settings": "Paramètres",
    "nav.language": "Langue",
    # Buttons
    "button.submit": "Soumettre",
    "button.cancel": "Annuler",
    "button.save": "Enregistrer",
    "button.download": "Télécharger",
    "button.evaluate": "Évaluer",
    "button.search": "Rechercher",
    "button.clear": "Effacer",
    "button.generate_report": "Générer un rapport",
    # Titles
    "title.property_valuation": "Évaluation de propriété",
    "title.portfolio_analysis": "Analyse de portefeuille",
    "title.batch_valuation": "Évaluation par lot",
    "title.report_generation": "Génération de rapport",
    # Form Labels
    "form.area_sqm": "Superficie (m²)",
    "form.location": "Localisation",
    "form.property_type": "Type de propriété",
    "form.property_type.residential": "Résidentiel",
    "form.property_type.commercial": "Commercial",
    "form.property_type.land": "Terrain",
    "form.primary_purpose": "Objectif d'évaluation",
    "form.primary_purpose.market_value": "Valeur marchande",
    "form.primary_purpose.insurance": "Assurance",
    "form.primary_purpose.mortgage": "Hypothèque",
    # Messages
    "message.loading": "Chargement...",
    "message.processing": "Traitement...",
    "message.success": "Opération réussie",
    "message.error": "Une erreur s'est produite",
    "message.validation_error": "Veuillez vérifier vos données",
    "message.no_data": "Aucune donnée disponible",
    # Results
    "result.primary_value": "Valeur principale",
    "result.confidence": "Niveau de confiance",
    "result.comparable_count": "Nombre de comparables",
    "result.unit_value": "Valeur unitaire (EGP/m²)",
    "result.methodology": "Méthodologie d'évaluation",
    # Confidence
    "confidence.high": "Élevé",
    "confidence.medium": "Moyen",
    "confidence.low": "Faible",
    # Errors
    "error.invalid_area": "La superficie doit être entre 1 et 100 000 m²",
    "error.invalid_location": "Veuillez entrer un emplacement valide",
    "error.invalid_property_type": "Veuillez sélectionner un type de propriété valide",
    "error.no_comparables": "Aucune propriété comparable trouvée",
    "error.valuation_failed": "Échec de l'évaluation",
    # Reports
    "report.title": "Rapport d'évaluation immobilière",
    "report.summary": "Résumé",
    "report.details": "Détails de la propriété",
    "report.methodology": "Méthodologie d'évaluation",
    "report.comparables": "Propriétés comparables",
    "report.reconciliation": "Réconciliation",
    "report.conclusion": "Conclusion",
    # Portfolio
    "portfolio.total_value": "Valeur totale du portefeuille",
    "portfolio.diversification": "Score de diversification",
    "portfolio.properties": "Nombre de propriétés",
    "portfolio.concentration": "Taux de concentration",
    # Help
    "help.area_help": "Entrez la superficie en mètres carrés",
    "help.location_help": "Sélectionnez le gouvernorat ou le district",
    "help.property_type_help": "Choisissez le type de propriété",
    "info.powered_by": "Propulsé par Expert Smart",
    "info.version": "Version {version}",
}


def get_translations(language: str) -> dict:
    """Return translations dict for the given language code."""
    lang_lower = language.lower()
    if lang_lower in ("ar", "arabic"):
        return ARABIC_TRANSLATIONS
    if lang_lower in ("fr", "french"):
        return FRENCH_TRANSLATIONS
    return ENGLISH_TRANSLATIONS
