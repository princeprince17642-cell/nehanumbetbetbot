import json
import logging
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ChatJoinRequestHandler, CommandHandler, MessageHandler, filters, ContextTypes

# --- FLASK SERVER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Personal Bot is Alive and Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

BOT_TOKEN = "8772146528:AAFTriqWVih_t8GvpfqpWEN6gVpomTlAS-Y"
ADMIN_ID = 8343576029  
USERS_FILE = "users.json"
VOICE_FILE_ID_FILE = "voice_id.txt"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def save_user(user_id):
    users = []
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                users = json.load(f)
        except:
            users = []
    if user_id not in users:
        users.append(user_id)
        try:
            with open(USERS_FILE, "w") as f:
                json.dump(users, f)
        except Exception as e:
            print(f"Error saving user file: {e}")

def get_all_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def get_saved_voice_id():
    if os.path.exists(VOICE_FILE_ID_FILE):
        with open(VOICE_FILE_ID_FILE, "r") as f:
            return f.read().strip()
    return None

# --- 1. चैनल ज्वाइन रिक्वेस्ट हैंडलर ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user_id = request.from_user.id
    
    save_user(user_id)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="Hello"
        )
    except Exception as e:
        print(f"Error sending welcome text: {e}")

    saved_voice = get_saved_voice_id()
    if saved_voice:
        try:
            await context.bot.send_voice(chat_id=user_id, voice=saved_voice)
            print(f"Voice note successfully sent to {user_id}")
        except Exception as e:
            print(f"Error sending voice note: {e}")

# --- 2. टेक्स्ट ब्रॉडकास्ट कमांड ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("तू इस कमांड को इस्तेमाल नहीं कर सकता!")
        return

    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("मैसेज लिखें, जैसे: /broadcast आपका संदेश")
        return

    users = get_all_users()
    if users:
        success = 0
        failed = 0
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=message_text)
                success += 1
            except Exception as e:
                failed += 1
        
        await update.message.reply_text(f"ब्रॉडकास्ट पूरा हुआ!\n सफल: {success}\n असफल: {failed}")
    else:
        await update.message.reply_text("❌ कोई यूजर डेटाबेस नहीं मिला या लिस्ट खाली है!")

# --- 3. लाइव चैट, वॉइस सेट और वॉइस ब्रॉडकास्ट सिस्टम ---
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if user.id == ADMIN_ID:
        if message.voice and message.caption and message.caption.strip() == "/setvoice":
            with open(VOICE_FILE_ID_FILE, "w") as f:
                f.write(message.voice.file_id)
            await message.reply_text("✅ दोस्त का वॉइस नोट परमानेंट सेट हो गया है!")
            return

        if message.voice and message.caption and message.caption.strip() == "/broadcast_voice":
            voice_file_id = message.voice.file_id
            users = get_all_users()
            
            if users:
                success = 0
                failed = 0
                status_msg = await message.reply_text("🎙️ वॉइस नोट ब्रॉडकास्ट शुरू हो रहा है...")
                
                for user_id in users:
                    try:
                        await context.bot.send_voice(chat_id=user_id, voice=voice_file_id)
                        success += 1
                    except Exception as e:
                        failed += 1
                
                await status_msg.edit_text(f"✅ वॉइस नोट ब्रॉडकास्ट पूरा हुआ!\n\n सफल: {success}\n असफल: {failed}")
            else:
                await message.reply_text("❌ कोई यूजर डेटाबेस नहीं मिला या लिस्ट खाली है!")
            return

        if message.reply_to_message:
            replied_text = message.reply_to_message.text or message.reply_to_message.caption
            if replied_text and "User ID:" in replied_text:
                try:
                    line = [l for l in replied_text.split('\n') if "User ID:" in l][0]
                    target_user_id = int(line.split(":")[1].strip())
                    
                    if message.voice:
                        await context.bot.send_voice(chat_id=target_user_id, voice=message.voice.file_id)
                    elif message.text:
                        await context.bot.send_message(chat_id=target_user_id, text=message.text)
                    
                    await message.reply_text("✅ मैसेज यूजर को भेज दिया गया है!")
                except Exception as e:
                    await message.reply_text(f"❌ भेजने में एरर आया: {e}")
        return

    else:
        save_user(user.id)
        
        user_name = user.full_name
        username = f"@{user.username}" if user.username else "कोई यूजरनेम नहीं"
        
        forward_header = f"📩 नया मैसेज आया है!\n👤 नाम: {user_name}\n🔗 यूजरनेम: {username}\n🆔 User ID: {user.id}\n-------------------\n"
        
        try:
            if message.text:
                await context.bot.send_message(chat_id=ADMIN_ID, text=forward_header + message.text)
            elif message.voice:
                await context.bot.send_message(chat_id=ADMIN_ID, text=forward_header + "[नीचे यूजर का वॉइस नोट है]")
                await context.bot.send_voice(chat_id=ADMIN_ID, voice=message.voice.file_id)
            elif message.photo:
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=forward_header + (message.caption or ""))
            else:
                await context.bot.send_message(chat_id=ADMIN_ID, text=forward_header + "[यूजर ने मीडिया भेजा है]")
        except Exception as e:
            print(f"Error forwarding to admin: {e}")

if __name__ == '__main__':
    keep_alive()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_messages))

    print("Personal Bot start ho gaya hai...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
