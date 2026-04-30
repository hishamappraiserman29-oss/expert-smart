// scheduler.js
// Coordinates mass scraping, cleaning, deduplication, and database insertion

const scraper = typeof require !== 'undefined' ? require('./scraper') : window.Scraper;
const cleaner = typeof require !== 'undefined' ? require('./data-cleaner') : window.DataCleaner;
const detector = typeof require !== 'undefined' ? require('./duplicate-detector') : window.DuplicateDetector;
const dbModule = typeof require !== 'undefined' ? require('./market-db') : window.MarketDB;

function runPipeline() {
    console.log("=== Starting Mass Market Data Engine Pipeline ===");

    // 1. Scraper collects raw listings
    const rawListings = scraper.simulateMassScrape();
    
    // Store in Raw Storage Layer
    rawListings.forEach(raw => dbModule.insertRecord('market_raw_listings', raw));

    let processedCount = 0;
    
    // Process each record
    rawListings.forEach(rawRecord => {
        // 2 & 4. Clean data & Normalize Location
        const cleanedRecord = cleaner.cleanData(rawRecord);

        // Determine target collection
        let collectionName;
        if (cleanedRecord.asset_type === 'property') collectionName = 'market_properties';
        else if (cleanedRecord.asset_type === 'machinery') collectionName = 'market_machinery';
        else if (cleanedRecord.asset_type === 'business') collectionName = 'market_businesses';
        
        if (!collectionName) return;

        // 3. Check for duplicates
        const existingRecords = dbModule.getRecords(collectionName);
        if (!detector.isDuplicate(cleanedRecord, existingRecords)) {
            // 5. Insert into DB
            dbModule.insertRecord(collectionName, cleanedRecord);
            processedCount++;
        }
    });
    
    // 6. Update Analytics
    cleaner.computeAnalytics(dbModule);

    console.log(`=== Pipeline Finished. Added ${processedCount} valid new records. ===`);
    console.log("Current Analytics State:", JSON.stringify(dbModule.db.analytics, null, 2));
}

let schedulerInterval = null;

function startDailyScheduler(intervalMs = 86400000) { // Default to 24 hrs
    console.log(`[Scheduler] Starting daily pipeline automatic runner...`);
    // Run immediately once
    runPipeline();
    // Schedule recurrences
    schedulerInterval = setInterval(runPipeline, intervalMs);
}

// Automatically run the pipeline when the file is executed directly in Node
if (typeof require !== 'undefined' && require.main === module) {
    runPipeline();
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runPipeline, startDailyScheduler };
} else {
    window.Scheduler = { runPipeline, startDailyScheduler };
}
