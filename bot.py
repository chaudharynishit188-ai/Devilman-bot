from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import requests
import os
import yt_dlp

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN not set")

# --- NSFW CHECK ---
def is_nsfw(file_url):
    try:
        res = requests.post(
            "https://api.deepai.org/api/nsfw-detector",
            data={"image": file_url},
            headers={"api-key": "quickstart-QUICKSTART"},
            timeout=10
        )
        data = res.json()
        if "output" in data:
            return data["output"]["nsfw_score"] > 0.6
    except Exception as e:
        print("NSFW error:", e)
    return False

# --- IMAGE FILTER ---
async def check_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    try:
        msg = update.message
        file = await msg.photo[-1].get_file()
        url = file.file_path

        if is_nsfw(url):
            await msg.delete()
            await context.bot.send_message(msg.chat.id, "🚫 NSFW image removed")
    except Exception as e:
        print("Image error:", e)

# --- STICKER FILTER ---
async def check_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    try:
        msg = update.message
        file = await msg.sticker.get_file()
        url = file.file_path

        if is_nsfw(url):
            await msg.delete()
            await context.bot.send_message(msg.chat.id, "🚫 NSFW sticker removed")
    except Exception as e:
        print("Sticker error:", e)

# --- CHAT ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    try:
        text = update.message.text.lower()
        if "ryo" in text:
            await update.message.reply_text("yo bro 😎")
    except Exception as e:
        print("Chat error:", e)

# --- MUSIC ---
async def song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Use: /song name")
        return

    await update.message.reply_text("🎧 downloading...")

    try:
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': 'song.%(ext)s',
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            path = ydl.prepare_filename(info['entries'][0])

        with open(path, "rb") as f:
            await update.message.reply_audio(audio=f)

        os.remove(path)

    except Exception as e:
        print("Song error:", e)
        await update.message.reply_text("❌ failed")

# --- AI IMAGE ---
async def ai_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Use: /aiimage prompt")
        return

    await update.message.reply_text("🎨 generating...")

    try:
        res = requests.post(
            "https://api.deepai.org/api/text2img",
            data={"text": prompt},
            headers={"api-key": "quickstart-QUICKSTART"},
            timeout=20
        )
        data = res.json()

        if "output_url" in data:
            await update.message.reply_photo(photo=data["output_url"])
        else:
            await update.message.reply_text("❌ failed")

    except Exception as e:
        print("AI image error:", e)
        await update.message.reply_text("❌ error")

# --- MAIN ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, chat))
app.add_handler(MessageHandler(filters.PHOTO, check_image))
app.add_handler(MessageHandler(filters.Sticker.ALL, check_sticker))

app.add_handler(CommandHandler("song", song))
app.add_handler(CommandHandler("aiimage", ai_image))

print("🔥 BOT RUNNING...")
app.run_polling()