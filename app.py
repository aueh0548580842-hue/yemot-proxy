import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from moviepy import VideoFileClip
from flask import Flask
from playwright.sync_api import sync_playwright

# ================= הגדרות =================
YEMOT_TOKEN = "033060711:219219" 
EXTENSION_PATH = "5"
URL_TO_SCRAPE = "https://hagizra.news/"
CHECK_INTERVAL = 300 # 5 דקות

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

# --- פונקציות עזר ---
def upload_to_yemot(file_path, file_name):
    url = "https://www.call2all.co.il/ym/api/UploadFile"
    params = {"token": YEMOT_TOKEN, "path": f"{EXTENSION_PATH}/{file_name}"}
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(url, data=params, files={'file': f})
        print(f"[+] העלאה הסתיימה עם קוד: {response.status_code}")
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
            print(f"שגיאה בעיבוד: {e}")
    else:
        text_filename = f"{post_id}.txt"
        with open(text_filename, 'w', encoding='utf-8') as f: f.write(text)
        upload_to_yemot(text_filename, text_filename)
        if os.path.exists(text_filename): os.remove(text_filename)

# --- לולאת הבוט ---
def run_bot():
    print("--- הבוט הופעל ברקע ---")
    while True:
        try:
            print("סורק את האתר...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(URL_TO_SCRAPE, wait_until="networkidle")
                content = page.content()
                browser.close()
            
            soup = BeautifulSoup(content, 'html.parser')
            # מוצא פוסטים (div עם ID מספרי)
            posts = [div for div in soup.find_all('div', id=True) if div.get('id').isdigit()]
            
            if posts:
                latest_post = posts[0]
                post_id = latest_post.get('id')
                
                # בדיקה אם זה חדש
                saved_id = ""
                if os.path.exists("last_id.txt"):
                    with open("last_id.txt", "r") as f: saved_id = f.read().strip()
                
                if post_id != saved_id:
                    print(f"!!! פוסט חדש: {post_id} !!!")
                    video_tag = latest_post.find('video')
                    video_url = video_tag['src'] if video_tag else None
                    process_and_upload(post_id, latest_post.text.strip(), video_url)
                    with open("last_id.txt", "w") as f: f.write(post_id)
                else:
                    print("אין פוסטים חדשים.")
        except Exception as e:
            print(f"שגיאה בסריקה: {e}")
        
        time.sleep(CHECK_INTERVAL)

# --- הפעלת האפליקציה ---
if __name__ == '__main__':
    # הפעלת הבוט לפני השרת
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
