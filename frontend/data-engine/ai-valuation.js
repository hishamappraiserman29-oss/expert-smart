// ai-valuation.js
// Phase 3 & 7 AI Valuation Engine

const dbModule = typeof require !== 'undefined' ? require('./market-db') : window.MarketDB;
const cleaner = typeof require !== 'undefined' ? require('./data-cleaner') : window.DataCleaner;

function formatCurrency(amount) {
    return new Intl.NumberFormat('ar-EG', { maximumFractionDigits: 0 }).format(amount) + ' درهم / EGP';
}

function evaluateAsset(assetRequest) {
    console.log("[AI Valuation] Starting evaluation for request:", assetRequest);
    
    // Normalize request location
    const normLocation = assetRequest.location ? assetRequest.location.trim().toUpperCase() : "UNKNOWN";
    
    // Determine collection
    let collectionName = 'market_properties';
    if (assetRequest.asset_type === 'machinery') collectionName = 'market_machinery';
    if (assetRequest.asset_type === 'business') collectionName = 'market_businesses';
    
    const records = dbModule.getRecords(collectionName);
    
    // 1. Filter Comparables
    // Rules: Same City, Same Asset Type, Area +/- 30%
    const comps = records.filter(record => {
        if (record.asset_type !== assetRequest.asset_type) return false;
        if (record.location !== normLocation) return false;
        
        // Handle Area Match
        if (assetRequest.area && record.normalized_area_m2) {
            const minArea = assetRequest.area * 0.7;
            const maxArea = assetRequest.area * 1.3;
            if (record.normalized_area_m2 < minArea || record.normalized_area_m2 > maxArea) {
                return false;
            }
        }
        
        // If it's a piece of machinery without an area, we only check location + type.
        return true;
    });

    console.log(`[AI Valuation] Found ${comps.length} comparable assets.`);

    if (comps.length === 0) {
        return {
            status: "error",
            message: "Insufficient comparable data in market db."
        };
    }

    // 2. Compute Average and Median Price Per Unit
    let totalValue = 0;
    let medianValue = 0;
    
    if (assetRequest.area && assetRequest.asset_type === 'property') {
        let ppm2Array = [];
        let sumPpm2 = 0;
        
        comps.forEach(c => {
            if (c.price_per_m2) {
                ppm2Array.push(c.price_per_m2);
                sumPpm2 += c.price_per_m2;
            }
        });
        
        const avgPpm2 = sumPpm2 / ppm2Array.length;
        totalValue = avgPpm2 * assetRequest.area;
        
        // Phase 7: Calculate Median
        ppm2Array.sort((a,b) => a - b);
        const mid = Math.floor(ppm2Array.length / 2);
        const medianPpm2 = ppm2Array.length % 2 !== 0 ? ppm2Array[mid] : (ppm2Array[mid - 1] + ppm2Array[mid]) / 2;
        medianValue = medianPpm2 * assetRequest.area;
        
    } else {
        // Fallback to simple average / median of absolute prices for businesses / machinery
        let pricesArray = [];
        let sumPrice = 0;
        comps.forEach(c => {
            if(c.normalized_price) {
                pricesArray.push(c.normalized_price);
                sumPrice += c.normalized_price;
            }
        });
        totalValue = sumPrice / pricesArray.length;
        
        // Phase 7: Calculate Median
        pricesArray.sort((a,b) => a - b);
        const mid = Math.floor(pricesArray.length / 2);
        medianValue = pricesArray.length % 2 !== 0 ? pricesArray[mid] : (pricesArray[mid - 1] + pricesArray[mid]) / 2;
    }

    // Adjust by condition (apply to both avg and median)
    let conditionModifier = 1.0;
    if (assetRequest.condition === 'New') conditionModifier = 1.1;
    if (assetRequest.condition === 'Needs Renovation') conditionModifier = 0.8;
    
    totalValue *= conditionModifier;
    medianValue *= conditionModifier;

    // 3. Confidence Interval (mocking +/- 10%)
    const margin = totalValue * 0.1;

    return {
        status: "success",
        estimatedValueRaw: totalValue,
        estimatedValueString: formatCurrency(totalValue),
        medianValueString: formatCurrency(medianValue),
        rangeLow: formatCurrency(totalValue - margin),
        rangeHigh: formatCurrency(totalValue + margin),
        comparablesCount: comps.length
    };
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { evaluateAsset };
} else {
    window.AIEngine = { evaluateAsset };
}
