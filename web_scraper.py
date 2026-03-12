"""
Modul Web Scraper - Extrage statistici de pe site-uri gratuite
Site-uri: Forebet, Flashscore, SofaScore, VitalSoccer, FootyStats
"""
import aiohttp
import asyncio
import re
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup


class FootballScraper:
    """Scraper pentru site-uri de statistici fotbal"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self._cache = {}
        self._cache_ttl = 600  # 10 minute cache

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Descarca pagina HTML"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=15) as response:
                    if response.status == 200:
                        return await response.text()
        except Exception as e:
            print(f"Eroare fetch {url}: {e}")
        return None

    async def get_forebet_prediction(self, home_team: str, away_team: str) -> Dict:
        """Obtine predictii de pe Forebet.com"""
        result = {
            "source": "Forebet",
            "prediction": None,
            "probability": None,
            "avg_goals": None,
            "weather": None
        }

        try:
            search_term = f"{home_team} {away_team}".replace(" ", "+")
            url = f"https://www.forebet.com/en/search?q={search_term}"

            html = await self._fetch_page(url)
            if not html:
                return result

            soup = BeautifulSoup(html, 'html.parser')

            pred_elem = soup.select_one('.rcnt .foremark')
            if pred_elem:
                result["prediction"] = pred_elem.get_text(strip=True)

            prob_elems = soup.select('.rcnt .fprc span')
            if prob_elems and len(prob_elems) >= 3:
                try:
                    result["probability"] = {
                        "home": prob_elems[0].get_text(strip=True),
                        "draw": prob_elems[1].get_text(strip=True),
                        "away": prob_elems[2].get_text(strip=True)
                    }
                except:
                    pass

            goals_elem = soup.select_one('.rcnt .avg_goals')
            if goals_elem:
                result["avg_goals"] = goals_elem.get_text(strip=True)

        except Exception as e:
            print(f"Eroare Forebet: {e}")

        return result

    async def get_flashscore_stats(self, home_team: str, away_team: str) -> Dict:
        """Obtine statistici de pe Flashscore.com"""
        result = {
            "source": "Flashscore",
            "home_form": None,
            "away_form": None,
            "h2h_summary": None,
            "standings": None
        }

        try:
            search_term = home_team.lower().replace(" ", "-")
            url = f"https://www.flashscore.com/team/{search_term}/"

            html = await self._fetch_page(url)
            if not html:
                return result

            soup = BeautifulSoup(html, 'html.parser')

            form_elems = soup.select('.form-ico')
            if form_elems:
                form = []
                for elem in form_elems[:5]:
                    classes = elem.get('class', [])
                    if 'form-ico--win' in str(classes) or 'form-w' in str(classes):
                        form.append('W')
                    elif 'form-ico--draw' in str(classes) or 'form-d' in str(classes):
                        form.append('D')
                    elif 'form-ico--lose' in str(classes) or 'form-l' in str(classes):
                        form.append('L')
                if form:
                    result["home_form"] = "".join(form)

        except Exception as e:
            print(f"Eroare Flashscore: {e}")

        return result

    async def get_sofascore_data(self, home_team: str, away_team: str) -> Dict:
        """Obtine date de pe SofaScore"""
        result = {
            "source": "SofaScore",
            "home_rating": None,
            "away_rating": None,
            "expected_goals": None,
            "key_stats": None
        }

        try:
            result["key_stats"] = {
                "tip": "Verifica SofaScore pentru statistici detaliate",
                "url": f"https://www.sofascore.com/search?q={home_team.replace(' ', '%20')}"
            }

        except Exception as e:
            print(f"Eroare SofaScore: {e}")

        return result

    async def get_vitalsoccer_data(self, home_team: str, away_team: str) -> Dict:
        """Obtine date de pe VitalSoccer.com"""
        result = {
            "source": "VitalSoccer",
            "btts_percentage": None,
            "over_25_percentage": None,
            "home_scored_avg": None,
            "away_scored_avg": None,
            "tip": None
        }

        try:
            # Cauta meciuri pe VitalSoccer
            search_term = home_team.lower().replace(" ", "-")
            url = f"https://www.vitalsoccer.com/search?q={home_team.replace(' ', '+')}"

            html = await self._fetch_page(url)
            if not html:
                # Ofera link direct pentru verificare manuala
                result["tip"] = {
                    "info": "Verifica VitalSoccer pentru statistici BTTS si Over/Under",
                    "url": f"https://www.vitalsoccer.com"
                }
                return result

            soup = BeautifulSoup(html, 'html.parser')

            # Cauta statistici BTTS (Both Teams To Score)
            btts_elem = soup.select_one('.btts-stat, .btts-percentage, [class*="btts"]')
            if btts_elem:
                btts_text = btts_elem.get_text(strip=True)
                btts_match = re.search(r'(\d+)%', btts_text)
                if btts_match:
                    result["btts_percentage"] = btts_match.group(1) + "%"

            # Cauta statistici Over 2.5
            over_elem = soup.select_one('.over-stat, .over25, [class*="over"]')
            if over_elem:
                over_text = over_elem.get_text(strip=True)
                over_match = re.search(r'(\d+)%', over_text)
                if over_match:
                    result["over_25_percentage"] = over_match.group(1) + "%"

            # Cauta media golurilor
            goals_elems = soup.select('.goals-avg, .team-goals, [class*="goals"]')
            for elem in goals_elems[:2]:
                goals_text = elem.get_text(strip=True)
                goals_match = re.search(r'(\d+\.?\d*)', goals_text)
                if goals_match:
                    if not result["home_scored_avg"]:
                        result["home_scored_avg"] = goals_match.group(1)
                    else:
                        result["away_scored_avg"] = goals_match.group(1)

            result["tip"] = {
                "info": "Date extrase de pe VitalSoccer",
                "url": f"https://www.vitalsoccer.com"
            }

        except Exception as e:
            print(f"Eroare VitalSoccer: {e}")
            result["tip"] = {
                "info": "Verifica VitalSoccer manual",
                "url": "https://www.vitalsoccer.com"
            }

        return result

    async def get_footystats_data(self, home_team: str, away_team: str) -> Dict:
        """Obtine date de pe FootyStats.org"""
        result = {
            "source": "FootyStats",
            "home_ppg": None,  # Points per game
            "away_ppg": None,
            "home_xg": None,  # Expected goals
            "away_xg": None,
            "league_position": None,
            "corners_avg": None,
            "cards_avg": None,
            "tip": None
        }

        try:
            # FootyStats are statistici detaliate per echipa
            search_term = home_team.lower().replace(" ", "-")
            url = f"https://footystats.org/clubs/{search_term}"

            html = await self._fetch_page(url)
            if not html:
                # Ofera link pentru cautare
                result["tip"] = {
                    "info": "Verifica FootyStats pentru statistici avansate xG",
                    "url": f"https://footystats.org/clubs"
                }
                return result

            soup = BeautifulSoup(html, 'html.parser')

            # Cauta PPG (Points Per Game)
            ppg_elem = soup.select_one('.ppg, .points-per-game, [class*="ppg"]')
            if ppg_elem:
                ppg_text = ppg_elem.get_text(strip=True)
                ppg_match = re.search(r'(\d+\.?\d*)', ppg_text)
                if ppg_match:
                    result["home_ppg"] = ppg_match.group(1)

            # Cauta xG (Expected Goals)
            xg_elem = soup.select_one('.xg, .expected-goals, [class*="xg"]')
            if xg_elem:
                xg_text = xg_elem.get_text(strip=True)
                xg_match = re.search(r'(\d+\.?\d*)', xg_text)
                if xg_match:
                    result["home_xg"] = xg_match.group(1)

            # Cauta statistici cornere
            corners_elem = soup.select_one('.corners, [class*="corner"]')
            if corners_elem:
                corners_text = corners_elem.get_text(strip=True)
                corners_match = re.search(r'(\d+\.?\d*)', corners_text)
                if corners_match:
                    result["corners_avg"] = corners_match.group(1)

            # Cauta statistici cartonase
            cards_elem = soup.select_one('.cards, [class*="card"]')
            if cards_elem:
                cards_text = cards_elem.get_text(strip=True)
                cards_match = re.search(r'(\d+\.?\d*)', cards_text)
                if cards_match:
                    result["cards_avg"] = cards_match.group(1)

            # Pozitia in clasament
            pos_elem = soup.select_one('.league-position, .position, [class*="rank"]')
            if pos_elem:
                pos_text = pos_elem.get_text(strip=True)
                pos_match = re.search(r'(\d+)', pos_text)
                if pos_match:
                    result["league_position"] = pos_match.group(1)

            result["tip"] = {
                "info": "Date extrase de pe FootyStats",
                "url": f"https://footystats.org/clubs/{search_term}"
            }

        except Exception as e:
            print(f"Eroare FootyStats: {e}")
            result["tip"] = {
                "info": "Verifica FootyStats manual pentru xG si statistici avansate",
                "url": "https://footystats.org"
            }

        return result

    async def get_combined_analysis(self, home_team: str, away_team: str) -> Dict:
        """Combina datele din toate cele 5 surse"""
        # Ruleaza toate request-urile in paralel
        forebet, flashscore, sofascore, vitalsoccer, footystats = await asyncio.gather(
            self.get_forebet_prediction(home_team, away_team),
            self.get_flashscore_stats(home_team, away_team),
            self.get_sofascore_data(home_team, away_team),
            self.get_vitalsoccer_data(home_team, away_team),
            self.get_footystats_data(home_team, away_team),
            return_exceptions=True
        )

        # Combina rezultatele
        combined = {
            "teams": f"{home_team} vs {away_team}",
            "sources_checked": 5,
            "forebet": forebet if not isinstance(forebet, Exception) else None,
            "flashscore": flashscore if not isinstance(flashscore, Exception) else None,
            "sofascore": sofascore if not isinstance(sofascore, Exception) else None,
            "vitalsoccer": vitalsoccer if not isinstance(vitalsoccer, Exception) else None,
            "footystats": footystats if not isinstance(footystats, Exception) else None
        }

        return combined

    def format_analysis(self, analysis: Dict) -> str:
        """Formateaza analiza pentru Telegram"""
        text = f"""
📊 *ANALIZA EXTINSA*
━━━━━━━━━━━━━━━━━━━━
🔎 *{analysis.get('teams', 'N/A')}*
📡 Surse verificate: {analysis.get('sources_checked', 0)}

"""
        # Forebet
        if analysis.get('forebet') and analysis['forebet'].get('prediction'):
            fb = analysis['forebet']
            text += f"""*🔮 Forebet:*
• Predictie: {fb.get('prediction', 'N/A')}
• Goluri medii: {fb.get('avg_goals', 'N/A')}
"""
            if fb.get('probability'):
                prob = fb['probability']
                text += f"• Probabilitati: 1={prob.get('home', '?')} X={prob.get('draw', '?')} 2={prob.get('away', '?')}\n"

        # Flashscore
        if analysis.get('flashscore') and analysis['flashscore'].get('home_form'):
            fs = analysis['flashscore']
            text += f"""
*📈 Flashscore:*
• Forma gazda: {fs.get('home_form', 'N/A')}
"""

        # VitalSoccer
        if analysis.get('vitalsoccer'):
            vs = analysis['vitalsoccer']
            text += "\n*⚽ VitalSoccer:*\n"
            if vs.get('btts_percentage'):
                text += f"• BTTS: {vs['btts_percentage']}\n"
            if vs.get('over_25_percentage'):
                text += f"• Over 2.5: {vs['over_25_percentage']}\n"
            if vs.get('home_scored_avg'):
                text += f"• Goluri gazda (avg): {vs['home_scored_avg']}\n"
            if vs.get('away_scored_avg'):
                text += f"• Goluri oaspete (avg): {vs['away_scored_avg']}\n"

        # FootyStats
        if analysis.get('footystats'):
            ft = analysis['footystats']
            text += "\n*📊 FootyStats:*\n"
            if ft.get('home_ppg'):
                text += f"• PPG gazda: {ft['home_ppg']}\n"
            if ft.get('home_xg'):
                text += f"• xG gazda: {ft['home_xg']}\n"
            if ft.get('corners_avg'):
                text += f"• Cornere (avg): {ft['corners_avg']}\n"
            if ft.get('cards_avg'):
                text += f"• Cartonase (avg): {ft['cards_avg']}\n"
            if ft.get('league_position'):
                text += f"• Pozitie clasament: #{ft['league_position']}\n"

        # Link-uri utile
        text += f"""
━━━━━━━━━━━━━━━━━━━━
🔗 *Link-uri pentru analiza:*
• [Forebet](https://forebet.com)
• [Flashscore](https://flashscore.com)
• [SofaScore](https://sofascore.com)
• [VitalSoccer](https://vitalsoccer.com)
• [FootyStats](https://footystats.org)
"""
        return text


# Functie helper pentru integrare in bot
async def get_extended_analysis(home_team: str, away_team: str) -> str:
    """Obtine analiza extinsa pentru un meci"""
    scraper = FootballScraper()
    analysis = await scraper.get_combined_analysis(home_team, away_team)
    return scraper.format_analysis(analysis)
