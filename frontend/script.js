/**
 * Expert_Smart — Frontend API Bridge
 * Handles all backend API calls, report downloads, and UI helpers.
 */

const BACKEND_URL = "http://localhost:5000/api";

// ── Valuation ──────────────────────────────────────────────────────────────────

async function runValuation(payload) {
    // land_method: 'dual_path' triggers Sales Comparison Matrix + Residual Method
    // for land, reconciled in the final Word and Excel reports (V2).
    const enriched = { land_method: "dual_path", ...payload };
    const res = await fetch(`${BACKEND_URL}/valuation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(enriched),
    });
    return res.json();
}

async function runEvaluate(payload) {
    const res = await fetch(`${BACKEND_URL}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

// ── Reports ────────────────────────────────────────────────────────────────────

async function downloadExcelReport(payload) {
    const enriched = { land_method: "dual_path", ...payload };
    const res = await fetch(`${BACKEND_URL}/generate-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(enriched),
    });
    if (!res.ok) throw new Error("فشل توليد تقرير Excel");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `تقرير_تقييم_${Date.now()}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
}

async function downloadWordReport(payload) {
    const enriched = { land_method: "dual_path", ...payload };
    const res = await fetch(`${BACKEND_URL}/word-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(enriched),
    });
    if (!res.ok) throw new Error("فشل توليد تقرير Word");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `تقرير_IVS_${Date.now()}.docx`;
    a.click();
    URL.revokeObjectURL(url);
}

async function downloadMasterReport(payload) {
    const res = await fetch(`${BACKEND_URL}/master-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("فشل توليد التقرير الموحد");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `تقرير_شامل_${Date.now()}.docx`;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Compliance Audit ───────────────────────────────────────────────────────────

async function auditReport(reportText) {
    const res = await fetch(`${BACKEND_URL}/compliance-audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report_text: reportText }),
    });
    return res.json();
}

// ── Price Map ─────────────────────────────────────────────────────────────────

async function loadPriceMap(payload, format = "json") {
    const url = `${BACKEND_URL}/price-map${format === "html" ? "?format=html" : ""}`;
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (format === "html") return res.text();
    return res.json();
}

// ── Field Data ─────────────────────────────────────────────────────────────────

async function addFieldData(payload) {
    const res = await fetch(`${BACKEND_URL}/field-data/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

async function queryFieldData(filters) {
    const res = await fetch(`${BACKEND_URL}/field-data/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(filters),
    });
    return res.json();
}

async function getFieldComps(payload) {
    const res = await fetch(`${BACKEND_URL}/field-data/comps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

// ── Sweep ─────────────────────────────────────────────────────────────────────

async function getSweepStats() {
    const res = await fetch(`${BACKEND_URL}/sweep/stats`);
    return res.json();
}

async function forceSweep() {
    const res = await fetch(`${BACKEND_URL}/sweep/run`, { method: "POST" });
    return res.json();
}

// ── HBU / Special Assets ──────────────────────────────────────────────────────

async function runHBUScenarios(payload) {
    const res = await fetch(`${BACKEND_URL}/hbu-scenarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

async function runSpecialAsset(payload) {
    const res = await fetch(`${BACKEND_URL}/special-asset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

async function runMassAppraisal(payload) {
    const res = await fetch(`${BACKEND_URL}/mass-appraisal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json();
}

// ── Valuation Purpose ─────────────────────────────────────────────────────────

const ValuationPurpose = (() => {
    let _purpose = "fair_market";
    return {
        set(p) { _purpose = p; },
        get() { return _purpose; },
        label() {
            const labels = {
                fair_market: "القيمة السوقية العادلة",
                liquidation: "قيمة التصفية",
                taxation:    "الوعاء الضريبي",
                usufruct:    "قيمة الانتفاع",
            };
            return labels[_purpose] || _purpose;
        },
    };
})();

// ── Input Guard ───────────────────────────────────────────────────────────────

const VALUATION_KEYWORDS = [
    "تقييم", "عقار", "شقة", "فيلا", "أرض", "مبنى", "سعر", "قيمة", "إيجار",
    "متر", "مساحة", "موقع", "منطقة", "حي", "مدينة", "طابق", "دور",
    "مقارنة", "سوق", "استثمار", "عائد", "دخل", "تكلفة", "إهلاك",
    "تقرير", "خبير", "مثمن", "IVS", "RICS", "IDW", "kriging",
    "property", "valuation", "appraisal", "real estate",
];

function validateValuationQuery(text) {
    const lower = text.toLowerCase();
    return VALUATION_KEYWORDS.some(kw => lower.includes(kw.toLowerCase()));
}

function checkAIGuardrail(text) {
    if (!validateValuationQuery(text)) {
        showToast("هذا النظام مخصص للتقييم العقاري فقط.", "warning");
        return false;
    }
    return true;
}

// ── Toast Helper ──────────────────────────────────────────────────────────────

function showToast(message, type = "info") {
    const toast = document.createElement("div");
    const colors = { info: "#1F4E78", success: "#166534", warning: "#92400e", error: "#991b1b" };
    toast.style.cssText = `
        position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
        background:${colors[type] || colors.info}; color:#fff;
        padding:12px 24px; border-radius:8px; font-family:'Tajawal',sans-serif;
        font-size:14px; z-index:9999; direction:rtl; box-shadow:0 4px 12px rgba(0,0,0,0.3);
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

// ── Chat Engine ───────────────────────────────────────────────────────────────

const ChatEngine = {
    _role:  null,   // "bank" | "fund" | "tax" | null
    _state: {},     // conversation state per role
    _busy:  false,

    // ── Non-real-estate scope guard ──────────────────────────────────────────
    _FORBIDDEN: ["machinery","equipment","vehicle","aircraft","automobile",
                 "bus","truck","helicopter","ship","factory equipment",
                 "business valuation","goodwill","intangible"],
    _scopeViolation(text) {
        const t = text.toLowerCase();
        return this._FORBIDDEN.some(kw => t.includes(kw));
    },

    // ── Init: Hisham El-Mahdy digital twin welcome ───────────────────────────
    init() {
        const box = document.getElementById("chat-messages");
        if (!box || box.dataset.initialized) return;
        box.dataset.initialized = "true";
        this._addBot(`
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                <img src="https://ui-avatars.com/api/?name=هشام+المهدي&background=1F4E78&color=d4af37&bold=true&font-size=0.4&size=80"
                     style="width:44px;height:44px;border-radius:50%;border:2px solid var(--primary);flex-shrink:0;">
                <div>
                    <strong style="color:var(--primary);font-size:1rem;">م. هشام المهدي — MRICS</strong><br>
                    <small style="color:#666;font-family:'Inter';">IVS 2022 | Basel III | IFRS 13 | IAAO</small>
                </div>
            </div>
            مرحباً بك في <strong>Expert_Smart</strong> — نظامك الذكي للتقييم العقاري المعتمد.<br>
            <em style="color:#777;font-size:0.85rem;">Welcome — I respond in Arabic & English. Ask me anything about real estate.</em><br><br>
            لأقدّم لك أفضل خدمة، اختر دورك:
            <div class="role-chips">
                <span class="role-chip" onclick="ChatEngine._setRole('bank',this)">🏦 مدقق بنكي / Basel III</span>
                <span class="role-chip" onclick="ChatEngine._setRole('fund',this)">📊 مدير صندوق / REIT</span>
                <span class="role-chip" onclick="ChatEngine._setRole('tax',this)">🏛️ مسؤول ضرائب / IAAO</span>
                <span class="role-chip" onclick="ChatEngine._setRole('expert',this)">🎓 خبير تقييم / مثمن</span>
            </div>
        `);
    },

    _setRole(role, el) {
        // ── Fix 1: Exclusive Toggle — close ALL open panels before activating ──
        if (typeof UIToggle !== "undefined") UIToggle.closeAll();

        // ── Fix 5: Clean Slate — clear previous conversation ──
        this._clearMessages();

        // ── Mark selected chip ──
        document.querySelectorAll(".role-chip").forEach(c => c.classList.remove("selected"));
        if (el) el.classList.add("selected");

        this._role  = role;
        this._state = {};

        // ── Fix 2: Role → Value Type Mapping ──
        const roleConfig = {
            bank: {
                icon: "🏦", color: "#3b82f6",
                tagBg: "rgba(59,130,246,0.09)", tagBorder: "rgba(59,130,246,0.28)",
                title:     "مدقق بنكي / Basel III Auditor",
                valueType: "قيمة الضمان الائتماني — Collateral Value",
                standard:  "Basel III · BCBS 239 · LTV ≤80% سكني / ≤60% تجاري / ≤65% استثماري",
                prompt:    `أرسل هذه البيانات في رسالة واحدة:<br>
                            <strong>نوع العقار</strong> (شقة / فيلا / تجاري / أرض) &nbsp;·&nbsp;
                            <strong>الموقع</strong> &nbsp;·&nbsp; <strong>المساحة م²</strong><br>
                            <strong>قيمة القرض القائم</strong> (ج.م) &nbsp;·&nbsp; <strong>القيمة السوقية الحالية</strong> (ج.م)<br><br>
                            <em style="color:#3a5270;font-size:0.83rem;">مثال: شقة — التجمع الخامس — 180م² — قرض 2,000,000 — قيمة 3,500,000</em>`,
            },
            fund: {
                icon: "📊", color: "#10b981",
                tagBg: "rgba(16,185,129,0.09)", tagBorder: "rgba(16,185,129,0.28)",
                title:     "مدير صندوق عقاري / REIT Manager",
                valueType: "القيمة العادلة IFRS 13 — Fair Value (Level 3) · NAV · FFO",
                standard:  "IFRS 13 · IVS-103 · NOI · Cap Rate · صندوق REIT",
                prompt:    `أرسل هذه البيانات في رسالة واحدة:<br>
                            <strong>نوع العقار</strong> &nbsp;·&nbsp; <strong>الموقع</strong> &nbsp;·&nbsp; <strong>المساحة م²</strong><br>
                            <strong>القيمة السوقية الحالية</strong> (ج.م) &nbsp;·&nbsp; <strong>الإيجار السنوي الإجمالي</strong> (ج.م)<br><br>
                            <em style="color:#3a5270;font-size:0.83rem;">مثال: مبنى تجاري — مدينة نصر — 600م² — قيمة 15,000,000 — إيجار 1,200,000</em>`,
            },
            tax: {
                icon: "🏛️", color: "#f59e0b",
                tagBg: "rgba(245,158,11,0.09)", tagBorder: "rgba(245,158,11,0.28)",
                title:     "مسؤول ضرائب / IAAO Tax Official",
                valueType: "الوعاء الضريبي — Mass Appraisal Value",
                standard:  "IAAO · COD: 5–15% · PRD: 0.98–1.03 · وزارة المالية",
                prompt:    `اختر أحد المسارين:<br>
                            &bull; اكتب <strong style="color:#f59e0b;">«دراسة IAAO»</strong> لتوليد 50 عقاراً تلقائياً (التجمع الخامس)<br>
                            &bull; اضغط <i class="fa-solid fa-paperclip"></i> وارفع <strong>ملف CSV/Excel</strong><br>
                            &nbsp;&nbsp;<em style="color:#3a5270;font-size:0.8rem;">أعمدة مطلوبة: id, property_type, area, market_value, old_tax_value</em>`,
            },
            expert: {
                icon: "🎓", color: "#d4a843",
                tagBg: "rgba(212,168,67,0.09)", tagBorder: "rgba(212,168,67,0.28)",
                title:     "خبير تقييم عقاري / IVS Appraiser",
                valueType: "القيمة السوقية العادلة — Fair Market Value (IVS-104)",
                standard:  "IVS 2022 · 7 طرق تقييم · IDW + Kriging GIS · OLS Regression",
                prompt:    `أرسل هذه البيانات في رسالة واحدة:<br>
                            <strong>نوع العقار</strong> (شقة / فيلا / أرض / تجاري) &nbsp;·&nbsp; <strong>الموقع</strong> &nbsp;·&nbsp; <strong>المساحة م²</strong><br>
                            <strong>سعر المتر السوقي</strong> (ج.م/م²) &nbsp;·&nbsp; الإيجار السنوي/م² (اختياري)<br><br>
                            <em style="color:#3a5270;font-size:0.83rem;">مثال: شقة — المعادي — 150م² — سعر المتر 35,000 — إيجار 400/م²</em>`,
            },
        };

        const c = roleConfig[role];
        if (!c) { this._addBot("كيف يمكنني مساعدتك؟"); return; }

        this._addBot(`
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.07);">
                <span style="font-size:2rem;line-height:1;">${c.icon}</span>
                <div>
                    <strong style="color:${c.color};font-size:1rem;display:block;margin-bottom:2px;">${c.title}</strong>
                    <span style="font-size:0.66rem;color:#4a5a70;font-family:'Inter';letter-spacing:0.3px;">${c.standard}</span>
                </div>
            </div>
            <div style="background:${c.tagBg};border:1px solid ${c.tagBorder};border-radius:8px;padding:0.5rem 0.85rem;margin-bottom:12px;font-size:0.82rem;color:${c.color};">
                <i class="fa-solid fa-tag" style="margin-left:6px;opacity:0.75;"></i>${c.valueType}
            </div>
            ${c.prompt}
        `);
    },

    _clearMessages() {
        const box = document.getElementById("chat-messages");
        if (!box) return;
        box.innerHTML = "";
        delete box.dataset.initialized;
    },

    async send() {
        if (this._busy) return;
        const inp = document.getElementById("chat-input");
        const text = inp.value.trim();
        if (!text) return;
        inp.value = "";
        inp.style.height = "46px";

        document.getElementById("sovereign-welcome")?.classList.add("hidden");

        const sovereignCtx = (typeof SovereignEngine !== "undefined")
            ? SovereignEngine.buildLLMContext()
            : "";
        const enrichedText = sovereignCtx ? `${sovereignCtx}\n\n${text}` : text;

        this._addUser(text);

        if (this._scopeViolation(text)) {
            this._addBot(`
                <div class="scope-alert">
                    <i class="fa-solid fa-ban"></i>
                    <strong>خارج النطاق:</strong> هذا النظام مخصص للتقييم العقاري فقط.<br>
                    تقييم الآلات أو الأعمال التجارية أو المركبات ليس ضمن اختصاصنا.
                </div>
            `);
            return;
        }

        this._busy = true;
        const typingId = this._addTyping();

        try {
            const reply = await this._route(enrichedText);
            this._removeTyping(typingId);
            this._addBot(reply);
        } catch (err) {
            console.error("[ChatEngine] Send Error:", err);
            this._removeTyping(typingId);
            const errorMsg = `
                <div style="color:#ef4444; padding:10px; border:1px solid rgba(239,68,68,0.2); border-radius:8px;">
                    <i class="fa-solid fa-triangle-exclamation"></i> 
                    <strong>فشل الاتصال:</strong> لم أتمكن من الوصول للمحرك الذكي.<br>
                    <small>السبب: ${err.message}</small><br>
                </div>
            `;
            this._addBot(errorMsg);
            showToast("فشل الاتصال بالخادم", "error");
        } finally {
            this._busy = false;
        }
    },

    async _route(text) {
        if (!this._role) {
            const t = text.toLowerCase();
            if (t.includes("بنك") || t.includes("قرض") || t.includes("ltv")) this._setRole("bank", null);
            else if (t.includes("صندوق") || t.includes("ريت") || t.includes("reit")) this._setRole("fund", null);
            else if (t.includes("ضريب") || t.includes("iaao")) this._setRole("tax", null);
            else this._setRole("expert", null);
            return "تم تحديد النمط تلقائياً. " + (await this._route(text));
        }
        switch (this._role) {
            case "bank":   return this._handleBank(text);
            case "fund":   return this._handleFund(text);
            case "tax":    return this._handleTax(text);
            case "expert": return this._handleExpert(text);
            default:       return "أنا لا أفهم الطلب.";
        }
    },

    async _handleBank(text) {
        const s = this._state;
        const nums = text.match(/\d[\d,\.]+/g) || [];
        const clean = t => parseFloat(String(t).replace(/,/g,""));

        if (!s.property_type) {
            if (text.includes("شقة")) s.property_type = "شقة سكنية";
            else if (text.includes("فيلا")) s.property_type = "فيلا فاخرة";
        }
        if (nums.length >= 1 && !s.area) s.area = clean(nums[0]);
        if (nums.length >= 2 && !s.current_market_value) s.current_market_value = clean(nums[1]);
        if (nums.length >= 3 && !s.loan_amount) s.loan_amount = clean(nums[2]);
        if (!s.location) s.location = "القاهرة الجديدة";

        if (!s.area || !s.current_market_value || !s.loan_amount) {
            const missing = [];
            if (!s.area) missing.push("المساحة (م²)");
            if (!s.current_market_value) missing.push("القيمة السوقية الحالية (ج.م)");
            if (!s.loan_amount) missing.push("قيمة القرض القائم (ج.م)");
            return `لإتمام التقييم الائتماني، أحتاج:<br>• ${missing.join("<br>• ")}`;
        }

        const res = await fetch(`${BACKEND_URL}/bank-audit`, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                property_type:            s.property_type || "شقة سكنية",
                location:                 s.location,
                area:                     s.area,
                current_market_value:     s.current_market_value,
                original_valuation_value: s.current_market_value * 1.1,
                original_valuation_date:  "2023-01-01",
                loan_amount:              s.loan_amount,
                loan_type:                "residential",
            }),
        });
        const data = await res.json();
        const a = data.audit;
        this._state = {};
        return `
            <strong>📋 تقرير المراقبة الائتمانية — Basel III</strong>
            <div class="metric-card">
                <div class="metric-row"><span class="metric-label">LTV</span><span class="metric-value">${(a.ltv_ratio*100).toFixed(1)}%</span></div>
                <div class="metric-row"><span class="metric-label">المخاطرة</span><span class="metric-value">${a.risk_level}</span></div>
                <div class="metric-row"><span class="metric-label">الإجراء</span><span class="metric-value amber">${a.required_action}</span></div>
            </div>
        `;
    },

    async _handleFund(text) {
        const s = this._state;
        const nums = text.match(/\d[\d,\.]+/g) || [];
        const clean = t => parseFloat(String(t).replace(/,/g,""));

        if (nums.length >= 1 && !s.area) s.area = clean(nums[0]);
        if (nums.length >= 2 && !s.market_value) s.market_value = clean(nums[1]);
        if (nums.length >= 3 && !s.annual_rent) s.annual_rent = clean(nums[2]);

        if (!s.area || !s.market_value || !s.annual_rent) {
            return "لإتمام تقييم الصندوق، أحتاج المساحة، القيمة، والإيجار.";
        }

        const res = await fetch(`${BACKEND_URL}/fund-valuation`, {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                property_type: s.property_type || "تجاري",
                location: s.location || "القاهرة",
                area: s.area,
                market_value: s.market_value,
                annual_rent: s.annual_rent,
                vacancy_rate: 0.08,
                operating_expenses: s.market_value * 0.02,
                ifrs_level: 3,
            }),
        });
        const data = await res.json();
        const f = data.fund;
        this._state = {};
        return `
            <strong>📊 تقييم الصندوق — IFRS 13</strong>
            <div class="metric-card">
                <div class="metric-row"><span class="metric-label">الصافي (NOI)</span><span class="metric-value">${Number(f.noi).toLocaleString()} ج.م</span></div>
                <div class="metric-row"><span class="metric-label">Cap Rate</span><span class="metric-value">${f.cap_rate_pct.toFixed(2)}%</span></div>
                <div class="metric-row"><span class="metric-label">NAV</span><span class="metric-value">${Number(f.nav).toLocaleString()} ج.م</span></div>
            </div>
        `;
    },

    async _handleTax(text) {
        if (text.includes("دراسة") || text.includes("iaao")) {
            const res = await fetch(`${BACKEND_URL}/tax-pilot`, {
                method:"POST", headers:{"Content-Type":"application/json"},
                body: JSON.stringify({download:false}),
            });
            const data = await res.json();
            const s = data.stats;
            if (typeof TaxPilot !== "undefined") TaxPilot._renderResults(s, data.properties);
            return `<strong>🏛️ نتائج دراسة IAAO</strong><br>تم تحليل ${s.n_properties} عقار بنجاح.`;
        }
        return "هل تريد تشغيل دراسة IAAO أم رفع بيانات؟";
    },

    async _handleExpert(text) {
        const s = this._state;
        const nums = text.match(/\d[\d,\.]+/g) || [];
        const clean = t => parseFloat(String(t).replace(/,/g,""));

        if (nums.length === 0 && text.length > 5) {
            const r = await fetch(`${BACKEND_URL}/chat`, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ message: text, role: "expert" }),
            });
            const d = await r.json();
            return d.reply;
        }

        if (nums.length >= 1 && !s.area) s.area = clean(nums[0]);
        if (nums.length >= 2 && !s.price_per_meter) s.price_per_meter = clean(nums[1]);

        if (!s.area || !s.price_per_meter) {
            return "لإتمام التقييم الجغرافي، أحتاج المساحة وسعر المتر.";
        }

        const res = await fetch(`${BACKEND_URL}/valuation`, {
            method: "POST", headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                area: s.area,
                price_per_meter: s.price_per_meter,
                rent_per_sqm: s.price_per_meter * 0.05,
                location: s.location || "القاهرة",
                property_type: s.property_type || "شقة",
                valuation_purpose: "fair_market",
            }),
        });
        const d = await res.json();
        this._lastValuation = d;
        this._lastPayload = { area: s.area, price_per_meter: s.price_per_meter };
        this._state = {};
        setTimeout(() => this._embedGISMap(s.location || "القاهرة", s.price_per_meter), 600);

        return `
            <strong>🏠 تقرير التقييم — م. هشام المهدي</strong>
            <div class="metric-card">
                <div class="metric-row"><span class="metric-label">القيمة السوقية</span><span class="metric-value green">${Number(d.reconciled_value).toLocaleString()} ج.م</span></div>
            </div>
            <button class="chat-action-btn" onclick="ExpertSignature.prompt(ChatEngine._lastValuation)">التوقيع والإصدار</button>
        `;
    },

    async _embedGISMap(location, pricePM) {
        try {
            const r = await fetch(`${BACKEND_URL}/price-map?format=html`, {
                method: "POST", headers: {"Content-Type":"application/json"},
                body: JSON.stringify({ location, price_per_meter: pricePM }),
            });
            const mapHtml = await r.text();
            const blob = new Blob([mapHtml], {type: "text/html"});
            const url = URL.createObjectURL(blob);
            this._addBot(`<iframe src="${url}" style="width:100%;height:250px;border-radius:12px;border:none;"></iframe>`);
        } catch {}
    },

    _addBot(html) {
        const box = document.getElementById("chat-messages");
        const wrap = document.createElement("div");
        wrap.className = "msg-wrap bot";
        wrap.innerHTML = `<div class="msg-bubble bot">${html}</div>`;
        box.appendChild(wrap);
        box.scrollTop = box.scrollHeight;
    },

    _addUser(text) {
        const box = document.getElementById("chat-messages");
        const wrap = document.createElement("div");
        wrap.className = "msg-wrap user";
        wrap.innerHTML = `<div class="msg-bubble user">${text}</div>`;
        box.appendChild(wrap);
        box.scrollTop = box.scrollHeight;
    },

    _addTyping() {
        const box = document.getElementById("chat-messages");
        const id = "typing-" + Date.now();
        const wrap = document.createElement("div");
        wrap.id = id;
        wrap.className = "msg-wrap bot";
        wrap.innerHTML = `<div class="msg-bubble bot">...</div>`;
        box.appendChild(wrap);
        box.scrollTop = box.scrollHeight;
        return id;
    },

    _removeTyping(id) {
        if (id) document.getElementById(id)?.remove();
    },

    // ── File upload handler — type-aware (learn=RAG style / value=AVM data) ──
    handleFileUpload(file, type = 'auto') {
        if (!file) return;
        const allowed = /\.(xlsx|xls|pdf|csv|docx|doc|txt|png|jpg|jpeg|gif|webp|bmp|tiff?)$/i;
        if (!allowed.test(file.name)) {
            showToast("الصيغ المقبولة: Excel, PDF, CSV, Word, TXT, صور", "warning");
            return;
        }
        UIToggle.closeAll();
        if (type === 'auto') {
            if (/\.(xlsx|xls|csv)$/i.test(file.name))        type = 'value';
            else if (/\.(png|jpg|jpeg|gif|webp|bmp|tiff?)$/i.test(file.name)) type = 'image';
            else                                               type = 'learn';
        }
        this._state._attachment = { name: file.name, size: file.size, type };

        const typeConfig = {
            learn: { icon: 'fa-graduation-cap', label: 'تعلّم الأسلوب (Style Learning)', msg: 'سيتعلّم النظام أسلوبك من هذا التقرير ويطبّقه على مخرجاتك.', color: '#a78bfa' },
            value: { icon: 'fa-file-excel',     label: 'بيانات AVM للمعالجة',           msg: 'تم استلام بيانات العقارات — جارٍ الرفع للمعالجة.', color: 'var(--green, #22c55e)' },
            image: { icon: 'fa-image',          label: 'صورة عقارية',                   msg: 'تم استلام الصورة — ستُضاف للتقرير المرئي.', color: '#f59e0b' },
        };
        const cfg = typeConfig[type] || typeConfig['learn'];

        /* ── User bubble: show what the user attached ── */
        document.getElementById('chatEmpty')?.remove();
        if (type === 'image') {
            const reader = new FileReader();
            reader.onload = (ev) => {
                this._addUser(`
                    <div style="display:flex;align-items:center;gap:10px;padding:6px 10px;
                                background:rgba(212,175,55,0.06);border-radius:10px;
                                border:1px solid rgba(212,175,55,0.25);">
                        <img src="${ev.target.result}"
                             style="width:56px;height:56px;object-fit:cover;border-radius:6px;
                                    border:1px solid rgba(212,175,55,0.4);">
                        <div>
                            <div style="font-size:0.78rem;color:#f59e0b;font-weight:600;">📷 صورة مرفقة</div>
                            <div style="font-size:0.85rem;">${file.name}</div>
                            <div style="font-size:0.72rem;color:#888;">${(file.size/1024).toFixed(1)} KB</div>
                        </div>
                    </div>`);
            };
            reader.readAsDataURL(file);
        } else {
            this._addUser(`
                <div style="display:flex;align-items:center;gap:10px;padding:6px 12px;
                            background:rgba(255,255,255,0.04);border-radius:10px;
                            border:1px solid ${cfg.color}33;">
                    <i class="fa-solid ${cfg.icon}" style="color:${cfg.color};font-size:1.1rem;"></i>
                    <div>
                        <div style="font-size:0.78rem;color:${cfg.color};font-weight:600;">📎 ملف مرفق</div>
                        <div style="font-size:0.85rem;">${file.name}</div>
                        <div style="font-size:0.72rem;color:#888;">${(file.size/1024).toFixed(1)} KB</div>
                    </div>
                </div>`);
        }

        /* ── Bot confirmation bubble ── */
        this._addBot(`
            <div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
                        background:rgba(255,255,255,0.04);border-radius:10px;
                        border:1px solid ${cfg.color}33;">
                <i class="fa-solid ${cfg.icon}" style="color:${cfg.color};font-size:1.2rem;"></i>
                <div>
                    <div style="font-size:0.82rem;color:${cfg.color};font-weight:600;">${cfg.label}</div>
                    <div style="font-size:0.9rem;">${file.name}</div>
                    <div style="font-size:0.78rem;color:#999;">${cfg.msg}</div>
                </div>
            </div>
        `);

        if (type === 'learn') {
            this._state._toneFile = file.name;
        } else if (type === 'image') {
            // ── Auto-Tag + EXIF GPS extraction ─────────────────────────────
            const imgForm = new FormData();
            imgForm.append('file', file);
            fetch(`${BACKEND_URL}/image/analyze`, { method: 'POST', body: imgForm })
                .then(r => r.json())
                .then(d => {
                    if (d.status !== 'success') return;
                    let extra = '';
                    if (d.tag && d.tag !== 'أخرى') {
                        extra += `<div style="font-size:0.78rem;color:#d4af37;margin-top:3px;">🏷️ التصنيف التلقائي: <b>${d.tag}</b></div>`;
                    }
                    if (d.has_gps && d.gps_lat && d.gps_lng) {
                        const lat = d.gps_lat.toFixed(5), lng = d.gps_lng.toFixed(5);
                        extra += `<div style="font-size:0.78rem;color:#34d399;margin-top:3px;">📍 GPS مستخرج: ${lat}, ${lng}</div>`;
                        // حقن الإحداثيات في حقل الإدخال آلياً
                        ExifGPS._injectCoords(d.gps_lat, d.gps_lng);
                    }
                    if (extra) {
                        this._addBot(`
                            <div style="padding:8px 12px;background:rgba(212,175,55,0.06);border-radius:10px;
                                        border:1px solid rgba(212,175,55,0.2);">
                                <div style="font-size:0.82rem;color:#d4af37;font-weight:600;margin-bottom:4px;">🔍 المُحقق البصري</div>
                                ${extra}
                            </div>`);
                    }
                    showToast("✅ تم تحليل الصورة وتصنيفها", "success");
                })
                .catch(() => showToast("⚠️ تعذّر تحليل الصورة", "warning"));
        } else {
            const form = new FormData();
            form.append('file', file);
            form.append('type', type);
            fetch(`${BACKEND_URL}/ingest`, { method: 'POST', body: form })
                .then(r => r.json())
                .then(d => {
                    if (d.status === 'success') showToast("✅ تم رفع البيانات بنجاح", "success");
                })
                .catch(() => showToast("⚠️ تعذّر الرفع — تحقق من اتصال الخادم", "warning"));
        }

        // Reset all file inputs to allow re-selecting the same file
        ['chat-file-input','training-file-input','cam-file-input'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    }
};

// ── Tax Pilot Engine ──────────────────────────────────────────────────────────

const TaxPilot = {
    async runPilot() {
        const btn = document.getElementById("btn-run-iaao");
        if (btn) { btn.disabled = true; btn.textContent = "جارٍ التحليل..."; }
        try {
            const res = await fetch(`${BACKEND_URL}/tax-pilot`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ download: false }),
            });
            const data = await res.json();
            this._renderResults(data.stats, data.properties);
            showToast("✅ اكتمل تحليل IAAO", "success");
        } catch (e) {
            showToast("فشل الاتصال بخادم IAAO", "error");
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = "تشغيل دراسة IAAO"; }
        }
    },

    async downloadExcel() {
        try {
            const res = await fetch(`${BACKEND_URL}/tax-pilot`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ download: true }),
            });
            if (!res.ok) throw new Error();
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a"); a.href = url;
            a.download = `تقرير_IAAO_${Date.now()}.xlsx`; a.click();
            URL.revokeObjectURL(url);
        } catch { showToast("فشل تنزيل تقرير Excel", "error"); }
    },

    _renderResults(stats, properties) {
        const box = document.getElementById("iaao-results");
        if (!box || !stats) return;
        box.style.display = "block";
        box.innerHTML = `
            <div style="display:flex;gap:16px;flex-wrap:wrap;margin-top:8px;">
                <div class="metric-row"><span class="metric-label">عدد العقارات</span><span class="metric-value">${stats.n_properties || 0}</span></div>
                <div class="metric-row"><span class="metric-label">متوسط COD</span><span class="metric-value">${(stats.cod||0).toFixed(2)}%</span></div>
                <div class="metric-row"><span class="metric-label">PRD</span><span class="metric-value">${(stats.prd||0).toFixed(3)}</span></div>
            </div>`;
    }
};

// ── UIToggle ──────────────────────────────────────────────────────────────────

const UIToggle = {
    closeAll() {
        document.getElementById("attach-panel")?.classList.remove("open");
    },

    onAttach() {
        const panel = document.getElementById("attach-panel");
        if (panel) panel.classList.toggle("open");
    },

    openMic() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            showToast("المتصفح لا يدعم الإدخال الصوتي", "warning");
            return;
        }
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        const rec = new SR();
        rec.lang = 'ar-EG';
        rec.interimResults = false;
        rec.onresult = e => {
            const inp = document.getElementById("chat-input");
            if (inp) { inp.value = e.results[0][0].transcript; inp.focus(); }
        };
        rec.onerror = () => showToast("فشل الإدخال الصوتي", "error");
        rec.start();
        showToast("🎙️ جارٍ الاستماع...", "info");
    },

    _triggerUpload(type) {
        const id = type === 'learn' ? 'training-file-input' : 'chat-file-input';
        const el = document.getElementById(id);
        if (el) { el.value = ''; el.click(); }
    }
};

// ── Purpose Sidebar ───────────────────────────────────────────────────────────

const PurposeSidebar = {
    _current: 'fair_market',

    _cfg: {
        fair_market: { label: 'القيمة السوقية العادلة', standard: 'IVS 104', color: '#3b82f6',
            weights: [0.35, 0.20, 0.15, 0.12, 0.10, 0.08] },
        liquidation: { label: 'قيمة التصفية / البيع القسري', standard: 'RICS VPS 4', color: '#ef4444',
            weights: [0.50, 0.15, 0.15, 0.10, 0.05, 0.05] },
        taxation:    { label: 'القيمة التقديرية الضريبية', standard: 'IAAO 2023', color: '#f59e0b',
            weights: [0.20, 0.40, 0.25, 0.08, 0.05, 0.02] },
        usufruct:    { label: 'قيمة حق الانتفاع', standard: 'IVS 104 §60', color: '#8b5cf6',
            weights: [0.15, 0.10, 0.55, 0.10, 0.05, 0.05] },
        banking:     { label: 'قيمة الضمان البنكي', standard: 'Basel III / CBE', color: '#06b6d4',
            weights: [0.40, 0.25, 0.15, 0.10, 0.05, 0.05] },
        reits:       { label: 'القيمة العادلة للصناديق (IFRS 13)', standard: 'IFRS 13 L3', color: '#10b981',
            weights: [0.25, 0.10, 0.45, 0.10, 0.05, 0.05] },
    },

    select(purpose) {
        this._current = purpose;
        // Highlight active chip
        document.querySelectorAll(".p-chip").forEach(c => {
            c.classList.toggle("active", c.dataset.purpose === purpose);
        });
        const cfg = this._cfg[purpose];
        if (!cfg) return;
        this._render(cfg);
        showToast(`تم تحديد الغرض: ${cfg.label}`, "info");
    },

    _render(cfg) {
        const box = document.getElementById("purpose-weights-display");
        if (!box) return;
        const methodNames = ['سوق','تكلفة','دخل','GIS','OLS','أرض'];
        box.innerHTML = `
            <div style="font-size:0.8rem;color:#999;margin-bottom:6px;">
                <strong style="color:${cfg.color}">${cfg.label}</strong>
                <span style="margin-right:8px;opacity:0.6;">${cfg.standard}</span>
            </div>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
                ${cfg.weights.map((w,i) => `
                    <div style="background:${cfg.color}18;border:1px solid ${cfg.color}44;border-radius:6px;
                                padding:3px 8px;font-size:0.75rem;color:${cfg.color};">
                        ${methodNames[i]}: ${(w*100).toFixed(0)}%
                    </div>`).join('')}
            </div>`;
    },

    async checkOllama() {
        try {
            const r = await fetch('http://localhost:11434/api/tags');
            const d = await r.json();
            const models = (d.models||[]).map(m=>m.name).join(', ');
            const el = document.getElementById("ollama-status");
            if (el) { el.textContent = `Ollama ✅ — ${models || 'جاهز'}`; el.style.color = '#22c55e'; }
        } catch {
            const el = document.getElementById("ollama-status");
            if (el) { el.textContent = 'Ollama ⚠️ غير متصل'; el.style.color = '#f59e0b'; }
        }
    }
};

// ── Sovereign Engine ──────────────────────────────────────────────────────────

const SovereignEngine = {
    ctx: {
        role: '', asset: '', date: '',
        reportSim: null, propertyData: null, brokerData: '', region: 'egypt'
    },

    _roleLabels: {
        'bank-auditor':   'مدقق بنكي / Basel III',
        'fund-manager':   'مدير صندوق / REIT',
        'tax-official':   'مسؤول ضرائب / IAAO',
        'expert':         'خبير تقييم / مثمن',
        'legal':          'مستشار قانوني',
        'developer':      'مطوّر عقاري',
        'investor':       'مستثمر',
        'researcher':     'باحث أكاديمي',
    },

    _assetLabels: {
        'traditional':    'عقارات تقليدية',
        'commercial':     'تجاري / مكاتب',
        'industrial':     'صناعي / مستودعات',
        'hotel':          'فندقي / سياحي',
        'agricultural':   'زراعي / أراضٍ',
        'healthcare':     'رعاية صحية',
        'special':        'أصول خاصة',
    },

    _dateLabels: {
        'current':     'تقييم حالي (Current)',
        'historical':  'تقييم تاريخي (Historical)',
        'prospective': 'تقييم استشرافي (Prospective)',
    },

    // ── Called every time a select/input changes in the 6 modules ──
    onContextChange() {
        const selRole  = document.getElementById('sel-role');
        const selAsset = document.getElementById('sel-asset');
        const selDate  = document.getElementById('sel-date');
        const broker   = document.getElementById('field-broker-data');

        if (selRole)  this.ctx.role       = selRole.value;
        if (selAsset) this.ctx.asset      = selAsset.value;
        if (selDate)  this.ctx.date       = selDate.value;
        if (broker)   this.ctx.brokerData = broker.value;

        this._updatePromptPlaceholder();
        this._renderChips();
        this._markActiveCards();
    },

    _updatePromptPlaceholder() {
        const inp = document.getElementById('chat-input');
        if (!inp) return;
        const { role, asset, date, region } = this.ctx;
        const rl = this._roleLabels[role];
        const al = this._assetLabels[asset];
        const dl = this._dateLabels[date];
        const std = region === 'saudi' ? 'TAQEEM/IVS' : 'FRA/IVS';

        if (rl || al) {
            inp.placeholder = `${rl ? rl + ' — ' : ''}${al ? al + ' — ' : ''}${dl || 'تقييم حالي'} (${std})`;
        } else {
            inp.placeholder = 'اختر الدور ونوع الأصل أعلاه لتفعيل السياق، ثم اكتب سؤالك...';
        }
    },

    _renderChips() {
        const strip = document.getElementById('context-chips');
        if (!strip) return;
        const { role, asset, date, reportSim, propertyData, region } = this.ctx;
        const chips = [];
        if (role)         chips.push(`<span class="ctx-chip role">${this._roleLabels[role]||role}</span>`);
        if (asset)        chips.push(`<span class="ctx-chip asset">${this._assetLabels[asset]||asset}</span>`);
        if (date)         chips.push(`<span class="ctx-chip date">${this._dateLabels[date]||date}</span>`);
        if (reportSim)    chips.push(`<span class="ctx-chip file">📄 ${reportSim.name}</span>`);
        if (propertyData) chips.push(`<span class="ctx-chip file">📊 ${propertyData.name}</span>`);
        chips.push(`<span class="ctx-chip region">${region === 'saudi' ? '🇸🇦 TAQEEM' : '🇪🇬 FRA'}</span>`);
        strip.innerHTML = chips.join('');
    },

    _markActiveCards() {
        const { role, asset, date, reportSim, propertyData } = this.ctx;
        const map = {
            'mod-role':          !!role,
            'mod-asset':         !!asset,
            'mod-date':          !!date,
            'mod-report-sim':    !!reportSim,
            'mod-property-data': !!propertyData,
            'mod-field-data':    !!this.ctx.brokerData,
        };
        Object.entries(map).forEach(([id, active]) => {
            document.getElementById(id)?.classList.toggle('active', active);
        });
    },

    // ── Build LLM context string injected into every prompt ──
    buildLLMContext() {
        const { role, asset, date, reportSim, propertyData, brokerData, region } = this.ctx;
        const lines = [];
        if (role)         lines.push(`الدور: ${this._roleLabels[role]||role}`);
        if (asset)        lines.push(`نوع الأصل: ${this._assetLabels[asset]||asset}`);
        if (date)         lines.push(`تاريخ التقييم: ${this._dateLabels[date]||date}`);
        if (reportSim)    lines.push(`تقرير مرجعي: ${reportSim.name}`);
        if (propertyData) lines.push(`بيانات عقار: ${propertyData.name}`);
        if (brokerData)   lines.push(`بيانات ميدانية: ${brokerData}`);
        const std = region === 'saudi' ? 'معايير TAQEEM / IVS 2022' : 'معايير FRA / IVS 2022 (مصر)';
        lines.push(`المعيار المطبق: ${std}`);
        return lines.length > 0
            ? `[سياق التقييم]\n${lines.join('\n')}\n[/سياق]`
            : '';
    },

    // ── Module upload triggers ──
    triggerUpload(module) {
        const ids = { 'report-sim': 'upload-report-sim', 'property-data': 'upload-property-data' };
        document.getElementById(ids[module])?.click();
    },

    onFileSelect(inputEl, moduleKey, hintId, cardId) {
        const file = inputEl.files[0];
        if (!file) return;
        const allowed = /\.(xlsx|xls|pdf|csv|docx|doc|txt)$/i;
        if (!allowed.test(file.name)) {
            showToast("الصيغ المقبولة: PDF, Word, Excel, CSV", "warning");
            inputEl.value = '';
            return;
        }
        if (moduleKey === 'report-sim')    this.ctx.reportSim    = { name: file.name, size: file.size };
        if (moduleKey === 'property-data') this.ctx.propertyData = { name: file.name, size: file.size };

        const hint = document.getElementById(hintId);
        if (hint) {
            hint.classList.add('has-file');
            hint.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${file.name}`;
        }
        this.onContextChange();
        ChatEngine.handleFileUpload(file, /\.(xlsx|xls|csv)$/i.test(file.name) ? 'value' : 'learn');
    },

    // ── Market scraper trigger ──
    async triggerScrape(region) {
        const btnId = region === 'saudi' ? 'btn-scrape-sa' : 'btn-scrape-eg';
        const btn   = document.getElementById(btnId);
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> جارٍ المسح...'; }
        try {
            const res  = await fetch(`${BACKEND_URL}/sweep/run`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ region }),
            });
            const data = await res.json();
            const count = data.records_added || data.count || 0;
            showToast(`✅ مسح السوق (${region === 'saudi' ? 'السعودية' : 'مصر'}): ${count} سجل`, 'success');
        } catch (e) {
            showToast('⚠️ تعذّر مسح السوق — الخادم غير متصل', 'warning');
        } finally {
            if (btn) {
                btn.disabled = false;
                setTimeout(() => { btn.innerHTML = originalHtml; }, 3000);
            }
        }
    },

    // ── Reset all 6 modules ──
    clearContext() {
        this.ctx = { role:'', asset:'', date:'', reportSim:null, propertyData:null, brokerData:'', region:'egypt' };
        ['sel-role','sel-asset','sel-date'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const broker = document.getElementById('field-broker-data');
        if (broker) broker.value = '';

        ['rs-hint','pd-hint'].forEach(id => {
            const h = document.getElementById(id);
            if (h) {
                h.classList.remove('has-file');
                h.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> ${id==='rs-hint' ? 'PDF / Word / Excel' : 'Excel / Word / PDF'}`;
            }
        });
        ['upload-report-sim','upload-property-data'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        this.onContextChange();
        document.getElementById('sovereign-welcome')?.classList.remove('hidden');
        showToast('تم مسح السياق', 'info');
    },

    // ── Sidebar collapse toggle ──
    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        const icon    = document.querySelector('#sidebar-toggle-btn i');
        if (!sidebar) return;
        sidebar.classList.toggle('collapsed');
        if (icon) {
            icon.className = sidebar.classList.contains('collapsed')
                ? 'fa-solid fa-bars-staggered'
                : 'fa-solid fa-bars';
        }
    },
};

// ── Expert Signature Modal ────────────────────────────────────────────────────

const ExpertSignature = {
    _data: null,

    prompt(valData) {
        this._data = valData;
        const modal = document.getElementById('expert-signature-modal');
        if (modal) modal.classList.add('open');
    },

    dismiss() {
        const modal = document.getElementById('expert-signature-modal');
        if (modal) modal.classList.remove('open');
        this._data = null;
    },

    async sign() {
        const nameEl  = document.getElementById('sig-expert-name');
        const licEl   = document.getElementById('sig-license');
        const dateEl  = document.getElementById('sig-date');
        const name    = nameEl?.value.trim();
        const license = licEl?.value.trim();
        if (!name || !license) {
            showToast('يرجى إدخال الاسم ورقم الترخيص', 'warning');
            return;
        }
        const sigBtn = document.querySelector('.sig-sign-btn');
        if (sigBtn) sigBtn.disabled = true;

        try {
            const res = await fetch(`${BACKEND_URL}/generate-report`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...(this._data || {}),
                    expert_name:    name,
                    license_number: license,
                    report_date:    dateEl?.value || new Date().toISOString().split('T')[0],
                    land_method:    'dual_path',
                }),
            });
            if (!res.ok) throw new Error('server error');
            const blob = await res.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement('a');
            a.href = url;
            a.download = `تقرير_موقّع_${Date.now()}.xlsx`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('✅ تم إصدار التقرير الموقّع', 'success');
            this.dismiss();
        } catch {
            showToast('فشل إصدار التقرير — تحقق من الخادم', 'error');
        } finally {
            if (sigBtn) sigBtn.disabled = false;
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════
// Super Intelligence Suite — واجهة الاستخبارات العقارية الفائقة
// ═══════════════════════════════════════════════════════════════════════════

/* ── EXIF GPS — استخراج إحداثيات GPS من الصور ───────────────────────────── */
const ExifGPS = {
    _injectCoords(lat, lng) {
        // يُحقن في حقل الموقع أو الـ textarea إذا كان موجوداً
        const locField = document.getElementById('location') ||
                         document.getElementById('propertyLocation') ||
                         document.getElementById('input');
        if (!locField) return;
        const tag = `[📍 GPS: ${lat.toFixed(5)}, ${lng.toFixed(5)}]`;
        if (locField.tagName === 'INPUT') {
            if (!locField.value.includes('GPS:')) locField.value += ' ' + tag;
        } else {
            if (!locField.value.includes('GPS:')) locField.value += '\n' + tag;
        }
        showToast(`📍 تم رصد موقع GPS من الصورة: ${lat.toFixed(4)}, ${lng.toFixed(4)}`, "success");
    }
};

/* ── FraudDetector — المُحقق الرقمي ─────────────────────────────────────── */
const FraudDetector = {
    async analyze(ppm, location, compPpms = []) {
        const res = await fetch(`${BACKEND_URL}/fraud/detect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ price_per_meter: ppm, location, comp_ppms: compPpms }),
        });
        return res.json();
    },

    renderCard(data) {
        const confColor = data.confidence_score >= 0.9 ? '#22c55e'
                        : data.confidence_score >= 0.7 ? '#f59e0b' : '#ef4444';
        const flagIcon  = data.flag === 'سليم' ? '✅' : data.flag.includes('حرج') ? '🚨' : '⚠️';
        return `
        <div style="background:rgba(239,68,68,0.04);border:1px solid rgba(239,68,68,0.2);
                    border-radius:12px;padding:14px 16px;margin-top:8px;">
            <div style="font-size:0.85rem;color:#ef4444;font-weight:700;margin-bottom:8px;">
                🔍 المُحقق الرقمي — كشف الشذوذ
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">
                <div style="background:rgba(0,0,0,0.2);padding:8px;border-radius:8px;text-align:center;">
                    <div style="font-size:1.4rem;font-weight:900;color:${confColor};">${data.confidence_pct}</div>
                    <div style="font-size:0.72rem;color:#888;">نسبة الثقة</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:8px;border-radius:8px;text-align:center;">
                    <div style="font-size:0.9rem;font-weight:700;color:${confColor};">${flagIcon} ${data.flag}</div>
                    <div style="font-size:0.72rem;color:#888;">الحكم</div>
                </div>
            </div>
            <div style="font-size:0.78rem;color:#aaa;margin-bottom:6px;">
                نطاق السوق: ${Number(data.market_low).toLocaleString()} — ${Number(data.market_high).toLocaleString()} ج.م/م²
                &nbsp;|&nbsp; Z-Score: ${data.z_score_market}σ
            </div>
            ${data.warning_message ? `<div style="font-size:0.78rem;color:#fbbf24;white-space:pre-line;border-top:1px solid rgba(251,191,36,0.2);padding-top:8px;">${data.warning_message}</div>` : ''}
            <div style="font-size:0.8rem;color:#d1d5db;margin-top:8px;font-style:italic;">${data.recommendation}</div>
        </div>`;
    },

    async runAndShow(ppm, location, compPpms) {
        try {
            const data = await this.analyze(ppm, location, compPpms);
            if (data.status === 'success') {
                ChatEngine._addBot(this.renderCard(data));
            }
        } catch(e) { console.warn('[FraudDetector]', e); }
    }
};

/* ── GeoRisk — التحليل الجيوتقني ──────────────────────────────────────── */
const GeoRisk = {
    async analyze(location, lat, lng) {
        const res = await fetch(`${BACKEND_URL}/geo/risk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location, lat, lng }),
        });
        return res.json();
    },

    renderCard(data) {
        const alertColor = data.alert_level === 'مرتفع' ? '#ef4444'
                         : data.alert_level === 'متوسط' ? '#f59e0b' : '#22c55e';
        const alertIcon  = data.alert_level === 'مرتفع' ? '🔴' : data.alert_level === 'متوسط' ? '🟡' : '🟢';
        return `
        <div style="background:rgba(34,197,94,0.04);border:1px solid rgba(34,197,94,0.2);
                    border-radius:12px;padding:14px 16px;margin-top:8px;">
            <div style="font-size:0.85rem;color:#34d399;font-weight:700;margin-bottom:8px;">
                🌍 التحليل الجيوتقني والبيئي
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
                <div style="background:rgba(0,0,0,0.2);padding:8px;border-radius:8px;text-align:center;">
                    <div style="font-size:0.8rem;font-weight:700;color:#60a5fa;">🌱 ${data.soil?.type || '—'}</div>
                    <div style="font-size:0.65rem;color:#888;">نوع التربة</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:8px;border-radius:8px;text-align:center;">
                    <div style="font-size:0.8rem;font-weight:700;color:#60a5fa;">🌊 ${data.flood?.risk || '—'}</div>
                    <div style="font-size:0.65rem;color:#888;">خطر السيول</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:8px;border-radius:8px;text-align:center;">
                    <div style="font-size:1.1rem;font-weight:900;color:${alertColor};">${alertIcon} ${data.risk_pct}</div>
                    <div style="font-size:0.65rem;color:#888;">معامل المخاطر</div>
                </div>
            </div>
            <details style="margin-top:6px;">
                <summary style="font-size:0.78rem;color:#d4af37;cursor:pointer;">عرض التقرير الكامل</summary>
                <pre style="font-size:0.72rem;color:#d1d5db;white-space:pre-wrap;margin-top:8px;
                            background:rgba(0,0,0,0.2);padding:10px;border-radius:6px;">${data.report_text}</pre>
            </details>
        </div>`;
    },

    async runAndShow(location, lat, lng) {
        try {
            const data = await this.analyze(location, lat, lng);
            if (data.status === 'success') ChatEngine._addBot(this.renderCard(data));
        } catch(e) { console.warn('[GeoRisk]', e); }
    }
};

/* ── DemoRadar — رادار الهجرة العقارية ──────────────────────────────────── */
const DemoRadar = {
    async analyze(location, horizonYr = 5) {
        const res = await fetch(`${BACKEND_URL}/demographic/flow`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ location, investment_horizon_yr: horizonYr }),
        });
        return res.json();
    },

    renderCard(data) {
        const trendColor = data.demand_outlook?.annual_growth_pct > 0 ? '#22c55e' : '#ef4444';
        const stars = (data.rising_stars || []).slice(0, 3);
        return `
        <div style="background:rgba(96,165,250,0.04);border:1px solid rgba(96,165,250,0.2);
                    border-radius:12px;padding:14px 16px;margin-top:8px;">
            <div style="font-size:0.85rem;color:#60a5fa;font-weight:700;margin-bottom:8px;">
                📡 رادار الهجرة العقارية
            </div>
            <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
                <div style="background:rgba(0,0,0,0.2);padding:8px 14px;border-radius:8px;">
                    <div style="font-size:0.78rem;color:#60a5fa;">وضع المنطقة</div>
                    <div style="font-size:0.9rem;font-weight:700;">${data.saturation}</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:8px 14px;border-radius:8px;">
                    <div style="font-size:0.78rem;color:#60a5fa;">نمو سنوي متوقع</div>
                    <div style="font-size:1.1rem;font-weight:900;color:${trendColor};">${data.demand_outlook?.annual_growth_pct > 0 ? '+' : ''}${data.demand_outlook?.annual_growth_pct}%</div>
                </div>
            </div>
            ${stars.length ? `
            <div style="font-size:0.78rem;color:#d4af37;margin-bottom:6px;">⭐ المناطق الصاعدة المُقترحة:</div>
            ${stars.map(s => `<div style="font-size:0.78rem;color:#d1d5db;margin-bottom:3px;">
                → <b>${s.name}</b> (${s.horizon_yr} سنوات) — ${s.driver}
            </div>`).join('')}` : ''}
            <details style="margin-top:8px;">
                <summary style="font-size:0.78rem;color:#60a5fa;cursor:pointer;">التوصية الاستثمارية الكاملة</summary>
                <pre style="font-size:0.72rem;color:#d1d5db;white-space:pre-wrap;margin-top:8px;
                            background:rgba(0,0,0,0.2);padding:10px;border-radius:6px;">${data.advisory_text}</pre>
            </details>
        </div>`;
    },

    async runAndShow(location, horizonYr) {
        try {
            const data = await this.analyze(location, horizonYr);
            if (data.status === 'success') ChatEngine._addBot(this.renderCard(data));
        } catch(e) { console.warn('[DemoRadar]', e); }
    }
};

/* ── AssetManager — إدارة الأصول الذكية ─────────────────────────────────── */
const AssetManager = {
    async registerFromValuation(valuationData) {
        const body = {
            name:          valuationData.property_description || 'عقار جديد',
            location:      valuationData.location || '',
            property_type: valuationData.property_type || '',
            area_m2:       valuationData.area_m2 || 0,
            base_value:    valuationData.reconciled_value || valuationData.total_value || 0,
            market:        valuationData.market || 'egypt',
            currency:      'EGP',
            metadata:      { source: 'valuation_report', report_date: new Date().toISOString() },
        };
        const res = await fetch(`${BACKEND_URL}/assets/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        return res.json();
    },

    async getDashboard() {
        const res = await fetch(`${BACKEND_URL}/assets/dashboard`);
        return res.json();
    },

    renderDashboard(data) {
        if (data.status === 'empty') return `<div style="color:#888;padding:12px;">لا توجد أصول مُسجَّلة بعد</div>`;
        const gainColor = data.gain_pct >= 0 ? '#22c55e' : '#ef4444';
        return `
        <div style="background:rgba(212,175,55,0.04);border:1px solid rgba(212,175,55,0.2);
                    border-radius:12px;padding:14px 16px;margin-top:8px;">
            <div style="font-size:0.85rem;color:#d4af37;font-weight:700;margin-bottom:10px;">
                🏛️ لوحة إدارة الأصول
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px;">
                <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:1.4rem;font-weight:900;color:#d4af37;">${data.total_assets}</div>
                    <div style="font-size:0.68rem;color:#888;">إجمالي الأصول</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:0.9rem;font-weight:700;color:#f9fafb;">${Number(data.total_current_value).toLocaleString()}</div>
                    <div style="font-size:0.68rem;color:#888;">القيمة الحالية</div>
                </div>
                <div style="background:rgba(0,0,0,0.2);padding:10px;border-radius:8px;text-align:center;">
                    <div style="font-size:1.1rem;font-weight:900;color:${gainColor};">${data.gain_pct > 0 ? '+' : ''}${data.gain_pct}%</div>
                    <div style="font-size:0.68rem;color:#888;">العائد الرأسمالي</div>
                </div>
            </div>
            ${data.top_performers?.length ? `
            <div style="font-size:0.78rem;color:#d4af37;margin-bottom:6px;">🏆 أعلى الأصول أداءً:</div>
            ${data.top_performers.map(a => `<div style="font-size:0.78rem;color:#d1d5db;margin-bottom:3px;">
                📌 ${a.name} (${a.location}) — <span style="color:#22c55e;">+${a.gain_pct}%</span>
            </div>`).join('')}` : ''}
        </div>`;
    },

    async showDashboard() {
        try {
            const data = await this.getDashboard();
            ChatEngine._addBot(this.renderDashboard(data));
        } catch(e) { console.warn('[AssetManager]', e); }
    }
};

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    console.log("[Expert_Smart] Sovereign Engine loaded — backend:", BACKEND_URL);

    // Boot ChatEngine (Hisham's digital twin)
    ChatEngine.init();

    // Boot PurposeSidebar
    PurposeSidebar._render(PurposeSidebar._cfg["fair_market"]);
    PurposeSidebar.checkOllama();

    // Boot SovereignEngine — wire initial placeholder and chips
    SovereignEngine.onContextChange();

    // Health Check — Verify connectivity to bridge_api.py
    fetch(`${BACKEND_URL}/health`)
        .then(r => r.json())
        .then(d => console.log("[Expert_Smart] Bridge API Healthy:", d))
        .catch(() => showToast("⚠️ تحذير: الخادم (bridge_api.py) غير متصل حالياً", "warning"));

    // NOTE: expert-signature-modal click + Escape keydown handlers are registered
    // in index.html's inline DOMContentLoaded — do NOT duplicate them here.
});
