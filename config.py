"""
Configurare Bot Telegram Predicții Fotbal - VERSIUNEA PRO
"""
import os

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8727326390:AAE9MrxPGx6b-zuZKFy8E43EYnVqT3_obHE")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# API-Football
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "8b42551bfc0154dd6ff290ce5c1ac246")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

# === SETĂRI PRO ===

# Interval cote - FĂRĂ LIMITĂ (afișează TOATE cotele)
MIN_ODD = 1.01  # Cotă minimă posibilă
MAX_ODD = 50.0  # Cotă maximă (practic nelimitat)

# Bilet PRO - cotă totală țintă
TICKET_MIN_TOTAL_ODD = 1.50
TICKET_MAX_TOTAL_ODD = 5.00

# Limită meciuri pe zi
MAX_MATCHES_PER_DAY = 10

# Timp notificare înainte de meci (minute)
NOTIFICATION_MINUTES_BEFORE = 30

# Interval verificare meciuri (minute)
CHECK_INTERVAL_MINUTES = 10

# Ligi principale de urmărit (prioritate)
TOP_LEAGUES = [
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    2,    # Champions League
    3,    # Europa League
    283,  # Liga 1 România
    94,   # Primeira Liga (Portugalia)
    88,   # Eredivisie
]

# Cache TTL (secunde)
CACHE_TTL = 300  # 5 minute
