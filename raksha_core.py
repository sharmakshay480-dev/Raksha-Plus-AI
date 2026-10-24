import cv2
import time
import requests
import winsound
import pyttsx3
import threading
import numpy as np
import mediapipe as mp
from scipy.spatial import distance as dist

# --- 1. TELEGRAM SETUP ---
BOT_TOKEN = "8863381776:AAEesmxr_z1LpNWezc7S6grKsdaC13UNTZU" 
CHAT_ID = "7552151321"

# --- 2. VOICE & ALARM (Anti-Frustration Logic) ---
last_alert_time = 0
ALERT_COOLDOWN = 10  # 10 second ka cooldown taki driver irritate na ho

def play_alarm_and_voice():
    # Pehle 2 tez Beep (Laptop Speaker)
    winsound.Beep(2500, 400)
    winsound.Beep(3200, 400)
    # Fir Voice Command
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.say("Alert! Driver uth jao, kripya saamne dekhein.")
    engine.runAndWait()

def trigger_full_alert(message):
    global last_alert_time
    current_time = time.time()
    
    if current_time - last_alert_time > ALERT_COOLDOWN:
        print(f"🚨 ALERT TRIGGERED: {message}")
        last_alert_time = current_time
        
        # Audio background thread mein chalega taki camera freeze na ho
        threading.Thread(target=play_alarm_and_voice, daemon=True).start()
        
        # Telegram Message
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={'chat_id': CHAT_ID, 'text': f"🚨 RAKSHA PLUS: {message}"})
        except:
            pass

# --- 3. MATHS FOR EYES & NECK ---
def get_ear(landmarks, indices, w, h):
    pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in indices])
    v1 = dist.euclidean(pts[1], pts[5])
    v2 = dist.euclidean(pts[2], pts[4])
    h_dist = dist.euclidean(pts[0], pts[3])
    if h_dist == 0: return 0.3
    return (v1 + v2) / (2.0 * h_dist)

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
NOSE_TIP, CHIN, FOREHEAD = 1, 152, 10

# --- 4. CAMERA & MEDIAPIPE SETUP ---
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW) # External Webcam
if not cap.isOpened():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Fallback to laptop cam

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

# Thresholds (Normal Blink vs Sleep)
EAR_THRESHOLD = 0.22
HEAD_DROP_THRESHOLD = 0.35  
SLEEP_TIME_LIMIT = 1.5  # 1.5 Second lagatar aankh band ya gardan niche rehne par bajeha

eye_closed_start = None
head_down_start = None

print("Raksha Plus Driver Monitor RUNNING! Press 'q' to exit.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    results = face_mesh.process(rgb_frame)
    current_time = time.time()
    
    status_msg = "Driver Active"
    color = (0, 255, 0)

    if results.multi_face_landmarks:
        lm = results.multi_face_landmarks[0].landmark
        
        # EAR Calculation
        l_ear = get_ear(lm, LEFT_EYE, w, h)
        r_ear = get_ear(lm, RIGHT_EYE, w, h)
        avg_ear = (l_ear + r_ear) / 2.0
        
        # Neck/Head Drop Calculation (Pitch Ratio)
        forehead_y, nose_y, chin_y = lm[FOREHEAD].y * h, lm[NOSE_TIP].y * h, lm[CHIN].y * h
        face_height = chin_y - forehead_y
        pitch_ratio = (chin_y - nose_y) / face_height if face_height > 0 else 0.45

        # Live values on screen
        cv2.putText(frame, f"EAR: {avg_ear:.2f} | PITCH: {pitch_ratio:.2f}", (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # --- LOGIC: EYE SLEEP DETECT ---
        if avg_ear < EAR_THRESHOLD:
            if eye_closed_start is None:
                eye_closed_start = current_time # Timer start
            elif current_time - eye_closed_start >= SLEEP_TIME_LIMIT:
                status_msg = "DRIVER SOO GYA HAIN!"
                color = (0, 0, 255)
                trigger_full_alert("Driver is SLEEPING (Eyes Closed)!")
        else:
            eye_closed_start = None # Normal blink par timer reset ho jayega

        # --- LOGIC: NECK DROP DETECT ---
        if pitch_ratio < HEAD_DROP_THRESHOLD:
            if head_down_start is None:
                head_down_start = current_time
            elif current_time - head_down_start >= SLEEP_TIME_LIMIT:
                status_msg = "DROWSY / HEAD DOWN!"
                color = (0, 0, 255)
                trigger_full_alert("Driver is DROWSY (Neck Dropped)!")
        else:
            head_down_start = None

    else:
        status_msg = "Face Not Found"
        color = (0, 255, 255)
        eye_closed_start = None
        head_down_start = None

    # Status Alert on Screen
    cv2.putText(frame, status_msg, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
    cv2.imshow("Raksha Plus - Face & Eye Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()