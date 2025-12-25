import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

user_state = {}

app = FastAPI()
telegram_app: Application | None = None


# ================= HELPERS =================
def calculate_bra_size(underbust, bust):
    band = round(underbust / 5) * 5
    diff = bust - underbust
    cup_map = {10: "A", 12: "B", 14: "C", 16: "D", 18: "DD"}
    cup = cup_map.get(min(cup_map.keys(), key=lambda x: abs(x - diff)), "B")
    return f"{int(band / 2)}{cup}"


# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_state[uid] = {"step": "UNDERBUST"}
    await update.message.reply_text(
        "👙 Welcome to Perfect Fit\n\nEnter underbust (cm):"
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in user_state:
        await start(update, context)
        return

    step = user_state[uid]["step"]

    if step == "UNDERBUST":
        if not text.isdigit():
            await update.message.reply_text("Enter numbers only")
            return
        user_state[uid]["underbust"] = int(text)
        user_state[uid]["step"] = "BUST"
        await update.message.reply_text("Enter bust (cm):")

    elif step == "BUST":
        if not text.isdigit():
            await update.message.reply_text("Enter numbers only")
            return
        size = calculate_bra_size(user_state[uid]["underbust"], int(text))
        user_state[uid]["size"] = size

        keyboard = [
            [InlineKeyboardButton("Daily Comfort", callback_data="TYPE_DAILY")],
            [InlineKeyboardButton("Sports", callback_data="TYPE_SPORTS")],
        ]

        await update.message.reply_text(
            f"✅ Your size: {size}\nChoose type:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🎉 Recommendations coming soon!\nType /start again."
    )


# ================= FASTAPI LIFESPAN =================
@app.on_event("startup")
async def startup():
    global telegram_app

    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))

    await telegram_app.initialize()
    await telegram_app.start()

    await telegram_app.bot.set_webhook(
        f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

    print("✅ Telegram bot started & webhook set")


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)

    # 🔥 THIS IS THE KEY LINE
    await telegram_app.update_queue.put(update)

    return {"ok": True}


@app.get("/")
def health():
    return {"status": "Perfect Fit running"}
    
