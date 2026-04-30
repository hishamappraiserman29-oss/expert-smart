// scraper.js
// Mass Market Data Collection System Simulator

const CITIES = ["Cairo", "New Cairo", "6th of October", "Giza", "Alexandria", "Mansoura", "Tanta", "Zayed"];
const RE_SOURCES = ["PropertyFinder", "Aqarmap", "OLX", "Direct Listing"];
const MACH_SOURCES = ["OLX", "Local Auction", "B2B Market"];
const CONDITIONS = ["New", "Excellent", "Good", "Used", "Needs Renovation"];
const BUSINESS_TYPES = ["Retail", "Factory", "Restaurant", "Tech Startup"];

function generateRandomListings(count, assetType) {
    const records = [];
    const now = new Date();
    
    for (let i = 0; i < count; i++) {
        const rCity = CITIES[Math.floor(Math.random() * CITIES.length)];
        const rCond = CONDITIONS[Math.floor(Math.random() * CONDITIONS.length)];
        // Past 30 days
        const rDate = new Date(now.getTime() - (Math.floor(Math.random() * 30) * 24 * 60 * 60 * 1000)); 
        const rId = Math.floor(Math.random() * 1000000);
        
        let price, area, source;
        if (assetType === 'property') {
            area = Math.floor(Math.random() * 400) + 50; // 50 to 450 sqm
            price = area * (Math.floor(Math.random() * 20000) + 10000); // 10k to 30k per sqm
            source = RE_SOURCES[Math.floor(Math.random() * RE_SOURCES.length)];
        } else if (assetType === 'machinery') {
            area = null; // No area for machinery usually
            price = Math.floor(Math.random() * 5000000) + 50000;
            source = MACH_SOURCES[Math.floor(Math.random() * MACH_SOURCES.length)];
        } else if (assetType === 'business') {
            area = Math.floor(Math.random() * 2000) + 100;
            price = Math.floor(Math.random() * 50000000) + 1000000;
            source = "Business Market Directory";
        }
        
        records.push({
            asset_type: assetType,
            location: rCity,
            price: price.toString() + ' EGP',
            area: area ? area.toString() + ' sq' : undefined,
            date: rDate.toISOString().split('T')[0],
            source: source,
            condition: rCond,
            listing_url: `https://mock-${source.toLowerCase().replace(' ', '')}.com/listing/${rId}`
        });
    }
    return records;
}

function simulateMassScrape() {
    console.log("[Scraper] Simulating mass scraping from Egyptian sources...");
    const properties = generateRandomListings(150, 'property');
    const machinery = generateRandomListings(50, 'machinery');
    const businesses = generateRandomListings(25, 'business');
    
    const all = [...properties, ...machinery, ...businesses];
    console.log(`[Scraper] Collected ${all.length} raw listings.`);
    return all;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { simulateMassScrape };
} else {
    window.Scraper = { simulateMassScrape };
}
