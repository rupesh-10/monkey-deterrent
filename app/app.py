from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import threading
import pygame
import time
import torch
import os
import logging
from datetime import datetime
from flask import send_file
import numpy as np
import requests
from PIL import Image
import io

# Suppress ultralytics verbose output
os.environ['YOLO_VERBOSE'] = 'False'
logging.getLogger('ultralytics').setLevel(logging.WARNING)

# Explicitly allowlist custom YOLO modules (new PyTorch 2.6+ safe loading requirement)
from ultralytics.nn.modules.conv import Conv
from ultralytics.nn.modules.block import C2f, Bottleneck, C3
from ultralytics.nn.modules.head import Detect
from ultralytics.nn.tasks import DetectionModel
from torch.nn.modules.container import Sequential

# Allowlist all YOLO custom classes
try:
    torch.serialization.add_safe_globals([
        DetectionModel, Sequential, Conv, C2f, Bottleneck, C3, Detect
    ])
except AttributeError:
    pass  # For older PyTorch versions

app = Flask(__name__)
CORS(app)  # Enable CORS for React Native or browser

# Load YOLO model (v8 or v11 as per your weights)
model = YOLO("../best.pt")  # Back to ../best.pt for correct path from app directory

class PiCameraStream:
    """A class to handle Pi camera MJPEG stream using requests"""
    def __init__(self, url):
        self.url = url
        self.session = None
        self.stream = None
        self.connected = False
        
    def connect(self):
        """Connect to the Pi camera stream"""
        try:
            self.session = requests.Session()
            self.stream = self.session.get(self.url, stream=True, timeout=10)
            if self.stream.status_code == 200:
                self.connected = True
                print(f"✅ Pi camera stream connected via requests")
                return True
            else:
                print(f"❌ Pi camera stream error: {self.stream.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to connect to Pi camera stream: {e}")
            return False
    
    def read_frame(self):
        """Read a frame from the MJPEG stream"""
        if not self.connected or not self.stream:
            return False, None
            
        try:
            # Read MJPEG boundary
            boundary = b'\r\n\r\n'
            chunk_size = 1024
            
            # Find the start of a frame
            data = b''
            while boundary not in data:
                chunk = self.stream.raw.read(chunk_size)
                if not chunk:
                    return False, None
                data += chunk
            
            # Find JPEG start marker
            jpeg_start = data.find(b'\xff\xd8')
            if jpeg_start == -1:
                return False, None
            
            # Read until JPEG end marker
            jpeg_data = data[jpeg_start:]
            while b'\xff\xd9' not in jpeg_data:
                chunk = self.stream.raw.read(chunk_size)
                if not chunk:
                    return False, None
                jpeg_data += chunk
            
            # Extract complete JPEG
            jpeg_end = jpeg_data.find(b'\xff\xd9') + 2
            jpeg_data = jpeg_data[:jpeg_end]
            
            # Convert to OpenCV format
            image = Image.open(io.BytesIO(jpeg_data))
            frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            return True, frame
            
        except Exception as e:
            print(f"Error reading frame from Pi camera: {e}")
            return False, None
    
    def release(self):
        """Release the connection"""
        self.connected = False
        if self.stream:
            self.stream.close()
        if self.session:
            self.session.close()

def create_pi_camera_capture():
    """Create a more robust video capture for Pi camera MJPEG stream"""
    try:
        # First, verify the Pi camera is accessible
        print(f"Testing Pi camera accessibility at {PI_CAMERA_URL}")
        response = requests.get(PI_CAMERA_URL, timeout=10, stream=True)
        if response.status_code != 200:
            print(f"Pi camera not accessible: HTTP {response.status_code}")
            return None
        
        print(f"✅ Pi camera HTTP accessible (Status: {response.status_code})")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        response.close()
        
        # Method 1: Try OpenCV VideoCapture first
        print("Method 1: Trying OpenCV VideoCapture...")
        
        backends_to_try = [
            (cv2.CAP_FFMPEG, "FFMPEG"),
            (cv2.CAP_GSTREAMER, "GSTREAMER"), 
            (cv2.CAP_ANY, "ANY")
        ]
        
        for backend, name in backends_to_try:
            try:
                print(f"Trying OpenCV backend: {name} ({backend})")
                cap = cv2.VideoCapture(PI_CAMERA_URL, backend)
                
                if cap.isOpened():
                    # Set properties that might help with MJPEG streams
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FPS, 15)
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    
                    # Test frame capture with timeout
                    print(f"Testing frame capture with {name} backend...")
                    start_time = time.time()
                    
                    while time.time() - start_time < 10:  # 10 second timeout
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            print(f"✅ Pi camera working with OpenCV {name} backend!")
                            print(f"Frame shape: {frame.shape}")
                            return cap
                        time.sleep(0.5)
                    
                    print(f"❌ {name} backend: No valid frames received within timeout")
                    cap.release()
                else:
                    print(f"❌ Could not open Pi camera with {name} backend")
            except Exception as e:
                print(f"❌ Error with {name} backend: {e}")
        
        # Method 2: Try requests-based MJPEG stream parser
        print("Method 2: Trying requests-based MJPEG parser...")
        pi_stream = PiCameraStream(PI_CAMERA_URL)
        if pi_stream.connect():
            # Test frame reading
            ret, frame = pi_stream.read_frame()
            if ret and frame is not None:
                print(f"✅ Pi camera working with requests-based parser!")
                print(f"Frame shape: {frame.shape}")
                return pi_stream
            else:
                print("❌ Requests-based parser: Could not read frames")
                pi_stream.release()
        
        print("❌ All methods failed for Pi camera")
        return None
            
    except Exception as e:
        print(f"❌ Error creating Pi camera capture: {e}")
        return None

# Sound setup
pygame.mixer.init()
alert_sound = pygame.mixer.Sound("../alert.wav")  # Back to ../alert.wav for correct path from app directory
is_playing = False
lock = threading.Lock()

# Webcam state
video_capture = None
webcam_active = False
PI_CAMERA_URL = "http://192.168.1.96:5000/video"  # Raspberry Pi camera stream

# Create directory for saved detections
DETECTIONS_DIR = "detections"
if not os.path.exists(DETECTIONS_DIR):
    os.makedirs(DETECTIONS_DIR)

# Monkey alert state
monkey_last_seen = 0
monkey_last_missing = 0
monkey_active = False
saved_detections = []  # List to store detection info
latest_detection = {
    'detected': False,
    'confidence': 0.0,
    'timestamp': None,
    'image_path': None
}

def play_alert():
    global is_playing
    with lock:
        if not is_playing:
            is_playing = True
            # alert_sound.play(-1)

def stop_alert():
    global is_playing
    with lock:
        if is_playing:
            # alert_sound.stop()
            is_playing = False

def save_detection_image(frame, confidence):
    """Save detection image with timestamp"""
    try:
        timestamp = datetime.now()
        filename = f"monkey_detected_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(DETECTIONS_DIR, filename)
        
        # Save the frame
        cv2.imwrite(filepath, frame)
        
        # Add to saved detections list
        detection_info = {
            'timestamp': timestamp.isoformat(),
            'confidence': confidence,
            'filename': filename,
            'filepath': filepath
        }
        saved_detections.append(detection_info)
        
        # Keep only last 50 detections to prevent disk overflow
        if len(saved_detections) > 50:
            old_detection = saved_detections.pop(0)
            if os.path.exists(old_detection['filepath']):
                os.remove(old_detection['filepath'])
        
        print(f"Saved detection image: {filename} (confidence: {confidence:.2f})")
        return filename
    except Exception as e:
        print(f"Error saving detection image: {e}")
        return None

def gen_frames():
    global monkey_last_seen, monkey_last_missing, monkey_active, video_capture, latest_detection
    
    print("Starting video frame generation...")
    frame_count = 0
    
    while webcam_active:
        try:
            if video_capture is None:
                print("Video capture is None, waiting...")
                time.sleep(0.1)
                continue

            # Handle different types of camera captures
            if isinstance(video_capture, PiCameraStream):
                # Use our custom Pi camera stream
                success, frame = video_capture.read_frame()
            else:
                # Use OpenCV VideoCapture
                success, frame = video_capture.read()
                
            if not success:
                print("Failed to read from camera, retrying...")
                time.sleep(0.1)
                continue

            frame_count += 1
            if frame_count % 30 == 0:  # Log every 30 frames
                print(f"Processing frame {frame_count}")

            # Check if frame is valid
            if frame is None or frame.size == 0:
                print("Invalid frame received")
                continue

            # Resize frame for better performance
            try:
                frame = cv2.resize(frame, (640, 480))
            except Exception as e:
                print(f"Error resizing frame: {e}")
                continue

            # Detection with YOLO (suppress verbose output)
            try:
                results = model(frame, imgsz=640, conf=0.5, verbose=False)
                annotated_frame = results[0].plot()
            except Exception as e:
                print(f"Error in YOLO detection: {e}")
                # Use original frame if detection fails
                annotated_frame = frame

            monkey_now_detected = False
            max_conf = 0.0

            # Check if there are any detected objects
            try:
                if results[0].boxes is not None:
                    # Loop over detected objects
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0].item())
                        cls_name = model.names[cls_id]
                        conf = float(box.conf[0].item())

                        if cls_name.lower() == "monkey":
                            monkey_now_detected = True
                            max_conf = max(max_conf, conf)
                            print(f"🐒 MONKEY DETECTED! Confidence: {conf:.2f}")
                            break
            except Exception as e:
                print(f"Error processing detections: {e}")

            current_time = time.time()

            if monkey_now_detected:
                monkey_last_seen = current_time
                
                # Save detection image
                try:
                    saved_filename = save_detection_image(annotated_frame, max_conf)
                except Exception as e:
                    print(f"Error saving detection image: {e}")
                    saved_filename = None
                
                latest_detection = { 
                    'detected': True,
                    'confidence': max_conf,
                    'timestamp': current_time,
                    'image_path': saved_filename
                }

                # Avoid sound spam: wait 3-4 sec if previously missed
                if not monkey_active and (current_time - monkey_last_missing) > 3:
                    play_alert()
                    monkey_active = True
            else:
                monkey_last_missing = current_time
                latest_detection = {
                    'detected': False,
                    'confidence': 0.0,
                    'timestamp': current_time,
                    'image_path': None
                }

                # Stop if no monkey for 3-4 seconds
                if monkey_active and (current_time - monkey_last_seen) > 4:
                    stop_alert()
                    monkey_active = False

            # Encode frame to JPEG with better quality for React Native
            try:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                ret, buffer = cv2.imencode('.jpg', annotated_frame, encode_param)
                
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    print("Failed to encode frame")
            except Exception as e:
                print(f"Error encoding frame: {e}")
            
        except Exception as e:
            print(f"Error in gen_frames: {e}")
            time.sleep(0.1)
            continue
    
    print("Frame generation stopped")

@app.route('/')
def index():
    return "🐒 Monkey Detector API is running"

@app.route('/webcam', methods=['POST'])
def webcam_control():
    global video_capture, webcam_active
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        action = data.get('action')
        
        if action == 'start':
            if not webcam_active:
                try:
                    print(f"Attempting to connect to Raspberry Pi camera: {PI_CAMERA_URL}")
                    
                    # Try to create Pi camera capture using our enhanced function
                    video_capture = create_pi_camera_capture()
                    
                    if video_capture is None:
                        print("Failed to connect to Raspberry Pi camera, trying local webcam as fallback...")
                        video_capture = cv2.VideoCapture(0)
                        
                        if not video_capture.isOpened():
                            return jsonify({"error": "Cannot open Raspberry Pi camera or local webcam"}), 500
                        camera_source = "Local Webcam (fallback)"
                        
                        # Set properties for local webcam
                        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    else:
                        # Determine the camera source type
                        if isinstance(video_capture, PiCameraStream):
                            camera_source = "Raspberry Pi Camera (requests-based)"
                        else:
                            camera_source = "Raspberry Pi Camera (OpenCV)"
                            # Set properties for OpenCV-based Pi camera
                            try:
                                video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            except:
                                pass  # Some backends might not support these properties
                        
                        print(f"Successfully created Pi camera capture: {camera_source}")
                    
                    webcam_active = True
                    print(f"Camera started successfully: {camera_source}")
                    return jsonify({
                        "status": "webcam started", 
                        "message": f"Camera initialized successfully using {camera_source}",
                        "source": camera_source
                    }), 200
                except Exception as e:
                    print(f"Error starting camera: {e}")
                    # Clean up if there was an error
                    if video_capture is not None:
                        if isinstance(video_capture, PiCameraStream):
                            video_capture.release()  # Custom release method
                        else:
                            video_capture.release()  # OpenCV release method
                        video_capture = None
                    return jsonify({"error": f"Failed to start camera: {str(e)}"}), 500
            else:
                return jsonify({"status": "webcam already running"}), 200
                
        elif action == 'stop':
            if webcam_active and video_capture is not None:
                # Handle different camera object types
                if isinstance(video_capture, PiCameraStream):
                    video_capture.release()  # Custom release method
                else:
                    video_capture.release()  # OpenCV release method
                video_capture = None
                webcam_active = False
                stop_alert()
                print("Camera stopped")
                return jsonify({"status": "webcam stopped"}), 200
            else:
                return jsonify({"status": "webcam already stopped"}), 200
        else:
            return jsonify({"error": "Invalid action. Use 'start' or 'stop'"}), 400
            
    except Exception as e:
        print(f"Server error in webcam_control: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/detection', methods=['GET'])
def get_detection():
    global latest_detection
    return jsonify(latest_detection)

@app.route('/status', methods=['GET'])
def get_status():
    """Get overall system status"""
    global webcam_active, monkey_active, latest_detection
    
    # Check Pi camera connectivity
    pi_camera_status = "unknown"
    try:
        response = requests.get(PI_CAMERA_URL, timeout=5)
        pi_camera_status = "online" if response.status_code == 200 else "offline"
    except:
        pi_camera_status = "offline"
    
    return jsonify({
        "webcam_active": webcam_active,
        "monkey_active": monkey_active,
        "latest_detection": latest_detection,
        "timestamp": time.time(),
        "camera_source": "Raspberry Pi" if webcam_active else "None",
        "pi_camera_url": PI_CAMERA_URL,
        "pi_camera_status": pi_camera_status
    })

@app.route('/video')
def video():
    """Stream video with monkey detection overlays"""
    if not webcam_active or video_capture is None:
        return jsonify({"error": "Camera not started. Please start camera first using POST /webcam with action='start'"}), 400
    
    try:
        return Response(gen_frames(), 
                       mimetype='multipart/x-mixed-replace; boundary=frame',
                       headers={
                           'Cache-Control': 'no-cache, no-store, must-revalidate',
                           'Pragma': 'no-cache',
                           'Expires': '0'
                       })
    except Exception as e:
        return jsonify({"error": f"Error streaming video: {str(e)}"}), 500

@app.route('/pi-video')
def pi_video():
    """Stream direct video from Raspberry Pi (without detection overlays)"""
    try:
        def generate_pi_frames():
            try:
                response = requests.get(PI_CAMERA_URL, stream=True, timeout=10)
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            yield chunk
                else:
                    print(f"Failed to connect to Pi camera: HTTP {response.status_code}")
            except Exception as e:
                print(f"Error streaming from Pi camera: {e}")
        
        return Response(generate_pi_frames(),
                       mimetype='multipart/x-mixed-replace; boundary=frame',
                       headers={
                           'Cache-Control': 'no-cache, no-store, must-revalidate',
                           'Pragma': 'no-cache',
                           'Expires': '0'
                       })
    except Exception as e:
        return jsonify({"error": f"Error streaming Pi video: {str(e)}"}), 500

@app.route('/detections', methods=['GET'])
def get_detections():
    """Get list of all saved detection images"""
    global saved_detections
    return jsonify({
        "total_detections": len(saved_detections),
        "detections": saved_detections
    })

@app.route('/detection-image/<filename>')
def get_detection_image(filename):
    """Serve a specific detection image"""
    try:
        filepath = os.path.join(DETECTIONS_DIR, filename)
        if os.path.exists(filepath):
            return send_file(filepath, mimetype='image/jpeg')
        else:
            return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving image: {str(e)}"}), 500

@app.route('/latest-detection-image')
def get_latest_detection_image():
    """Get the most recent detection image"""
    global saved_detections
    try:
        if saved_detections:
            latest = saved_detections[-1]
            filepath = latest['filepath']
            if os.path.exists(filepath):
                return send_file(filepath, mimetype='image/jpeg')
            else:
                return jsonify({"error": "Latest image not found"}), 404
        else:
            return jsonify({"error": "No detections available"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving latest image: {str(e)}"}), 500

@app.route('/test-pi-connection')
def test_pi_connection():
    """Test Raspberry Pi camera connection with detailed logging"""
    try:
        print("Testing Pi camera connection...")
        
        # Test basic HTTP connectivity
        response = requests.get(PI_CAMERA_URL, timeout=10)
        if response.status_code != 200:
            return jsonify({
                "status": "failed",
                "error": f"HTTP request failed with status {response.status_code}",
                "details": "Pi camera service might not be running"
            }), 400
        
        # Test if it's a valid MJPEG stream
        content_type = response.headers.get('content-type', '')
        
        # Test OpenCV connection
        test_cap = create_pi_camera_capture()
        opencv_status = "success" if test_cap is not None else "failed"
        
        if test_cap:
            test_cap.release()
        
        return jsonify({
            "status": "success",
            "pi_camera_url": PI_CAMERA_URL,
            "http_status": response.status_code,
            "content_type": content_type,
            "opencv_connection": opencv_status,
            "message": "Pi camera is accessible via HTTP" + (
                " and OpenCV" if opencv_status == "success" else " but OpenCV connection failed"
            )
        })
        
    except requests.exceptions.ConnectException:
        return jsonify({
            "status": "failed",
            "error": "Connection refused",
            "details": "Pi camera service is not running or wrong IP address"
        }), 400
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "failed", 
            "error": "Connection timeout",
            "details": "Pi camera is not responding within 10 seconds"
        }), 400
    except Exception as e:
        return jsonify({
            "status": "failed",
            "error": str(e),
            "details": "Unexpected error occurred"
        }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
