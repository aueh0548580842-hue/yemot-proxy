import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from moviepy import VideoFileClip
from flask import Flask
from playwright.sync_api import sync_playwright

# ================= הגדרות המערכת =================
YEMOT_TOKEN = "033060711:219219" 
EXTENSION_PATH = "5"
URL_TO_SCRAPE = "https://hagizra.news/"
CHECK_INTERVAL_SECONDS = 300 
# ==================================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def upload_to_yemot(file_path, file_name):
    url = "https://www.call2all.co.il/ym/api/UploadFile"
    params = {"token": YEMOT_TOKEN, "path": f"{EXTENSION_PATH}/{file_name}"}
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(url, data=params, files={'file': f})
        if response.status_code == 200:
            print(f"[+] הועלה לימות המשיח: {file_name}")
    except Exception as e:
        print(f"שגיאה בהעלאה: {e}")

def process_and_upload(post_id, text, video_url=None):
    print(f"[*] מעבד פוסט {post_id}...")
    if video_url:
        try:
            video_filename = "temp_v.mp4"
            audio_filename = f"{post_id}.mp3"
            # הורדת הוידאו
            r = requests.get(video_url, stream=True, timeout=30)
            with open(video_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: f.write(chunk)
            # המרה
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

def check_website():
    print("--- סורק את האתר עם Playwright ---")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(URL_TO_SCRAPE, wait_until="networkidle")
            content = page.content()
            browser.close()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # מחפש כל div עם id מספרי (זו הלוגיקה שלך)
        posts = [div for div in soup.find_all('div', id=True) if div.get('id').isdigit()]
        
        if not posts:
            print("לא נמצאו פוסטים.")
            return

        latest_post = posts[0]
        post_id = latest_post.get('id')
        
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
            print("אין עדכונים חדשים.")
            
    except Exception as e:
        print(f"שגיאה קריטית בסריקה: {e}")

def run_bot():
    while True:
        check_website()
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
