"""
alt_props_service.py — Fetch alt/longshot player prop lines from FanDuel.

Returns real sportsbook alt lines (e.g., Brunson 5+ threes at +850)
that the standard Odds API doesn't provide. Uses FanDuel's public JSON API.

No authentication required. No browser automation needed.
"""
import logging
import time
from datetime import date, timedelta
from typing import Optional, Dict, List, Any

import httpx

logger = logging.getLogger(__name__)

FANDUEL_API = "https://sbapi.nj.sportsbook.fanduel.com/api"
FANDUEL_AK = "FhMFpcPWXMeyZxOx"  # Public frontend API key

# Cache
_alt_cache: Optional[Dict] = None
_alt_cache_time: Optional[float] = None
_CACHE_TTL = 300  # 5 minutes

# Reds players to track
REDS_PLAYERS = {
    "Elly De La Cruz", "TJ Friedl", "Spencer Steer",
    "Tyler Stephenson", "Jonathan India", "Jake Fraley",
    "Jeimer Candelario", "Hunter Greene", "Nick Lodolo",
    "Andrew Abbott", "Graham Ashcraft",
}


async def _find_event_id(team_keyword: str = "Reds") -> Optional[str]:
    """Find today's game event ID on FanDuel."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{FANDUEL_API}/content-managed-page",
                params={"page": "CUSTOM", "customPageId": "mlb", "_ak": FANDUEL_AK},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        events = data.get("attachments", {}).get("events", {})
        today = date.today()
        tomorrow = today + timedelta(days=1)

        for eid, ev in events.items():
            name = ev.get("name", "")
            if team_keyword not in name:
                continue
            open_date = ev.get("openDate", "")[:10]
            try:
                event_date = date.fromisoformat(open_date)
                if event_date in (today, tomorrow):
                    logger.info(f"FanDuel: Found event {eid} — {name}")
                    return eid
            except ValueError:
                continue

        return None
    except Exception as e:
        logger.warning(f"FanDuel event search failed: {e}")
        return None


async def fetch_alt_props(team_keyword: str = "Reds", players: set = None) -> Dict[str, List[Dict]]:
    """
    Fetch alt/longshot player prop lines from FanDuel.

    Returns: {
        "Jalen Brunson": [
            {"market": "To Score 30+ Points", "odds": "+172", "odds_int": 172},
            {"market": "4+ Made Threes", "odds": "+360", "odds_int": 360},
            ...
        ],
        ...
    }
    """
    global _alt_cache, _alt_cache_time
    now = time.time()
    if _alt_cache and _alt_cache_time and (now - _alt_cache_time) < _CACHE_TTL:
        return _alt_cache

    if players is None:
        players = REDS_PLAYERS

    event_id = await _find_event_id(team_keyword)
    if not event_id:
        return {}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{FANDUEL_API}/event-page",
                params={"_ak": FANDUEL_AK, "eventId": event_id, "tab": "POPULAR"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        markets = data.get("attachments", {}).get("markets", {})
        result: Dict[str, List[Dict]] = {}

        # Skip noisy/exotic markets
        SKIP_MARKETS = {"method of first basket", "game specials", "first basket scorer",
                        "race to", "exact total", "odd / even", "half time"}

        for m in markets.values():
            market_name = m.get("marketName", "")
            # Skip exotic markets
            if any(skip in market_name.lower() for skip in SKIP_MARKETS):
                continue
            runners = m.get("runners", [])

            for r in runners:
                player_name = r.get("runnerName", "")
                # Match against our players — require BOTH first and last name
                matched = None
                for p in players:
                    first = p.split()[0].lower()
                    last = p.split()[-1].lower()
                    runner_lower = player_name.lower()
                    if first in runner_lower and last in runner_lower:
                        matched = p
                        break

                if not matched:
                    continue

                odds_data = r.get("winRunnerOdds", {}).get("americanDisplayOdds", {})
                odds_str = odds_data.get("americanOdds", "")
                if not odds_str:
                    continue

                try:
                    odds_int = int(odds_str)
                except ValueError:
                    continue

                # Only include plus-money or near-even props (the interesting ones)
                if odds_int < -300:
                    continue

                if matched not in result:
                    result[matched] = []

                result[matched].append({
                    "market": market_name,
                    "odds": f"{odds_int:+d}",
                    "odds_int": odds_int,
                })

        # Sort each player's props by odds (most interesting first — positive odds)
        for player in result:
            result[player].sort(key=lambda x: -x["odds_int"])

        _alt_cache = result
        _alt_cache_time = now

        logger.info(f"FanDuel alt props: {sum(len(v) for v in result.values())} props for {len(result)} players")
        return result

    except Exception as e:
        logger.warning(f"FanDuel alt props fetch failed: {e}")
        return {}


def format_alt_props_block(alt_props: Dict[str, List[Dict]], top_n: int = 5) -> str:
    """Format alt props as a prompt block for Claude."""
    if not alt_props:
        return ""

    lines = ["=== FANDUEL ALT PROP LINES (Real Sportsbook Odds) ==="]
    lines.append("These are REAL FanDuel lines — higher odds = bigger payout but lower probability.")
    lines.append("")

    for player, props in sorted(alt_props.items()):
        if not props:
            continue
        lines.append(f"{player}:")
        for p in props[:top_n]:
            lines.append(f"  {p['market']}: {p['odds']}")
        lines.append("")

    lines.append("Look for VALUE: where the model's projection suggests the odds are too high (mispriced).")
    lines.append("=== END ALT PROPS ===")
    return "\n".join(lines)


async def find_best_alt_value(
    alt_props: Dict[str, List[Dict]],
    player_projections: Dict[str, Dict] = None,
) -> List[Dict]:
    """
    Find the best value alt props by comparing odds to projections.

    Returns list of {player, market, odds, edge_reason} sorted by value.
    """
    if not alt_props:
        return []

    # For now, flag props in the +100 to +400 range as "interesting"
    # These are the sweet spot — achievable but with good payouts
    value_props = []

    for player, props in alt_props.items():
        for p in props:
            odds = p["odds_int"]
            market = p["market"]

            # Sweet spot: +100 to +400 (achievable longshots)
            if 100 <= odds <= 400:
                value_props.append({
                    "player": player,
                    "market": market,
                    "odds": p["odds"],
                    "tier": "VALUE" if odds <= 250 else "LONGSHOT",
                })

    # Sort by odds (lower = more likely to hit)
    value_props.sort(key=lambda x: abs(int(x["odds"].replace("+", "").replace("-", ""))))
    return value_props[:10]
