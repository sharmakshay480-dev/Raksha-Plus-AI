import cv2
import time
import requests
import winsound
import pyttsx3
import threading
import numpy as np
import mediapipe as mp
from ultralytics import YOLO
from scipy.spatial import distance as dist

# --- 1. TELEGRAM SETUP ---
BOT_TOKEN = "8863381776:AAEesmxr_z1LpNWezc7S6grKsdaC13UNTZU" 
CHAT_ID = "7552151321"

# --- 2. VOICE & ALARM (Anti-Frustration) ---
last_alert_time = 0
ALERT_COOLDOWN = 10  

def play_alarm_and_voice():
    winsound.Beep(2500, 400)
    winsound.Beep(3200, 400)
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.say("Alert! Driver uth jao, kripya saamne dekhein.")
    engine.runAndWait()

def trigger_full_alert(message):
    global last_alert_time
    current_time = time.time()
    if current_time - last_alert_time > ALERT_COOLDOWN:
        print(f"🚨 ALERT: {message}")
        last_alert_time = current_time
        threading.Thread(target=play_alarm_and_voice, daemon=True).start()
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={'chat_id': CHAT_ID, 'text': f"🚨 RAKSHA PLUS: {message}"})
        except:
            pass

# --- 3. EYES SETUP (MEDIAPIPE) ---
def get_ear(landmarks, indices, w, h):
    pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in indices])
    v1 = dist.euclidean(pts[1], pts[5])
    v2 = dist.euclidean(pts[2], pts[4])
    h_dist = dist.euclidean(pts[0], pts[3])
    if h_dist == 0: return 0.3
    return (v1 + v2) / (2.0 * h_dist)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

# --- 4. NECK SETUP (YOLOv8) ---
print("YOLO Model Load ho raha hai...")
model = YOLO('yolov8n-pose.pt')

# --- 5. CAMERA SETUP ---
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW) # External Cam
if not cap.isOpened():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Laptop Cam

EAR_THRESHOLD = 0.22
SLEEP_TIME_LIMIT = 1.5 
eye_closed_start = None
head_down_start = None

print("Raksha Plus HYBRID Core RUNNING! Press 'q' to exit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    current_time = time.time()
    status_msg = "Driver Active"
    color = (0, 255, 0)

    # --- PART A: EYES (MediaPipe) ---
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results_mp = face_mesh.process(rgb_frame)
    avg_ear = 0.3 # Default

    if results_mp.multi_face_landmarks:
        lm = results_mp.multi_face_landmarks[0].landmark
        avg_ear = (get_ear(lm, LEFT_EYE, w, h) + get_ear(lm, RIGHT_EYE, w, h)) / 2.0
        
        if avg_ear < EAR_THRESHOLD:
            if eye_closed_start is None: eye_closed_start = current_time
            elif current_time - eye_closed_start >= SLEEP_TIME_LIMIT:
                status_msg = "SLEEPING (Eyes)!"
                color = (0, 0, 255)
                trigger_full_alert("Driver is SLEEPING (Eyes Closed)!")
        else:
            eye_closed_start = None

    # --- PART B: NECK DROP (YOLO) ---
    results_yolo = model(frame, verbose=False)
    for r in results_yolo:
        keypoints = r.keypoints
        if keypoints is not None and len(keypoints.xy[0]) > 6:
            pts = keypoints.xy[0]
            nose = pts[0]
            l_shoulder, r_shoulder = pts[5], pts[6]
            
            if nose[1] > 0 and l_shoulder[1] > 0:
                shoulder_y_avg = (l_shoulder[1] + r_shoulder[1]) / 2
                dist_nose_shoulder = shoulder_y_avg - nose[1]
                
                if dist_nose_shoulder < 45: # Gardan jhukne par distance kam hota hai
                    if head_down_start is None: head_down_start = current_time
                    elif current_time - head_down_start >= SLEEP_TIME_LIMIT:
                        status_msg = "DROWSY (Neck Drop)!"
                        color = (0, 0, 255)
                        trigger_full_alert("Driver is DROWSY (Neck Dropped)!")
                else:
                    head_down_start = None

    # --- Display ---
    cv2.putText(frame, f"EAR: {avg_ear:.2f}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, status_msg, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
    cv2.imshow("Raksha Plus - Hybrid Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()