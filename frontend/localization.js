/**
 * localization.js — Phase 23 Client-side i18n
 * Loads translations from /api/language/strings, applies RTL, translates DOM.
 */

class Localization {
    constructor() {
        this.language  = localStorage.getItem('language') || this.detectBrowserLanguage();
        this.direction = 'ltr';
        this.translations = {};
    }

    async init() {
        await this.loadTranslations();
    }

    detectBrowserLanguage() {
        const lang = (navigator.language || 'en').split('-')[0];
        if (lang === 'ar') return 'ar';
        if (lang === 'fr') return 'fr';
        return 'en';
    }

    async loadTranslations() {
        try {
            const res  = await fetch('/api/language/strings');
            const data = await res.json();
            this.translations = data.strings  || {};
            this.language     = data.language || this.language;
            this.direction    = data.direction || 'ltr';
            this.applyTranslations();
            this.applyDirection();
        } catch (err) {
            console.warn('[i18n] Failed to load translations:', err);
        }
    }

    applyTranslations() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key        = el.getAttribute('data-i18n');
            const translated = this.t(key);
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                el.placeholder = translated;
            } else {
                el.textContent = translated;
            }
        });
    }

    applyDirection() {
        document.documentElement.dir = this.direction;
        if (this.direction === 'rtl') {
            document.body.classList.add('rtl');
            document.body.classList.remove('ltr');
        } else {
            document.body.classList.add('ltr');
            document.body.classList.remove('rtl');
        }
    }

    t(key, variables = {}) {
        let text = this.translations[key] || key;
        for (const [k, v] of Object.entries(variables)) {
            text = text.replace(`{${k}}`, v);
        }
        return text;
    }

    async setLanguage(code) {
        this.language = code;
        localStorage.setItem('language', code);
        try {
            await fetch(`/api/language/set/${code}`, { method: 'POST' });
        } catch (_) { /* ignore */ }
        await this.loadTranslations();
    }

    getLanguage()  { return this.language;  }
    getDirection() { return this.direction; }
}

// Global instance — auto-init on DOMContentLoaded
const i18n = new Localization();
document.addEventListener('DOMContentLoaded', () => i18n.init());
