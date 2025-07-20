# Monkey Detection API Documentation

**Base URL:** `http://your-server-ip:5050`

## Authentication
No authentication required for current endpoints.

## Endpoints

### 1. Get Detection Status
**GET** `/api/status`

Returns current detection system status.

**Response:**
```json
{
  "is_detecting": true,
  "monkey_active": false,
  "video_source": "webcam",
  "last_seen": 1703123456.789,
  "last_missing": 1703123450.123
}
```

### 2. Start Detection
**POST** `/api/start_detection`

Start monkey detection with specified video source.

**Request Body:**
```json
{
  "source": "webcam" | "youtube",
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID" // Required if source is "youtube"
}
```

**Response:**
```json
{
  "message": "Detection started successfully",
  "source": "webcam"
}
```

**Error Response:**
```json
{
  "error": "Failed to open video source"
}
```

### 3. Stop Detection
**POST** `/api/stop_detection`

Stop monkey detection and release video resources.

**Request Body:** Empty

**Response:**
```json
{
  "message": "Detection stopped successfully"
}
```

### 4. Get Detection History
**GET** `/api/detections`

Retrieve monkey detection history with optional filtering.

**Query Parameters:**
- `limit` (optional): Number of records to return (default: 50, max: 100)
- `days` (optional): Filter detections from last N days

**Example:** `GET /api/detections?limit=20&days=7`

**Response:**
```json
{
  "detections": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:45.123456",
      "confidence": 0.85,
      "location_x": 320.5,
      "location_y": 240.2,
      "image_path": null,
      "video_source": "webcam"
    }
  ],
  "total": 1
}
```

### 5. Get Detection Statistics
**GET** `/api/detections/stats`

Get detection statistics for specified period.

**Query Parameters:**
- `days` (optional): Statistics for last N days (default: 7)

**Example:** `GET /api/detections/stats?days=30`

**Response:**
```json
{
  "total_detections": 45,
  "today_detections": 3,
  "period_days": 30
}
```

### 6. Video Stream
**GET** `/api/video_stream`

Stream live video feed with detection overlays.

**Response:** Multipart JPEG stream (MIME: `multipart/x-mixed-replace`)

**Usage in React Native:**
```javascript
// Use with Image component
<Image 
  source={{ uri: 'http://your-server-ip:5050/api/video_stream' }}
  style={{ width: 300, height: 200 }}
/>
```

## Data Models

### Detection Object
```json
{
  "id": "integer",
  "timestamp": "ISO 8601 datetime string",
  "confidence": "float (0.0-1.0)",
  "location_x": "float | null",
  "location_y": "float | null", 
  "image_path": "string | null",
  "video_source": "string"
}
```

### Status Object
```json
{
  "is_detecting": "boolean",
  "monkey_active": "boolean",
  "video_source": "string",
  "last_seen": "timestamp | null",
  "last_missing": "timestamp | null"
}
```

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Error description"
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `500`: Server Error

## React Native Implementation Examples

### Using Fetch API
```javascript
// Start detection
const startDetection = async (source = 'webcam', youtubeUrl = null) => {
  try {
    const response = await fetch('http://your-server-ip:5050/api/start_detection', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        source,
        youtube_url: youtubeUrl
      })
    });
    return await response.json();
  } catch (error) {
    console.error('Error starting detection:', error);
  }
};

// Get detection history
const getDetections = async (limit = 50, days = null) => {
  try {
    let url = `http://your-server-ip:5050/api/detections?limit=${limit}`;
    if (days) url += `&days=${days}`;
    
    const response = await fetch(url);
    return await response.json();
  } catch (error) {
    console.error('Error fetching detections:', error);
  }
};

// Get status
const getStatus = async () => {
  try {
    const response = await fetch('http://your-server-ip:5050/api/status');
    return await response.json();
  } catch (error) {
    console.error('Error fetching status:', error);
  }
};
```

### Using Axios
```javascript
import axios from 'axios';

const API_BASE = 'http://your-server-ip:5050';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

// Start detection
const startDetection = (source = 'webcam', youtubeUrl = null) => {
  return api.post('/api/start_detection', {
    source,
    youtube_url: youtubeUrl
  });
};

// Get detections
const getDetections = (limit = 50, days = null) => {
  const params = { limit };
  if (days) params.days = days;
  return api.get('/api/detections', { params });
};

// Get status
const getStatus = () => {
  return api.get('/api/status');
};
``` 