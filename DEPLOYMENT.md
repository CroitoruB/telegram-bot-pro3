# 🚀 Ghid Deployment Bot Telegram PRO

## Opțiuni Hosting Gratuit 24/7

### 1. Railway.app (Recomandat) ⭐

**Avantaje:** Simplu, gratuit 500 ore/lună, deploy automat din GitHub

**Pași:**

1. **Creează cont GitHub** (dacă nu ai): https://github.com
2. **Urcă codul pe GitHub:**
   - Creează repository nou
   - Urcă toate fișierele din acest folder

3. **Creează cont Railway:** https://railway.app
   - Login cu GitHub

4. **Deploy:**
   - Click "New Project" → "Deploy from GitHub repo"
   - Selectează repository-ul cu botul
   - Railway va detecta automat Python

5. **Adaugă variabilele de mediu:**
   - Go to project → Variables → Add:
   ```
   TELEGRAM_BOT_TOKEN=8727326390:AAE9MrxPGx6b-zuZKFy8E43EYnVqT3_obHE
   OPENAI_API_KEY=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
   API_FOOTBALL_KEY=8b42551bfc0154dd6ff290ce5c1ac246
   ```

6. **Deploy!** Botul va rula 24/7

---

### 2. Render.com

**Avantaje:** 750 ore gratuite/lună, SSL gratuit

**Pași:**

1. **Creează cont:** https://render.com
2. **New** → **Background Worker**
3. **Connect GitHub** repository
4. **Settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
5. **Environment Variables:** Adaugă cele 3 variabile
6. **Create Background Worker**

---

### 3. Fly.io

**Avantaje:** 3 VM-uri gratuite, uptime excelent

**Pași:**

1. **Instalează flyctl:** https://fly.io/docs/hands-on/install-flyctl/
2. **Login:** `flyctl auth login`
3. **În folder-ul botului:**
   ```bash
   flyctl launch
   flyctl secrets set TELEGRAM_BOT_TOKEN=... OPENAI_API_KEY=... API_FOOTBALL_KEY=...
   flyctl deploy
   ```

---

### 4. PythonAnywhere

**Avantaje:** Specializat Python, interfață simplă

**Pași:**

1. **Creează cont:** https://www.pythonanywhere.com
2. **Consoles** → **Bash** → Upload fișierele
3. **Tasks** → Adaugă "Always-on task": `python3 /home/username/bot.py`

---

## Variabile de Mediu Necesare

| Variabilă | Descriere |
|-----------|-----------|
| `TELEGRAM_BOT_TOKEN` | Token de la @BotFather |
| `OPENAI_API_KEY` | API key OpenAI |
| `API_FOOTBALL_KEY` | API key API-Football |

---

## Verificare Funcționare

După deployment, testează:

1. Deschide Telegram: [@Bog234_bot](https://t.me/Bog234_bot)
2. Trimite `/start`
3. Trimite `/tips` sau `/bilet`
4. Trimite `/subscribe` pentru notificări

---

## Troubleshooting

| Problemă | Soluție |
|----------|---------|
| Bot nu răspunde | Verifică logs în dashboard hosting |
| Eroare 429 | Ai depășit limita API - așteaptă |
| Notificări nu vin | Verifică `/subscribe` este activ |
| Deploy eșuează | Verifică requirements.txt și Procfile |

---

## Monitorizare

- **Railway:** Dashboard → Logs
- **Render:** Dashboard → Logs
- **Fly.io:** `flyctl logs`

---

## Costuri

| Platform | Gratuit | Limite |
|----------|---------|--------|
| Railway | 500 ore/lună | ~21 zile continuous |
| Render | 750 ore/lună | ~31 zile continuous |
| Fly.io | 3 VM-uri | Nelimitat în free tier |
| PythonAnywhere | Always-on | 1 task gratuit |

💡 **Sfat:** Folosește Railway sau Render pentru început, sunt cele mai simple!
