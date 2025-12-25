import os
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "10000"))

user_state = {}
app = FastAPI()
telegram_app = None

def calculate_bra_size(underbust, bust):
    band = round(underbust / 5) * 5
    diff = bust - underbust
    cup_map = {10: "A", 12: "B", 14: "C", 16: "D", 18: "DD"}
    cup = cup_map.get(min(cup_map.keys(), key=lambda x: abs(x - diff)), "B")
    return f"{int(band / 2)}{cup}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = {"step": "UNDERBUST"}
    await update.message.reply_text("👙 Welcome to Perfect Fit\nEnter underbust (cm):")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if uid not in user_state:
        await start(update, context)
        return
    step = user_state[uid]["step"]
    if step == "UNDERBUST":
        user_state[uid]["underbust"] = int(text)
        user_state[uid]["step"] = "BUST"
        await update.message.reply_text("Enter bust (cm):")
    elif step == "BUST":
        size = calculate_bra_size(user_state[uid]["underbust"], int(text))
        user_state[uid]["size"] = size
        kb = [[InlineKeyboardButton("Daily Comfort", callback_data="TYPE_DAILY")]]
        await update.message.reply_text(f"Your size is {size}", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Thanks! Type /start again.")

@app.on_event("startup")
async def startup():
    global telegram_app
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook", drop_pending_updates=True)
    await telegram_app.start()

@app.post("/webhook")
async def webhook(req: Request):
    update = Update.de_json(await req.json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.get("/")
def health():
    return {"status": "ok"}
