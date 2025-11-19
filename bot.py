import os
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# -------------------------------
# Small background web server (Render requires a web process)
# -------------------------------
def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"✅ Web server running on port {port}")
    server.serve_forever()

# Start the web server in a background thread
Thread(target=run_web_server, daemon=True).start()

# -------------------------------
# Telegram bot token from environment
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set BOT_TOKEN environment variable!")

# -------------------------------
# Reply keyboard (2 rows)
# -------------------------------
def get_filter_keyboard():
    keyboard = [
        ["/enable_filter"],    # Row 1
        ["/disable_filter"]    # Row 2
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

# -------------------------------
# /start command
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ Bot is active and ready!\n\n"
        "Commands:\n"
        "/enable_filter – Enable link blocking (admins only in groups)\n"
        "/disable_filter – Disable link blocking (admins only in groups)\n\n"
        "Use the buttons below 👇"
    )
    await update.message.reply_text(
        text,
        reply_markup=get_filter_keyboard()
    )

# -------------------------------
# Enable filter
# -------------------------------
async def enable_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type in ["group", "supergroup"]:
        member = await context.bot.get_chat_member(chat.id, user_id)
        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "❌ Only group admins can enable the filter in groups.",
                reply_markup=get_filter_keyboard()
            )
            return

    context.chat_data["filter_enabled"] = True
    await update.message.reply_text(
        "✔ Link filter ENABLED.\nMessages with links from normal users will be deleted.",
        reply_markup=get_filter_keyboard()
    )

# -------------------------------
# Disable filter
# -------------------------------
async def disable_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type in ["group", "supergroup"]:
        member = await context.bot.get_chat_member(chat.id, user_id)
        if member.status not in ["administrator", "creator"]:
            await update.message.reply_text(
                "❌ Only group admins can disable the filter in groups.",
                reply_markup=get_filter_keyboard()
            )
            return

    context.chat_data["filter_enabled"] = False
    await update.message.reply_text(
        "❌ Link filter DISABLED.\nUsers can now send links.",
        reply_markup=get_filter_keyboard()
    )

# -------------------------------
# Delete messages containing links
# -------------------------------
async def delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat

    if not context.chat_data.get("filter_enabled", False):
        return

    if not message or not message.entities:
        return

    user_id = message.from_user.id
    member = await context.bot.get_chat_member(chat.id, user_id)
    if member.status in ["administrator", "creator"]:
        return

    for entity in message.entities:
        if entity.type in ["url", "text_link"]:
            try:
                await message.delete()
                print(f"Deleted a link from user: {user_id}")
            except Exception as e:
                print("Failed to delete message:", e)
            return

# -------------------------------
# Main
# -------------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("enable_filter", enable_filter))
    app.add_handler(CommandHandler("disable_filter", disable_filter))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_links))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
