"""
Motor Predicții PRO v3 - Analiză completă cu AI + date web
Generează PRONOSTIC CLAR bazat pe multiple surse
"""
from openai import AsyncOpenAI
from typing import Dict, List, Tuple, Optional
from config import (
    OPENAI_API_KEY, MIN_ODD, MAX_ODD,
    TICKET_MIN_TOTAL_ODD, TICKET_MAX_TOTAL_ODD,
    MAX_MATCHES_PER_DAY
)


class PredictionEngine:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
        self.last_confidence = 70  # Pentru notificări

        self.system_prompt = """Ești un analist sportiv profesionist de elită cu 20+ ani experiență în pariuri sportive.

MISIUNE: Analizezi datele primite despre un meci și oferi UN SINGUR PRONOSTIC FINAL cu cea mai mare șansă de reușită.

PROCES DE ANALIZĂ:
1. Analizează TOATE datele primite (cote, forme, statistici, predicții externe)
2. Identifică pattern-urile și tendințele
3. Calculează probabilitatea reală vs cota oferită
4. Alege DOAR pronosticul cu cel mai bun raport risc/câștig

IMPORTANT:
- Oferă UN SINGUR pronostic final, nu mai multe opțiuni
- Fii DIRECT și CLAR - nu cere userului să verifice el
- Încrederea trebuie să reflecte realitatea datelor
- Dacă datele sunt limitate, ajustează încrederea corespunzător

FORMAT RĂSPUNS OBLIGATORIU:
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 *PRONOSTIC FINAL*
━━━━━━━━━━━━━━━━━━━━━━━━

⚽ *[Gazdă] vs [Oaspete]*
🏆 [Competiție]

📊 *ANALIZĂ RAPIDĂ:*
• [Punct cheie 1 - ex: Forma gazdă ultimele 5: WWWDW]
• [Punct cheie 2 - ex: H2H: Gazda 4-1-0 în ultimele 5]
• [Punct cheie 3 - ex: Over 2.5 în 80% meciuri gazdă]

✅ *PRONOSTIC: [Tip pariu exact]*
💰 *COTĂ: [X.XX]*
📈 *ÎNCREDERE: [XX]%*
⚠️ *NIVEL RISC: [Scăzut/Mediu/Ridicat]*

💡 *DE CE:* [1-2 propoziții scurte cu motivul principal]
━━━━━━━━━━━━━━━━━━━━━━━━

Răspunde DOAR în acest format, în română, fără explicații suplimentare."""

    async def analyze_match(self, fixture: Dict, extra_stats: Dict = None) -> str:
        """Analiză completă pentru un meci"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]

        odds_info = ""
        if "odds" in fixture:
            odds = fixture["odds"]
            odds_info = f"""
COTE DISPONIBILE:
- Victoria gazdă (1): {odds['home']:.2f}
- Egal (X): {odds['draw']:.2f}
- Victoria oaspete (2): {odds['away']:.2f}"""

        stats_info = ""
        if extra_stats:
            stats_info = f"""
STATISTICI:
- Forma gazdă: {extra_stats.get('home_form', 'N/A')}
- Forma oaspete: {extra_stats.get('away_form', 'N/A')}
- H2H: {extra_stats.get('h2h', 'N/A')}"""

        user_prompt = f"""Analizează acest meci și oferă PRONOSTICUL FINAL:

MECI: {home} vs {away}
LIGA: {league}
{odds_info}
{stats_info}

Alege pronosticul cu cea mai mare șansă de reușită și oferă-l în formatul cerut."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=600,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Eroare analiză: {str(e)}"

    async def analyze_with_web_data(self, home_team: str, away_team: str, web_data: Dict) -> str:
        """
        Analiză COMPLETĂ folosind datele extrase de pe web
        Returnează UN PRONOSTIC CLAR, nu link-uri
        """
        # Construiește contextul din datele web
        context_parts = []

        # Forebet
        if web_data.get('forebet'):
            fb = web_data['forebet']
            if fb.get('prediction'):
                context_parts.append(f"FOREBET: Predicție {fb['prediction']}")
            if fb.get('probability'):
                prob = fb['probability']
                context_parts.append(f"  - Probabilități: 1={prob.get('home','?')}% X={prob.get('draw','?')}% 2={prob.get('away','?')}%")
            if fb.get('avg_goals'):
                context_parts.append(f"  - Media goluri: {fb['avg_goals']}")

        # Flashscore
        if web_data.get('flashscore'):
            fs = web_data['flashscore']
            if fs.get('home_form'):
                context_parts.append(f"FLASHSCORE: Forma gazdă: {fs['home_form']}")
            if fs.get('away_form'):
                context_parts.append(f"  - Forma oaspete: {fs['away_form']}")

        # VitalSoccer
        if web_data.get('vitalsoccer'):
            vs = web_data['vitalsoccer']
            if vs.get('btts_percentage'):
                context_parts.append(f"VITALSOCCER: BTTS (Ambele marchează): {vs['btts_percentage']}")
            if vs.get('over_25_percentage'):
                context_parts.append(f"  - Over 2.5 goluri: {vs['over_25_percentage']}")
            if vs.get('home_scored_avg'):
                context_parts.append(f"  - Media goluri gazdă: {vs['home_scored_avg']}")

        # FootyStats
        if web_data.get('footystats'):
            ft = web_data['footystats']
            if ft.get('home_ppg'):
                context_parts.append(f"FOOTYSTATS: PPG gazdă: {ft['home_ppg']}")
            if ft.get('home_xg'):
                context_parts.append(f"  - xG (Expected Goals): {ft['home_xg']}")
            if ft.get('corners_avg'):
                context_parts.append(f"  - Media cornere: {ft['corners_avg']}")
            if ft.get('league_position'):
                context_parts.append(f"  - Poziție clasament: #{ft['league_position']}")

        web_context = "\n".join(context_parts) if context_parts else "Date limitate disponibile"

        analysis_prompt = f"""ANALIZEAZĂ acest meci cu datele de mai jos și oferă PRONOSTICUL FINAL.

MECI: {home_team} vs {away_team}

DATE DIN SURSE EXTERNE:
{web_context}

INSTRUCȚIUNI:
1. Analizează TOATE datele de mai sus
2. Identifică pronosticul cu cea mai mare șansă
3. Oferă UN SINGUR PRONOSTIC CLAR
4. NU cere utilizatorului să verifice el - TU faci analiza!
5. Estimează o cotă realistă bazată pe probabilități

Oferă pronosticul în formatul standard."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=700,
                temperature=0.4
            )

            # Extrage încrederea pentru notificări
            result = response.choices[0].message.content
            try:
                if "ÎNCREDERE:" in result:
                    conf_part = result.split("ÎNCREDERE:")[1].split("%")[0]
                    self.last_confidence = int(''.join(filter(str.isdigit, conf_part[:5])))
            except:
                self.last_confidence = 70

            return result
        except Exception as e:
            return f"❌ Eroare analiză AI: {str(e)}"

    async def get_smart_prediction(self, fixture: Dict, web_data: Dict = None) -> str:
        """Predicție inteligentă combinând API + date web"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]

        # Construiește context complet
        context = f"MECI: {home} vs {away}\nLIGA: {league}\n"

        # Adaugă cote dacă există
        if "odds" in fixture:
            odds = fixture["odds"]
            context += f"\nCOTE: 1={odds['home']:.2f} | X={odds['draw']:.2f} | 2={odds['away']:.2f}"

        # Adaugă date web
        if web_data:
            web_parts = []
            if web_data.get('forebet', {}).get('prediction'):
                web_parts.append(f"Forebet: {web_data['forebet']['prediction']}")
            if web_data.get('vitalsoccer', {}).get('btts_percentage'):
                web_parts.append(f"BTTS: {web_data['vitalsoccer']['btts_percentage']}")
            if web_data.get('vitalsoccer', {}).get('over_25_percentage'):
                web_parts.append(f"Over2.5: {web_data['vitalsoccer']['over_25_percentage']}")
            if web_parts:
                context += f"\nDATE EXTERNE: {', '.join(web_parts)}"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Analizează și oferă PRONOSTIC FINAL:\n\n{context}"}
                ],
                max_tokens=600,
                temperature=0.5
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Eroare: {str(e)}"

    async def generate_ticket(self, fixtures: List[Dict]) -> Tuple[str, List[Dict]]:
        """Generează bilet PRO"""
        if not fixtures:
            return "❌ Nu am găsit meciuri pentru bilet.", []

        ticket_bets = []
        total_odd = 1.0

        for fixture in fixtures[:MAX_MATCHES_PER_DAY]:
            if "odds" not in fixture:
                continue

            odds = fixture["odds"]
            # Alege cea mai mică cotă (mai sigură)
            best_odd = min(odds['home'], odds['draw'], odds['away'])

            if best_odd == odds['home']:
                bet_type, desc = "1", "Victoria gazdă"
            elif best_odd == odds['draw']:
                bet_type, desc = "X", "Egal"
            else:
                bet_type, desc = "2", "Victoria oaspete"

            # Adaugă la bilet
            if best_odd >= 1.10:
                new_total = total_odd * best_odd
                if new_total <= TICKET_MAX_TOTAL_ODD + 0.5:
                    ticket_bets.append({
                        "fixture": fixture,
                        "bet_type": bet_type,
                        "odd": best_odd,
                        "description": desc
                    })
                    total_odd = new_total

            if total_odd >= TICKET_MIN_TOTAL_ODD:
                break

        if not ticket_bets:
            return "❌ Nu am putut genera bilet.", []

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

⚠️ Pariază responsabil!
"""

        return ticket_text, ticket_bets

    async def get_quick_prediction(self, fixture: Dict) -> str:
        """Predicție rapidă pentru notificări"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]

        if "odds" not in fixture:
            return None

        odds = fixture["odds"]
        # Alege cota cea mai mică (favorit clar)
        min_odd = min(odds['home'], odds['draw'], odds['away'])

        if min_odd == odds['home']:
            bet = "1 (Victoria gazdă)"
        elif min_odd == odds['draw']:
            bet = "X (Egal)"
        else:
            bet = "2 (Victoria oaspete)"

        self.last_confidence = int(100 / min_odd) if min_odd > 1 else 70

        return f"""
🔔 *ALERTĂ PREDICȚIE*
━━━━━━━━━━━━━━━━

⚽ *{home}* vs *{away}*
⏰ Începe în 30 minute!

✅ *Predicție:* {bet}
📈 *Cotă:* {min_odd:.2f}
💪 *Încredere:* ~{self.last_confidence}%

💡 /tips pentru analiză completă
"""
