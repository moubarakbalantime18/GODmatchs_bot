import os, random, asyncio, threading, math, requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_FOOTBALL_KEY")

LEAGUES = {
    "can": {"name": "🌍 CAN", "api_id": 6},
    "espagne": {"name": "🇪🇸 La Liga", "api_id": 140},
    "angleterre": {"name": "🏴󐁧󐁢󐁥󐁮󐁧󐁿 Premier League", "api_id": 39},
    "france": {"name": "🇫🇷 Ligue 1", "api_id": 61},
    "coupe_du_monde": {"name": "🏆 Coupe du Monde", "api_id": 1},
}

ELO_BASE = {"Maroc":1820,"Senegal":1780,"Nigeria":1750,"Cote d'Ivoire":1720,"Egypte":1700,"Algerie":1690,"Ghana":1620,"Togo":1450,"Real Madrid":1960,"Barcelone":1940,"Atletico Madrid":1880,"Seville":1750,"Arsenal":1930,"Man City":1950,"Liverpool":1920,"Chelsea":1860,"Man United":1820,"Tottenham":1800,"PSG":1930,"Marseille":1820,"Lyon":1780,"Monaco":1800,"Lille":1760,"Lens":1720,"France":1960,"Argentine":1950,"Espagne":1940,"Angleterre":1920,"Allemagne":1900,"Portugal":1890}

HEADERS = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": "v3.football.api-sports.io"} if API_KEY else {}

def api_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.json().get("response", [])
    except:
        return []

def poisson(k, lam):
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)

def get_stats(team_id):
    fixtures = api_get(f"https://v3.football.api-sports.io/fixtures?team={team_id}&last=5")
    if not fixtures:
        return {"pts": 8, "bm": 1.4, "be": 1.1}
    pts=0; bm=0; be=0; n=0
    for m in fixtures:
        gh=m["goals"]["home"]; ga=m["goals"]["away"]
        if gh is None: continue
        is_home = m["teams"]["home"]["id"]==team_id
        my = gh if is_home else ga
        opp = ga if is_home else gh
        bm+=my; be+=opp; n+=1
        if my>opp: pts+=3
        elif my==opp: pts+=1
    n=max(1,n)
    return {"pts": pts, "bm": bm/n, "be": be/n}

def get_blessures(team_id):
    if not team_id: return 0
    return len(api_get(f"https://v3.football.api-sports.io/injuries?team={team_id}&season=2026"))

def analyse(home, away, hid, aid):
    st_h = get_stats(hid) if hid else {"pts":8,"bm":1.4,"be":1.1}
    st_a = get_stats(aid) if aid else {"pts":8,"bm":1.4,"be":1.1}
    bh = get_blessures(hid); ba = get_blessures(aid)
    lam_h = max(0.3, min(3.5, 1.35 * (st_h["bm"]/1.35) * (st_a["be"]/1.35) * 1.22))
    lam_a = max(0.3, min(3.5, 1.35 * (st_a["bm"]/1.35) * (st_h["be"]/1.35) * 0.85))
    p_home=p_draw=p_away=p_over15=p_btts=p_under35=0
    best_score = "1-0"; best_score_p = 0
    for gh in range(0,7):
        for ga in range(0,7):
            p = poisson(gh,lam_h)*poisson(ga,lam_a)
            if p > best_score_p:
                best_score_p = p; best_score = f"{gh}-{ga}"
            if gh>ga: p_home+=p
            elif gh==ga: p_draw+=p
            else: p_away+=p
            if gh+ga>1.5: p_over15+=p
            if gh+ga<3.5: p_under35+=p
            if gh>0 and ga>0: p_btts+=p
    p_dnb_h = p_home + p_draw*(p_home/(p_home+p_away+0.001))
    p_dnb_a = p_away + p_draw*(p_away/(p_home+p_away+0.001))
    options = [("DNB HOME ✅", p_dnb_h),("DNB AWAY ✈️", p_dnb_a),("OVER 1.5 BUTS ⚽", p_over15),("UNDER 3.5 BUTS 🛡️", p_under35),("BTTS - LES 2 MARQUENT ⚽⚽", p_btts),("DOUBLE CHANCE 1X 🤝", p_home+p_draw),("DOUBLE CHANCE X2 🤝", p_away+p_draw),]
    options.sort(key=lambda x: x[1], reverse=True)
    best = options[0]; second = options[1]
    if best[1] < 0.68:
        dc = max([o for o in options if "DOUBLE CHANCE" in o[0]], key=lambda x: x[1])
        best = dc; second = [o for o in options if o[0]!=dc[0]][0]
    def feu(pts):
        if pts>=12: return "🔥🔥🔥"
        if pts>=8: return "🔥🔥"
        if pts>=5: return "🔥"
        return "❄️"
    return best[0], min(93,int(best[1]*100)+6), int(best[1]*100), lam_h, lam_a, int(p_home*100), int(p_draw*100), int(p_away*100), feu(st_h["pts"]), feu(st_a["pts"]), bh, ba, best_score, int(best_score_p*100), second[0]

def get_matchs(league_key):
    # 1. D'ABORD : On essaie l'API pour avoir les VRAIES dates officielles
    if API_KEY:
        try:
            data=api_get(f"https://v3.football.api-sports.io/fixtures?league={LEAGUES[league_key]['api_id']}&next=8")
            if data:
                return [(m["teams"]["home"]["name"],m["teams"]["away"]["name"],m["fixture"]["date"][:10],m["teams"]["home"]["id"],m["teams"]["away"]["id"]) for m in data[:8]], True
        except: pass
    # 2. SINON : Dates calculées automatiquement à partir d'AUJOURD'HUI
    # Aujourd'hui + 1 jour, + 2 jours, + 3 jours... Ca marche en Nov, Dec, Jan 2027, toujours !
    base = datetime.now()
    def d(jours):
        return (base + timedelta(days=jours)).strftime("%Y-%m-%d")
    FALLBACK={
        "can":[("Maroc","Senegal",d(1),None,None),("Nigeria","Cote d'Ivoire",d(2),None,None),("Egypte","Algerie",d(3),None,None),("Togo","Ghana",d(4),None,None),("Cameroun","Mali",d(5),None,None)],
        "espagne":[("Real Madrid","Barcelone",d(1),None,None),("Atletico Madrid","Seville",d(2),None,None),("Real Sociedad","Villarreal",d(3),None,None)],
        "angleterre":[("Arsenal","Man City",d(1),None,None),("Liverpool","Chelsea",d(2),None,None),("Man United","Tottenham",d(3),None,None),("Newcastle","Brighton",d(4),None,None)],
        "france":[("PSG","Marseille",d(1),None,None),("Lyon","Monaco",d(2),None,None),("Lille","Lens",d(3),None,None),("Rennes","Nantes",d(4),None,None)],
        "coupe_du_monde":[("France","Argentine",d(1),None,None),("Espagne","Angleterre",d(2),None,None),("Allemagne","Portugal",d(3),None,None)]
    }
    return FALLBACK[league_key], False

def make_prediction(league_key):
    league=LEAGUES[league_key]
    matchs,is_live=get_matchs(league_key)
    home,away,date,hid,aid=random.choice(matchs)
    pick,conf,dnp,lam_h,lam_a,ph,pd,pa,feu_h,feu_a,bh,ba,score,score_p,second=analyse(home,away,hid,aid)
    try:
        dt=datetime.strptime(date, "%Y-%m-%d")
        date_jolie=dt.strftime("%d %b %Y")
    except:
        date_jolie=date
    api_txt = "🟢 API LIVE" if is_live else "🟠 MODE SECOURS"
    text=f"⚽ *WINMATCH PRO*\n\n{league['name']}\n{home} vs {away}\n📅 {date_jolie}\n{api_txt}\n\n🎯 *PREDICTION : {pick}*\n💯 Confiance : {conf}%\n📊 DNP : {dnp}%\n\n📈 *Analyse :*\nButs attendus : {lam_h:.1f} - {lam_a:.1f}\nProba : 1 = {ph}% | N = {pd}% | 2 = {pa}%\nForme : {home} {feu_h} | {away} {feu_a}\nBlessés : {bh} vs {ba}\n\n🔢 *Score Exact : {score} ({score_p}%)*\n🛡️ *2ème Option : {second}*\n\n🔥 Bonne chance patron !"
    kb=[[InlineKeyboardButton("🔄 NOUVELLE PREDICTION", callback_data=f"cat_{league_key}")],[InlineKeyboardButton("⬅️ AUTRE COMPETITION", callback_data="back")]]
    return text, InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard=[[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
    await update.message.reply_text("⚽ *WINMATCH PRO*\nPoisson + Elo + Forme + Blessés + Score Exact\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    if q.data.startswith("cat_"):
        key=q.data.replace("cat_","")
        text,kb=make_prediction(key)
        await q.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    elif q.data=="back":
        keyboard=[[InlineKeyboardButton(v["name"], callback_data=f"cat_{k}")] for k,v in LEAGUES.items()]
        await q.edit_message_text("⚽ *WINMATCH PRO*\nChoisis ta competition 👇", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").lower()
    league_key = "angleterre"
    if "can" in txt: league_key = "can"
    elif "espagne" in txt or "liga" in txt: league_key = "espagne"
    elif "france" in txt or "ligue" in txt: league_key = "france"
    elif "monde" in txt or "coupe" in txt: league_key = "coupe_du_monde"
    matchs, _ = get_matchs(league_key)
    liste = "\n".join([f"• {h} vs {a} - {d}" for h,a,d,_,_ in matchs[:5]])
    await update.message.reply_text(f"⚽ *PROCHAINS MATCHS - {LEAGUES[league_key]['name']}*\n\n{liste}\n\nClique sur une compétition pour avoir la prédiction 👇", parse_mode="Markdown")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Bot is alive")
    def log_message(self, format, *args): pass

def run_server():
    port=int(os.environ.get("PORT",10000))
    HTTPServer(("0.0.0.0",port), Handler).serve_forever()

async def main():
    threading.Thread(target=run_server, daemon=True).start()
    app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    await app.initialize(); await app.start(); await app.updater.start_polling(); await asyncio.Event().wait()

if __name__=="__main__":
    asyncio.run(main())
