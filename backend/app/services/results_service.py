import logging
import httpx
from datetime import date, datetime, timezone
from app.db import get_supabase

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
REDS_ESPN_ID    = "17"


async def fetch_game_result(game_date: str) -> dict | None:
    """Fetch final score for a Reds game on game_date (YYYY-MM-DD).
    Tries scoreboard first, then falls back to team schedule."""
    ds = game_date.replace("-", "")

    # Try scoreboard first (works for recent games)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{ESPN_SCOREBOARD}?dates={ds}")
            data = r.json()
        for event in data.get("events", []):
            comp        = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            ids         = [c.get("team", {}).get("id") for c in competitors]
            if REDS_ESPN_ID not in ids:
                continue
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            return {
                "home_team":  home.get("team", {}).get("displayName", ""),
                "away_team":  away.get("team", {}).get("displayName", ""),
                "home_score": int(home.get("score", 0) or 0),
                "away_score": int(away.get("score", 0) or 0),
            }
    except Exception as e:
        logger.error(f"Scoreboard fetch failed: {e}")

    # Fallback: team schedule (always has completed games)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams/{REDS_ESPN_ID}/schedule")
            data = r.json()
        for event in data.get("events", []):
            event_date = event.get("date", "")[:10]
            if event_date != game_date:
                continue
            comp        = event.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            status_name = comp.get("status", {}).get("type", {}).get("name", "")
            if "FINAL" not in status_name:
                continue
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            home_score = home.get("score")
            away_score = away.get("score")
            if isinstance(home_score, dict):
                home_score = home_score.get("value", 0)
            if isinstance(away_score, dict):
                away_score = away_score.get("value", 0)
            return {
                "home_team":  home.get("team", {}).get("displayName", ""),
                "away_team":  away.get("team", {}).get("displayName", ""),
                "home_score": int(home_score or 0),
                "away_score": int(away_score or 0),
            }
    except Exception as e:
        logger.error(f"Team schedule fetch failed: {e}")

    return None


async def fetch_player_stats_from_boxscore(game_id: str, player: str) -> dict | None:
    """Fetch player stats from ESPN boxscore for result grading."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r    = await client.get(url)
            data = r.json()
    except Exception as e:
        logger.error(f"Boxscore fetch failed: {e}")
        return None

    player_lower = player.lower()
    for box in data.get("boxscore", {}).get("players", []):
        for stat_group in box.get("statistics", []):
            for athlete in stat_group.get("athletes", []):
                name = athlete.get("athlete", {}).get("displayName", "").lower()
                if player_lower.split()[-1] not in name:
                    continue
                stats  = athlete.get("stats", [])
                labels = stat_group.get("labels", [])
                return dict(zip(labels, stats))
    return None


async def resolve_game_predictions(game_date: str) -> dict:
    """Resolve all predictions for game_date against actual result."""
    result = await fetch_game_result(game_date)
    if not result:
        return {"status": "no_result", "game_date": game_date}

    db = get_supabase()
    if not db:
        return {"status": "no_db"}

    articles = db.table("articles").select("*").eq("game_date", game_date).eq("site_id", "redshub").execute()
    if not articles.data:
        return {"status": "no_articles", "game_date": game_date}

    is_reds_home = "Reds" in result["home_team"] or "Cincinnati" in result["home_team"]
    reds_score   = result["home_score"] if is_reds_home else result["away_score"]
    opp_score    = result["away_score"] if is_reds_home else result["home_score"]
    total        = reds_score + opp_score
    reds_margin  = reds_score - opp_score

    resolved = 0
    logger.info(f"Resolving {len(articles.data)} articles for {game_date}, result: {result}")
    for article in articles.data:
        picks = article.get("key_picks") or {}
        if not isinstance(picks, dict):
            logger.info(f"  Skipping {article.get('slug')} — key_picks not a dict: {type(picks).__name__}")
            continue
        art_type = article.get("article_type", "")
        logger.info(f"  Article: {article.get('slug')} type={art_type} picks={picks}")

        if art_type in ("prediction", "best_bet"):
            spread_result = None
            total_result  = None

            # Run line: RL typically ±1.5. COVER = Reds win by 2+
            spread_lean = picks.get("spread_lean", "").upper()
            if spread_lean == "COVER":
                spread_result = "HIT" if reds_margin >= 2 else "MISS"
            elif spread_lean in ("FADE", "LOSS"):
                spread_result = "HIT" if reds_margin < 2 else "MISS"

            # Over/Under
            total_lean = picks.get("total_lean", "").upper()
            try:
                ou_line = float(str(picks.get("total_pick", "0")).split()[-1])
            except:
                ou_line = None
            if total_lean == "OVER" and ou_line:
                total_result = "HIT" if total > ou_line else "MISS"
            elif total_lean == "UNDER" and ou_line:
                total_result = "HIT" if total < ou_line else "MISS"

            # Moneyline
            ml_result = None
            ml_lean = picks.get("moneyline_lean", "").upper()
            if ml_lean in ("REDS", "WIN"):
                ml_result = "HIT" if reds_score > opp_score else "MISS"
            elif ml_lean in ("OPPONENT", "LOSS"):
                ml_result = "HIT" if reds_score < opp_score else "MISS"

            if spread_result or total_result or ml_result:
                opponent = result["away_team"] if "reds" in result["home_team"].lower() or "cincinnati" in result["home_team"].lower() else result["home_team"]
                upsert_data = {
                    "slug":            article["slug"],
                    "game_date":       game_date,
                    "opponent":        opponent,
                    "spread_pick":     picks.get("spread_pick"),
                    "spread_lean":     picks.get("spread_lean"),
                    "spread_result":   spread_result,
                    "total_pick":      picks.get("total_pick"),
                    "total_lean":      picks.get("total_lean"),
                    "total_result":    total_result,
                    "moneyline_pick":  picks.get("moneyline_pick"),
                    "moneyline_lean":  picks.get("moneyline_lean"),
                    "moneyline_result": ml_result,
                    "knicks_score":    reds_score,  # Field named after KnicksHub (shared DB schema) — stores Reds score
                    "opp_score":       opp_score,
                    "resolved_at":     datetime.now(timezone.utc).isoformat(),
                    "site_id":         "redshub",
                }
                # Try full payload, then strip columns that may not exist in DB
                saved = False
                for remove_keys in [
                    [],
                    ["moneyline_pick", "moneyline_lean", "moneyline_result"],
                    ["moneyline_pick", "moneyline_lean", "moneyline_result", "site_id"],
                    ["moneyline_pick", "moneyline_lean", "moneyline_result", "site_id", "knicks_score", "opp_score"],
                ]:
                    try:
                        payload = {k: v for k, v in upsert_data.items() if k not in remove_keys}
                        db.table("prediction_results").upsert(payload, on_conflict="slug")
                        resolved += 1
                        saved = True
                        if remove_keys:
                            logger.info(f"Upsert succeeded after removing {remove_keys}")
                        break
                    except Exception as e2:
                        logger.warning(f"Upsert failed (removed {remove_keys}): {e2}")
                        continue
                if not saved:
                    logger.error(f"All upsert attempts failed for {article.get('slug')}")

    # ── Prop grading ──────────────────────────────────────────────────────────
    # MLB stat label mapping from ESPN box score to prop_type keys
    MLB_STAT_MAP = {
        "hits":          "H",
        "total_bases":   "TB",
        "home_runs":     "HR",
        "rbi":           "RBI",
        "strikeouts":    "K",   # pitcher strikeouts
        "stolen_bases":  "SB",
    }
    # Human-readable prop_type aliases coming from key_picks
    PROP_TYPE_ALIASES = {
        "total bases": "total_bases",
        "hits":        "hits",
        "home runs":   "home_runs",
        "home run":    "home_runs",
        "rbi":         "rbi",
        "rbis":        "rbi",
        "strikeouts":  "strikeouts",
        "stolen bases": "stolen_bases",
        "stolen base":  "stolen_bases",
    }

    # Fetch the game_id needed for box score lookups
    game_id = None
    ds = game_date.replace("-", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r2 = await client.get(f"{ESPN_SCOREBOARD}?dates={ds}")
            d2 = r2.json()
        for event in d2.get("events", []):
            comp2       = event.get("competitions", [{}])[0]
            competitors = comp2.get("competitors", [])
            ids         = [c.get("team", {}).get("id") for c in competitors]
            if REDS_ESPN_ID in ids:
                game_id = event.get("id")
                break
    except Exception as e:
        logger.warning(f"Could not fetch game_id for prop grading: {e}")

    props_resolved = 0
    for article in articles.data:
        if article.get("article_type") != "prop":
            continue

        picks      = article.get("key_picks") or {}
        if not isinstance(picks, dict):
            picks = {}

        player     = article.get("player") or picks.get("player")
        if not player:
            logger.warning(f"Prop article {article.get('slug')} has no player — saving as pending")
        raw_type   = (article.get("prop_type") or picks.get("prop_type") or picks.get("best_prop_type") or "").lower()
        prop_type  = PROP_TYPE_ALIASES.get(raw_type, raw_type) or "hits"

        # Resolve the line
        pick_str   = picks.get("pick") or picks.get(f"{prop_type}_pick") or picks.get("line") or ""
        lean       = (picks.get("lean") or picks.get(f"{prop_type}_lean") or "").upper()
        line       = None
        try:
            line = float(str(pick_str).replace("Over", "").replace("Under", "").strip())
        except (ValueError, AttributeError):
            pass

        # Attempt to fetch actual stat from box score
        actual_value = None
        if game_id and player:
            player_stats = await fetch_player_stats_from_boxscore(game_id, player)
            if player_stats:
                stat_label = MLB_STAT_MAP.get(prop_type)
                if stat_label and stat_label in player_stats:
                    try:
                        actual_value = float(str(player_stats[stat_label]).split("-")[0])
                    except (ValueError, TypeError):
                        actual_value = None

        # Grade if we have everything; otherwise save as pending
        if actual_value is not None and line is not None and lean in ("OVER", "UNDER"):
            result_str = "HIT" if (lean == "OVER" and actual_value > line) or (lean == "UNDER" and actual_value < line) else "MISS"
        else:
            result_str = None  # pending

        prop_row = {
            "slug":         article["slug"],
            "game_date":    game_date,
            "player":       player or "",
            "prop_type":    prop_type,
            "line":         line,
            "lean":         lean or None,
            "actual_value": actual_value,
            "result":       result_str,
            "resolved_at":  datetime.now(timezone.utc).isoformat(),
            "site_id":      "redshub",
        }
        try:
            db.table("prop_results").upsert(prop_row, on_conflict="slug")
            props_resolved += 1
        except Exception as e:
            logger.error(f"prop_results upsert failed for {article.get('slug')}: {e}")

    return {"status": "resolved", "game_date": game_date, "resolved": resolved, "props_resolved": props_resolved}
