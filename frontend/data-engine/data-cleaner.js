// data-cleaner.js
// Normalizes and cleans collected data

const LOCATION_MAP = {
    "cairo": "CAIRO",
    "new cairo": "CAIRO",
    "heliopolis": "CAIRO",
    "6th of october": "GIZA",
    "october": "GIZA",
    "giza": "GIZA",
    "zayed": "GIZA",
    "alexandria": "ALEXANDRIA"
};

function normalizeLocation(rawLocation) {
    if (!rawLocation) return "UNKNOWN";
    const lower = rawLocation.trim().toLowerCase();
    return LOCATION_MAP[lower] || lower.toUpperCase(); // fallback to upper string if not mapped
}

function calcPriceTrend(condition, daysOld) {
    let baseScore = 1.0;
    if (condition === "New" || condition === "Excellent") baseScore += 0.1;
    if (condition === "Needs Renovation") baseScore -= 0.2;
    // slightly depreciate older listings
    if (daysOld > 15) baseScore -= 0.05;
    
    if (baseScore > 1) return "Rising";
    if (baseScore < 1) return "Falling";
    return "Stable";
}

function cleanData(record) {
    const cleaned = { ...record };

    // Standardize price format
    if (cleaned.price) {
        // Remove non-numeric characters for amount (assuming EGP or USD)
        const numericPrice = parseFloat(cleaned.price.toString().replace(/[^0-9.]/g, ''));
        cleaned.normalized_price = numericPrice;
    }

    // Convert area to square meters
    if (cleaned.area) {
        const numericArea = parseFloat(cleaned.area.toString().replace(/[^0-9.]/g, ''));
        cleaned.normalized_area_m2 = numericArea;
    }

    // Calculate price_per_m2
    if (cleaned.normalized_price && cleaned.normalized_area_m2) {
        cleaned.price_per_m2 = cleaned.normalized_price / cleaned.normalized_area_m2;
    }

    // Phase 4: Location Normalizer
    cleaned.location = normalizeLocation(cleaned.location);

    // Default valid date or remove invalid
    let daysOld = 0;
    if (cleaned.date) {
        const parsedDate = new Date(cleaned.date);
        if (isNaN(parsedDate.getTime())) {
            cleaned.date = null; // invalid date
        } else {
            daysOld = Math.floor((new Date() - parsedDate) / (1000 * 60 * 60 * 24));
        }
    }

    // Advanced derived fields
    cleaned.price_trend = calcPriceTrend(cleaned.condition, daysOld);

    return cleaned;
}

// Analytics functions
function computeAnalytics(dbModule) {
    const properties = dbModule.getRecords('market_properties');
    
    // Compute median price by location
    const pricesByLoc = {};
    properties.forEach(p => {
        if (!p.normalized_price) return;
        if (!pricesByLoc[p.location]) pricesByLoc[p.location] = [];
        pricesByLoc[p.location].push(p.normalized_price);
    });

    const medians = {};
    for (const [loc, arr] of Object.entries(pricesByLoc)) {
        arr.sort((a,b) => a - b);
        const mid = Math.floor(arr.length / 2);
        medians[loc] = arr.length % 2 !== 0 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2;
    }
    dbModule.updateAnalytics('median_price_by_location', medians);
    
    // Compute price trend (simple count of rising vs falling per city)
    const trendsByLoc = {};
    properties.forEach(p => {
        if (!trendsByLoc[p.location]) trendsByLoc[p.location] = { rising: 0, falling: 0, stable: 0 };
        if (p.price_trend === 'Rising') trendsByLoc[p.location].rising++;
        else if (p.price_trend === 'Falling') trendsByLoc[p.location].falling++;
        else trendsByLoc[p.location].stable++;
    });

    const finalTrends = {};
    for (const [loc, counts] of Object.entries(trendsByLoc)) {
        if (counts.rising > counts.falling) finalTrends[loc] = "Upward";
        else if (counts.falling > counts.rising) finalTrends[loc] = "Downward";
        else finalTrends[loc] = "Stable";
    }
    dbModule.updateAnalytics('price_trend_by_city', finalTrends);
    
    console.log("[DataCleaner] Analytics computed and stored.");
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        cleanData, computeAnalytics
    };
} else {
    window.DataCleaner = {
        cleanData, computeAnalytics
    };
}
