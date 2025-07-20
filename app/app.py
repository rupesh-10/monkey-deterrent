from flask import Flask, render_template, Response, request
from flask_cors import CORS
from ultralytics import YOLO
import cv2
import threading
import pygame
import time
import yt_dlp

app = Flask(__name__)
CORS(app)  # Enable CORS for mobile access

# Load YOLOv8 or YOLOv11 model
model = YOLO("best.pt")

# Sound setup
pygame.mixer.init()
alert_sound = pygame.mixer.Sound("alert.wav")
is_playing = False
lock = threading.Lock()

# Video source global state
video_source = 0
video_capture = None

# Monkey alert state
monkey_last_seen = 0
monkey_last_missing = 0
monkey_active = False

def play_alert():
    global is_playing
    with lock:
        if not is_playing:
            is_playing = True
            alert_sound.play(-1)

def stop_alert():
    global is_playing
    with lock:
        if is_playing:
            alert_sound.stop()
            is_playing = False

def gen_frames():
    global monkey_last_seen, monkey_last_missing, monkey_active, video_capture

    while True:
        if video_capture is None:
            time.sleep(1)
            continue

        success, frame = video_capture.read()
        if not success:
            break

        results = model(frame, imgsz=640, conf=0.5)
        annotated_frame = results[0].plot()

        monkey_now_detected = False
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            cls_name = model.names[cls_id]
            if cls_name.lower() == "monkey":
                monkey_now_detected = True
                break

        current_time = time.time()

        if monkey_now_detected:
            monkey_last_seen = current_time
            if not monkey_active and (current_time - monkey_last_missing) > 1:
                play_alert()
                monkey_active = True
        else:
            monkey_last_missing = current_time
            if monkey_active and (current_time - monkey_last_seen) > 2:
                stop_alert()
                monkey_active = False

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return "Monkey Detector is running"

@app.route('/set_source', methods=['POST'])
def set_source():
    global video_capture, video_source

    source = request.form.get('source')
    if source == 'webcam':
        video_source = 0
        video_capture = cv2.VideoCapture(video_source)
        return "Webcam source set", 200

    elif source == 'youtube':
        url = request.form.get('yt_url')
        if not url:
            return "No URL provided", 400

        try:
            ydl_opts = {'format': 'best[ext=mp4]'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                video_url = info_dict['url']
                video_capture = cv2.VideoCapture(video_url)
            return "YouTube source set", 200
        except Exception as e:
            print("Error loading YouTube:", e)
            return "Failed to load YouTube", 400

    return "Invalid source", 400

@app.route('/video')
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050, debug=True)
