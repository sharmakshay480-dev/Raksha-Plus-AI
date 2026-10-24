import requests

# 1. अपना असली Token यहाँ डालें (शुरू से लेकर आखिर तक, बिना किसी Space के)
BOT_TOKEN = "8863381776:AAEesmxr_z1LpNWezc7S6grKsdaC13UNTZU" 

# 2. अपना असली Chat ID यहाँ डालें (यह सिर्फ नंबर होता है)
CHAT_ID = "7552151321"

def send_telegram_alert(message):
    # URL बनाते समय इस बात का ध्यान रखें कि 'bot' शब्द टोकन से बिल्कुल सटा हुआ हो!
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    
    try:
        print("Messege bhej raha hoon... URL check karo:")
        # Security ke liye hum pura token print nahi karenge, sirf check ke liye
        print(f"URL: {url[:35]}...[hidden]") 
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print("✅ SUCCESS: Phone par Telegram message chala gaya!")
        else:
            print(f"❌ ERROR {response.status_code}: {response.text}")
    except Exception as e:
        print("❌ CRITICAL ERROR:", e)

# Test Message
send_telegram_alert("🚨 Raksha Plus System Test: System is Online!")