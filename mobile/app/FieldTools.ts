/**
 * Field tools: Camera, GPS, Voice Notes.
 */

import { launchCamera, launchImageLibrary } from 'react-native-image-picker';
import Geolocation from '@react-native-community/geolocation';
import Voice from '@react-native-voice/voice';
import { offlineStorage } from './OfflineStorage';

export interface Photo {
  id: string;
  uri: string;
  timestamp: string;
  location?: {
    latitude: number;
    longitude: number;
  };
}

export interface VoiceNote {
  id: string;
  uri: string;
  duration: number;
  timestamp: string;
  text?: string;
}

export class FieldTools {
  private _isRecording = false;
  private recordingStartTime = 0;

  // ──────────────── Camera ────────────────

  async takePhoto(valuationId: string): Promise<Photo | null> {
    return new Promise((resolve) => {
      launchCamera(
        { mediaType: 'photo', cameraType: 'back', saveToPhotos: true, quality: 0.8 },
        async (response: any) => {
          if (response.didCancel || response.errorCode) {
            resolve(null);
            return;
          }
          const photo: Photo = {
            id: `photo_${Date.now()}`,
            uri: response.assets?.[0]?.uri || '',
            timestamp: new Date().toISOString(),
            location: (await this.getCurrentLocation()) ?? undefined,
          };
          resolve(photo);
        }
      );
    });
  }

  async pickPhoto(): Promise<Photo | null> {
    return new Promise((resolve) => {
      launchImageLibrary(
        { mediaType: 'photo', selectionLimit: 1 },
        async (response: any) => {
          if (response.didCancel || response.errorCode) {
            resolve(null);
            return;
          }
          const photo: Photo = {
            id: `photo_${Date.now()}`,
            uri: response.assets?.[0]?.uri || '',
            timestamp: new Date().toISOString(),
            location: (await this.getCurrentLocation()) ?? undefined,
          };
          resolve(photo);
        }
      );
    });
  }

  // ──────────────── GPS ────────────────

  async getCurrentLocation(): Promise<{
    latitude: number;
    longitude: number;
    accuracy: number;
  } | null> {
    return new Promise((resolve) => {
      Geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          });
        },
        (error) => {
          console.error('GPS error:', error);
          resolve(null);
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
      );
    });
  }

  watchLocation(
    onUpdate: (loc: { latitude: number; longitude: number; accuracy: number }) => void
  ): number {
    return Geolocation.watchPosition(
      (position) => {
        onUpdate({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
      },
      (error) => { console.error('GPS watch error:', error); },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 5000, distanceFilter: 10 }
    );
  }

  stopWatchLocation(watchId: number): void {
    Geolocation.clearWatch(watchId);
  }

  // ──────────────── Voice Notes ────────────────

  async startRecording(): Promise<boolean> {
    try {
      await Voice.start('en-US');
      this._isRecording = true;
      this.recordingStartTime = Date.now();
      return true;
    } catch (error) {
      console.error('Recording error:', error);
      return false;
    }
  }

  async stopRecording(): Promise<VoiceNote | null> {
    try {
      const result = (await Voice.stop()) as any;
      this._isRecording = false;
      const duration = (Date.now() - this.recordingStartTime) / 1000;

      return {
        id: `note_${Date.now()}`,
        uri: result?.uri || '',
        duration,
        timestamp: new Date().toISOString(),
        text: result?.value?.[0],
      };
    } catch (error) {
      console.error('Stop recording error:', error);
      return null;
    }
  }

  isCurrentlyRecording(): boolean { return this._isRecording; }

  // ──────────────── Field Summary ────────────────

  async generateFieldSummary(valuationId: string): Promise<{
    photos: number;
    notes: number;
    location: any;
    timestamp: string;
  }> {
    const valuation = await offlineStorage.getValuation(valuationId);
    return {
      photos: valuation?.photos?.length || 0,
      notes: valuation?.notes ? 1 : 0,
      location: valuation?.gps,
      timestamp: new Date().toISOString(),
    };
  }
}

export const fieldTools = new FieldTools();
