"""
prop_lines_service.py — Fetches real sportsbook player prop lines for MLB.

Primary: The Odds API (real DraftKings/FanDuel lines)
Fallback: Dynamic lines calculated from MLB season averages
"""
import logging
import math
import httpx
from datetime import date, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ODDS_API_KEY = "ea936af7908166c106f76b3f68a87d4f"
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SPORT = "baseball_mlb"

# MLB prop markets
PROP_MARKETS = [
    "batter_hits",
    "batter_total_bases",
    "batter_home_runs",
    "batter_rbis",
    "batter_runs_scored",
    "batter_stolen_bases",
    "pitcher_strikeouts",
    "pitcher_outs",
]

MARKET_MAP = {
    "batter_hits": "hits",
    "batter_total_bases": "total_bases",
    "batter_home_runs": "home_runs",
    "batter_rbis": "rbi",
    "batter_runs_scored": "runs",
    "batter_stolen_bases": "stolen_bases",
    "pitcher_strikeouts": "strikeouts",
    "pitcher_outs": "outs",
}

# Reds rotation players
REDS_PLAYERS = [
    "Elly De La Cruz", "TJ Friedl", "Spencer Steer",
    "Tyler Stephenson", "Jonathan India", "Jake Fraley",
    "Jeimer Candelario", "Stuart Fairchild", "Santiago Espinal",
    "Hunter Greene", "Nick Lodolo", "Andrew Abbott",
    "Graham Ashcraft", "Frankie Montas",
]


def _match_reds_player(name: str) -> Optional[str]:
    """Match an API player name to a canonical Reds player name."""
    name_lower = name.lower()
    for rp in REDS_PLAYERS:
        first = rp.split()[0].lower()
        last = rp.split()[-1].lower()
        if first in name_lower and last in name_lower:
            return rp
    return None


async def _fetch_reds_event_id() -> Optional[str]:
    """Find today's or tomorrow's Reds game event ID from The Odds API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ODDS_API_BASE}/sports/{SPORT}/events",
                params={"apiKey": ODDS_API_KEY}
            )
            resp.raise_for_status()
            events = resp.json()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        for event in events:
            home = event.get("home_team", "")
            away = event.get("away_team", "")
            if "Reds" not in home and "Reds" not in away and "Cincinnati" not in home and "Cincinnati" not in away:
                continue

            commence = event.get("commence_time", "")
            if commence:
                game_date_str = commence[:10]
                try:
                    game_date = date.fromisoformat(game_date_str)
                    if game_date in (today, tomorrow):
                        event_id = event.get("id")
                        logger.info(f"Odds API: Found Reds event {event_id} ({away} @ {home})")
                        return event_id
                except ValueError:
                    pass

        logger.warning("Odds API: No upcoming Reds game found in events")
        return None

    except Exception as e:
        logger.error(f"Odds API: Failed to fetch events: {e}")
        return None


async def _fetch_odds_api_props(event_id: str) -> Dict[str, Dict[str, float]]:
    """Fetch player prop lines from The Odds API for a specific event."""
    lines: Dict[str, Dict[str, float]] = {}

    try:
        markets_str = ",".join(PROP_MARKETS)
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{ODDS_API_BASE}/sports/{SPORT}/events/{event_id}/odds",
                params={
                    "apiKey": ODDS_API_KEY,
                    "regions": "us",
                    "markets": markets_str,
                    "oddsFormat": "american",
                }
            )
            resp.raise_for_status()
            data = resp.json()

        remaining = resp.headers.get("x-requests-remaining", "?")
        used = resp.headers.get("x-requests-used", "?")
        logger.info(f"Odds API: Credits used={used}, remaining={remaining}")

        bookmakers = data.get("bookmakers", [])
        if not bookmakers:
            logger.warning("Odds API: No bookmakers returned for event")
            return {}

        for bookmaker in bookmakers:
            bk_name = bookmaker.get("title", "Unknown")
            markets = bookmaker.get("markets", [])

            for market in markets:
                market_key = market.get("key", "")
                prop_type = MARKET_MAP.get(market_key)
                if not prop_type:
                    continue

                outcomes = market.get("outcomes", [])
                for outcome in outcomes:
                    player_name = outcome.get("description", "")
                    canonical = _match_reds_player(player_name)
                    if not canonical:
                        continue

                    point = outcome.get("point")
                    if point is not None:
                        if canonical not in lines:
                            lines[canonical] = {}
                        if prop_type not in lines[canonical]:
                            lines[canonical][prop_type] = float(point)

            if lines:
                logger.info(f"Odds API: Got prop lines from {bk_name} for {len(lines)} players")
                break

        return lines

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 422:
            logger.warning("Odds API: Props not available yet for this event (422)")
        elif e.response.status_code == 429:
            logger.warning("Odds API: Rate limited / credits exhausted")
        else:
            logger.error(f"Odds API: HTTP error {e.response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Odds API: Failed to fetch props: {e}")
        return {}


# ── Fallback: Season averages ──

def _round_to_half(value: float) -> float:
    """Round to nearest 0.5 (standard sportsbook prop line interval)."""
    return math.floor(value * 2) / 2 + 0.5 if value % 0.5 != 0 else value + 0.5


def _stat_to_prop_line(avg: float) -> float:
    """Convert a season average to a prop line, rounded to nearest .5."""
    if avg <= 0:
        return 0.5
    return _round_to_half(avg)


async def _fallback_season_avg_lines() -> Dict[str, Dict[str, float]]:
    """Generate prop lines from MLB season averages as fallback."""
    try:
        from app.services.mlb_service import fetch_player_stats
        stats = await fetch_player_stats()
    except Exception as e:
        logger.error(f"Fallback: Failed to fetch player stats: {e}")
        return {}

    if not stats:
        return {}

    lines: Dict[str, Dict[str, float]] = {}

    for player in stats:
        name = player.player_name if hasattr(player, 'player_name') else player.get('player_name', '')
        canonical = _match_reds_player(name)
        if not canonical:
            continue

        gp = float(player.games_played if hasattr(player, 'games_played') else player.get('games_played', 0) or 0)
        if gp < 5:
            continue

        player_lines = {}

        # Batting stats
        hits = float(player.hits if hasattr(player, 'hits') else player.get('hits', 0) or 0)
        hr = float(player.home_runs if hasattr(player, 'home_runs') else player.get('home_runs', 0) or 0)
        rbi = float(player.rbi if hasattr(player, 'rbi') else player.get('rbi', 0) or 0)
        sb = float(player.stolen_bases if hasattr(player, 'stolen_bases') else player.get('stolen_bases', 0) or 0)

        if gp > 0:
            if hits / gp > 0:
                player_lines["hits"] = _stat_to_prop_line(hits / gp)
            if hr / gp > 0.05:
                player_lines["home_runs"] = 0.5
            if rbi / gp > 0:
                player_lines["rbi"] = _stat_to_prop_line(rbi / gp)
            if sb / gp > 0.1:
                player_lines["stolen_bases"] = 0.5

            # Total bases estimate: hits + extra base hits
            tb_per_game = (hits + hr * 3) / gp  # rough estimate
            if tb_per_game > 0:
                player_lines["total_bases"] = _stat_to_prop_line(tb_per_game)

        # Pitching stats (strikeouts)
        era = player.era if hasattr(player, 'era') else player.get('era')
        if era is not None:
            k = float(player.strikeouts if hasattr(player, 'strikeouts') else player.get('strikeouts', 0) or 0)
            ip = float(player.innings_pitched if hasattr(player, 'innings_pitched') else player.get('innings_pitched', 0) or 0)
            starts = float(player.games_started if hasattr(player, 'games_started') else player.get('games_started', gp) or gp)
            if starts > 0 and k > 0:
                k_per_start = k / starts
                player_lines["strikeouts"] = _stat_to_prop_line(k_per_start)

        if player_lines:
            lines[canonical] = player_lines

    logger.info(f"Fallback: Generated prop lines from season averages for {len(lines)} players")
    return lines


# ── Main entry point ──

async def fetch_live_prop_lines(home_team: str, away_team: str) -> Dict[str, Dict[str, float]]:
    """
    Fetch real sportsbook prop lines for MLB.
    Primary: The Odds API
    Fallback: Season averages

    Returns dict: {player_name: {prop_type: line}}
    """
    event_id = await _fetch_reds_event_id()
    if event_id:
        odds_lines = await _fetch_odds_api_props(event_id)
        if odds_lines:
            fallback = await _fallback_season_avg_lines()
            for player, plines in fallback.items():
                if player not in odds_lines:
                    odds_lines[player] = plines
                else:
                    for prop_type, line in plines.items():
                        if prop_type not in odds_lines[player]:
                            odds_lines[player][prop_type] = line
            logger.info(f"Using Odds API lines (supplemented with season avg fallback)")
            return odds_lines
        else:
            logger.warning("Odds API returned no props — falling back to season averages")

    return await _fallback_season_avg_lines()
