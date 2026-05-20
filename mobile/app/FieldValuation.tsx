/**
 * Main field valuation screen.
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from 'react-native';
import { TextInput } from 'react-native-gesture-handler';
import { offlineStorage } from './OfflineStorage';
import { fieldTools, Photo, VoiceNote } from './FieldTools';
import { syncEngine } from './SyncEngine';
import { fieldApiClient } from '../api/FieldApiClient';

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: { padding: 16, backgroundColor: '#203864', color: '#fff' },
  headerText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  offlineBanner: { backgroundColor: '#ff9800', padding: 12, alignItems: 'center' },
  offlineText: { color: '#fff', fontWeight: 'bold' },
  content: { flex: 1, padding: 16 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 14, fontWeight: 'bold', marginBottom: 8, color: '#333' },
  input: { borderWidth: 1, borderColor: '#ddd', borderRadius: 8, padding: 12, fontSize: 14 },
  buttonRow: { flexDirection: 'row', gap: 12, marginBottom: 16 },
  button: { flex: 1, backgroundColor: '#203864', padding: 12, borderRadius: 8, alignItems: 'center' },
  buttonText: { color: '#fff', fontWeight: 'bold' },
  photoGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  photo: { width: 100, height: 100, borderRadius: 8 },
  stats: { flexDirection: 'row', justifyContent: 'space-around', padding: 16, backgroundColor: '#f5f5f5', borderRadius: 8 },
  statItem: { alignItems: 'center' },
  statValue: { fontSize: 18, fontWeight: 'bold', color: '#203864' },
  statLabel: { fontSize: 12, color: '#666' },
});

interface FieldValuationProps {
  tenantId: string;
}

export const FieldValuation: React.FC<FieldValuationProps> = ({ tenantId }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(fieldApiClient.isCurrentlyOnline());
  const [isSyncing, setIsSyncing] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  const [valuationId, setValuationId] = useState('');
  const [location, setLocation] = useState('');
  const [areaSqm, setAreaSqm] = useState('');
  const [propertyType, setPropertyType] = useState('residential');
  const [notes, setNotes] = useState('');
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [voiceNotes, setVoiceNotes] = useState<VoiceNote[]>([]);

  const [stats, setStats] = useState({
    totalValuations: 0,
    draftValuations: 0,
    completedValuations: 0,
    pendingSyncs: 0,
  });

  useEffect(() => {
    initializeValuation();
    loadStats();

    const interval = setInterval(() => {
      setIsOnline(fieldApiClient.isCurrentlyOnline());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const initializeValuation = async () => {
    const loc = await fieldTools.getCurrentLocation();
    if (loc) {
      setLocation(`${loc.latitude}, ${loc.longitude}`);
    }
  };

  const loadStats = async () => {
    const newStats = await offlineStorage.getStorageStats();
    setStats({
      totalValuations: newStats.totalValuations,
      draftValuations: newStats.draftValuations,
      completedValuations: newStats.completedValuations,
      pendingSyncs: newStats.pendingSyncs,
    });
  };

  const handleTakePhoto = async () => {
    setIsLoading(true);
    try {
      const photo = await fieldTools.takePhoto(valuationId);
      if (photo) setPhotos([...photos, photo]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartRecording = async () => {
    const success = await fieldTools.startRecording();
    if (success) setIsRecording(true);
  };

  const handleStopRecording = async () => {
    const note = await fieldTools.stopRecording();
    if (note) {
      setVoiceNotes([...voiceNotes, note]);
      setIsRecording(false);
    }
  };

  const handleSaveValuation = async () => {
    if (!areaSqm || !propertyType) {
      Alert.alert('Error', 'Please fill in required fields');
      return;
    }

    setIsLoading(true);
    try {
      const id = await offlineStorage.saveValuation({
        propertyId: `prop_${Date.now()}`,
        location,
        propertyType,
        areaSqm: parseFloat(areaSqm),
        comparables: [],
        primaryValue: 0,
        methodology: 'Field evaluation',
        status: 'draft',
        photos: photos.map((p) => p.uri),
        notes,
        gps: { latitude: 0, longitude: 0, accuracy: 0 },
        tenantId,
        syncStatus: 'pending',
      });

      setValuationId(id);
      Alert.alert('Success', 'Valuation saved locally');
      await loadStats();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSync = async () => {
    if (!isOnline) {
      Alert.alert('Offline', 'Cannot sync while offline');
      return;
    }

    setIsSyncing(true);
    try {
      const result = await syncEngine.startSync(tenantId);
      Alert.alert(
        'Sync Complete',
        `Success: ${result.success}, Failed: ${result.failed}, Conflicts: ${result.conflicts.length}`
      );
      await loadStats();
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerText}>Field Valuation</Text>
      </View>

      {!isOnline && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>Offline Mode - Changes will sync when online</Text>
        </View>
      )}

      <ScrollView style={styles.content}>
        <View style={styles.stats}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.totalValuations}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.draftValuations}</Text>
            <Text style={styles.statLabel}>Draft</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.pendingSyncs}</Text>
            <Text style={styles.statLabel}>Pending Sync</Text>
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Location</Text>
          <TextInput
            style={styles.input}
            placeholder="Address or coordinates"
            value={location}
            onChangeText={setLocation}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Area (sqm)</Text>
          <TextInput
            style={styles.input}
            placeholder="150"
            value={areaSqm}
            onChangeText={setAreaSqm}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Property Type</Text>
          <View style={styles.buttonRow}>
            {['residential', 'commercial', 'land'].map((type) => (
              <TouchableOpacity
                key={type}
                style={[styles.button, propertyType === type && { backgroundColor: '#4CAF50' }]}
                onPress={() => setPropertyType(type)}
              >
                <Text style={styles.buttonText}>{type}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Photos ({photos.length})</Text>
          <TouchableOpacity style={styles.button} onPress={handleTakePhoto}>
            <Text style={styles.buttonText}>Take Photo</Text>
          </TouchableOpacity>
          {photos.length > 0 && (
            <View style={[styles.photoGrid, { marginTop: 12 }]}>
              {photos.map((photo) => (
                <Image key={photo.id} source={{ uri: photo.uri }} style={styles.photo} />
              ))}
            </View>
          )}
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Voice Notes ({voiceNotes.length})</Text>
          <TouchableOpacity
            style={[styles.button, isRecording && { backgroundColor: '#f44336' }]}
            onPress={isRecording ? handleStopRecording : handleStartRecording}
          >
            <Text style={styles.buttonText}>
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Notes</Text>
          <TextInput
            style={[styles.input, { minHeight: 100 }]}
            placeholder="Additional notes..."
            value={notes}
            onChangeText={setNotes}
          />
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity style={styles.button} onPress={handleSaveValuation} disabled={isLoading}>
            {isLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Save</Text>
            )}
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.button}
            onPress={handleSync}
            disabled={isSyncing || !isOnline}
          >
            {isSyncing ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sync</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );
};
