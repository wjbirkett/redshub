"""
advanced_stats_service.py — MLB advanced team stats for RedsHub.

Fetches pitching/hitting advanced stats from MLB Stats API (free, no key).
Supports any team, season + recent splits.
"""
import logging
import time
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

MLB_API = "https://statsapi.mlb.com/api/v1"

# Cache
_cache: Dict[str, tuple] = {}
_CACHE_TTL = 600

MLB_TEAMS = {
    "Arizona Diamondbacks": 109, "Atlanta Braves": 144, "Baltimore Orioles": 110,
    "Boston Red Sox": 111, "Chicago Cubs": 112, "Chicago White Sox": 145,
    "Cincinnati Reds": 113, "Cleveland Guardians": 114, "Colorado Rockies": 115,
    "Detroit Tigers": 116, "Houston Astros": 117, "Kansas City Royals": 118,
    "Los Angeles Angels": 108, "Los Angeles Dodgers": 119, "Miami Marlins": 146,
    "Milwaukee Brewers": 158, "Minnesota Twins": 142, "New York Mets": 121,
    "New York Yankees": 147, "Oakland Athletics": 133, "Philadelphia Phillies": 143,
    "Pittsburgh Pirates": 134, "San Diego Padres": 135, "San Francisco Giants": 137,
    "Seattle Mariners": 136, "St. Louis Cardinals": 138, "Tampa Bay Rays": 139,
    "Texas Rangers": 140, "Toronto Blue Jays": 141, "Washington Nationals": 120,
}

REDS_ID = 113


def _resolve_team_id(name: str) -> Optional[int]:
    if name in MLB_TEAMS:
        return MLB_TEAMS[name]
    keyword = name.split()[-1].lower()
    for n, tid in MLB_TEAMS.items():
        if keyword in n.lower():
            return tid
    return None


async def get_team_stats(team_name: str, season: int = 2026) -> Optional[Dict[str, Any]]:
    """Get team hitting + pitching stats from MLB Stats API."""
    team_id = _resolve_team_id(team_name)
    if not team_id:
        return None

    cache_key = f"{team_id}_{season}"
    now = time.time()
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if now - ts < _CACHE_TTL:
            return data

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Hitting stats
            hit_resp = await client.get(
                f"{MLB_API}/teams/{team_id}/stats",
                params={"stats": "season", "group": "hitting", "season": str(season)}
            )
            hit_data = hit_resp.json()

            # Pitching stats
            pitch_resp = await client.get(
                f"{MLB_API}/teams/{team_id}/stats",
                params={"stats": "season", "group": "pitching", "season": str(season)}
            )
            pitch_data = pitch_resp.json()

        hit_splits = hit_data.get("stats", [{}])[0].get("splits", [{}])
        hit_stat = hit_splits[0].get("stat", {}) if hit_splits else {}

        pitch_splits = pitch_data.get("stats", [{}])[0].get("splits", [{}])
        pitch_stat = pitch_splits[0].get("stat", {}) if pitch_splits else {}

        result = {
            # Hitting
            "avg": hit_stat.get("avg"),
            "obp": hit_stat.get("obp"),
            "slg": hit_stat.get("slg"),
            "ops": hit_stat.get("ops"),
            "runs_per_game": hit_stat.get("runs") / max(hit_stat.get("gamesPlayed", 1), 1) if hit_stat.get("runs") else None,
            "home_runs": hit_stat.get("homeRuns"),
            "stolen_bases": hit_stat.get("stolenBases"),
            "strikeouts_hitting": hit_stat.get("strikeOuts"),
            "hits": hit_stat.get("hits"),
            "games_played": hit_stat.get("gamesPlayed"),
            # Pitching
            "era": pitch_stat.get("era"),
            "whip": pitch_stat.get("whip"),
            "k_per_9": pitch_stat.get("strikeoutsPer9Inn"),
            "bb_per_9": pitch_stat.get("walksPer9Inn"),
            "hr_per_9": pitch_stat.get("homeRunsPer9"),
            "innings_pitched": pitch_stat.get("inningsPitched"),
            "saves": pitch_stat.get("saves"),
            "holds": pitch_stat.get("holds"),
            "runs_allowed_per_game": float(pitch_stat.get("earnedRuns", 0)) / max(float(pitch_stat.get("gamesPlayed", 1)), 1) if pitch_stat.get("earnedRuns") else None,
            "batting_avg_against": pitch_stat.get("avg"),
        }

        _cache[cache_key] = (result, now)
        return result
    except Exception as e:
        logger.warning(f"MLB stats fetch failed for {team_name}: {e}")
        return None


async def get_matchup_stats(reds_name: str = "Cincinnati Reds", opponent_name: str = "") -> Dict[str, Any]:
    """Get stats for both teams."""
    import asyncio
    reds_stats, opp_stats = await asyncio.gather(
        get_team_stats(reds_name),
        get_team_stats(opponent_name),
        return_exceptions=True,
    )
    def safe(v):
        return v if not isinstance(v, Exception) else None
    return {"reds_season": safe(reds_stats), "opp_season": safe(opp_stats)}


def format_matchup_block(matchup: Dict[str, Any], opponent: str) -> str:
    """Format matchup stats as prompt block."""
    lines = ["=== ADVANCED MATCHUP STATS ==="]
    rs = matchup.get("reds_season")
    os_ = matchup.get("opp_season")

    def fmt(label, s):
        if not s:
            return
        lines.append(f"\n{label}:")
        lines.append(f"  Hitting: AVG {s.get('avg','?')} | OBP {s.get('obp','?')} | SLG {s.get('slg','?')} | OPS {s.get('ops','?')}")
        rpg = s.get('runs_per_game')
        lines.append(f"  Runs/Game: {round(rpg, 1) if rpg else '?'} | HR: {s.get('home_runs','?')} | SB: {s.get('stolen_bases','?')}")
        lines.append(f"  Pitching: ERA {s.get('era','?')} | WHIP {s.get('whip','?')} | K/9 {s.get('k_per_9','?')} | BB/9 {s.get('bb_per_9','?')}")

    fmt("Reds", rs)
    fmt(opponent, os_)

    if rs and os_:
        reds_rpg = rs.get("runs_per_game") or 0
        opp_rpg = os_.get("runs_per_game") or 0
        reds_era = float(rs.get("era") or 99)
        opp_era = float(os_.get("era") or 99)
        if reds_rpg + opp_rpg > 9:
            lines.append(f"\nRun environment: HIGH ({reds_rpg:.1f} + {opp_rpg:.1f} = {reds_rpg+opp_rpg:.1f} combined RPG) — lean Over")
        elif reds_rpg + opp_rpg < 7.5:
            lines.append(f"\nRun environment: LOW ({reds_rpg:.1f} + {opp_rpg:.1f} = {reds_rpg+opp_rpg:.1f} combined RPG) — lean Under")

    lines.append("=== END ADVANCED STATS ===")
    return "\n".join(lines)


async def get_probable_pitchers(game_date: str) -> Dict[str, Any]:
    """Get probable starters. Primary: MLB Stats API. Fallback: ESPN."""
    # Try MLB Stats API first (more reliable for probable pitchers)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{MLB_API}/schedule",
                params={"sportId": 1, "date": game_date, "hydrate": "probablePitcher"}
            )
            data = resp.json()

        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams = g.get("teams", {})
                home_team = teams.get("home", {}).get("team", {})
                away_team = teams.get("away", {}).get("team", {})
                if home_team.get("id") == REDS_ID or away_team.get("id") == REDS_ID:
                    home_pp = teams.get("home", {}).get("probablePitcher", {})
                    away_pp = teams.get("away", {}).get("probablePitcher", {})
                    result = {}
                    if home_team.get("id") == REDS_ID:
                        result["reds_sp"] = home_pp.get("fullName", "TBD")
                        result["opp_sp"] = away_pp.get("fullName", "TBD")
                    else:
                        result["reds_sp"] = away_pp.get("fullName", "TBD")
                        result["opp_sp"] = home_pp.get("fullName", "TBD")
                    if result.get("reds_sp") != "TBD" or result.get("opp_sp") != "TBD":
                        logger.info(f"Probable pitchers from MLB API: {result}")
                        return result
    except Exception as e:
        logger.warning(f"MLB Stats API probable pitchers failed: {e}")

    # Fallback: ESPN
    try:
        ds = game_date.replace("-", "")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={ds}")
            data = resp.json()

        for ev in data.get("events", []):
            comp = ev["competitions"][0]
            teams = [c.get("team", {}).get("id") for c in comp.get("competitors", [])]
            if "17" in teams:  # Reds ESPN ID
                probables = comp.get("probables", [])
                result = {}
                for p in probables:
                    team_id = p.get("team", {}).get("id")
                    pitcher = p.get("athlete", {})
                    name = pitcher.get("displayName", "TBD")
                    if team_id == "17":
                        result["reds_sp"] = name
                    else:
                        result["opp_sp"] = name
                if result:
                    return result
        return {}
    except Exception as e:
        logger.warning(f"Probable pitchers fetch failed: {e}")
        return {}
