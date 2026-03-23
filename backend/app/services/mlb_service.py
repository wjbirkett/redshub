import asyncio, httpx, logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from app.models.schemas import InjuryReport, Game, TeamStanding, PlayerStat

logger = logging.getLogger(__name__)

REDS_ESPN_ID  = "28"
ESPN_BASE     = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
ESPN_V2       = "https://site.api.espn.com/apis/v2/sports/baseball/mlb"
MLB_STATS_BASE = "https://statsapi.mlb.com/api/v1"

def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except:
        return default

def _safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except:
        return default


# ── Injuries ─────────────────────────────────────────────────────────────────

async def fetch_injury_report() -> List[InjuryReport]:
    url = f"{ESPN_BASE}/injuries"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"ESPN injury fetch failed: {e}")
        return []

    status_map = {
        "Day-To-Day": "Day-To-Day", "GTD": "Day-To-Day", "DTD": "Day-To-Day",
        "Out": "Out", "Doubtful": "Doubtful", "Questionable": "Questionable",
        "10-Day IL": "IL-10", "15-Day IL": "IL-15", "60-Day IL": "IL-60",
    }

    reds = next(
        (t for t in data.get("injuries", []) if t.get("id") == REDS_ESPN_ID),
        None
    )
    if not reds:
        return []

    injuries = []
    for inj in reds.get("injuries", []):
        athlete   = inj.get("athlete", {})
        raw_status = inj.get("status", "Unknown").strip()
        status    = status_map.get(raw_status, raw_status)
        details   = inj.get("details", {})
        if details.get("type"):
            body_part = details.get("type", "")
            detail    = details.get("detail", "")
            reason    = f"{body_part} ({detail})" if detail else body_part
        else:
            reason = inj.get("shortComment") or inj.get("longComment") or "Not specified"
        try:
            href      = next(l for l in athlete.get("links", []) if "player" in l.get("rel", []))
            player_id = int(href["href"].split("/id/")[1].split("/")[0])
        except:
            player_id = hash(athlete.get("displayName", "")) % 100000

        injuries.append(InjuryReport(
            player_id=player_id,
            player_name=athlete.get("displayName", "Unknown"),
            status=status,
            reason=reason,
            updated_at=datetime.utcnow(),
        ))
    return injuries


# ── Schedule ──────────────────────────────────────────────────────────────────

async def fetch_schedule() -> List[Game]:
    url = f"{ESPN_BASE}/teams/{REDS_ESPN_ID}/schedule"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"ESPN schedule fetch failed: {e}")
        return []

    games = []
    for event in data.get("events", []):
        try:
            comp        = event["competitions"][0]
            competitors = comp["competitors"]
            home = next((c for c in competitors if c["homeAway"] == "home"), competitors[0])
            away = next((c for c in competitors if c["homeAway"] == "away"), competitors[1])

            raw_date = event.get("date", "")
            try:
                game_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
            except:
                game_date = date.today()

            status_name = comp.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
            if "FINAL" in status_name:
                status = "Final"
            elif "PROGRESS" in status_name:
                status = "Live"
            else:
                status = "Scheduled"

            def parse_score(c):
                s = c.get("score")
                if s is None or status == "Scheduled":
                    return None
                if isinstance(s, dict):
                    return int(s.get("value", 0))
                return _safe_int(s) or None

            games.append(Game(
                game_id=_safe_int(event.get("id", 0)),
                game_date=game_date,
                home_team=home.get("team", {}).get("displayName", ""),
                away_team=away.get("team", {}).get("displayName", ""),
                home_score=parse_score(home),
                away_score=parse_score(away),
                status=status,
                arena=comp.get("venue", {}).get("fullName"),
                broadcast=None,
            ))
        except Exception as e:
            logger.warning(f"Skipping game parse: {e}")
            continue

    games.sort(key=lambda g: g.game_date)
    return games


# ── Standings ─────────────────────────────────────────────────────────────────

async def fetch_standings() -> List[TeamStanding]:
    url = f"{ESPN_V2}/standings"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"ESPN standings fetch failed: {e}")
        return []

    standings = []
    for league in data.get("children", []):           # AL / NL
        league_name = "NL" if "National" in league.get("name", "") else "AL"
        for div in league.get("children", []):        # East / Central / West
            div_name = div.get("name", "").replace(f"{league_name} ", "").replace("National League ", "").replace("American League ", "")
            entries  = div.get("standings", {}).get("entries", [])
            for i, entry in enumerate(entries):
                team  = entry.get("team", {})
                stats = {s["name"]: s.get("displayValue", "0") for s in entry.get("stats", [])}
                try:
                    wins, losses = stats.get("overall", "0-0").split("-")
                except:
                    wins, losses = "0", "0"
                try:
                    gb_raw = stats.get("gamesBehind", "0").replace("\u2014", "0").replace("-", "0")
                    gb     = float(gb_raw) if gb_raw.replace(".", "").isdigit() else 0.0
                except:
                    gb = 0.0
                try:
                    wp_raw  = stats.get("winPercent", "0").lstrip(".")
                    win_pct = float("0." + wp_raw) if wp_raw.isdigit() else float(wp_raw or 0)
                except:
                    win_pct = 0.0

                standings.append(TeamStanding(
                    team_name=team.get("displayName", ""),
                    conference=league_name,
                    division=div_name,
                    wins=_safe_int(wins),
                    losses=_safe_int(losses),
                    win_pct=win_pct,
                    games_back=gb,
                    conference_rank=i + 1,
                ))

    # Re-rank within each division by wins desc
    from itertools import groupby
    def div_key(s): return (s.conference, s.division)
    for _, group in groupby(sorted(standings, key=div_key), key=div_key):
        grp = sorted(group, key=lambda s: s.wins, reverse=True)
        for i, s in enumerate(grp):
            s.conference_rank = i + 1

    return standings


# ── Player Stats (MLB Stats API — free, no key) ────────────────────────────

async def fetch_player_stats() -> List[PlayerStat]:
    """
    Fetches Reds roster via MLB Stats API, then fetches hitting + pitching
    season stats for each player. No API key required.
    """
    # Step 1: Get Reds team ID from MLB Stats API (Cincinnati = 113)
    REDS_MLB_ID = 113
    season = date.today().year

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            # Fetch hitting stats
            hit_url = f"{MLB_STATS_BASE}/teams/{REDS_MLB_ID}/stats?stats=season&group=hitting&season={season}&sportId=1"
            pit_url = f"{MLB_STATS_BASE}/teams/{REDS_MLB_ID}/stats?stats=season&group=pitching&season={season}&sportId=1"
            hit_resp = await client.get(hit_url)
            pit_resp = await client.get(pit_url)
    except Exception as e:
        logger.error(f"MLB Stats API fetch failed: {e}")
        return []

    stats: List[PlayerStat] = []
    seen_ids = set()

    # Parse hitting
    try:
        for split in hit_resp.json().get("stats", [{}])[0].get("splits", []):
            p   = split.get("player", {})
            s   = split.get("stat", {})
            pid = _safe_int(p.get("id", 0))
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            stats.append(PlayerStat(
                player_id=pid,
                player_name=p.get("fullName", ""),
                position=split.get("position", {}).get("abbreviation"),
                games_played=_safe_int(s.get("gamesPlayed", 0)),
                avg=_safe_float(s.get("avg")) or None,
                home_runs=_safe_int(s.get("homeRuns")),
                rbi=_safe_int(s.get("rbi")),
                ops=_safe_float(s.get("ops")) or None,
                stolen_bases=_safe_int(s.get("stolenBases")),
                at_bats=_safe_int(s.get("atBats")),
            ))
    except Exception as e:
        logger.warning(f"Hitting stats parse failed: {e}")

    # Parse pitching — merge into existing or append new
    try:
        for split in pit_resp.json().get("stats", [{}])[0].get("splits", []):
            p   = split.get("player", {})
            s   = split.get("stat", {})
            pid = _safe_int(p.get("id", 0))
            existing = next((x for x in stats if x.player_id == pid), None)
            try:
                ip_str = s.get("inningsPitched", "0.0")
                ip     = float(ip_str) if ip_str else 0.0
            except:
                ip = 0.0
            if existing:
                existing.era             = _safe_float(s.get("era")) or None
                existing.wins            = _safe_int(s.get("wins"))
                existing.losses          = _safe_int(s.get("losses"))
                existing.strikeouts      = _safe_int(s.get("strikeOuts"))
                existing.whip            = _safe_float(s.get("whip")) or None
                existing.innings_pitched = ip or None
                existing.saves           = _safe_int(s.get("saves"))
            else:
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    stats.append(PlayerStat(
                        player_id=pid,
                        player_name=p.get("fullName", ""),
                        position=split.get("position", {}).get("abbreviation"),
                        games_played=_safe_int(s.get("gamesPitched", 0)),
                        era=_safe_float(s.get("era")) or None,
                        wins=_safe_int(s.get("wins")),
                        losses=_safe_int(s.get("losses")),
                        strikeouts=_safe_int(s.get("strikeOuts")),
                        whip=_safe_float(s.get("whip")) or None,
                        innings_pitched=ip or None,
                        saves=_safe_int(s.get("saves")),
                    ))
    except Exception as e:
        logger.warning(f"Pitching stats parse failed: {e}")

    # Sort by games played
    stats.sort(key=lambda p: p.games_played, reverse=True)
    return stats


# ── Roster (for birthday service) ─────────────────────────────────────────────

async def fetch_roster() -> list:
    url = f"{ESPN_BASE}/teams/{REDS_ESPN_ID}/roster"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"ESPN roster fetch failed: {e}")
        return []

    roster = []
    for athlete in data.get("athletes", []):
        dob = athlete.get("dateOfBirth", "")
        try:
            birth_date = datetime.strptime(dob[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            birth_date = ""
        roster.append({
            "PLAYER_ID":  _safe_int(athlete.get("id", 0)),
            "PLAYER":     athlete.get("displayName", ""),
            "POSITION":   athlete.get("position", {}).get("abbreviation", ""),
            "BIRTH_DATE": birth_date,
            "NUM":        athlete.get("jersey", ""),
        })
    return roster


async def fetch_recent_games(last_n: int = 5) -> List[Game]:
    games    = await fetch_schedule()
    finished = [g for g in games if g.status == "Final"]
    return finished[-last_n:] if finished else []


# ── Probable Pitcher Detection ────────────────────────────────────────────────

async def fetch_probable_pitcher(home_team: str, away_team: str) -> Optional[str]:
    """
    Fetch the Reds' probable starting pitcher from the ESPN scoreboard.
    Checks today and tomorrow. Returns the pitcher's displayName or None.
    """
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    scoreboard_url = f"{ESPN_BASE}/scoreboard"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for check_date in [today, tomorrow]:
                ds = check_date.strftime("%Y%m%d")
                resp = await client.get(f"{scoreboard_url}?dates={ds}")
                if resp.status_code != 200:
                    continue
                data = resp.json()

                for event in data.get("events", []):
                    comp = event.get("competitions", [{}])[0]
                    competitors = comp.get("competitors", [])
                    team_ids = [c.get("team", {}).get("id") for c in competitors]

                    if REDS_ESPN_ID not in team_ids:
                        continue

                    # Found a Reds game — look for probable pitchers
                    for competitor in competitors:
                        tid = competitor.get("team", {}).get("id")
                        if tid != REDS_ESPN_ID:
                            continue
                        # ESPN puts probable pitchers in "probables" array
                        probables = competitor.get("probables", [])
                        for prob in probables:
                            athlete = prob.get("athlete", {})
                            name = athlete.get("displayName")
                            if name:
                                logger.info(f"Probable Reds starter found: {name}")
                                return name

                    # Also check the top-level "competitions[0].startingLineups"
                    # or "status" fields for pitcher info
                    for competitor in competitors:
                        tid = competitor.get("team", {}).get("id")
                        if tid != REDS_ESPN_ID:
                            continue
                        # Some ESPN responses nest pitchers differently
                        leaders = competitor.get("leaders", [])
                        for leader_group in leaders:
                            if leader_group.get("abbreviation") == "SP":
                                for ldr in leader_group.get("leaders", []):
                                    name = ldr.get("athlete", {}).get("displayName")
                                    if name:
                                        logger.info(f"Probable Reds starter (from leaders): {name}")
                                        return name

        logger.info("No probable Reds pitcher found in ESPN scoreboard")
        return None
    except Exception as e:
        logger.error(f"Probable pitcher fetch failed: {e}")
        return None
