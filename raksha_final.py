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

# --- 2. ALARM & VOICE ---
last_alert_time = 0
ALERT_COOLDOWN = 8  

def play_alarm(msg_type="drowsy"):
    winsound.Beep(2500, 300)
    winsound.Beep(3200, 300)
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    if msg_type == "yawn":
        engine.say("You look tired. Please take a break.")
    elif msg_type == "baby":
        engine.say("Emergency. Driver is missing. Checking baby safety.")
    else:
        engine.say("Alert! Kripya road par dhyaan de.")
    engine.runAndWait()

def trigger_alert(msg, msg_type="drowsy"):
    global last_alert_time
    curr_time = time.time()
    if curr_time - last_alert_time > ALERT_COOLDOWN:
        print(f"🚨 {msg}")
        last_alert_time = curr_time
        threading.Thread(target=play_alarm, args=(msg_type,), daemon=True).start()
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={'chat_id': CHAT_ID, 'text': f"🚨 RAKSHA PLUS: {msg}"})
        except:
            pass

# --- 3. MATHEMATICS (EYES, YAWN, NECK) ---
def get_ear(landmarks, indices, w, h):
    pts = np.array([[landmarks[i].x * w, landmarks[i].y * h] for i in indices])
    v1 = dist.euclidean(pts[1], pts[5])
    v2 = dist.euclidean(pts[2], pts[4])
    h_dist = dist.euclidean(pts[0], pts[3])
    if h_dist == 0: return 0.3
    return (v1 + v2) / (2.0 * h_dist), pts

def get_mar(landmarks, w, h):
    top = np.array([landmarks[13].x * w, landmarks[13].y * h])
    bottom = np.array([landmarks[14].x * w, landmarks[14].y * h])
    left = np.array([landmarks[78].x * w, landmarks[78].y * h])
    right = np.array([landmarks[308].x * w, landmarks[308].y * h])
    v_dist = dist.euclidean(top, bottom)
    h_dist = dist.euclidean(left, right)
    return v_dist / h_dist if h_dist > 0 else 0

LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
FOREHEAD, NOSE, CHIN = 10, 1, 152

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)

# --- 4. SMART CAMERA FINDER ---
print("कैमरा ढूंढा जा रहा है...")
cap = cv2.VideoCapture(1) # Pehle USB Cam (Index 1) try karo
if not cap.isOpened() or not cap.read()[0]: 
    cap = cv2.VideoCapture(2) # Agar 1 nahi chala, toh index 2 try karo
    if not cap.isOpened() or not cap.read()[0]:
        print("USB कैमरा नहीं मिला, लैपटॉप कैमरा (0) शुरू हो रहा है!")
        cap = cv2.VideoCapture(0) # End mein laptop cam

# THRESHOLDS & TIMERS
EAR_THRESH = 0.23        
PITCH_THRESH = 0.30  
MAR_THRESH = 0.45        
SLEEP_TIME_LIMIT = 1.2   
MISSING_TIME_LIMIT = 3.0 
BABY_ALERT_LIMIT = 15.0  

eye_closed_time = None
head_down_time = None
face_missing_time = None
yawn_time = None
baby_alert_sent = False

print("🚀 RAKSHA PLUS - ULTIMATE STARTUP MODE RUNNING!")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    
    # Night Mode Logic
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if np.mean(gray) < 70:  
        frame = cv2.convertScaleAbs(frame, alpha=1.3, beta=40) 

    h, w, _ = frame.shape
    curr_time = time.time()
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = face_mesh.process(rgb)
    
    status_msg = "Driver Active"
    color = (0, 255, 0)
    eye_color = (0, 255, 0) 

    if res.multi_face_landmarks:
        face_missing_time = None 
        baby_alert_sent = False
        lm = res.multi_face_landmarks[0].landmark
        
        l_ear, l_pts = get_ear(lm, LEFT_EYE, w, h)
        r_ear, r_pts = get_ear(lm, RIGHT_EYE, w, h)
        best_ear = max(l_ear, r_ear)
        mar = get_mar(lm, w, h)
        
        nose_x = lm[NOSE].x
        left_eye_x = lm[263].x
        right_eye_x = lm[33].x
        dist_left = abs(nose_x - left_eye_x)
        dist_right = abs(right_eye_x - nose_x)
        turn_ratio = dist_left / dist_right if dist_right > 0 else 1.0

        fh_y, n_y, c_y = lm[FOREHEAD].y * h, lm[NOSE].y * h, lm[CHIN].y * h
        face_ht = c_y - fh_y
        pitch_ratio = (c_y - n_y) / face_ht if face_ht > 0 else 0.5
            
        cv2.putText(frame, f"EAR: {best_ear:.2f} | MAR: {mar:.2f} | PITCH: {pitch_ratio:.2f}", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # Smart Logic
        if turn_ratio > 3.0 or turn_ratio < 0.3:
            status_msg = "Looking Aside / Mirror"
            color = (0, 255, 255) 
            eye_closed_time = None
            head_down_time = None
            yawn_time = None
            eye_color = (0, 255, 255)
            
        else:
            if mar > MAR_THRESH:
                if yawn_time is None: yawn_time = curr_time
                elif curr_time - yawn_time > 1.5:
                    status_msg = "YAWNING!"
                    color = (0, 165, 255)
                    trigger_alert("Driver is Yawning (Tired)!", "yawn")
            else:
                yawn_time = None

            if best_ear < EAR_THRESH:
                eye_color = (0, 0, 255) 
                if eye_closed_time is None: eye_closed_time = curr_time
                elif curr_time - eye_closed_time > SLEEP_TIME_LIMIT:
                    status_msg = "SLEEPING (Eyes)!"
                    color = (0, 0, 255)
                    trigger_alert("Driver Aankh Band Karke So Raha Hai!")
            else:
                eye_closed_time = None

            if pitch_ratio < PITCH_THRESH:
                if head_down_time is None: head_down_time = curr_time
                elif curr_time - head_down_time > SLEEP_TIME_LIMIT:
                    status_msg = "DROWSY (Neck Drop)!"
                    color = (0, 0, 255)
                    trigger_alert("Driver Ki Gardan Jhuk Gayi Hai (Neend)!")
            else:
                head_down_time = None

        cv2.polylines(frame, [l_pts.astype(np.int32)], True, eye_color, 1)
        cv2.polylines(frame, [r_pts.astype(np.int32)], True, eye_color, 1)

    else:
        if face_missing_time is None:
            face_missing_time = curr_time
        
        missing_duration = curr_time - face_missing_time
        
        if missing_duration > BABY_ALERT_LIMIT and not baby_alert_sent:
            status_msg = "⚠️ BABY SAFETY ALERT!"
            color = (0, 0, 255)
            trigger_alert("URGENT: Driver is Away! Please check if BABY or PET is left in the car!", "baby")
            baby_alert_sent = True
        elif missing_duration > MISSING_TIME_LIMIT:
            status_msg = "DRIVER MISSING / DISTRACTED!"
            color = (0, 0, 255)
            if not baby_alert_sent: trigger_alert("Driver seat par nahi hai!")
        else:
            status_msg = f"Face Lost... Wait {int(MISSING_TIME_LIMIT - missing_duration)}s"
            color = (0, 165, 255)
        
        eye_closed_time = None
        head_down_time = None
        yawn_time = None

    cv2.putText(frame, status_msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.imshow("Raksha Plus - Ultimate Startup AI", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()