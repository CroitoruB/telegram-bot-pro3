"""
🤖 Bot Telegram Predicții Fotbal - VERSIUNEA PRO v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✔ Predicții 30 min înainte de meci
✔ Cote filtrate 1.20-1.45
✔ Maximum 3 meciuri pe zi
✔ Notificări automate
✔ Bilete PRO cu cotă 1.6-1.8
✔ Afișare TOATE meciurile (nou!)
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


def load_notified_matches() -> set:
    try:
        if os.path.exists(NOTIFIED_MATCHES_FILE):
            with open(NOTIFIED_MATCHES_FILE, "r") as f:
                data = json.load(f)
                now = datetime.now().timestamp()
                return set(k for k, v in data.items() if now - v < 86400)
    except:
        pass
    return set()


def save_notified_matches(matches: set):
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
• Notificări *{NOTIFICATION_MINUTES_BEFORE} min* înainte

📋 *COMENZI:*
/tips - 🎯 Top predicții ale zilei
/bilet - 🎫 Bilet PRO al zilei
/live - 🔴 Predicții live
/meciuri - 📅 Meciuri cu cote {MIN_ODD}-{MAX_ODD}
/toate - 📋 TOATE meciurile (fără filtru)
/analiza - 🔬 Analiză extinsă (3 surse web)
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
Primești alertă cu {NOTIFICATION_MINUTES_BEFORE} min înainte.

📋 *Toate comenzile:*
/tips - Predicții detaliate (cote {MIN_ODD}-{MAX_ODD})
/bilet - Bilet gata făcut
/live - Meciuri în desfășurare
/meciuri - Meciuri cu cote țintă
/toate - TOATE meciurile (fără filtru cote)
/subscribe - Activează notificări
/stats - Statistici bot

⚠️ *Disclaimer:*
Pariază responsabil. Predicțiile nu garantează câștiguri.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def get_all_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /toate - TOATE meciurile fără filtru"""
    await update.message.reply_text("📋 *Caut TOATE meciurile de azi...*", parse_mode='Markdown')

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)

        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri pentru următoarele 24 ore.")
            return

        header = f"""
📋 *TOATE MECIURILE - {datetime.now().strftime('%d.%m.%Y')}*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total meciuri găsite: {len(upcoming)}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        # Obține cote pentru primele meciuri
        fixtures_with_any_odds = await api_football.get_all_fixtures_with_odds(upcoming, max_fixtures=15)

        if not fixtures_with_any_odds:
            # Afișează meciurile fără cote
            for fixture in upcoming[:10]:
                match_info = api_football.format_fixture_simple(fixture)
                await update.message.reply_text(match_info, parse_mode='Markdown')
                await asyncio.sleep(0.3)
        else:
            for fixture in fixtures_with_any_odds[:10]:
                match_info = api_football.format_fixture_with_highlight(fixture)
                await update.message.reply_text(match_info, parse_mode='Markdown')
                await asyncio.sleep(0.3)

        # Rezumat
        summary = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📊 *Afișate:* {min(len(fixtures_with_any_odds), 10)} meciuri
💡 Meciurile cu ✅ au cote în intervalul {MIN_ODD}-{MAX_ODD}

Folosește /tips pentru predicții detaliate!
"""
        await update.message.reply_text(summary, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in get_all_matches: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /tips - predicții ale zilei"""
    await update.message.reply_text(
        f"🎯 *Caut cele mai bune predicții...*\n⏳ Analizez meciurile cu cote {MIN_ODD}-{MAX_ODD}",
        parse_mode='Markdown'
    )

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri pentru următoarele 24 ore.")
            return

        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(upcoming, max_fixtures=15)

        if not fixtures_with_odds:
            # Arată meciurile găsite chiar dacă nu au cote țintă
            await update.message.reply_text(
                f"⚠️ Nu am găsit meciuri cu cote {MIN_ODD}-{MAX_ODD}.\n\n"
                f"📋 Am găsit {len(upcoming)} meciuri în total.\n"
                f"Folosește /toate pentru a le vedea pe toate!"
            )
            return

        header = f"""
🎯 *TOP PREDICȚII - {datetime.now().strftime('%d.%m.%Y')}*
━━━━━━━━━━━━━━━━━━━━━━━━
📊 Meciuri cu cote {MIN_ODD}-{MAX_ODD}: {len(fixtures_with_odds)}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        for fixture in fixtures_with_odds[:MAX_MATCHES_PER_DAY]:
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
                f"⚠️ Nu am găsit suficiente meciuri cu cote {MIN_ODD}-{MAX_ODD} pentru bilet.\n\n"
                f"📋 Am găsit {len(upcoming)} meciuri în total.\n"
                f"Folosește /toate pentru a le vedea!"
            )
            return

        ticket_text, ticket_bets = await prediction_engine.generate_ticket(fixtures_with_odds)
        await update.message.reply_text(ticket_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in get_ticket: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /live - TOATE meciurile live cu TOATE cotele"""
    await update.message.reply_text("🔴 *Caut TOATE meciurile live cu cote...*", parse_mode='Markdown')

    try:
        live_fixtures = await api_football.get_live_fixtures()

        if not live_fixtures:
            await update.message.reply_text(
                "❌ Nu sunt meciuri live acum.\n"
                "Folosește /meciuri sau /toate pentru meciurile viitoare."
            )
            return

        # Obține TOATE meciurile live cu TOATE cotele (fără filtrare)
        fixtures_with_odds = await api_football.get_all_fixtures_with_odds(live_fixtures, max_fixtures=10)

        header = f"""
🔴 *MECIURI LIVE*
━━━━━━━━━━━━━━━━━━━━
📊 Total live: {len(live_fixtures)}
💰 Cu cote disponibile: {len(fixtures_with_odds)}
━━━━━━━━━━━━━━━━━━━━
"""
        await update.message.reply_text(header, parse_mode='Markdown')

        if fixtures_with_odds:
            for fixture in fixtures_with_odds[:8]:
                match_info = api_football.format_fixture_with_highlight(fixture)
                await update.message.reply_text(match_info, parse_mode='Markdown')
                await asyncio.sleep(0.3)
        else:
            # Afișează fără cote
            for fixture in live_fixtures[:8]:
                match_info = api_football.format_fixture_simple(fixture)
                await update.message.reply_text(match_info, parse_mode='Markdown')
                await asyncio.sleep(0.3)

        footer = f"""
━━━━━━━━━━━━━━━━━━━━
✅ Meciurile cu cotă {MIN_ODD}-{MAX_ODD} sunt marcate
💡 /tips pentru predicții detaliate
"""
        await update.message.reply_text(footer, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in get_live: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /meciuri - meciuri cu cote țintă"""
    await update.message.reply_text(f"📅 *Caut meciuri cu cote {MIN_ODD}-{MAX_ODD}...*", parse_mode='Markdown')

    try:
        upcoming = await api_football.get_upcoming_fixtures(hours=24)
        if not upcoming:
            await update.message.reply_text("❌ Nu am găsit meciuri.")
            return

        fixtures_with_odds = await api_football.get_fixtures_with_target_odds(upcoming)

        if not fixtures_with_odds:
            await update.message.reply_text(
                f"⚠️ Nu am găsit meciuri cu cote {MIN_ODD}-{MAX_ODD}.\n\n"
                f"📋 Am găsit {len(upcoming)} meciuri în total.\n"
                f"👉 Folosește /toate pentru a le vedea pe toate!"
            )
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

        keyboard = [[InlineKeyboardButton("🎫 Generează Bilet PRO", callback_data="gen_ticket")]]
        await update.message.reply_text(
            "Vrei un bilet gata făcut?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in get_matches: {e}")
        await update.message.reply_text(f"❌ Eroare: {str(e)}")


async def get_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comandă /analiza - analiză extinsă din 3 surse web"""
    # Verifică dacă s-au dat argumentele
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ *Folosire:* /analiza [Echipa1] vs [Echipa2]\n\n"
            "*Exemple:*\n"
            "/analiza Barcelona vs Real Madrid\n"
            "/analiza Liverpool vs Manchester City\n"
            "/analiza Bayern vs Dortmund",
            parse_mode='Markdown'
        )
        return

    # Extrage numele echipelor
    full_text = " ".join(context.args)

    # Încearcă să separe după "vs" sau "-"
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
            await update.message.reply_text("❌ Nu am putut identifica echipele. Folosește formatul: /analiza Echipa1 vs Echipa2")
            return

    if len(parts) < 2:
        await update.message.reply_text("❌ Te rog specifică două echipe.")
        return

    home_team = parts[0].strip().title()
    away_team = parts[1].strip().title()

    await update.message.reply_text(
        f"🔬 *Caut analiză pentru:*\n{home_team} vs {away_team}\n\n"
        f"📡 Verific 5 surse: Forebet, Flashscore, SofaScore, VitalSoccer, FootyStats...",
        parse_mode='Markdown'
    )

    try:
        # Obține analiza extinsă
        analysis_text = await get_extended_analysis(home_team, away_team)
        await update.message.reply_text(analysis_text, parse_mode='Markdown', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error in get_analysis: {e}")
        await update.message.reply_text(
            f"⚠️ Nu am putut obține analiză completă.\n\n"
            f"🔗 Verifică manual:\n"
            f"• [Forebet](https://forebet.com)\n"
            f"• [Flashscore](https://flashscore.com)\n"
            f"• [SofaScore](https://sofascore.com)",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )


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
        matches_soon = await api_football.get_matches_starting_soon(NOTIFICATION_MINUTES_BEFORE)
        if not matches_soon:
            return

        matches_with_odds = await api_football.get_fixtures_with_target_odds(matches_soon, max_fixtures=5)
        if not matches_with_odds:
            return

        for fixture in matches_with_odds[:MAX_MATCHES_PER_DAY]:
            fixture_id = str(fixture["fixture"]["id"])

            if fixture_id in notified_matches:
                continue

            notification = await prediction_engine.get_quick_prediction(fixture)
            if not notification:
                continue

            for user_id in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=notification,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to notify {user_id}: {e}")

            notified_matches.add(fixture_id)

        save_notified_matches(notified_matches)

    except Exception as e:
        logger.error(f"Error in check_and_notify: {e}")


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
    application.add_handler(CommandHandler("analiza", get_analysis))  # NOU - 3 surse web!
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("stats", stats))

    application.add_handler(CallbackQueryHandler(button_callback))

    job_queue = application.job_queue
    job_queue.run_repeating(
        check_and_notify,
        interval=CHECK_INTERVAL_MINUTES * 60,
        first=30
    )

    print("=" * 50)
    print("🤖 BOT PREDICȚII FOTBAL PRO v2 - ACTIV")
    print(f"📊 Cote: {MIN_ODD}-{MAX_ODD}")
    print(f"🎫 Bilet: {TICKET_MIN_TOTAL_ODD}-{TICKET_MAX_TOTAL_ODD}")
    print(f"📋 Comandă nouă: /toate")
    print("=" * 50)
    logger.info("Bot PRO v2 pornit cu succes!")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
