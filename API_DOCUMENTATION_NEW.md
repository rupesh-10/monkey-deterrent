# Monkey Detector API Documentation

This API provides real-time monkey detection using YOLO and streams webcam video with detection overlays. It's designed to work seamlessly with React Native apps and web frontends.

## Server Configuration

- **Host:** `0.0.0.0` (accessible from any device on the network)
- **Port:** `5050`
- **CORS:** Enabled for cross-origin requests
- **Base URL:** `http://YOUR_SERVER_IP:5050`

## API Endpoints

### 1. Health Check
**GET /** 

Returns server status to verify the API is running.

**Response:**
```
🐒 Monkey Detector API is running
```

### 2. Webcam Control
**POST /webcam**

Start or stop the webcam capture.

**Request Body:**
```json
{
  "action": "start" | "stop"
}
```

**Responses:**

*Success (Start):*
```json
{
  "status": "webcam started",
  "message": "Camera initialized successfully"
}
```

*Success (Stop):*
```json
{
  "status": "webcam stopped"
}
```

*Error Examples:*
```json
{
  "error": "Cannot open camera"
}
```

### 3. Video Stream
**GET /video**

Returns an MJPEG video stream with real-time monkey detection overlays.

**Requirements:** Webcam must be started first using `/webcam` endpoint.

**Response:** Multipart JPEG stream (`multipart/x-mixed-replace; boundary=frame`)

**Headers:**
- `Cache-Control: no-cache, no-store, must-revalidate`
- `Pragma: no-cache`
- `Expires: 0`

### 4. Detection Status
**GET /detection**

Get the latest monkey detection result.

**Response:**
```json
{
  "detected": true,
  "confidence": 0.95,
  "timestamp": 1693472347.123
}
```

### 5. System Status
**GET /status**

Get comprehensive system status information.

**Response:**
```json
{
  "webcam_active": true,
  "monkey_active": false,
  "latest_detection": {
    "detected": false,
    "confidence": 0.0,
    "timestamp": 1693472347.123
  },
  "timestamp": 1693472347.123
}
```

## React Native Integration

### Installation

First, install required dependencies in your React Native project:

```bash
npm install react-native-webview
# or
yarn add react-native-webview
```

### Implementation

#### 1. Complete React Native Component Example

```jsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Alert,
  StyleSheet,
  Dimensions
} from 'react-native';
import { WebView } from 'react-native-webview';

const MonkeyDetectorApp = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [webcamActive, setWebcamActive] = useState(false);
  const [detectionData, setDetectionData] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Replace with your server's IP address
  const SERVER_URL = 'http://192.168.1.100:5050';
  
  // Check server connection
  const checkConnection = async () => {
    try {
      const response = await fetch(`${SERVER_URL}/`);
      if (response.ok) {
        setIsConnected(true);
        checkStatus();
      }
    } catch (error) {
      setIsConnected(false);
      Alert.alert('Connection Error', 'Cannot connect to monkey detector server');
    }
  };
  
  // Check system status
  const checkStatus = async () => {
    try {
      const response = await fetch(`${SERVER_URL}/status`);
      const data = await response.json();
      setWebcamActive(data.webcam_active);
      setDetectionData(data.latest_detection);
    } catch (error) {
      console.error('Status check failed:', error);
    }
  };
  
  // Start webcam
  const startWebcam = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${SERVER_URL}/webcam`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'start' }),
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setWebcamActive(true);
        Alert.alert('Success', 'Webcam started successfully');
      } else {
        Alert.alert('Error', result.error || 'Failed to start webcam');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  // Stop webcam
  const stopWebcam = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${SERVER_URL}/webcam`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'stop' }),
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setWebcamActive(false);
        Alert.alert('Success', 'Webcam stopped');
      } else {
        Alert.alert('Error', result.error || 'Failed to stop webcam');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch detection data periodically
  useEffect(() => {
    if (!webcamActive) return;
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${SERVER_URL}/detection`);
        const data = await response.json();
        setDetectionData(data);
      } catch (error) {
        console.error('Detection fetch failed:', error);
      }
    }, 1000); // Update every second
    
    return () => clearInterval(interval);
  }, [webcamActive]);
  
  // Check connection on mount
  useEffect(() => {
    checkConnection();
  }, []);
  
  return (
    <View style={styles.container}>
      <Text style={styles.title}>🐒 Monkey Detector</Text>
      
      {/* Connection Status */}
      <View style={styles.statusContainer}>
        <Text style={[styles.status, { color: isConnected ? 'green' : 'red' }]}>
          Server: {isConnected ? 'Connected' : 'Disconnected'}
        </Text>
        <Text style={[styles.status, { color: webcamActive ? 'green' : 'orange' }]}>
          Webcam: {webcamActive ? 'Active' : 'Inactive'}
        </Text>
      </View>
      
      {/* Detection Status */}
      {detectionData && (
        <View style={styles.detectionContainer}>
          <Text style={styles.detectionTitle}>Detection Status:</Text>
          <Text style={[styles.detectionText, { color: detectionData.detected ? 'red' : 'green' }]}>
            {detectionData.detected ? 
              `🚨 MONKEY DETECTED! (${(detectionData.confidence * 100).toFixed(1)}%)` : 
              '✅ No monkeys detected'
            }
          </Text>
        </View>
      )}
      
      {/* Control Buttons */}
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={[styles.button, styles.connectButton]} 
          onPress={checkConnection}
        >
          <Text style={styles.buttonText}>Refresh Connection</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.button, webcamActive ? styles.stopButton : styles.startButton]} 
          onPress={webcamActive ? stopWebcam : startWebcam}
          disabled={loading || !isConnected}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Loading...' : webcamActive ? 'Stop Webcam' : 'Start Webcam'}
          </Text>
        </TouchableOpacity>
      </View>
      
      {/* Video Stream */}
      {isConnected && webcamActive && (
        <View style={styles.videoContainer}>
          <Text style={styles.videoTitle}>Live Feed:</Text>
          <WebView
            source={{ uri: `${SERVER_URL}/video` }}
            style={styles.webview}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            startInLoadingState={true}
            scalesPageToFit={true}
            onError={(error) => {
              console.error('WebView error:', error);
              Alert.alert('Video Error', 'Failed to load video stream');
            }}
          />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
    marginTop: 40,
  },
  statusContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 20,
  },
  status: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
  },
  detectionContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 20,
  },
  detectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  detectionText: {
    fontSize: 14,
    fontWeight: '600',
  },
  buttonContainer: {
    marginBottom: 20,
  },
  button: {
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    alignItems: 'center',
  },
  connectButton: {
    backgroundColor: '#007AFF',
  },
  startButton: {
    backgroundColor: '#34C759',
  },
  stopButton: {
    backgroundColor: '#FF3B30',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  videoContainer: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 10,
  },
  videoTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
    textAlign: 'center',
  },
  webview: {
    flex: 1,
    borderRadius: 5,
  },
});

export default MonkeyDetectorApp;
```

#### 2. Simple Video Display Only

If you only need to display the video stream:

```jsx
import React from 'react';
import { View, Text } from 'react-native';
import { WebView } from 'react-native-webview';

const SimpleVideoStream = () => {
  const SERVER_URL = 'http://192.168.1.100:5050'; // Replace with your server IP
  
  return (
    <View style={{ flex: 1 }}>
      <Text style={{ textAlign: 'center', fontSize: 18, margin: 20 }}>
        Monkey Detection Live Feed
      </Text>
      <WebView
        source={{ uri: `${SERVER_URL}/video` }}
        style={{ flex: 1 }}
        javaScriptEnabled={true}
      />
    </View>
  );
};

export default SimpleVideoStream;
```

### Usage Steps

1. **Setup Server:**
   ```bash
   cd /path/to/monkey-deterrent/app
   python app.py
   ```

2. **Find Server IP:**
   - On Windows: `ipconfig`
   - On Linux/Mac: `ifconfig` or `ip addr`
   - Update `SERVER_URL` in your React Native code

3. **Start Webcam:**
   - Call the `/webcam` endpoint with `{"action": "start"}`
   - Or use the button in the React Native app

4. **View Stream:**
   - Access `/video` endpoint through WebView
   - The stream will show live detection overlays

### Network Requirements

- **Same Network:** Both server and React Native device must be on the same WiFi network
- **Firewall:** Ensure port 5050 is not blocked
- **IP Address:** Use the actual IP address of the server, not `localhost` or `127.0.0.1`

### Troubleshooting

#### Common Issues:

1. **Connection Refused:**
   - Check if server is running
   - Verify IP address and port
   - Check firewall settings

2. **Video Not Loading:**
   - Ensure webcam is started via `/webcam` endpoint
   - Check if camera is available on server
   - Try refreshing the WebView

3. **Detection Not Working:**
   - Verify YOLO model (`best.pt`) is present
   - Check console logs for errors
   - Ensure sufficient lighting for camera

#### Debug Commands:

```bash
# Test server connection
curl http://YOUR_SERVER_IP:5050/

# Test webcam start
curl -X POST http://YOUR_SERVER_IP:5050/webcam \
  -H "Content-Type: application/json" \
  -d '{"action": "start"}'

# Test detection status
curl http://YOUR_SERVER_IP:5050/detection
```

## Technical Notes

- **Frame Rate:** Optimized for ~30 FPS
- **Resolution:** 640x480 for better performance
- **JPEG Quality:** 85% for good quality/performance balance
- **Detection Confidence:** 50% threshold
- **Alert Cooldown:** 3-4 seconds to prevent spam

---

For additional customization or troubleshooting, refer to the source code in `app.py`.
