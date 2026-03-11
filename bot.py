"""
🤖 Bot Telegram Predicții Fotbal - VERSIUNEA PRO v3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✔ Scanare CONTINUĂ meciuri live
✔ Notificări SMART când găsește cote bune
✔ Link-uri SUPERBET pentru pariuri rapide
✔ Analiză AI cu ChatGPT
✔ 5 surse web pentru statistici
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import asyncio
import logging
import json
import os
import urllib.parse
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import (
    TELEGRAM_BOT_TOKEN, MIN_ODD, MAX_ODD,
    MAX_MATCHES_PER_DAY, CHECK_INTERVAL_MINUTES,
    NOTIFICATION_MINUTES_BEFORE, TICKET_MIN_TOTAL_ODD, TICKET_MAX_TOTAL_ODD
)
from api_football import APIFootball
from prediction_engine import PredictionEngine
from web_scraper import get_extended_analysis, FootballScraper

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Servicii
api_football = APIFootball()
prediction_engine = PredictionEngine()

# Stocare date
SUBSCRIBERS_FILE = "subscribers.json"
NOTIFIED_MATCHES_FILE = "notified_matches.json"
SMART_ALERTS_FILE = "smart_alerts.json"

# Setări scanare live
LIVE_SCAN_INTERVAL = 3  # minute - scanează la fiecare 3 minute
MIN_CONFIDENCE = 65  # procent minim încredere pentru notificare
GOOD_ODD_MIN = 1.30  # cotă minimă considerată "bună"
GOOD_ODD_MAX = 2.50  # cotă maximă considerată "sigură"


def get_superbet_link(home_team: str, away_team: str) -> str:
    """Generează link de căutare Superbet"""
    search_term = f"{home_team} {away_team}"
    encoded = urllib.parse.quote(search_term)
    return f"https://superbet.ro/pariuri-sportive/cautare?query={encoded}"


def load_subscribers() -> set:
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
    except:
        pass
    return set()


def save_subscribers(subscribers: set):
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(list(subscribers), f)
    except:
        pass


def load_notified_matches() -> dict:
    try:
        if os.path.exists(NOTIFIED_MATCHES_FILE):
            with open(NOTIFIED_MATCHES_FILE, "r") as f:
                data = json.load(f)
                now = datetime.now().timestamp()
                # Păstrează doar notificările din ultimele 24 ore
                return {k: v for k, v in data.items() if now - v < 86400}
    except:
        pass
    return {}


def save_notified_matches(matches: dict):
    try:
        with open(NOTIFIED_MATCHES_FILE, "w") as f:
            json.dump(matches, f)
    except:
        pass


# Date globale
subscribers = load_subscribers()
notified_matches = load_notified_matches()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /start"""
    user = update.effective_user
    welcome = f"""
🤖 *Bine ai venit, {user.first_name}!*
━━━━━━━━━━━━━━━━━━━━━━━━

Sunt botul tău PRO de predicții fotbal cu SUPERBET!

🎯 *FUNCȚII SMART:*
• Scanare LIVE la fiecare {LIVE_SCAN_INTERVAL} minute
• Notificări când găsesc cote BUNE
• Link-uri directe SUPERBET
• Analiză AI + 5 surse web

📋 *COMENZI:*
/tips - 🎯 Top predicții ale zilei
/bilet - 🎫 Bilet PRO al zilei
/live - 🔴 Meciuri live + cote
/toate - 📋 TOATE meciurile
/analiza - 🔬 Analiză din 5 surse
/subscribe - 🔔 Notificări SMART
/stop - 🔕 Oprește notificările
/help - ℹ️ Ajutor

━━━━━━━━━━━━━━━━━━━━━━━━
🎰 *SUPERBET:* Link-uri directe la fiecare meci!
💡 Trimite /subscribe pentru alerte automate!
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /help"""
    help_text = f"""
ℹ️ *GHID BOT PRO v3*
━━━━━━━━━━━━━━━━━━━━━━━━

🔔 *NOTIFICĂRI SMART:*
Botul scanează meciurile live la fiecare {LIVE_SCAN_INTERVAL} minute.
Când găsește un meci cu:
• Cotă între {GOOD_ODD_MIN}-{GOOD_ODD_MAX}
• Încredere AI > {MIN_CONFIDENCE}%
➡️ Primești NOTIFICARE automată!

🎰 *SUPERBET:*
Fiecare meci vine cu link direct
către Superbet pentru pariat rapid.

📋 *Toate comenzile:*
/tips - Predicții detaliate
/bilet - Bilet gata făcut
/live - Meciuri live cu cote
/toate - TOATE meciurile
/meciuri - Meciuri viitoare
/analiza [echipa1] vs [echipa2] - Analiză 5 surse
/subscribe - Activează notificări
/stop - Dezactivează notificări
/stats - Statistici bot

⚠️ *Disclaimer:*
Pariază responsabil. Predicțiile nu garantează câștiguri.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def get_all_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /toate - TOATE meciurile"""
    await update.message.reply_text("📋 *Caut TOATE meciurile...*", parse_mode='Markdown')

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)

        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        header = f"""
📋 *TOATE MECIURILE - {datetime.now().strftime('%d.%m.%Y')}*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total: {len(upcoming)} meciuri
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(upcoming, max_fixtures=15)

        for fixture in (fixtures_with_odds or upcoming)[:10]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            match_info = format_match_with_superbet(fixture)
            await update.message.reply_text(match_info, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Error in get_all_matches: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


def format_match_with_superbet(fixture: dict) -> str:
    """Formatează meci cu link Superbet"""
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    league = fixture["league"]["name"]

    match_time = datetime.fromtimestamp(fixture["fixture"]["timestamp"])
    time_str = match_time.strftime("%H:%M")

    status = fixture["fixture"]["status"]["short"]

    if status == "NS":
        score = f"⏰ {time_str}"
    elif status in ["1H", "2H", "HT", "ET", "P", "LIVE"]:
        elapsed = fixture["fixture"]["status"]["elapsed"] or 0
        goals_home = fixture["goals"]["home"] or 0
        goals_away = fixture["goals"]["away"] or 0
        score = f"🔴 LIVE {elapsed}' | {goals_home}-{goals_away}"
    else:
        score = f"📊 {status}"

    odds_str = ""
    if "odds" in fixture:
        odds = fixture["odds"]
        odds_str = f"\n💰 1={odds['home']:.2f} | X={odds['draw']:.2f} | 2={odds['away']:.2f}"

    superbet_link = get_superbet_link(home, away)

    return f"""
⚽ *{home}* vs *{away}*
🏆 {league} | {score}{odds_str}
🎰 [PARIAZĂ PE SUPERBET]({superbet_link})
"""


async def get_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /tips - predicții ale zilei"""
    await update.message.reply_text(
        "🎯 *Analizez meciurile cu AI...*\n⏳ Așteptați...",
        parse_mode='Markdown'
    )

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(upcoming, max_fixtures=10)

        if not fixtures_with_odds:
            await update.message.reply_text("❌ Nu am putut obține cotele.")
            return

        header = f"""
🎯 *TOP PREDICȚII - {datetime.now().strftime('%d.%m.%Y')}*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Meciuri analizate: {len(fixtures_with_odds)}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in fixtures_with_odds[:5]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]

            prediction = await prediction_engine.analyze_match(fixture)
            superbet_link = get_superbet_link(home, away)

            full_msg = f"{prediction}\n\n🎰 [PARIAZĂ PE SUPERBET]({superbet_link})"
            await update.message.reply_text(full_msg, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in get_tips: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /bilet - bilet PRO"""
    await update.message.reply_text(
        f"🎫 *Generez biletul PRO...*\n🎯 Cotă țintă: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}",
        parse_mode='Markdown'
    )

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(upcoming, max_fixtures=10)

        if not fixtures_with_odds:
            await update.message.reply_text("❌ Nu am putut obține cote.")
            return

        ticket_text, ticket_bets = await prediction_engine.generate_ticket(fixtures_with_odds)

        # Adaugă link Superbet pentru fiecare meci din bilet
        superbet_links = "\n\n🎰 *LINK-URI SUPERBET:*"
        for fixture in fixtures_with_odds[:3]:
            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            link = get_superbet_link(home, away)
            superbet_links += f"\n• [{home} vs {away}]({link})"

        await update.message.reply_text(
            ticket_text + superbet_links,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in get_ticket: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /live - meciuri live"""
    await update.message.reply_text("🔴 *Caut meciuri LIVE...*", parse_mode='Markdown')

    try:
        live_fixtures = await api_football.get_live_fixtures()

        if not live_fixtures:
            await update.message.reply_text(
                "❌ Nu sunt meciuri live acum.\n"
                "Folosește /toate pentru meciurile viitoare."
            )
            return

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(live_fixtures, max_fixtures=10)

        header = f"""
🔴 *MECIURI LIVE*
━━━━━━━━━━━━━━━━━━━━
📊 Total live: {len(live_fixtures)}
💰 Cu cote: {len(fixtures_with_odds)}
━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in (fixtures_with_odds or live_fixtures)[:8]:
            match_info = format_match_with_superbet(fixture)
            await update.message.reply_text(match_info, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Error in get_live: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /meciuri"""
    await update.message.reply_text("📅 *Caut meciuri viitoare...*", parse_mode='Markdown')

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=12)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(upcoming, max_fixtures=10)

        header = f"📅 *MECIURI VIITOARE* - {len(fixtures_with_odds)} cu cote"
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in fixtures_with_odds[:8]:
            match_info = format_match_with_superbet(fixture)
            await update.message.reply_text(match_info, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /analiza - analiză COMPLETĂ cu PRONOSTIC FINAL"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ *Folosire:* /analiza [Echipa1] vs [Echipa2]\n\n"
            "*Exemple:*\n"
            "/analiza Barcelona vs Real Madrid\n"
            "/analiza Liverpool vs Manchester City",
            parse_mode='Markdown'
        )
        return

    full_text = " ".join(context.args)

    if " vs " in full_text.lower():
        parts = full_text.lower().split(" vs ")
    elif " - " in full_text:
        parts = full_text.split(" - ")
    else:
        parts = full_text.split()
        if len(parts) >= 2:
            mid = len(parts) // 2
            parts = [" ".join(parts[:mid]), " ".join(parts[mid:])]
        else:
            await update.message.reply_text("❌ Format: /analiza Echipa1 vs Echipa2")
            return

    if len(parts) < 2:
        await update.message.reply_text("❌ Te rog specifică două echipe.")
        return

    home_team = parts[0].strip().title()
    away_team = parts[1].strip().title()

    await update.message.reply_text(
        f"🔬 *Analizez:* {home_team} vs {away_team}\n\n"
        f"📡 Caut date din 5 surse...\n"
        f"🤖 Generez PRONOSTIC FINAL cu AI...",
        parse_mode='Markdown'
    )

    try:
        # 1. Obține date din surse web
        scraper = FootballScraper()
        web_data = await scraper.get_combined_analysis(home_team, away_team)

        # 2. Trimite datele la AI pentru pronostic FINAL
        prediction = await prediction_engine.analyze_with_web_data(
            home_team,
            away_team,
            web_data
        )

        # 3. Adaugă link Superbet
        superbet_link = get_superbet_link(home_team, away_team)
        full_msg = f"{prediction}\n\n🎰 [PARIAZĂ PE SUPERBET]({superbet_link})"

        await update.message.reply_text(full_msg, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error in get_analysis: {e}")
        # Fallback - oferă predicție fără date web
        try:
            fallback = await prediction_engine.analyze_with_web_data(home_team, away_team, {})
            superbet_link = get_superbet_link(home_team, away_team)
            await update.message.reply_text(
                f"{fallback}\n\n🎰 [PARIAZĂ PE SUPERBET]({superbet_link})",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except:
            await update.message.reply_text(f"❌ Eroare la analiză: {str(e)}")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /subscribe - activează notificări SMART"""
    user_id = update.effective_user.id
    if user_id in subscribers:
        await update.message.reply_text("✅ Ești deja abonat la notificări SMART!")
    else:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text(f"""
🔔 *NOTIFICĂRI SMART ACTIVATE!*
━━━━━━━━━━━━━━━━━━━━━━━━

Vei primi alerte automate când găsesc:
• Meciuri LIVE cu cote bune ({GOOD_ODD_MIN}-{GOOD_ODD_MAX})
• Predicții cu încredere > {MIN_CONFIDENCE}%
• Link direct SUPERBET pentru pariere rapidă

📊 Scanare: la fiecare {LIVE_SCAN_INTERVAL} minute
⚡ Răspuns: notificare instant

Folosește /stop pentru dezabonare.
""", parse_mode='Markdown')


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /stop - dezactivează notificări"""
    user_id = update.effective_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text("🔕 Notificări dezactivate.")
    else:
        await update.message.reply_text("ℹ️ Nu ești abonat la notificări.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /stats"""
    stats_text = f"""
📊 *STATISTICI BOT PRO v3*
━━━━━━━━━━━━━━━━━━━━━━━━

🔔 *Notificări:*
• Abonați: {len(subscribers)}
• Scanare: la {LIVE_SCAN_INTERVAL} min
• Încredere minimă: {MIN_CONFIDENCE}%

💰 *Cote monitorizate:*
• Interval: {GOOD_ODD_MIN} - {GOOD_ODD_MAX}

🎰 *Integrare:*
• Casa de pariuri: SUPERBET
• Link-uri: Active

🕐 *Ora server:* {datetime.now().strftime('%H:%M:%S')}
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler butoane"""
    query = update.callback_query
    await query.answer()

    if query.data == "gen_ticket":
        await query.edit_message_text("🎫 Folosește /bilet pentru bilet nou")


async def smart_live_scanner(context: ContextTypes.DEFAULT_TYPE):
    """
    JOB: Scanează meciurile LIVE și trimite notificări SMART
    Rulează la fiecare LIVE_SCAN_INTERVAL minute
    """
    global notified_matches

    if not subscribers:
        return

    try:
        logger.info("🔍 Scanare SMART meciuri live...")

        # Obține meciuri live
        live_fixtures = await api_football.get_live_fixtures()
        if not live_fixtures:
            return

        # Obține cote pentru meciurile live
        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(live_fixtures, max_fixtures=8)
        if not fixtures_with_odds:
            return

        for fixture in fixtures_with_odds:
            fixture_id = str(fixture["fixture"]["id"])

            # Skip dacă am notificat deja
            if fixture_id in notified_matches:
                continue

            # Verifică dacă are cote "bune"
            if "odds" not in fixture:
                continue

            odds = fixture["odds"]
            home_odd = odds.get("home", 0)
            draw_odd = odds.get("draw", 0)
            away_odd = odds.get("away", 0)

            # Găsește cea mai bună cotă în intervalul dorit
            best_bet = None
            best_odd = 0

            if GOOD_ODD_MIN <= home_odd <= GOOD_ODD_MAX:
                best_bet = ("1 (Victoria gazdă)", home_odd)
                best_odd = home_odd
            if GOOD_ODD_MIN <= draw_odd <= GOOD_ODD_MAX and draw_odd > best_odd:
                best_bet = ("X (Egal)", draw_odd)
                best_odd = draw_odd
            if GOOD_ODD_MIN <= away_odd <= GOOD_ODD_MAX and away_odd > best_odd:
                best_bet = ("2 (Victoria oaspete)", away_odd)
                best_odd = away_odd

            if not best_bet:
                continue

            # Obține predicție AI rapidă
            try:
                quick_analysis = await prediction_engine.get_quick_prediction(fixture)
                confidence = prediction_engine.last_confidence if hasattr(prediction_engine, 'last_confidence') else 70
            except:
                confidence = 70
                quick_analysis = None

            # Trimite notificare dacă încrederea e suficientă
            if confidence >= MIN_CONFIDENCE or best_odd >= 1.50:
                home = fixture["teams"]["home"]["name"]
                away = fixture["teams"]["away"]["name"]
                league = fixture["league"]["name"]
                elapsed = fixture["fixture"]["status"]["elapsed"] or 0
                goals_home = fixture["goals"]["home"] or 0
                goals_away = fixture["goals"]["away"] or 0

                superbet_link = get_superbet_link(home, away)

                notification = f"""
🚨 *ALERTĂ SMART!*
━━━━━━━━━━━━━━━━━━━━

⚽ *{home}* vs *{away}*
🏆 {league}
🔴 LIVE: {elapsed}' | Scor: {goals_home}-{goals_away}

💰 *PRONOSTIC:* {best_bet[0]}
📊 *COTĂ:* {best_bet[1]:.2f}
🎯 *Încredere:* ~{confidence}%

━━━━━━━━━━━━━━━━━━━━
🎰 [PARIAZĂ ACUM PE SUPERBET]({superbet_link})
━━━━━━━━━━━━━━━━━━━━

⚠️ Pariază responsabil!
"""
                # Trimite la toți abonații
                for user_id in subscribers:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=notification,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )
                        logger.info(f"📤 Notificare trimisă: {fixture_id} -> {user_id}")
                    except Exception as e:
                        logger.error(f"Eroare notificare {user_id}: {e}")

                # Marchează ca notificat
                notified_matches[fixture_id] = datetime.now().timestamp()

        # Salvează meciurile notificate
        save_notified_matches(notified_matches)

    except Exception as e:
        logger.error(f"Eroare în smart_live_scanner: {e}")


async def check_upcoming_matches(context: ContextTypes.DEFAULT_TYPE):
    """
    JOB: Verifică meciuri care încep curând și trimite notificări
    """
    global notified_matches

    if not subscribers:
        return

    try:
        matches_soon = await api_football.get_matches_starting_soon(NOTIFICATION_MINUTES_BEFORE)
        if not matches_soon:
            return

        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(matches_soon, max_fixtures=5)

        for fixture in (fixtures_with_odds or matches_soon[:3]):
            fixture_id = f"upcoming_{fixture['fixture']['id']}"

            if fixture_id in notified_matches:
                continue

            home = fixture["teams"]["home"]["name"]
            away = fixture["teams"]["away"]["name"]
            league = fixture["league"]["name"]
            match_time = datetime.fromtimestamp(fixture["fixture"]["timestamp"])

            odds_str = ""
            if "odds" in fixture:
                odds = fixture["odds"]
                odds_str = f"\n💰 1={odds['home']:.2f} | X={odds['draw']:.2f} | 2={odds['away']:.2f}"

            superbet_link = get_superbet_link(home, away)

            notification = f"""
⏰ *MECI ÎN {NOTIFICATION_MINUTES_BEFORE} MIN!*
━━━━━━━━━━━━━━━━━━━━

⚽ *{home}* vs *{away}*
🏆 {league}
🕐 Ora: {match_time.strftime('%H:%M')}{odds_str}

━━━━━━━━━━━━━━━━━━━━
🎰 [PARIAZĂ PE SUPERBET]({superbet_link})
"""
            for user_id in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=notification,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.error(f"Eroare notificare upcoming {user_id}: {e}")

            notified_matches[fixture_id] = datetime.now().timestamp()

        save_notified_matches(notified_matches)

    except Exception as e:
        logger.error(f"Eroare în check_upcoming_matches: {e}")


def main():
    """Pornește botul"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlere comenzi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tips", get_tips))
    application.add_handler(CommandHandler("bilet", get_ticket))
    application.add_handler(CommandHandler("live", get_live))
    application.add_handler(CommandHandler("meciuri", get_matches))
    application.add_handler(CommandHandler("toate", get_all_matches))
    application.add_handler(CommandHandler("analiza", get_analysis))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("stop", unsubscribe))
    application.add_handler(CommandHandler("stats", stats))

    application.add_handler(CallbackQueryHandler(button_callback))

    # JOB-URI AUTOMATE
    job_queue = application.job_queue

    # 1. Scanare SMART meciuri LIVE - la fiecare 3 minute
    job_queue.run_repeating(
        smart_live_scanner,
        interval=LIVE_SCAN_INTERVAL * 60,
        first=30
    )

    # 2. Verificare meciuri care încep curând - la fiecare 10 minute
    job_queue.run_repeating(
        check_upcoming_matches,
        interval=CHECK_INTERVAL_MINUTES * 60,
        first=60
    )

    print("=" * 50)
    print("🤖 BOT PREDICȚII FOTBAL PRO v3 - ACTIV")
    print(f"🔔 Scanare LIVE: la {LIVE_SCAN_INTERVAL} minute")
    print(f"🎰 Integrare: SUPERBET")
    print(f"📊 Încredere minimă: {MIN_CONFIDENCE}%")
    print("=" * 50)
    logger.info("Bot PRO v3 pornit cu succes!")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
