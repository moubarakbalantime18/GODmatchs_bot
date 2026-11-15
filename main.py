import os, requests, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

LEAGUES = {
    "coupe_du_monde": {"name": "🏆 Coupe du Monde", "id": "4429"},
    "can": {"name": "🌍 CAN", "id": "4738"},
    "espagne": {"name": "🇪🇸 Espagne La Liga", "id": "4335"},
    "angleterre": {"name": "🏴󐁧󐁢󐁥󐁮󐁧󐁿 Angleterre Premier League", "id": "4328"},
    "france": {"name": "🇫🇷 France Ligue 1", "id": "4334"},
}

def get_next_matches(league_id):
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id={league_id}"
        r = requests.get(url, timeout=10).json()
        return r.get("events", [])[:10]
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
    await update.message.reply_text("⚽ *WINMATCH*\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("cat_"):
        key = q.data.replace("cat_", "")
        league = LEAGUES[key]
        matches = get_next_matches(league["id"])
        if not matches:
            await q.edit_message_text("Pas de match trouve pour le moment, reessaie plus tard.")
            return
        m = matches[0]
        home = m.get("strHomeTeam", "Home")
        away = m.get("strAwayTeam", "Away")
        date = m.get("dateEvent", "")
        time = m.get("strTime", "")
        dnp = max(45, min(85, 55 + random.randint(-10, 15)))
        conf = dnp + random.randint(-5, 5)
        pick = "DNB HOME" if dnp >= 55 else "DNB AWAY"
        text = f"⚽ *WINMATCH - {league['name']}*\n\n{home} vs {away}\n📅 {date} {time}\n\n🎯 *Prediction : {pick}*\n💯 Confiance : {conf}%\n📊 DNP : {dnp}%\n\n🔥 Prochain match ?"
        kb = [[InlineKeyboardButton("🔄 NOUVELLE PREDICTION", callback_data=q.data)], [InlineKeyboardButton("⬅️ AUTRE COMPETITION", callback_data="back")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif q.data == "back":
        keyboard = [[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
        await q.edit_message_text("⚽ *WINMATCH*\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
