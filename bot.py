"""
🤖 Bot Telegram Predicții Fotbal - VERSIUNEA PRO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✔ Predicții 30 min înainte de meci
✔ Cote filtrate 1.20-1.45
✔ Maximum 3 meciuri pe zi
✔ Notificări automate
✔ Bilete PRO cu cotă 1.6-1.8
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import asyncio
import logging
import json
import os
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


def load_subscribers() -> set:
    """Încarcă abonații din fișier"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
    except:
        pass
    return set()


def save_subscribers(subscribers: set):
    """Salvează abonații în fișier"""
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(list(subscribers), f)
    except:
        pass


def load_notified_matches() -> set:
    """Încarcă meciurile pentru care s-au trimis notificări"""
    try:
        if os.path.exists(NOTIFIED_MATCHES_FILE):
            with open(NOTIFIED_MATCHES_FILE, "r") as f:
                data = json.load(f)
                # Curăță meciurile vechi (mai vechi de 24h)
                now = datetime.now().timestamp()
                return set(k for k, v in data.items() if now - v < 86400)
    except:
        pass
    return set()


def save_notified_matches(matches: set):
    """Salvează meciurile notificate"""
    try:
        now = datetime.now().timestamp()
        data = {m: now for m in matches}
        with open(NOTIFIED_MATCHES_FILE, "w") as f:
            json.dump(data, f)
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

Sunt botul tău PRO de predicții fotbal!

🎯 *FUNCȚII PRO:*
• Predicții cu cote *{MIN_ODD}-{MAX_ODD}*
• Bilete cu cotă totală *{TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}*
• Maximum *{MAX_MATCHES_PER_DAY} meciuri/zi*
• Notificări *{NOTIFICATION_MINUTES_BEFORE} min* înainte de meci

📋 *COMENZI:*
/tips - 🎯 Top predicții ale zilei
/bilet - 🎫 Bilet PRO al zilei
/live - 🔴 Predicții live
/meciuri - 📅 Meciuri cu cote bune
/subscribe - 🔔 Activează notificări
/unsubscribe - 🔕 Dezactivează notificări
/help - ℹ️ Ajutor

━━━━━━━━━━━━━━━━━━━━━━━━
💡 *Start rapid:* Trimite /bilet pentru biletul zilei!
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /help"""
    help_text = f"""
ℹ️ *GHID BOT PRO*
━━━━━━━━━━━━━━━━━━━━━━━━

📊 *Despre cote {MIN_ODD}-{MAX_ODD}:*
Probabilitate implicită: ~70-83%
Risc: Scăzut spre Mediu

🎫 *Despre bilete:*
Cotă totală țintă: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}
Meciuri pe bilet: 2-{MAX_MATCHES_PER_DAY}

🔔 *Notificări:*
Primești alertă cu {NOTIFICATION_MINUTES_BEFORE} min înainte de meciurile selectate.

📋 *Toate comenzile:*
/tips - Predicții detaliate
/bilet - Bilet gata făcut
/live - Meciuri în desfășurare
/meciuri - Lista meciurilor
/subscribe - Activează notificări
/unsubscribe - Oprește notificări
/stats - Statistici bot

⚠️ *Disclaimer:*
Pariază responsabil. Predicțiile nu garantează câștiguri.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def get_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /tips - predicții ale zilei"""
    await update.message.reply_text(
        f"🎯 *Caut cele mai bune predicții...*\n⏳ Analizez meciurile cu cote {MIN_ODD}-{MAX_ODD}",
        parse_mode='Markdown'
    )

    try:
        # Obține meciuri
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri pentru următoarele 24 ore.")
            return

        # Filtrează după cote
        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(upcoming, max_fixtures=15)

        if not fixtures_with_odds:
            await update.message.reply_text(
                f"⚠️ Nu am găsit meciuri cu cote în intervalul {MIN_ODD}-{MAX_ODD}.\n"
                "Încearcă mai târziu."
            )
            return

        # Header
        header = f"""
🎯 *TOP PREDICȚII - {datetime.now().strftime('%d.%m.%Y')}*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Meciuri analizate: {len(fixtures_with_odds)}
💰 Interval cote: {MIN_ODD}-{MAX_ODD}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        # Generează predicții pentru primele 3 meciuri
        for fixture in fixtures_with_odds[:MAX_MATCHES_PER_DAY]:
            # Obține statistici extra
            home_id = fixture["teams"]["home"]["id"]
            away_id = fixture["teams"]["away"]["id"]

            extra_stats = {}
            try:
                extra_stats["home_form"] = await api_football.get_team_form(home_id)
                extra_stats["away_form"] = await api_football.get_team_form(away_id)
                h2h = await api_football.get_h2h(home_id, away_id)
                extra_stats["h2h"] = f"{h2h['team1_wins']}W-{h2h['draws']}D-{h2h['team2_wins']}L"
            except:
                pass

            prediction = await prediction_engine.analyze_match(fixture, extra_stats)
            await update.message.reply_text(prediction, parse_mode='Markdown')
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in get_tips: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /bilet - bilet PRO al zilei"""
    await update.message.reply_text(
        f"🎫 *Generez biletul PRO al zilei...*\n🎯 Cotă țintă: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}",
        parse_mode='Markdown'
    )

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri pentru bilet.")
            return

        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(upcoming, max_fixtures=10)

        if not fixtures_with_odds:
            await update.message.reply_text(
                f"⚠️ Nu am găsit suficiente meciuri cu cote {MIN_ODD}-{MAX_ODD} pentru bilet."
            )
            return

        ticket_text, ticket_bets = await prediction_engine.generate_ticket(fixtures_with_odds)
        await update.message.reply_text(ticket_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in get_ticket: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /live - predicții live"""
    await update.message.reply_text("🔴 *Caut meciuri live...*", parse_mode='Markdown')

    try:
        live_fixtures = await api_football.get_live_fixtures()

        if not live_fixtures:
            await update.message.reply_text(
                "❌ Nu sunt meciuri live acum.\n"
                "Folosește /meciuri pentru meciurile viitoare."
            )
            return

        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(live_fixtures, max_fixtures=5)

        if not fixtures_with_odds:
            await update.message.reply_text(
                f"⚠️ Am găsit {len(live_fixtures)} meciuri live, "
                f"dar niciunul nu are cote în intervalul {MIN_ODD}-{MAX_ODD}."
            )
            return

        header = f"🔴 *MECIURI LIVE - {len(fixtures_with_odds)} cu cote bune*\n━━━━━━━━━━━━━━━━━━━━"
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in fixtures_with_odds[:3]:
            prediction = await prediction_engine.analyze_match(fixture)
            await update.message.reply_text(prediction, parse_mode='Markdown')
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Error in get_live: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /meciuri - lista meciurilor"""
    await update.message.reply_text("📅 *Caut meciuri cu cote bune...*", parse_mode='Markdown')

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(upcoming)

        if not fixtures_with_odds:
            await update.message.reply_text(f"⚠️ Nu am găsit meciuri cu cote {MIN_ODD}-{MAX_ODD}.")
            return

        header = f"""
📅 *MECIURI CU COTE {MIN_ODD}-{MAX_ODD}*
━━━━━━━━━━━━━━━━━━━━━━━━
Găsite: {len(fixtures_with_odds)} meciuri
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in fixtures_with_odds[:8]:
            match_info = api_football.format_fixture(fixture)
            await update.message.reply_text(match_info, parse_mode='Markdown')
            await asyncio.sleep(0.5)

        # Buton pentru bilet
        keyboard = [[InlineKeyboardButton("🎫 Generează Bilet PRO", callback_data="gen_ticket")]]
        await update.message.reply_text(
            "Vrei un bilet gata făcut?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /subscribe"""
    user_id = update.effective_user.id
    if user_id in subscribers:
        await update.message.reply_text("✅ Ești deja abonat la notificări!")
    else:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text(f"""
🔔 *Te-ai abonat cu succes!*
━━━━━━━━━━━━━━━━━━━━━━━━

Vei primi notificări:
• Cu *{NOTIFICATION_MINUTES_BEFORE} minute* înainte de meci
• Pentru meciuri cu cote *{MIN_ODD}-{MAX_ODD}*
• Maximum *{MAX_MATCHES_PER_DAY}* notificări/zi

Folosește /unsubscribe pentru dezabonare.
""", parse_mode='Markdown')


async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /unsubscribe"""
    user_id = update.effective_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text("🔕 Te-ai dezabonat de la notificări.")
    else:
        await update.message.reply_text("ℹ️ Nu ești abonat la notificări.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /stats"""
    stats_text = f"""
📊 *STATISTICI BOT PRO*
━━━━━━━━━━━━━━━━━━━━━━━━

🎯 *Setări:*
• Interval cote: {MIN_ODD}-{MAX_ODD}
• Cotă bilet: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}
• Max meciuri/zi: {MAX_MATCHES_PER_DAY}
• Notificare: {NOTIFICATION_MINUTES_BEFORE} min înainte

👥 *Abonați:* {len(subscribers)}
🕐 *Ora server:* {datetime.now().strftime('%H:%M')}

━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler butoane"""
    query = update.callback_query
    await query.answer()

    if query.data == "gen_ticket":
        await query.edit_message_text("🎫 Generez bilet... Folosește /bilet")


async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    """Job: verifică meciuri și trimite notificări"""
    global notified_matches

    if not subscribers:
        return

    try:
        # Găsește meciuri care încep în 30 minute
        matches_soon = await api_football.get_matches_starting_soon(NOTIFICATION_MINUTES_BEFORE)

        if not matches_soon:
            return

        # Filtrează după cote
        matches_with_odds = await api_football.get_fixtures_with_target_odds(matches_soon, max_fixtures=5)

        if not matches_with_odds:
            return

        # Trimite notificări
        for fixture in matches_with_odds[:MAX_MATCHES_PER_DAY]:
            fixture_id = str(fixture["fixture"]["id"])

            # Skip dacă deja notificat
            if fixture_id in notified_matches:
                continue

            # Generează notificare
            notification = await prediction_engine.get_quick_prediction(fixture)
            if not notification:
                continue

            # Trimite la toți abonații
            for user_id in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=notification,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify {user_id}: {e}")

            # Marchează ca notificat
            notified_matches.add(fixture_id)

        # Salvează
        save_notified_matches(notified_matches)

    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}")


def main():
    """Pornește botul"""
    # Creează aplicația
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handlere comenzi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tips", get_tips))
    application.add_handler(CommandHandler("bilet", get_ticket))
    application.add_handler(CommandHandler("live", get_live))
    application.add_handler(CommandHandler("meciuri", get_matches))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("stats", stats))

    # Handler butoane
    application.add_handler(CallbackQueryHandler(button_callback))

    # Job notificări (la fiecare 10 minute)
    job_queue = application.job_queue
    job_queue.run_repeating(
        check_and_notify,
        interval=CHECK_INTERVAL_MINUTES * 60,
        first=30
    )

    # Start
    print("=" * 50)
    print("🤖 BOT PREDICȚII FOTBAL PRO - ACTIV")
    print(f"📊 Cote: {MIN_ODD}-{MAX_ODD}")
    print(f"🎫 Bilet: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}")
    print(f"🔔 Notificări: {NOTIFICATION_MINUTES_BEFORE} min înainte")
    print(f"👥 Abonați: {len(subscribers)}")
    print("=" * 50)
    logger.info("Bot PRO pornit cu succes!")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
