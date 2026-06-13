import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from moviepy import VideoFileClip
from flask import Flask

# ================= הגדרות =================
YEMOT_TOKEN = "033060711:219219" 
EXTENSION_PATH = "ivr2:5/"  
API_URL = "https://haredim-jerusalem.co.il/wp-json/wp/v2/posts"
CHECK_INTERVAL = 300 # בודק כל 5 דקות

app = Flask(__name__)

@app.route('/')
def home():
    return "API Bot is running!"

# --- פונקציות העלאה ---
def upload_to_yemot(file_path, file_name):
    url = "https://www.call2all.co.il/ym/api/UploadFile"
    # מחבר את הנתיב עם שם הקובץ: ivr2:5/filename.txt
    full_path = f"{EXTENSION_PATH}{file_name}"
    params = {"token": YEMOT_TOKEN, "path": full_path}
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(url, data=params, files={'file': f})
        print(f"[+] תשובת השרת של ימות המשיח: {response.text}")
    except Exception as e:
        print(f"[-] שגיאה בהעלאה: {e}")

def process_and_upload(post_id, text, video_url=None):
    print(f"[*] מעבד פוסט {post_id}...")
    if video_url:
        try:
            video_filename = "temp_v.mp4"
            audio_filename = f"{post_id}.mp3"
            r = requests.get(video_url, stream=True, timeout=30)
            with open(video_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            with VideoFileClip(video_filename) as clip:
                clip.audio.write_audiofile(audio_filename, logger=None)
            upload_to_yemot(audio_filename, audio_filename)
            if os.path.exists(video_filename): os.remove(video_filename)
            if os.path.exists(audio_filename): os.remove(audio_filename)
        except Exception as e:
            print(f"שגיאה בעיבוד וידאו: {e}")
    else:
        text_filename = f"{post_id}.txt"
        with open(text_filename, 'w', encoding='utf-8') as f: f.write(text)
        upload_to_yemot(text_filename, text_filename)
        if os.path.exists(text_filename): os.remove(text_filename)

# --- לולאת הבוט (מבוססת API) ---
def run_bot():
    print("--- הבוט הופעל ברקע (עובד מול API) ---")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    while True:
        try:
            print("מושך נתונים מה-API...")
            response = requests.get(API_URL, headers=headers, timeout=15)
            
            if response.status_code == 200:
                posts = response.json()
                
                if posts and len(posts) > 0:
                    latest_post = posts[0]
                    post_id = str(latest_post['id'])
                    
                    raw_html = latest_post['content']['rendered']
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    clean_text = soup.get_text(separator='\n').strip()
                    
                    video_tag = soup.find('video')
                    video_url = video_tag['src'] if video_tag else None
                    
                    saved_id = ""
                    if os.path.exists("last_id.txt"):
                        with open("last_id.txt", "r") as f: saved_id = f.read().strip()
                    
                    if post_id != saved_id:
                        print(f"!!! פוסט חדש זוהה מ-API: {post_id} !!!")
                        process_and_upload(post_id, clean_text, video_url)
                        with open("last_id.txt", "w") as f: f.write(post_id)
                    else:
                        print(f"אין פוסטים חדשים (האחרון שנסרק: {saved_id}).")
                else:
                    print("ה-API לא החזיר פוסטים.")
            else:
                print(f"שגיאה בגישה ל-API. קוד תגובה: {response.status_code}")
                
        except Exception as e:
            print(f"שגיאה בסריקת ה-API: {e}")
        
        time.sleep(CHECK_INTERVAL)

# --- הפעלת האפליקציה ---
if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
