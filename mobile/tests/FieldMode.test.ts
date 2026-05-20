/**
 * FieldMode.test.ts — Mobile / Field Mode Tests
 *
 * Covers:
 *   A. OfflineStorage   (A01–A14)
 *   B. SyncEngine       (B01–B08)
 *   C. FieldTools       (C01–C08)
 *   D. FieldApiClient   (D01–D08)
 *   E. Integration      (E01–E06)
 */

import { OfflineStorage, offlineStorage as moduleOfflineStorage } from '../app/OfflineStorage';
import { SyncEngine } from '../app/SyncEngine';
import { FieldTools } from '../app/FieldTools';
import { FieldApiClient } from '../api/FieldApiClient';
import SQLite, { MockSQLiteDatabase } from '../__mocks__/react-native-sqlite-storage';

// ─── helpers ────────────────────────────────────────────────────────────────

function makeStorage(): OfflineStorage {
  const s = new OfflineStorage();
  return s;
}

function baseValuation(overrides: Partial<any> = {}) {
  return {
    propertyId: 'prop-001',
    location: 'Cairo, Nasr City',
    propertyType: 'residential',
    areaSqm: 120,
    comparables: [],
    primaryValue: 1_500_000,
    methodology: 'Sales Comparison',
    status: 'draft' as const,
    photos: [],
    notes: '',
    gps: { latitude: 30.0444, longitude: 31.2357, accuracy: 5 },
    tenantId: 'tenant-abc',
    syncStatus: 'pending' as const,
    ...overrides,
  };
}

// Reset the mock DB and counter between suites
beforeEach(() => {
  SQLite._db._clearAll();
  jest.clearAllMocks();
});

// ============================================================================
// A. OfflineStorage
// ============================================================================

describe('OfflineStorage', () => {

  test('A01 — initialize creates tables without error', async () => {
    const storage = makeStorage();
    await expect(storage.initialize()).resolves.toBeUndefined();
  });

  test('A02 — initialize is idempotent (second call is no-op)', async () => {
    const storage = makeStorage();
    await storage.initialize();
    const callsBefore = SQLite.openDatabase.mock.calls.length;
    await storage.initialize();
    expect(SQLite.openDatabase.mock.calls.length).toBe(callsBefore);
  });

  test('A03 — saveValuation returns a non-empty ID string', async () => {
    const storage = makeStorage();
    await storage.initialize();
    const id = await storage.saveValuation(baseValuation());
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  test('A04 — saveValuation inserts record into valuations table', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation());
    const rows = SQLite._db._getTable('valuations');
    expect(rows.length).toBe(1);
    expect(rows[0].location).toBe('Cairo, Nasr City');
  });

  test('A05 — saveValuation adds entry to sync_queue', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation());
    const queue = SQLite._db._getTable('sync_queue');
    expect(queue.length).toBeGreaterThanOrEqual(1);
  });

  test('A06 — getValuation retrieves saved record by ID', async () => {
    const storage = makeStorage();
    await storage.initialize();
    const id = await storage.saveValuation(baseValuation({ location: 'Alexandria' }));
    const record = await storage.getValuation(id);
    expect(record).not.toBeNull();
    expect(record!.location).toBe('Alexandria');
  });

  test('A07 — getValuation returns null for unknown ID', async () => {
    const storage = makeStorage();
    await storage.initialize();
    const result = await storage.getValuation('nonexistent-id');
    expect(result).toBeNull();
  });

  test('A08 — listValuations filters by tenantId', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation({ tenantId: 'T1' }));
    await storage.saveValuation(baseValuation({ tenantId: 'T2' }));
    const list = await storage.listValuations('T1');
    expect(list.length).toBe(1);
    expect(list[0].tenantId).toBe('T1');
  });

  test('A09 — listValuations with status filter returns matching records', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation({ status: 'draft' }));
    await storage.saveValuation(baseValuation({ status: 'completed' }));
    const drafts = await storage.listValuations('tenant-abc', 'draft');
    expect(drafts.every((v) => v.status === 'draft')).toBe(true);
  });

  test('A10 — getSyncQueue returns pending items', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation());
    const queue = await storage.getSyncQueue();
    expect(queue.length).toBeGreaterThanOrEqual(1);
    expect(queue[0].operation).toBe('create');
  });

  test('A11 — markAsSynced updates queue entry status', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation());
    const before = await storage.getSyncQueue();
    await storage.markAsSynced(before[0].id);
    const after = SQLite._db._getTable('sync_queue');
    const updated = after.find((r) => r.id === before[0].id);
    expect(updated!.status).toBe('synced');
  });

  test('A12 — incrementRetries increments the retries counter', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.addToSyncQueue('create', 'valuations', { id: 'v1' });
    const queueBefore = SQLite._db._getTable('sync_queue');
    const entry = queueBefore[queueBefore.length - 1];
    expect(entry.retries).toBe(0);
    await storage.incrementRetries(entry.id);
    const queueAfter = SQLite._db._getTable('sync_queue');
    const updated = queueAfter.find((r: any) => r.id === entry.id);
    expect(updated.retries).toBe(1);
  });

  test('A13 — getStorageStats returns correct counts', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation({ status: 'draft' }));
    await storage.saveValuation(baseValuation({ status: 'completed' }));
    const stats = await storage.getStorageStats();
    expect(stats.totalValuations).toBe(2);
    expect(stats.draftValuations).toBe(1);
    expect(stats.completedValuations).toBe(1);
    expect(typeof stats.databaseSize).toBe('string');
  });

  test('A14 — getStorageStats returns zeros when db not initialized', async () => {
    const storage = makeStorage(); // not initialized
    const stats = await storage.getStorageStats();
    expect(stats.totalValuations).toBe(0);
    expect(stats.pendingSyncs).toBe(0);
  });
});

// ============================================================================
// B. SyncEngine
// ============================================================================

describe('SyncEngine', () => {

  test('B01 — startSync returns {success, failed, conflicts} shape', async () => {
    const engine = new SyncEngine();
    const client = new FieldApiClient();
    client._setOnline(false);
    // Nothing in queue → 0 success
    const storage = makeStorage();
    await storage.initialize();

    // Patch the module-level singleton used by SyncEngine
    jest.mock('../app/OfflineStorage', () => ({
      offlineStorage: storage,
    }));

    const result = await engine.startSync('tenant-x');
    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('failed');
    expect(result).toHaveProperty('conflicts');
  });

  test('B02 — concurrent startSync calls: second returns early', async () => {
    const engine = new SyncEngine();
    // Mark as syncing manually
    (engine as any)._isSyncing = true;
    const result = await engine.startSync('tenant-x');
    expect(result.success).toBe(0);
    expect(result.failed).toBe(0);
  });

  test('B03 — isSyncInProgress reflects state', () => {
    const engine = new SyncEngine();
    expect(engine.isSyncInProgress()).toBe(false);
    (engine as any)._isSyncing = true;
    expect(engine.isSyncInProgress()).toBe(true);
  });

  test('B04 — calculateCompleteness returns 0 for null', () => {
    const engine = new SyncEngine();
    expect(engine.calculateCompleteness(null)).toBe(0);
  });

  test('B05 — calculateCompleteness returns 1 for fully filled object', () => {
    const engine = new SyncEngine();
    const full = {
      location: 'Cairo',
      areaSqm: 100,
      propertyType: 'residential',
      comparables: ['a'],
      primaryValue: 1_000_000,
      methodology: 'Sales Comparison',
    };
    expect(engine.calculateCompleteness(full)).toBe(1);
  });

  test('B06 — calculateCompleteness returns 0.5 for half-filled object', () => {
    const engine = new SyncEngine();
    const half = { location: 'Cairo', areaSqm: 100, propertyType: 'residential' };
    expect(engine.calculateCompleteness(half)).toBeCloseTo(0.5);
  });

  test('B07 — getSyncError returns undefined for unknown item', () => {
    const engine = new SyncEngine();
    expect(engine.getSyncError('ghost')).toBeUndefined();
  });

  test('B08 — clearSyncError removes the error', () => {
    const engine = new SyncEngine();
    (engine as any).syncErrors.set('item1', 'some error');
    engine.clearSyncError('item1');
    expect(engine.getSyncError('item1')).toBeUndefined();
  });
});

// ============================================================================
// C. FieldTools
// ============================================================================

describe('FieldTools', () => {
  const { launchCamera, launchImageLibrary } = require('../__mocks__/react-native-image-picker');
  const Voice = require('../__mocks__/@react-native-voice/voice').default;
  const Geolocation = require('../__mocks__/@react-native-community/geolocation').default;

  test('C01 — getCurrentLocation returns coords from geolocation', async () => {
    const tools = new FieldTools();
    const loc = await tools.getCurrentLocation();
    expect(loc).not.toBeNull();
    expect(loc!.latitude).toBe(30.0444);
    expect(loc!.longitude).toBe(31.2357);
    expect(loc!.accuracy).toBe(10);
  });

  test('C02 — getCurrentLocation returns null when GPS fails', async () => {
    Geolocation.getCurrentPosition.mockImplementationOnce(
      (_success: any, error: any) => error({ code: 2, message: 'GPS unavailable' })
    );
    const tools = new FieldTools();
    const loc = await tools.getCurrentLocation();
    expect(loc).toBeNull();
  });

  test('C03 — watchLocation returns a numeric watch ID', () => {
    const tools = new FieldTools();
    const id = tools.watchLocation(() => {});
    expect(typeof id).toBe('number');
    expect(id).toBe(42);
  });

  test('C04 — stopWatchLocation calls clearWatch', () => {
    const tools = new FieldTools();
    tools.stopWatchLocation(42);
    expect(Geolocation.clearWatch).toHaveBeenCalledWith(42);
  });

  test('C05 — startRecording sets isCurrentlyRecording to true', async () => {
    const tools = new FieldTools();
    await tools.startRecording();
    expect(tools.isCurrentlyRecording()).toBe(true);
  });

  test('C06 — stopRecording returns a VoiceNote with transcribed text', async () => {
    const tools = new FieldTools();
    await tools.startRecording();
    const note = await tools.stopRecording();
    expect(note).not.toBeNull();
    expect(note!.text).toBe('Property in good condition, three bedrooms');
    expect(tools.isCurrentlyRecording()).toBe(false);
  });

  test('C07 — takePhoto returns null when user cancels', async () => {
    launchCamera.mockImplementationOnce((_opts: any, cb: any) => cb({ didCancel: true }));
    const tools = new FieldTools();
    const photo = await tools.takePhoto('val-001');
    expect(photo).toBeNull();
  });

  test('C08 — takePhoto returns Photo object on success', async () => {
    launchCamera.mockImplementationOnce((_opts: any, cb: any) =>
      cb({ assets: [{ uri: 'file://photo.jpg' }] })
    );
    const tools = new FieldTools();
    const photo = await tools.takePhoto('val-001');
    expect(photo).not.toBeNull();
    expect(photo!.uri).toBe('file://photo.jpg');
    expect(photo!.id).toMatch(/^photo_/);
  });
});

// ============================================================================
// D. FieldApiClient
// ============================================================================

describe('FieldApiClient', () => {
  const { axiosInstance } = require('../__mocks__/axios');

  test('D01 — isCurrentlyOnline reflects network state', () => {
    const client = new FieldApiClient();
    client._setOnline(false);
    expect(client.isCurrentlyOnline()).toBe(false);
    client._setOnline(true);
    expect(client.isCurrentlyOnline()).toBe(true);
  });

  test('D02 — createValuation offline → saves locally and returns {id, offline: true}', async () => {
    const client = new FieldApiClient();
    client._setOnline(false);

    // Spy on the module-level singleton used by FieldApiClient
    const spy = jest.spyOn(moduleOfflineStorage, 'saveValuation').mockResolvedValue('local-id-001');

    const result = await client.createValuation('tenant-1', {
      areaSqm: 100,
      location: 'Cairo',
      propertyType: 'residential',
    });
    expect(result.offline).toBe(true);
    spy.mockRestore();
  });

  test('D03 — createValuation online → calls API post', async () => {
    axiosInstance.post.mockResolvedValueOnce({ data: { data: { id: 'server-id' } } });
    const client = new FieldApiClient();
    client._setOnline(true);

    const result = await client.createValuation('tenant-1', {
      id: 'client-gen-id',
      areaSqm: 200,
      location: 'Giza',
      propertyType: 'commercial',
    });

    expect(axiosInstance.post).toHaveBeenCalled();
    expect(result.id).toBe('server-id');
  });

  test('D04 — createValuation falls back to offline when API throws', async () => {
    axiosInstance.post.mockRejectedValueOnce(new Error('Network error'));
    const client = new FieldApiClient();
    client._setOnline(true);

    const spy = jest.spyOn(moduleOfflineStorage, 'saveValuation').mockResolvedValue('fallback-id');

    const result = await client.createValuation('tenant-1', {
      areaSqm: 80,
      location: 'Alexandria',
      propertyType: 'residential',
    });
    expect(result.offline).toBe(true);
    spy.mockRestore();
  });

  test('D05 — getValuation online → calls API get', async () => {
    axiosInstance.get.mockResolvedValueOnce({ data: { data: { id: 'v-001', location: 'Cairo' } } });
    const client = new FieldApiClient();
    client._setOnline(true);

    const result = await client.getValuation('v-001');
    expect(axiosInstance.get).toHaveBeenCalled();
    expect(result.id).toBe('v-001');
  });

  test('D06 — getValuation offline → falls back to local storage', async () => {
    const client = new FieldApiClient();
    client._setOnline(false);
    // When offline, no API call should be made
    const result = await client.getValuation('local-v-999');
    expect(axiosInstance.get).not.toHaveBeenCalled();
  });

  test('D07 — deleteValuation offline → adds to sync queue', async () => {
    const client = new FieldApiClient();
    client._setOnline(false);
    await expect(client.deleteValuation('tenant-1', 'v-002')).resolves.toBeUndefined();
    expect(axiosInstance.delete).not.toHaveBeenCalled();
  });

  test('D08 — setTenantContext sets Authorization header', () => {
    const client = new FieldApiClient();
    client.setTenantContext('tenant-99', 'token-xyz');
    expect(axiosInstance.defaults.headers.common['Authorization']).toBe('Bearer token-xyz');
    expect(axiosInstance.defaults.headers.common['X-Tenant-ID']).toBe('tenant-99');
  });
});

// ============================================================================
// E. Integration scenarios
// ============================================================================

describe('Integration', () => {

  test('E01 — full offline → save → getSyncQueue flow', async () => {
    const storage = makeStorage();
    await storage.initialize();

    const id = await storage.saveValuation(baseValuation({ location: 'Hurghada' }));
    const queue = await storage.getSyncQueue();

    const queueEntry = queue.find((q) => q.data.id === id);
    expect(queueEntry).toBeDefined();
    expect(queueEntry!.operation).toBe('create');
    expect(queueEntry!.status).toBe('pending');
  });

  test('E02 — mark synced → entry removed from pending queue', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation());
    const queue = await storage.getSyncQueue();
    expect(queue.length).toBeGreaterThan(0);

    await storage.markAsSynced(queue[0].id);
    const remaining = await storage.getSyncQueue();
    expect(remaining.find((q) => q.id === queue[0].id)).toBeUndefined();
  });

  test('E03 — SyncEngine completeness drives conflict resolution: server wins when more complete', () => {
    const engine = new SyncEngine();
    const local = { location: 'Cairo' };  // 1/6 fields
    const server = {
      location: 'Cairo', areaSqm: 100, propertyType: 'residential',
      comparables: [], primaryValue: 1_000_000, methodology: 'SCA',
    };  // 6/6 fields
    const localScore = engine.calculateCompleteness(local);
    const serverScore = engine.calculateCompleteness(server);
    expect(serverScore).toBeGreaterThan(localScore);
  });

  test('E04 — SyncEngine completeness drives conflict resolution: local wins when more complete', () => {
    const engine = new SyncEngine();
    const local = {
      location: 'Alex', areaSqm: 80, propertyType: 'land',
      comparables: ['x'], primaryValue: 500_000, methodology: 'Cost',
    };
    const server = { location: 'Alex' };
    expect(engine.calculateCompleteness(local)).toBeGreaterThan(
      engine.calculateCompleteness(server)
    );
  });

  test('E05 — FieldTools GPS attaches location to photo', async () => {
    const { launchCamera } = require('../__mocks__/react-native-image-picker');
    launchCamera.mockImplementationOnce((_opts: any, cb: any) =>
      cb({ assets: [{ uri: 'file://field.jpg' }] })
    );
    const tools = new FieldTools();
    const photo = await tools.takePhoto('v-test');
    expect(photo).not.toBeNull();
    expect(photo!.location).toBeDefined();
    expect(photo!.location!.latitude).toBe(30.0444);
  });

  test('E06 — storage stats reflect cumulative saves', async () => {
    const storage = makeStorage();
    await storage.initialize();
    await storage.saveValuation(baseValuation({ status: 'draft' }));
    await storage.saveValuation(baseValuation({ status: 'draft' }));
    await storage.saveValuation(baseValuation({ status: 'completed' }));
    const stats = await storage.getStorageStats();
    expect(stats.totalValuations).toBe(3);
    expect(stats.draftValuations).toBe(2);
    expect(stats.completedValuations).toBe(1);
    expect(stats.pendingSyncs).toBeGreaterThanOrEqual(3); // queue entries per save
  });
});
