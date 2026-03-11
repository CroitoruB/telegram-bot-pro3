"""
Modul API-Football PRO - cu caching avansat și rate limiting
"""
import aiohttp
import asyncio
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from config import (
    API_FOOTBALL_KEY, API_FOOTBALL_BASE_URL,
    MIN_ODD, MAX_ODD, TOP_LEAGUES, CACHE_TTL,
    NOTIFICATION_MINUTES_BEFORE
)


class APIFootball:
    def __init__(self):
        self.base_url = API_FOOTBALL_BASE_URL
        self.headers = {"x-apisports-key": API_FOOTBALL_KEY}
        self._cache = {}
        self._cache_ttl = CACHE_TTL
        self._last_request_time = 0
        self._min_request_interval = 3  # 3 secunde între request-uri

    async def _rate_limit(self):
        """Rate limiting între request-uri"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _get_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None

    def _set_cache(self, key: str, data: Any):
        self._cache[key] = (data, time.time())

    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Request cu rate limiting și caching"""
        cache_key = f"{endpoint}_{str(params)}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        await self._rate_limit()

        url = f"{self.base_url}/{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._set_cache(cache_key, data)
                        return data
                    elif response.status == 429:
                        return {"errors": "Rate limit atins", "rate_limited": True}
                    else:
                        return {"errors": f"HTTP {response.status}"}
        except asyncio.TimeoutError:
            return {"errors": "Timeout"}
        except Exception as e:
            return {"errors": str(e)}

    async def get_live_fixtures(self) -> List[Dict]:
        """Meciuri live"""
        data = await self._make_request("fixtures", {"live": "all"})
        return data.get("response", [])

    async def get_matches_starting_soon(self, minutes: int = 30) -> List[Dict]:
        """Meciuri care încep în următoarele X minute"""
        today = datetime.now().strftime("%Y-%m-%d")
        data = await self._make_request("fixtures", {"date": today})

        if "response" not in data:
            return []

        now = datetime.now()
        target_time = now + timedelta(minutes=minutes)

        upcoming = []
        for fixture in data["response"]:
            try:
                match_time = datetime.fromtimestamp(fixture["fixture"]["timestamp"])
                # Meciuri care încep între acum și target_time
                if now < match_time <= target_time:
                    upcoming.append(fixture)
            except:
                continue

        return upcoming

    async def get_upcoming_fixtures(self, hours: int = 24) -> List[Dict]:
        """Meciuri în următoarele X ore"""
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        fixtures = []
        for date in [today, tomorrow]:
            data = await self._make_request("fixtures", {"date": date})
            if "response" in data:
                fixtures.extend(data["response"])

        now = datetime.now()
        upcoming = []
        for fixture in fixtures:
            try:
                match_time = datetime.fromtimestamp(fixture["fixture"]["timestamp"])
                if now < match_time < now + timedelta(hours=hours):
                    upcoming.append(fixture)
            except:
                continue

        # Sortează după ora meciului
        upcoming.sort(key=lambda x: x["fixture"]["timestamp"])
        return upcoming

    async def get_fixtures_with_target_odds(self, fixtures: List[Dict], max_fixtures: int = 10) -> List[Dict]:
        """Adaugă cote și filtrează după interval 1.20-1.45"""
        results = []

        for fixture in fixtures[:max_fixtures]:
            fixture_id = fixture["fixture"]["id"]
            odds_data = await self._make_request("odds", {
                "fixture": fixture_id,
                "bookmaker": 8
            })

            if odds_data.get("rate_limited"):
                break

            if "response" in odds_data and len(odds_data["response"]) > 0:
                try:
                    odds = odds_data["response"][0]
                    bets = odds.get("bookmakers", [{}])[0].get("bets", [{}])[0].get("values", [])

                    home_odd = float(bets[0].get("odd", 0)) if len(bets) > 0 else 0
                    draw_odd = float(bets[1].get("odd", 0)) if len(bets) > 1 else 0
                    away_odd = float(bets[2].get("odd", 0)) if len(bets) > 2 else 0

                    # Verifică cotele în interval
                    target_bets = []
                    if MIN_ODD <= home_odd <= MAX_ODD:
                        target_bets.append(("1", home_odd, "Victoria gazdă"))
                    if MIN_ODD <= draw_odd <= MAX_ODD:
                        target_bets.append(("X", draw_odd, "Egal"))
                    if MIN_ODD <= away_odd <= MAX_ODD:
                        target_bets.append(("2", away_odd, "Victoria oaspete"))

                    if target_bets:
                        fixture["odds"] = {
                            "home": home_odd,
                            "draw": draw_odd,
                            "away": away_odd,
                            "target_bets": target_bets
                        }
                        results.append(fixture)
                except (IndexError, KeyError, ValueError):
                    continue

            await asyncio.sleep(1)

        return results

    async def get_team_form(self, team_id: int, last: int = 5) -> str:
        """Forma echipei (ultimele X meciuri)"""
        data = await self._make_request("fixtures", {
            "team": team_id,
            "last": last
        })

        if "response" not in data:
            return "N/A"

        form = []
        for match in data["response"]:
            try:
                home_id = match["teams"]["home"]["id"]
                home_goals = match["goals"]["home"] or 0
                away_goals = match["goals"]["away"] or 0

                if team_id == home_id:
                    if home_goals > away_goals:
                        form.append("W")
                    elif home_goals < away_goals:
                        form.append("L")
                    else:
                        form.append("D")
                else:
                    if away_goals > home_goals:
                        form.append("W")
                    elif away_goals < home_goals:
                        form.append("L")
                    else:
                        form.append("D")
            except:
                continue

        return "".join(form) if form else "N/A"

    async def get_h2h(self, team1_id: int, team2_id: int, last: int = 5) -> Dict:
        """Meciuri directe (H2H)"""
        data = await self._make_request("fixtures/headtohead", {
            "h2h": f"{team1_id}-{team2_id}",
            "last": last
        })

        if "response" not in data:
            return {"matches": 0, "team1_wins": 0, "team2_wins": 0, "draws": 0}

        matches = data["response"]
        team1_wins = 0
        team2_wins = 0
        draws = 0

        for match in matches:
            try:
                home_id = match["teams"]["home"]["id"]
                home_goals = match["goals"]["home"] or 0
                away_goals = match["goals"]["away"] or 0

                if home_goals > away_goals:
                    if home_id == team1_id:
                        team1_wins += 1
                    else:
                        team2_wins += 1
                elif away_goals > home_goals:
                    if home_id == team1_id:
                        team2_wins += 1
                    else:
                        team1_wins += 1
                else:
                    draws += 1
            except:
                continue

        return {
            "matches": len(matches),
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws
        }

    def format_fixture(self, fixture: Dict, include_odds: bool = True) -> str:
        """Formatează meci pentru afișare"""
        home = fixture["teams"]["home"]["name"]
        away = fixture["teams"]["away"]["name"]
        league = fixture["league"]["name"]

        match_time = datetime.fromtimestamp(fixture["fixture"]["timestamp"])
        time_str = match_time.strftime("%H:%M")
        date_str = match_time.strftime("%d.%m")

        status = fixture["fixture"]["status"]["short"]

        if status == "NS":
            score = f"📅 {date_str} | ⏰ {time_str}"
        elif status in ["1H", "2H", "HT", "ET", "P", "LIVE"]:
            elapsed = fixture["fixture"]["status"]["elapsed"] or 0
            goals_home = fixture["goals"]["home"] or 0
            goals_away = fixture["goals"]["away"] or 0
            score = f"🔴 LIVE {elapsed}' | {goals_home}-{goals_away}"
        elif status == "FT":
            goals_home = fixture["goals"]["home"] or 0
            goals_away = fixture["goals"]["away"] or 0
            score = f"✅ Final: {goals_home}-{goals_away}"
        else:
            score = f"📊 {status}"

        odds_str = ""
        if include_odds and "odds" in fixture:
            odds = fixture["odds"]
            odds_str = f"\n💰 *Cote:* 1={odds['home']:.2f} | X={odds['draw']:.2f} | 2={odds['away']:.2f}"

            if "target_bets" in odds:
                for bet_type, odd, desc in odds["target_bets"]:
                    odds_str += f"\n✅ *RECOMANDARE: {bet_type} ({desc}) @ {odd:.2f}*"

        return f"""
⚽ *{home}* vs *{away}*
🏆 {league}
{score}{odds_str}
"""
