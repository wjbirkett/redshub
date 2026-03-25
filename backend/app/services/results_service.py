import logging
import httpx
from datetime import date
from app.db import get_supabase

logger = logging.getLogger(__name__)

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"
REDS_ESPN_ID    = "28"


async def fetch_game_result(game_date: str) -> dict | None:
    """Fetch final score for a Reds game on game_date (YYYY-MM-DD)."""
    ds = game_date.replace("-", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{ESPN_SCOREBOARD}?dates={ds}")
            data = r.json()
    except Exception as e:
        logger.error(f"Scoreboard fetch failed: {e}")
        return None

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

    articles = db.table("articles").select("*").eq("game_date", game_date).execute()
    if not articles.data:
        return {"status": "no_articles", "game_date": game_date}

    is_reds_home = "Reds" in result["home_team"] or "Cincinnati" in result["home_team"]
    reds_score   = result["home_score"] if is_reds_home else result["away_score"]
    opp_score    = result["away_score"] if is_reds_home else result["home_score"]
    total        = reds_score + opp_score
    reds_margin  = reds_score - opp_score

    resolved = 0
    for article in articles.data:
        picks = article.get("key_picks") or {}
        if not isinstance(picks, dict):
            continue
        art_type = article.get("article_type", "")

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
                db.table("prediction_results").upsert({
                    "slug":          article["slug"],
                    "game_date":     game_date,
                    "home_team":     result["home_team"],
                    "away_team":     result["away_team"],
                    "spread_result": spread_result,
                    "total_result":  total_result,
                    "moneyline_result": ml_result,
                }, on_conflict="slug")
                resolved += 1

    return {"status": "resolved", "game_date": game_date, "resolved": resolved}
