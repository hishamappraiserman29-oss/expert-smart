// duplicate-detector.js
// Checks if a listing already exists in the database

function isDuplicate(newRecord, existingRecords) {
    if (!existingRecords || existingRecords.length === 0) {
        return false; // No existing records to duplicate
    }

    for (let i = 0; i < existingRecords.length; i++) {
        const existing = existingRecords[i];

        // Phase 4: Strict 4-point matching (Type doesn't need to be checked if collection is already split)
        // But we check just in case.
        const sameType = newRecord.asset_type === existing.asset_type;
        const sameLocation = newRecord.location === existing.location; // pre-normalized by DataCleaner
        const samePrice = newRecord.normalized_price === existing.normalized_price;
        const sameDate = newRecord.date === existing.date;

        // Note: For machinery or business without explicit 'area', we just check if both exist or both don't
        const sameArea = newRecord.normalized_area_m2 === existing.normalized_area_m2;

        if (sameType && sameLocation && samePrice && sameArea && sameDate) {
            return true; // Duplicate found!
        }
    }

    return false;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        isDuplicate
    };
} else {
    window.DuplicateDetector = {
        isDuplicate
    };
}
