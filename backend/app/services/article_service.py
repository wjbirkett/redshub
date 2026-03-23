import re, logging
from datetime import datetime
from typing import Optional
from app.config import settings
from app.db import get_supabase

logger = logging.getLogger(__name__)

TEAM_NAME      = "Cincinnati Reds"
TEAM_SHORT     = "Reds"
TEAM_ABBR      = "CIN"
SPORT          = "MLB"
RUN_LINE_LABEL = "run line"
PROP_TYPES     = ["hits", "home runs", "strikeouts", "RBI", "total bases"]

# Key Reds players for prop articles
PROP_PLAYERS = [
    "Elly De La Cruz", "TJ Friedl", "Spencer Steer",
    "Tyler Stephenson", "Jonathan India", "Jake Fraley",
    "Hunter Greene", "Nick Lodolo", "Graham Ashcraft",
]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:120]


async def _call_claude(prompt: str, system: str = None, max_tokens: int = 1200) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msgs   = [{"role": "user", "content": prompt}]
    kwargs = {"model": "claude-opus-4-5", "max_tokens": max_tokens, "messages": msgs}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return resp.content[0].text


async def get_articles(limit: int = 20):
    db = get_supabase()
    if not db:
        return []
    result = db.table("articles").select("*").order("game_date", desc=True).limit(limit).execute()
    return result.data or []


async def get_article_by_slug(slug: str):
    db = get_supabase()
    if not db:
        return None
    result = db.table("articles").select("*").eq("slug", slug).single().execute()
    return result.data


async def save_article(article: dict) -> dict:
    db = get_supabase()
    if not db:
        return article
    result = db.table("articles").upsert(article, on_conflict="slug")
    return result.data[0] if result.data else article


async def _fetch_opponent_injuries(opponent: str) -> list:
    """Fetch injury report for the opposing team."""
    import httpx
    ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{ESPN_BASE}/injuries")
            data = resp.json()
        opp_lower = opponent.lower().split()[-1]
        opp_team  = next(
            (t for t in data.get("injuries", [])
             if opp_lower in t.get("displayName", "").lower()),
            None
        )
        if not opp_team:
            return []
        return [
            {"player_name": i.get("athlete", {}).get("displayName", ""), "status": i.get("status", "")}
            for i in opp_team.get("injuries", [])[:5]
        ]
    except:
        return []


# ── Game Preview / Prediction ─────────────────────────────────────────────────

async def generate_game_preview(
    home_team: str, away_team: str, game_date: str,
    spread: str, moneyline: str, over_under: str,
    injuries: list, recent_games: list, top_stats: list,
) -> dict:
    opp_injuries = await _fetch_opponent_injuries(
        away_team if "Reds" in home_team or "Cincinnati" in home_team else home_team
    )
    is_home   = "Reds" in home_team or "Cincinnati" in home_team
    opp_name  = away_team if is_home else home_team
    location  = "at home" if is_home else "on the road"

    inj_text  = "\n".join([f"- {i.get('player_name','?')}: {i.get('status','?')} ({i.get('reason','?')})" for i in injuries[:4]]) or "None reported"
    opp_inj   = "\n".join([f"- {i.get('player_name','?')}: {i.get('status','?')}" for i in opp_injuries]) or "None reported"
    recent    = recent_games[-5:] if recent_games else []
    recent_str = "\n".join([f"- {g.get('home_team','')} {g.get('home_score',0)} – {g.get('away_score',0)} {g.get('away_team','')}" for g in recent if g.get("home_score") is not None]) or "N/A"
    stats_str = "\n".join([f"- {s.get('player_name','?')}: {s.get('games_played',0)}G, AVG {s.get('avg','?')}, HR {s.get('home_runs','?')}, RBI {s.get('rbi','?')}" for s in top_stats[:5]]) or "N/A"

    prompt = f"""You are an expert MLB analyst writing for RedsHub, a Cincinnati Reds fan betting dashboard.

Generate a comprehensive game prediction article for:
{TEAM_NAME} ({location}) vs {opp_name}
Date: {game_date}
Run Line (Reds): {spread}
Reds Moneyline: {moneyline}
Total (O/U): {over_under}

Reds injuries:
{inj_text}

{opp_name} injuries:
{opp_inj}

Recent results:
{recent_str}

Key Reds batting stats:
{stats_str}

Write a 500-700 word analysis covering:
1. Pitching matchup (starting pitchers, recent form)
2. Offensive outlook for both teams
3. Bullpen and lineup considerations
4. Run line analysis (Reds {spread})
5. Over/under analysis ({over_under} runs)
6. Final pick with confidence level

End with a JSON block EXACTLY like this (no markdown):
PICKS_JSON_START
{{
  "spread_pick": "Reds {spread}",
  "spread_lean": "COVER or FADE",
  "total_pick": "Over/Under {over_under}",
  "total_lean": "OVER or UNDER",
  "confidence": "High or Medium or Low"
}}
PICKS_JSON_END

Use markdown headers (##) for sections. Write with conviction."""

    content = await _call_claude(prompt, max_tokens=1400)
    picks   = _extract_picks(content)
    body    = re.sub(r"PICKS_JSON_START.*?PICKS_JSON_END", "", content, flags=re.DOTALL).strip()

    title = f"{away_team} vs {home_team} Prediction — {game_date}"
    slug  = slugify(f"{away_team}-vs-{home_team}-prediction-{game_date}")

    return {
        "slug":         slug,
        "title":        title,
        "content":      body,
        "article_type": "prediction",
        "game_date":    game_date,
        "home_team":    home_team,
        "away_team":    away_team,
        "key_picks":    picks,
        "created_at":   datetime.utcnow().isoformat(),
    }


# ── Best Bet ──────────────────────────────────────────────────────────────────

async def generate_best_bet(
    home_team: str, away_team: str, game_date: str,
    spread: str, moneyline: str, over_under: str,
    injuries: list, top_stats: list,
    forced_total_lean: str = None, forced_total_pick: str = None,
) -> dict:
    is_home  = "Reds" in home_team or "Cincinnati" in home_team
    opp_name = away_team if is_home else home_team
    force_note = ""
    if forced_total_lean:
        force_note = f"\nIMPORTANT: The total lean MUST be {forced_total_lean} (consistent with prediction article)."

    prompt = f"""You are a sharp MLB betting analyst for RedsHub.

Give your single strongest best bet for:
{TEAM_NAME} vs {opp_name} on {game_date}
Run Line (Reds): {spread} | Moneyline: {moneyline} | Total: {over_under}
{force_note}

Choose ONE of: Run Line, Moneyline, or Over/Under.
Write 300-400 words explaining exactly why this is the best bet.

End with PICKS_JSON_START
{{
  "spread_pick": "Reds {spread}",
  "spread_lean": "COVER or FADE",
  "total_pick": "{forced_total_pick or f'Over/Under {over_under}'}",
  "total_lean": "{forced_total_lean or 'OVER or UNDER'}",
  "confidence": "High or Medium or Low"
}}
PICKS_JSON_END"""

    content = await _call_claude(prompt, max_tokens=800)
    picks   = _extract_picks(content)
    body    = re.sub(r"PICKS_JSON_START.*?PICKS_JSON_END", "", content, flags=re.DOTALL).strip()

    opp_short = opp_name.split()[-1]
    slug  = slugify(f"best-reds-bet-vs-{opp_short}-{game_date}")
    title = f"Best Bet: Reds vs {opp_name} — {game_date}"

    return {
        "slug":         slug,
        "title":        title,
        "content":      body,
        "article_type": "best_bet",
        "game_date":    game_date,
        "home_team":    home_team,
        "away_team":    away_team,
        "key_picks":    picks,
        "created_at":   datetime.utcnow().isoformat(),
    }


# ── Player Prop ───────────────────────────────────────────────────────────────

async def generate_player_prop(
    player: str, home_team: str, away_team: str, game_date: str,
    player_stats: dict, injuries: list, top_stats: list, over_under: str,
) -> dict:
    stat_str = ""
    if player_stats:
        stat_str = (
            f"Season stats: AVG {player_stats.get('avg','?')}, "
            f"HR {player_stats.get('home_runs','?')}, RBI {player_stats.get('rbi','?')}, "
            f"OPS {player_stats.get('ops','?')}, G {player_stats.get('games_played','?')}"
        )
    opp = away_team if "Reds" in home_team or "Cincinnati" in home_team else home_team

    prompt = f"""You are a sharp MLB prop analyst for RedsHub.

Write a 300-400 word prop bet analysis for {player} ({TEAM_NAME}) against {opp} on {game_date}.
{stat_str}
Game total: {over_under}

Pick ONE prop (hits O/U, home run, strikeouts, RBI, total bases).
State the line clearly and argue OVER or UNDER with conviction.

End with PICKS_JSON_START
{{
  "prop_type": "e.g. Hits",
  "prop_line": "e.g. Over 1.5 Hits",
  "prop_lean": "OVER or UNDER",
  "confidence": "High or Medium or Low"
}}
PICKS_JSON_END"""

    content = await _call_claude(prompt, max_tokens=700)
    picks   = _extract_picks(content)
    body    = re.sub(r"PICKS_JSON_START.*?PICKS_JSON_END", "", content, flags=re.DOTALL).strip()

    player_slug = player.lower().replace(" ", "-")
    opp_short   = opp.split()[-1].lower()
    slug        = slugify(f"{player_slug}-prop-{opp_short}-{game_date}")
    title       = f"{player} Prop Prediction vs {opp} — {game_date}"

    return {
        "slug":         slug,
        "title":        title,
        "content":      body,
        "article_type": "prop",
        "game_date":    game_date,
        "home_team":    home_team,
        "away_team":    away_team,
        "player":       player,
        "key_picks":    picks,
        "created_at":   datetime.utcnow().isoformat(),
    }


async def generate_daily_props(
    home_team: str, away_team: str, game_date: str,
    players: list, over_under: str, injuries: list,
    top_stats: list, max_props_per_player: int = 1,
) -> list:
    articles = []
    for player in players:
        player_stat = next(
            (s for s in top_stats if player.lower().split()[-1] in s.get("player_name", "").lower()),
            None
        )
        try:
            art = await generate_player_prop(
                player=player, home_team=home_team, away_team=away_team,
                game_date=game_date, player_stats=player_stat,
                injuries=injuries, top_stats=top_stats, over_under=over_under,
            )
            articles.append(art)
        except Exception as e:
            logger.error(f"Prop generation failed for {player}: {e}")
    return articles


# ── History Article ───────────────────────────────────────────────────────────

async def generate_history_article(today_str: str) -> dict:
    from datetime import datetime as dt
    d     = dt.strptime(today_str, "%Y-%m-%d")
    month = d.strftime("%B")
    day   = d.day

    prompt = f"""You are a Cincinnati Reds historian writing for RedsHub.

Write a 400-500 word "This Day in Reds History" article for {month} {day}.

Include 2-3 specific memorable moments, players, or games that happened on this date throughout Reds history. Be specific with years and stats. If nothing notable happened, write about a great Reds moment from this week in history.

Use markdown headers (##). Write engagingly for a passionate Reds fan base."""

    content = await _call_claude(prompt, max_tokens=900)
    slug    = slugify(f"this-day-in-reds-history-{month}-{day}")
    title   = f"This Day in Reds History: {month} {day}"

    return {
        "slug":         slug,
        "title":        title,
        "content":      content,
        "article_type": "history",
        "game_date":    today_str,
        "home_team":    "Cincinnati Reds",
        "away_team":    "",
        "key_picks":    None,
        "created_at":   datetime.utcnow().isoformat(),
    }


# ── Postgame Analysis ─────────────────────────────────────────────────────────

async def generate_postgame_analysis(game_date: str) -> dict:
    from app.services.mlb_service import fetch_schedule
    games    = await fetch_schedule()
    game     = next((g for g in games if str(g.game_date) == game_date and g.status == "Final"), None)
    if not game:
        return {}

    is_home  = "Reds" in game.home_team or "Cincinnati" in game.home_team
    reds_score = game.home_score if is_home else game.away_score
    opp_score  = game.away_score if is_home else game.home_score
    opp_name   = game.away_team if is_home else game.home_team
    result_str = "W" if reds_score > opp_score else "L"

    prompt = f"""You are a Cincinnati Reds beat writer for RedsHub.

Write a 400-500 word postgame analysis for:
Cincinnati Reds {reds_score} – {opp_score} {opp_name} ({game_date})
Result: {result_str}

Cover: key offensive performances, pitching summary, turning point of the game, and what it means for the Reds going forward.

Use markdown headers (##). Be insightful and fan-focused."""

    content   = await _call_claude(prompt, max_tokens=900)
    opp_short = opp_name.split()[-1].lower()
    slug      = slugify(f"reds-postgame-vs-{opp_short}-{game_date}")
    title     = f"Reds {reds_score}–{opp_score} {opp_name}: Postgame Analysis"

    return {
        "slug":         slug,
        "title":        title,
        "content":      content,
        "article_type": "postgame",
        "game_date":    game_date,
        "home_team":    game.home_team,
        "away_team":    game.away_team,
        "key_picks":    None,
        "created_at":   datetime.utcnow().isoformat(),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_picks(content: str) -> dict:
    import json
    try:
        match = re.search(r"PICKS_JSON_START\s*(\{.*?\})\s*PICKS_JSON_END", content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        logger.warning(f"Picks JSON parse failed: {e}")
    return {}
