from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, InlineQueryHandler, filters, ContextTypes
import requests, os, yt_dlp, uuid
from PIL import Image

TOKEN = os.getenv("TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

# --- NSFW CHECK (API BASED LIGHT) ---
def is_nsfw(path):
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        with open(path, "rb") as f:
            res = requests.post(
                "https://api-inference.huggingface.co/models/facebook/detr-resnet-50",
                headers=headers,
                data=f
            )

        if res.status_code == 200:
            text = res.text.lower()
            return any(word in text for word in ["person", "body", "skin"])
    except:
        pass
    return False

# --- AI CHAT ---
def generate_reply(text):
    try:
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        res = requests.post(
            "https://api-inference.huggingface.co/models/google/flan-t5-base",
            headers=headers,
            json={"inputs": text},
            timeout=10
        )
        data = res.json()
        if isinstance(data, list):
            return data[0]["generated_text"]
    except:
        pass

    return "⚠️ bro AI not working rn"

# --- CHAT ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text.lower()

    is_reply = msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id

    if "ryo" not in text and not is_reply:
        return

    clean = text.replace("ryo", "").strip()

    if not clean:
        await msg.reply_text("yeah?")
        return

    reply = generate_reply(clean)
    await msg.reply_text(reply)

# --- IMAGE CHECK ---
async def check_image(update: Update, context):
    msg = update.message
    file = await msg.photo[-1].get_file()
    path = f"{msg.message_id}.jpg"
    await file.download_to_drive(path)

    if is_nsfw(path):
        await msg.delete()
        await context.bot.send_message(msg.chat_id, "🚫 image removed")

    os.remove(path)

# --- STICKER CHECK ---
async def check_sticker(update: Update, context):
    msg = update.message
    file = await msg.sticker.get_file()
    path = f"{msg.message_id}.webp"
    await file.download_to_drive(path)

    img = Image.open(path).convert("RGB")
    jpg = f"{msg.message_id}.jpg"
    img.save(jpg)

    if is_nsfw(jpg):
        await msg.delete()
        await context.bot.send_message(msg.chat_id, "🚫 sticker removed")

    os.remove(path)
    os.remove(jpg)

# --- AI IMAGE ---
async def ai_image(update, context):
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Use: /aiimage prompt")
        return

    await update.message.reply_text("🎨 generating...")

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    res = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2",
        headers=headers,
        json={"inputs": prompt},
        timeout=60
    )

    if res.status_code == 200:
        with open("img.png", "wb") as f:
            f.write(res.content)

        await update.message.reply_photo(open("img.png", "rb"))
        os.remove("img.png")
    else:
        await update.message.reply_text("❌ failed")

# --- MUSIC ---
async def song(update, context):
    query = " ".join(context.args)

    if not query:
        await update.message.reply_text("Use: /song name")
        return

    await update.message.reply_text("🎧 downloading...")

    try:
        with yt_dlp.YoutubeDL({'format': 'bestaudio', 'outtmpl': 'song.%(ext)s'}) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=True)
            path = ydl.prepare_filename(info['entries'][0])

        await update.message.reply_audio(audio=open(path, "rb"))
        os.remove(path)
    except:
        await update.message.reply_text("❌ failed")

# --- INLINE MUSIC SEARCH ---
def search_song(query):
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        return ydl.extract_info(f"ytsearch5:{query}", download=False)['entries']

async def inline_query(update, context):
    query = update.inline_query.query
    if not query:
        return

    results = []
    for song in search_song(query)[:5]:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=song['title'],
                input_message_content=InputTextMessageContent(f"/song {song['title']}")
            )
        )

    await update.inline_query.answer(results)

# --- MAIN ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT, chat))
app.add_handler(MessageHandler(filters.PHOTO, check_image))
app.add_handler(MessageHandler(filters.Sticker.ALL, check_sticker))

app.add_handler(CommandHandler("aiimage", ai_image))
app.add_handler(CommandHandler("song", song))
app.add_handler(InlineQueryHandler(inline_query))

print("🔥 FULL BOT RUNNING (24/7 READY)")
app.run_polling()