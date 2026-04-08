import React, { useState } from 'react';
import {
  StyleSheet, View, Text, TextInput, TouchableOpacity,
  Alert, ActivityIndicator, SafeAreaView, ScrollView, StatusBar,
} from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import * as MediaLibrary from 'expo-media-library';

// 10.0.2.2 = host Mac when running in Android emulator
// Change to your Mac's Wi-Fi IP (e.g. 192.168.1.89) when using a real phone
const SERVER_IP = '10.0.2.2';
const SERVER_URL = `http://${SERVER_IP}:8080`;

export default function App() {
  const [videoUrl, setVideoUrl] = useState('');
  const [status, setStatus] = useState('');
  const [statusType, setStatusType] = useState('idle'); // idle | loading | success | error
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    const url = videoUrl.trim();

    if (!url) {
      setStatus('Please paste a Meta AI share URL.');
      setStatusType('error');
      return;
    }

    setIsDownloading(true);
    setProgress(0);
    setProgressLabel('');
    setStatus('');

    try {
      // Step 1: Extract CDN URL via Flask
      setStatus('Analyzing link — may take up to 30 seconds…');
      setStatusType('loading');

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const infoRes = await fetch(`${SERVER_URL}/api/info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const infoData = await infoRes.json();
      if (!infoRes.ok) throw new Error(infoData.error || `Server error ${infoRes.status}`);

      const { video_url: cdnUrl, title = 'meta_ai_video', ext = 'mp4' } = infoData;
      const safeTitle = title.replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '_') || 'meta_ai_video';
      const fileName = `${safeTitle}_${Date.now()}.${ext}`;
      const destination = FileSystem.cacheDirectory + fileName;

      setStatus(`Found video. Requesting storage permission…`);

      // Step 2: Request permission
      const { status: permStatus, canAskAgain } = await MediaLibrary.requestPermissionsAsync();
      if (permStatus !== 'granted') {
        if (!canAskAgain) {
          Alert.alert(
            'Permission Required',
            'Go to Settings → Apps → Expo Go → Permissions → Media → Allow All',
            [{ text: 'OK' }]
          );
        }
        throw new Error('Storage permission denied.');
      }

      // Step 3: Download from CDN with progress
      setStatus('Downloading video…');
      setStatusType('loading');

      const downloadResumable = FileSystem.createDownloadResumable(
        cdnUrl,
        destination,
        {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
            'Referer': 'https://www.meta.ai/',
          },
        },
        ({ totalBytesWritten, totalBytesExpectedToWrite }) => {
          if (totalBytesExpectedToWrite > 0) {
            const pct = totalBytesWritten / totalBytesExpectedToWrite;
            setProgress(pct);
            setProgressLabel(`${Math.round(pct * 100)}%`);
          } else {
            const mb = (totalBytesWritten / 1024 / 1024).toFixed(1);
            setProgressLabel(`${mb} MB downloaded`);
          }
        }
      );

      const result = await downloadResumable.downloadAsync();
      if (!result) throw new Error('Download failed — no result returned.');
      const { uri } = result;

      // Step 4: Save to gallery
      setStatus('Saving to gallery…');
      const asset = await MediaLibrary.createAssetAsync(uri);
      const album = await MediaLibrary.getAlbumAsync('Meta AI Videos');
      if (album == null) {
        await MediaLibrary.createAlbumAsync('Meta AI Videos', asset, true);
      } else {
        await MediaLibrary.addAssetsToAlbumAsync([asset], album, true);
      }

      // Cleanup cache
      await FileSystem.deleteAsync(uri, { idempotent: true });

      setStatus('Downloaded! Saved to "Meta AI Videos" album in your gallery.');
      setStatusType('success');
      setProgress(1);
      setProgressLabel('100%');
      setVideoUrl('');

    } catch (err) {
      const msg = err.name === 'AbortError'
        ? 'Request timed out. Make sure Flask is running on your Mac.'
        : err.message;
      setStatus(`Error: ${msg}`);
      setStatusType('error');
    } finally {
      setIsDownloading(false);
    }
  };

  const statusBg    = { idle: 'transparent', loading: '#e8f0fe', success: '#e6f4ea', error: '#fdecea' }[statusType];
  const statusColor = { idle: '#444', loading: '#1a56db', success: '#1e7e34', error: '#c62828' }[statusType];

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor="#f0f2f5" />
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>

          {/* Header */}
          <View style={styles.logoRow}>
            <View style={styles.logoIcon}>
              <Text style={styles.logoText}>▼</Text>
            </View>
            <Text style={styles.title}>Meta AI Downloader</Text>
          </View>
          <Text style={styles.subtitle}>
            Paste a Meta AI "Copy Link" URL to download the video to your gallery.
          </Text>

          {/* Video URL */}
          <Text style={styles.label}>Video Share URL</Text>
          <TextInput
            style={[styles.input, styles.inputMulti]}
            placeholder="https://www.meta.ai/s/..."
            value={videoUrl}
            onChangeText={setVideoUrl}
            autoCapitalize="none"
            autoCorrect={false}
            multiline
          />

          {/* Button */}
          <TouchableOpacity
            style={[styles.button, isDownloading && styles.buttonDisabled]}
            onPress={handleDownload}
            disabled={isDownloading}
            activeOpacity={0.85}
          >
            {isDownloading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.buttonText}>Download Video</Text>
            }
          </TouchableOpacity>

          {/* Progress */}
          {progressLabel !== '' && (
            <View style={styles.progressWrap}>
              <View style={styles.progressTrack}>
                <View style={[styles.progressBar, { width: `${Math.min(progress * 100, 100)}%` }]} />
              </View>
              <Text style={styles.progressLabel}>{progressLabel}</Text>
            </View>
          )}

          {/* Status */}
          {status !== '' && (
            <View style={[styles.statusBox, { backgroundColor: statusBg }]}>
              <Text style={[styles.statusText, { color: statusColor }]}>{status}</Text>
            </View>
          )}

        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe:           { flex: 1, backgroundColor: '#f0f2f5' },
  container:      { flexGrow: 1, justifyContent: 'center', padding: 20 },
  card:           { backgroundColor: '#fff', borderRadius: 16, padding: 28,
                    shadowColor: '#000', shadowOpacity: 0.10, shadowRadius: 12, elevation: 6 },
  logoRow:        { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  logoIcon:       { width: 36, height: 36, borderRadius: 10, marginRight: 10,
                    backgroundColor: '#0066ff', justifyContent: 'center', alignItems: 'center' },
  logoText:       { color: '#fff', fontSize: 18 },
  title:          { fontSize: 18, fontWeight: '700', color: '#1a1a2e', flex: 1 },
  subtitle:       { color: '#888', fontSize: 13, marginBottom: 22 },
  label:          { fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 6 },
  input:          { borderWidth: 1.5, borderColor: '#ddd', borderRadius: 8,
                    padding: 12, fontSize: 15, color: '#222' },
  inputMulti:     { minHeight: 70, textAlignVertical: 'top' },
  button:         { marginTop: 20, padding: 14, borderRadius: 8,
                    backgroundColor: '#0066ff', alignItems: 'center' },
  buttonDisabled: { backgroundColor: '#b0bec5' },
  buttonText:     { color: '#fff', fontSize: 16, fontWeight: '600' },
  progressWrap:   { marginTop: 14 },
  progressTrack:  { height: 8, backgroundColor: '#e0e0e0', borderRadius: 4, overflow: 'hidden' },
  progressBar:    { height: '100%', backgroundColor: '#0066ff', borderRadius: 4 },
  progressLabel:  { textAlign: 'center', fontSize: 12, color: '#555', marginTop: 4 },
  statusBox:      { marginTop: 16, padding: 14, borderRadius: 8 },
  statusText:     { fontSize: 14, lineHeight: 20 },
});
