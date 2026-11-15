import os, random, asyncio, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("BOT_TOKEN")

LEAGUES = {
    "coupe_du_monde": {"name": "🏆 Coupe du Monde"},
    "can": {"name": "🌍 CAN"},
    "espagne": {"name": "🇪🇸 Espagne La Liga"},
    "angleterre": {"name": "🏴󐁧󐁢󐁥󐁮󐁧󐁿 Angleterre Premier League"},
    "france": {"name": "🇫🇷 France Ligue 1"},
}

MATCHS = {
    "coupe_du_monde": [("France", "Argentine", "21 Dec 2026"), ("Espagne", "Angleterre", "22 Dec 2026"), ("Allemagne", "Portugal", "23 Dec 2026")],
    "can": [("Maroc", "Senegal", "21 Dec 2025"), ("Nigeria", "Cote d'Ivoire", "21 Dec 2025"), ("Egypte", "Algerie", "22 Dec 2025"), ("Togo", "Ghana", "22 Dec 2025")],
    "espagne": [("Real Madrid", "Barcelone", "23 Nov 2026"), ("Atletico Madrid", "Seville", "23 Nov 2026")],
    "angleterre": [("Arsenal", "Man City", "22 Nov 2026"), ("Liverpool", "Chelsea", "22 Nov 2026"), ("Man United", "Tottenham", "23 Nov 2026")],
    "france": [("PSG", "Marseille", "22 Nov 2026"), ("Lyon", "Monaco", "22 Nov 2026"), ("Lille", "Lens", "23 Nov 2026")],
}

def make_prediction(league_key):
    league = LEAGUES[league_key]
    home, away, date = random.choice(MATCHS[league_key])
    dnp = random.randint(52, 82)
    conf = min(92, dnp + random.randint(-3, 8))
    pick = "DNB HOME" if dnp >= 60 else "DNB AWAY" if dnp < 50 else "DNB HOME"
    if dnp < 55:
        pick = "DNB AWAY"
    text = f"⚽ *WINMATCH - {league['name']}*\n\n{home} vs {away}\n📅 {date}\n\n🎯 *Prediction : {pick}*\n💯 Confiance : {conf}%\n📊 DNP : {dnp}%\n\n🔥 Bonne chance patron !"
    kb = [[InlineKeyboardButton("🔄 NOUVELLE PREDICTION", callback_data=f"cat_{league_key}")], [InlineKeyboardButton("⬅️ AUTRE COMPETITION", callback_data="back")]]
    return text, InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
    await update.message.reply_text("⚽ *WINMATCH*\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("cat_"):
        key = q.data.replace("cat_", "")
        text, kb = make_prediction(key)
        await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    elif q.data == "back":
        keyboard = [[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
        await q.edit_message_text("⚽ *WINMATCH*\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive")
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

async def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
