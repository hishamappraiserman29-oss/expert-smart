/**
 * Local SQLite database for offline field work.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import SQLite from 'react-native-sqlite-storage';
import { v4 as uuid } from 'uuid';

export interface ValuationRecord {
  id: string;
  propertyId: string;
  location: string;
  propertyType: string;
  areaSqm: number;
  comparables: any[];
  primaryValue: number;
  methodology: string;
  status: 'draft' | 'completed' | 'synced';
  createdAt: string;
  updatedAt: string;
  photos: string[];
  notes: string;
  gps: {
    latitude: number;
    longitude: number;
    accuracy: number;
  };
  tenantId: string;
  syncStatus: 'pending' | 'synced' | 'error';
  syncError?: string;
}

export interface SyncQueue {
  id: string;
  operation: 'create' | 'update' | 'delete';
  table: string;
  data: any;
  timestamp: string;
  retries: number;
  status: 'pending' | 'synced' | 'failed';
}

export class OfflineStorage {
  private db: SQLite.SQLiteDatabase | null = null;
  private dbName = 'expert_smart.db';
  private isInitialized = false;

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      this.db = await SQLite.openDatabase({
        name: this.dbName,
        location: 'default',
      });

      await this.createTables();
      this.isInitialized = true;
    } catch (error) {
      console.error('Failed to initialize storage:', error);
      throw error;
    }
  }

  private async createTables(): Promise<void> {
    if (!this.db) return;

    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS valuations (
        id TEXT PRIMARY KEY,
        propertyId TEXT NOT NULL,
        location TEXT NOT NULL,
        propertyType TEXT NOT NULL,
        areaSqm REAL NOT NULL,
        comparables TEXT,
        primaryValue REAL,
        methodology TEXT,
        status TEXT DEFAULT 'draft',
        createdAt TEXT,
        updatedAt TEXT,
        photos TEXT,
        notes TEXT,
        gps TEXT,
        tenantId TEXT,
        syncStatus TEXT DEFAULT 'pending',
        syncError TEXT
      )
    `);

    await this.db.executeSql(`
      CREATE TABLE IF NOT EXISTS sync_queue (
        id TEXT PRIMARY KEY,
        operation TEXT NOT NULL,
        table_name TEXT NOT NULL,
        data TEXT,
        timestamp TEXT,
        retries INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending'
      )
    `);

    await this.db.executeSql(
      'CREATE INDEX IF NOT EXISTS idx_valuations_tenant ON valuations(tenantId)'
    );
    await this.db.executeSql(
      'CREATE INDEX IF NOT EXISTS idx_valuations_status ON valuations(status)'
    );
    await this.db.executeSql(
      'CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status)'
    );
  }

  async saveValuation(valuation: Omit<ValuationRecord, 'id' | 'createdAt' | 'updatedAt'>): Promise<string> {
    if (!this.db) throw new Error('Database not initialized');

    const id = uuid();
    const now = new Date().toISOString();

    await this.db.executeSql(
      `INSERT INTO valuations (
        id, propertyId, location, propertyType, areaSqm,
        comparables, primaryValue, methodology, status,
        createdAt, updatedAt, photos, notes, gps,
        tenantId, syncStatus
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        valuation.propertyId,
        valuation.location,
        valuation.propertyType,
        valuation.areaSqm,
        JSON.stringify(valuation.comparables),
        valuation.primaryValue,
        valuation.methodology,
        valuation.status,
        now,
        now,
        JSON.stringify(valuation.photos),
        valuation.notes,
        JSON.stringify(valuation.gps),
        valuation.tenantId,
        'pending',
      ]
    );

    await this.addToSyncQueue('create', 'valuations', {
      ...valuation,
      id,
      createdAt: now,
      updatedAt: now,
    });

    return id;
  }

  async updateValuation(id: string, updates: Partial<ValuationRecord>): Promise<void> {
    if (!this.db) throw new Error('Database not initialized');

    const now = new Date().toISOString();
    const keys = Object.keys(updates);
    const setClause = keys.map((key) => `${key} = ?`).join(', ');
    const values = [
      ...Object.values(updates).map((v) =>
        typeof v === 'object' && v !== null ? JSON.stringify(v) : v
      ),
      now,
      id,
    ];

    await this.db.executeSql(
      `UPDATE valuations SET ${setClause}, updatedAt = ? WHERE id = ?`,
      values
    );

    await this.addToSyncQueue('update', 'valuations', { id, ...updates });
  }

  async getValuation(id: string): Promise<ValuationRecord | null> {
    if (!this.db) return null;

    const [result] = await this.db.executeSql(
      'SELECT * FROM valuations WHERE id = ?',
      [id]
    );

    if (result.rows.length === 0) return null;
    return this.parseValuation(result.rows.item(0));
  }

  async listValuations(tenantId: string, status?: string): Promise<ValuationRecord[]> {
    if (!this.db) return [];

    let query = 'SELECT * FROM valuations WHERE tenantId = ?';
    const params: any[] = [tenantId];

    if (status) {
      query += ' AND status = ?';
      params.push(status);
    }

    query += ' ORDER BY updatedAt DESC';

    const [result] = await this.db.executeSql(query, params);
    const valuations: ValuationRecord[] = [];
    for (let i = 0; i < result.rows.length; i++) {
      valuations.push(this.parseValuation(result.rows.item(i)));
    }
    return valuations;
  }

  async getSyncQueue(): Promise<SyncQueue[]> {
    if (!this.db) return [];

    const [result] = await this.db.executeSql(
      "SELECT * FROM sync_queue WHERE status = 'pending' ORDER BY timestamp ASC"
    );

    const queue: SyncQueue[] = [];
    for (let i = 0; i < result.rows.length; i++) {
      const row = result.rows.item(i);
      queue.push({
        id: row.id,
        operation: row.operation,
        table: row.table_name,
        data: JSON.parse(row.data || '{}'),
        timestamp: row.timestamp,
        retries: row.retries,
        status: row.status,
      });
    }
    return queue;
  }

  async addToSyncQueue(
    operation: 'create' | 'update' | 'delete',
    table: string,
    data: any
  ): Promise<void> {
    if (!this.db) return;

    const id = uuid();
    const now = new Date().toISOString();

    await this.db.executeSql(
      `INSERT INTO sync_queue (id, operation, table_name, data, timestamp, retries, status)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, operation, table, JSON.stringify(data), now, 0, 'pending']
    );
  }

  async markAsSynced(queueId: string): Promise<void> {
    if (!this.db) return;
    await this.db.executeSql(
      "UPDATE sync_queue SET status = 'synced' WHERE id = ?",
      [queueId]
    );
  }

  async incrementRetries(queueId: string): Promise<void> {
    if (!this.db) return;
    await this.db.executeSql(
      'UPDATE sync_queue SET retries = retries + 1 WHERE id = ?',
      [queueId]
    );
  }

  private parseValuation(row: any): ValuationRecord {
    return {
      id: row.id,
      propertyId: row.propertyId,
      location: row.location,
      propertyType: row.propertyType,
      areaSqm: row.areaSqm,
      comparables: JSON.parse(row.comparables || '[]'),
      primaryValue: row.primaryValue,
      methodology: row.methodology,
      status: row.status,
      createdAt: row.createdAt,
      updatedAt: row.updatedAt,
      photos: JSON.parse(row.photos || '[]'),
      notes: row.notes,
      gps: JSON.parse(row.gps || '{}'),
      tenantId: row.tenantId,
      syncStatus: row.syncStatus,
      syncError: row.syncError,
    };
  }

  async getStorageStats(): Promise<{
    totalValuations: number;
    draftValuations: number;
    completedValuations: number;
    pendingSyncs: number;
    databaseSize: string;
  }> {
    if (!this.db) {
      return {
        totalValuations: 0,
        draftValuations: 0,
        completedValuations: 0,
        pendingSyncs: 0,
        databaseSize: '0 MB',
      };
    }

    const [total] = await this.db.executeSql(
      'SELECT COUNT(*) as count FROM valuations'
    );
    const [drafts] = await this.db.executeSql(
      "SELECT COUNT(*) as count FROM valuations WHERE status = 'draft'"
    );
    const [completed] = await this.db.executeSql(
      "SELECT COUNT(*) as count FROM valuations WHERE status = 'completed'"
    );
    const [pending] = await this.db.executeSql(
      "SELECT COUNT(*) as count FROM sync_queue WHERE status = 'pending'"
    );

    return {
      totalValuations: total.rows.item(0).count,
      draftValuations: drafts.rows.item(0).count,
      completedValuations: completed.rows.item(0).count,
      pendingSyncs: pending.rows.item(0).count,
      databaseSize: 'Estimated 2-5 MB',
    };
  }

  // Expose for testing
  _resetInitialized(): void { this.isInitialized = false; this.db = null; }
}

export const offlineStorage = new OfflineStorage();
