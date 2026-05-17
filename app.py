from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
# מאפשר לאפליקציה שלך ב-Vercel לשלוח לפה נתונים ללא חסימת אבטחה
CORS(app) 

@app.route('/upload_to_yemot', methods=['POST'])
def upload_to_yemot():
    try:
        # מקבלים את הנתונים מהדפדפן
        token = request.form.get('token')
        path = request.form.get('path')
        audio_file = request.files.get('file')

        if not token or not path or not audio_file:
            return jsonify({"error": "חסרים נתונים (טוקן, נתיב או קובץ)"}), 400

        # אורזים את הנתונים לפורמט שבימות המשיח מצפים לקבל
        data = {
            'token': token,
            'path': path
        }
        files = {
            'file': (audio_file.filename, audio_file.read(), audio_file.content_type)
        }

        # שולחים לבימות המשיח (ללא שום אזכור ל-Vercel)
        response = requests.post('https://www.yemot.co.il/ym/api/UploadFile', data=data, files=files)
        
        try:
            result = response.json()
            return jsonify(result), response.status_code
        except Exception:
            return jsonify({"error": "השרת של בימות המשיח דחה את הבקשה", "details": response.text[:100]}), 502

    except Exception as e:
        return jsonify({"error": f"שגיאת שרת פנימית: {str(e)}"}), 500

if __name__ == '__main__':
    # הפעלת השרת על פורט שזמין לאינטרנט
    app.run(host='0.0.0.0', port=10000)
