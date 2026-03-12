"""
Motor Predicții PRO - cu bilete și analiză avansată
"""
from openai import AsyncOpenAI
from typing import Dict, List, Tuple
from config import (
    OPENAI_API_KEY, MIN_ODD, MAX_ODD,
    TICKET_MIN_TOTAL_ODD, TICKET_MAX_TOTAL_ODD,
    MAX_MATCHES_PER_DAY
)


class PredictionEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

        self.system_prompt = f"""Ești un analist sportiv profesionist de elită, specializat în predicții fotbal cu cote sigure ({MIN_ODD}-{MAX_ODD}).

MISIUNE: Generezi predicții precise cu încredere ridicată pentru pariuri sigure.

REGULI STRICTE:
1. Analizează DOAR opțiuni cu cote {MIN_ODD}-{MAX_ODD}
2. Bazează-te pe: formă recentă, meciuri directe, avantaj teren, absențe
3. Oferă nivel de încredere realist (70-95%)
4. Menționează factorii de risc
5. Maximum {MAX_MATCHES_PER_DAY} predicții pe zi

FORMAT RĂSPUNS:
⚽ **PREDICȚIE PRO**
━━━━━━━━━━━━━━━━━━
🏟️ **Meci:** [Gazdă] vs [Oaspete]
🏆 **Liga:** [Competiție]

📊 **ANALIZĂ:**
• [Factor 1]
• [Factor 2]
• [Factor 3]

✅ **PREDICȚIE:** [Tip pariu]
📈 **COTĂ:** [X.XX]
💪 **ÎNCREDERE:** [XX%]
⚠️ **RISC:** [Scăzut/Mediu]
━━━━━━━━━━━━━━━━━━

IMPORTANT: Răspunde în română, concis și profesionist."""

    async def analyze_match(self, fixture: Dict, extra_stats: Dict = None) -> str:
        """Analiză completă pentru un meci"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]

        odds_info = ""
        if "odds" in fixture:
            odds = fixture["odds"]
            odds_info = f"""
Cote disponibile:
- Victoria gazdă (1): {odds['home']:.2f}
- Egal (X): {odds['draw']:.2f}
- Victoria oaspete (2): {odds['away']:.2f}

Cote în intervalul țintă ({MIN_ODD}-{MAX_ODD}):"""
            if "target_bets" in odds:
                for bet_type, odd, desc in odds["target_bets"]:
                    odds_info += f"\n✓ {bet_type} - {desc}: {odd:.2f}"

        stats_info = ""
        if extra_stats:
            stats_info = f"""
Statistici suplimentare:
- Forma gazdă: {extra_stats.get('home_form', 'N/A')}
- Forma oaspete: {extra_stats.get('away_form', 'N/A')}
- H2H: {extra_stats.get('h2h', 'N/A')}"""

        user_prompt = f"""Analizează acest meci și oferă predicție PRO:

🏠 Echipa gazdă: {home}
🚌 Echipa oaspete: {away}
🏆 Liga: {league}
{odds_info}
{stats_info}

Oferă o predicție detaliată pentru cotele între {MIN_ODD}-{MAX_ODD}."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Eroare: {str(e)}"

    async def generate_ticket(self, fixtures: List[Dict]) -> Tuple[str, List[Dict]]:
        """Generează bilet PRO cu cotă totală 1.6-1.8"""
        if not fixtures:
            return "❌ Nu am găsit meciuri potrivite pentru bilet.", []

        # Selectează cele mai bune pariuri pentru bilet
        ticket_bets = []
        total_odd = 1.0

        for fixture in fixtures[:MAX_MATCHES_PER_DAY]:
            if "odds" not in fixture or "target_bets" not in fixture["odds"]:
                continue

            # Alege cea mai bună cotă din interval
            best_bet = None
            for bet_type, odd, desc in fixture["odds"]["target_bets"]:
                if MIN_ODD <= odd <= MAX_ODD:
                    if best_bet is None or odd > best_bet[1]:
                        best_bet = (bet_type, odd, desc)

            if best_bet:
                new_total = total_odd * best_bet[1]
                # Verifică să nu depășească cota maximă dorită
                if new_total <= TICKET_MAX_TOTAL_ODD + 0.2:
                    ticket_bets.append({
                        "fixture": fixture,
                        "bet_type": best_bet[0],
                        "odd": best_bet[1],
                        "description": best_bet[2]
                    })
                    total_odd = new_total

            # Stop dacă am atins cota țintă
            if total_odd >= TICKET_MIN_TOTAL_ODD:
                break

        if not ticket_bets:
            return "❌ Nu am putut genera un bilet cu meciurile disponibile.", []

        # Formatează biletul
        ticket_text = f"""
🎫 *BILET PRO AL ZILEI*
━━━━━━━━━━━━━━━━━━━━━━

"""
        for i, bet in enumerate(ticket_bets, 1):
            home = bet["fixture"]["teams"]["home"]["name"]
            away = bet["fixture"]["teams"]["away"]["name"]
            match_time = bet["fixture"]["fixture"]["timestamp"]
            from datetime import datetime
            time_str = datetime.fromtimestamp(match_time).strftime("%H:%M")

            ticket_text += f"""*{i}. {home} vs {away}*
   ⏰ Ora: {time_str}
   ✅ Pariu: *{bet["bet_type"]}* ({bet["description"]})
   📈 Cotă: *{bet["odd"]:.2f}*

"""

        ticket_text += f"""━━━━━━━━━━━━━━━━━━━━━━
💰 *COTĂ TOTALĂ: {total_odd:.2f}*
🎯 *Meciuri: {len(ticket_bets)}*
━━━━━━━━━━━━━━━━━━━━━━

⚠️ *Disclaimer:* Predicțiile sunt generate de AI.
Pariază responsabil și doar sume pe care ți le poți permite să le pierzi.
"""

        return ticket_text, ticket_bets

    async def get_quick_prediction(self, fixture: Dict) -> str:
        """Predicție rapidă pentru notificări"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]

        if "odds" not in fixture or "target_bets" not in fixture["odds"]:
            return None

        best_bet = fixture["odds"]["target_bets"][0]
        bet_type, odd, desc = best_bet

        return f"""
🔔 *ALERTĂ PREDICȚIE*
━━━━━━━━━━━━━━━━

⚽ *{home}* vs *{away}*
⏰ Începe în 30 minute!

✅ *Predicție:* {bet_type} ({desc})
📈 *Cotă:* {odd:.2f}

💡 Folosește /tips pentru analiză completă.
"""
