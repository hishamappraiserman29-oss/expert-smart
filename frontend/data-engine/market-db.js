// market-db.js
// Database structure for storing market data

const db = {
    // Phase 5 Raw Storage
    market_raw_listings: [],
    
    // Processed Data
    market_properties: [],
    market_machinery: [],
    market_businesses: [],
    market_transactions: [], // User submitted transactions
    auction_results: [],
    
    // Phase 5 Analytics Storage
    analytics: {
        median_price_by_location: {},
        price_trend_by_city: {}
    }
};

function insertRecord(collectionName, record) {
    if (db[collectionName]) {
        db[collectionName].push(record);
        console.log(`[MarketDB] Record added to ${collectionName}`);
        return true;
    }
    console.error(`[MarketDB] Collection ${collectionName} does not exist.`);
    return false;
}

function getRecords(collectionName) {
    return db[collectionName] || [];
}

function updateAnalytics(key, data) {
    if (db.analytics[key]) {
        db.analytics[key] = data;
        return true;
    }
    return false;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        db,
        insertRecord,
        getRecords,
        updateAnalytics
    };
} else {
    window.MarketDB = {
        db,
        insertRecord,
        getRecords,
        updateAnalytics
    };
}
