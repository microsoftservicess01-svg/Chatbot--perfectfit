import os
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder

BOT_TOKEN = os.getenv("BOT_TOKEN")

app = FastAPI()
tg_app = None

@app.on_event("startup")
async def startup():
    global tg_app
    tg_app = ApplicationBuilder().token(BOT_TOKEN).build()
    await tg_app.initialize()
    await tg_app.start()
    print("✅ Telegram app started")

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)

    if update.message:
        await tg_app.bot.send_message(
            chat_id=update.message.chat.id,
            text="✅ OK (echo test)"
        )

    return {"ok": True}

@app.get("/")
def health():
    return {"status": "running"}
    
