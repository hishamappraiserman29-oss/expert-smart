/**
 * Synchronization engine with conflict resolution.
 */

import { offlineStorage } from './OfflineStorage';
import { fieldApiClient } from '../api/FieldApiClient';

export interface SyncConflict {
  valuationId: string;
  localValue: any;
  serverValue: any;
  resolution: 'local' | 'server' | 'merge';
}

export interface SyncResult {
  success: number;
  failed: number;
  conflicts: SyncConflict[];
}

export class SyncEngine {
  private _isSyncing = false;
  private syncErrors: Map<string, string> = new Map();

  async startSync(tenantId: string): Promise<SyncResult> {
    if (this._isSyncing) {
      return { success: 0, failed: 0, conflicts: [] };
    }

    this._isSyncing = true;
    let success = 0;
    let failed = 0;
    const conflicts: SyncConflict[] = [];

    try {
      const queue = await offlineStorage.getSyncQueue();

      for (const item of queue) {
        try {
          const conflict = await this.checkConflict(item);

          if (conflict) {
            conflicts.push(conflict);
            continue;
          }

          const result = await this.syncItem(item, tenantId);

          if (result) {
            await offlineStorage.markAsSynced(item.id);
            success++;
          } else {
            await offlineStorage.incrementRetries(item.id);
            failed++;
          }
        } catch (error) {
          await offlineStorage.incrementRetries(item.id);
          failed++;
        }
      }

      return { success, failed, conflicts };
    } finally {
      this._isSyncing = false;
    }
  }

  private async checkConflict(item: any): Promise<SyncConflict | null> {
    try {
      const serverValuation = await fieldApiClient.getValuation(item.data.id);

      if (!serverValuation) return null;

      const localUpdated = new Date(item.timestamp);
      const serverUpdated = new Date(serverValuation.updatedAt);

      if (serverUpdated <= localUpdated) return null;

      return {
        valuationId: item.data.id,
        localValue: item.data,
        serverValue: serverValuation,
        resolution: await this.resolveConflict(item.data, serverValuation),
      };
    } catch {
      return null;
    }
  }

  private async resolveConflict(
    local: any,
    server: any
  ): Promise<'local' | 'server' | 'merge'> {
    const localCompleteness = this.calculateCompleteness(local);
    const serverCompleteness = this.calculateCompleteness(server);

    if (serverCompleteness > localCompleteness) return 'server';
    if (localCompleteness > serverCompleteness) return 'local';
    return 'merge';
  }

  calculateCompleteness(obj: any): number {
    if (!obj) return 0;
    const fields = [
      'location', 'areaSqm', 'propertyType', 'comparables', 'primaryValue', 'methodology',
    ];
    const filled = fields.filter((f) => obj[f] != null && obj[f] !== '').length;
    return filled / fields.length;
  }

  private async syncItem(item: any, tenantId: string): Promise<boolean> {
    try {
      switch (item.operation) {
        case 'create':
          await fieldApiClient.createValuation(tenantId, item.data);
          return true;
        case 'update':
          await fieldApiClient.updateValuation(tenantId, item.data.id, item.data);
          return true;
        case 'delete':
          await fieldApiClient.deleteValuation(tenantId, item.data.id);
          return true;
        default:
          return false;
      }
    } catch (error) {
      this.syncErrors.set(item.id, String(error));
      return false;
    }
  }

  isSyncInProgress(): boolean { return this._isSyncing; }
  getSyncError(itemId: string): string | undefined { return this.syncErrors.get(itemId); }
  clearSyncError(itemId: string): void { this.syncErrors.delete(itemId); }
}

export const syncEngine = new SyncEngine();
