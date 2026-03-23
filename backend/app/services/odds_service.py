import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional
import httpx
from app.models.schemas import BettingLine

logger = logging.getLogger(__name__)

ESPN_BASE     = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REDS_ESPN_ID  = "28"


async def fetch_reds_lines() -> List[BettingLine]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            today    = date.today().strftime("%Y%m%d")
            tomorrow = (date.today() + timedelta(days=1)).strftime("%Y%m%d")
            data     = {"events": []}
            for ds in [today, tomorrow]:
                r = await client.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={ds}"
                )
                if r.status_code == 200:
                    data["events"].extend(r.json().get("events", []))

        game_id = None
        home_team = away_team = None
        commence_time = datetime.now(timezone.utc)

        for event in data.get("events", []):
            comps       = event.get("competitions", [])
            if not comps:
                continue
            competitors = comps[0].get("competitors", [])
            team_ids    = [c.get("team", {}).get("id") for c in competitors]
            if REDS_ESPN_ID in team_ids:
                game_id = event.get("id")
                for c in competitors:
                    if c.get("homeAway") == "home":
                        home_team = c.get("team", {}).get("displayName")
                    else:
                        away_team = c.get("team", {}).get("displayName")
                try:
                    commence_time = datetime.fromisoformat(event.get("date", "").replace("Z", "+00:00"))
                except:
                    pass
                break

        if not game_id:
            logger.warning("No Reds game found in ESPN scoreboard")
            return []

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{ESPN_BASE}/events/{game_id}/competitions/{game_id}/odds")
            resp.raise_for_status()
            odds_data = resp.json()

        items = odds_data.get("items", [])
        if not items:
            logger.warning("No odds found for Reds game")
            return []

        item       = items[0]
        spread     = item.get("spread")        # run line, usually ±1.5
        over_under = item.get("current", {}).get("total", {}).get("alternateDisplayValue")
        if not over_under:
            over_under = item.get("overUnder")

        home_odds = item.get("homeTeamOdds", {})
        away_odds = item.get("awayTeamOdds", {})
        ml_home   = home_odds.get("moneyLine")
        ml_away   = away_odds.get("moneyLine")

        if over_under:
            try:
                over_under = float(over_under)
            except:
                pass

        line = BettingLine(
            game_id=game_id,
            home_team=home_team or "Cincinnati Reds",
            away_team=away_team or "Unknown",
            commence_time=commence_time,
            bookmaker="DraftKings (ESPN)",
            spread=spread,
            moneyline_home=int(ml_home) if ml_home else None,
            moneyline_away=int(ml_away) if ml_away else None,
            over_under=float(over_under) if over_under else None,
        )
        logger.info(f"ESPN MLB odds: spread={spread}, ml_home={ml_home}, ml_away={ml_away}, ou={over_under}")
        return [line]

    except Exception as e:
        logger.error(f"ESPN MLB odds fetch failed: {e}")
        return []
