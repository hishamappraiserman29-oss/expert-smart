/**
 * API client with offline fallback.
 */

import axios from 'axios';
import NetInfo from '@react-native-community/netinfo';
import { offlineStorage } from '../app/OfflineStorage';

export class FieldApiClient {
  private api: ReturnType<typeof axios.create>;
  private baseURL = 'https://api.expert-smart.com';
  private _isOnline = false;
  private tenantId: string = '';

  constructor() {
    this.api = axios.create({
      baseURL: this.baseURL,
      timeout: 10000,
    });
    this.setupNetworkMonitoring();
  }

  private async setupNetworkMonitoring(): Promise<void> {
    const netInfo = await NetInfo.fetch();
    this._isOnline = netInfo.isConnected || false;

    NetInfo.addEventListener((state: any) => {
      const wasOnline = this._isOnline;
      this._isOnline = state.isConnected || false;

      if (!wasOnline && this._isOnline) {
        this.startAutoSync();
      }
    });
  }

  setTenantContext(tenantId: string, accessToken: string): void {
    this.tenantId = tenantId;
    this.api.defaults.headers.common['X-Tenant-ID'] = tenantId;
    this.api.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
  }

  async createValuation(tenantId: string, data: any): Promise<any> {
    try {
      if (!this._isOnline) {
        const id = await offlineStorage.saveValuation({
          ...data,
          tenantId,
          status: 'draft',
        });
        return { id, offline: true };
      }

      const response = await this.api.post('/api/valuation/full', {
        subject_property: {
          area_sqm: data.areaSqm,
          location: data.location,
          property_type: data.propertyType,
        },
        'Idempotency-Key': data.id,
      });

      return (response as any).data.data;
    } catch (error) {
      const id = await offlineStorage.saveValuation({
        ...data,
        tenantId,
        status: 'draft',
      });
      return { id, offline: true, error: String(error) };
    }
  }

  async updateValuation(tenantId: string, id: string, data: any): Promise<void> {
    try {
      if (!this._isOnline) {
        await offlineStorage.updateValuation(id, data);
        return;
      }

      await this.api.put(`/api/valuation/${id}`, data, {
        headers: { 'Idempotency-Key': id },
      } as any);

      await offlineStorage.updateValuation(id, { syncStatus: 'synced' });
    } catch {
      await offlineStorage.updateValuation(id, data);
    }
  }

  async getValuation(id: string): Promise<any | null> {
    try {
      if (this._isOnline) {
        const response = await this.api.get(`/api/valuation/${id}`);
        return (response as any).data.data;
      }
    } catch {
      // fall through to local
    }
    return offlineStorage.getValuation(id);
  }

  async deleteValuation(tenantId: string, id: string): Promise<void> {
    try {
      if (!this._isOnline) {
        await offlineStorage.addToSyncQueue('delete', 'valuations', { id });
        return;
      }
      await this.api.delete(`/api/valuation/${id}`);
    } catch {
      await offlineStorage.addToSyncQueue('delete', 'valuations', { id });
    }
  }

  private async startAutoSync(): Promise<void> {
    try {
      const { syncEngine } = await import('../app/SyncEngine');
      await syncEngine.startSync(this.tenantId);
    } catch (error) {
      console.error('Auto-sync failed:', error);
    }
  }

  isCurrentlyOnline(): boolean { return this._isOnline; }

  // Test helper
  _setOnline(val: boolean): void { this._isOnline = val; }
}

export const fieldApiClient = new FieldApiClient();
