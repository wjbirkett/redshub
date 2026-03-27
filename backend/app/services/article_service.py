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

# Key Reds BATTERS for prop articles (position players only — no pitchers)
PROP_PLAYERS = [
    "Elly De La Cruz", "TJ Friedl", "Spencer Steer",
    "Tyler Stephenson", "Jonathan India", "Jake Fraley",
    "Jeimer Candelario", "Stuart Fairchild", "Santiago Espinal",
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
    # Filter by site_id first; fall back to team-name heuristic for legacy rows
    try:
        result = db.table("articles").select("*").eq("site_id", "redshub").order("game_date", desc=True).limit(limit).execute()
        rows = result.data or []
    except Exception:
        rows = []
    if not rows:
        # Legacy fallback: rows without site_id, filtered by team name
        result = db.table("articles").select("*").or_("home_team.ilike.%Reds%,away_team.ilike.%Reds%,home_team.ilike.%Cincinnati%,away_team.ilike.%Cincinnati%").order("game_date", desc=True).limit(limit).execute()
        rows = [r for r in (result.data or []) if not r.get("site_id") or r.get("site_id") == "redshub"]
    return rows


async def get_article_by_slug(slug: str):
    db = get_supabase()
    if not db:
        return None
    result = db.table("articles").select("*").eq("slug", slug).single().execute()
    row = result.data
    if not row:
        return None
    site = row.get("site_id")
    if site == "knickshub":
        # Block cross-site leakage
        return None
    if site == "redshub" or site is None:
        # Allow redshub rows and legacy rows with no site_id
        return row
    return None


async def save_article(article: dict) -> dict:
    db = get_supabase()
    if not db:
        return article
    article["site_id"] = "redshub"
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

    # Composite scoring
    try:
        from app.services.scoring_service import compute_game_score
        scoring_result = await compute_game_score(home_team, away_team, game_date, injuries)
        scoring_block = scoring_result.get("scoring_block", "")
    except Exception as e:
        logger.warning(f"Scoring service failed: {e}")
        scoring_block = ""

    # ML prediction
    try:
        from app.services.ml_scoring_service import predict_game
        ml_result = await predict_game(home_team, away_team, over_under)
        ml_block = ml_result.get("ml_block", "")
    except Exception as e:
        logger.warning(f"ML prediction failed: {e}")
        ml_block = ""

    # Situational flags
    try:
        from app.services.situational_flags import get_situational_flags
        situational_block = await get_situational_flags(home_team, away_team, game_date)
    except Exception:
        situational_block = ""

    # Umpire context
    try:
        from app.services.umpire_service import get_umpire_context
        umpire_block = await get_umpire_context(game_date)
    except Exception:
        umpire_block = ""

    # FanDuel alt prop lines
    try:
        from app.services.alt_props_service import fetch_alt_props, format_alt_props_block
        alt_props = await fetch_alt_props("Reds")
        alt_props_block = format_alt_props_block(alt_props)
    except Exception:
        alt_props_block = ""

    # Advanced matchup stats
    try:
        from app.services.advanced_stats_service import get_matchup_stats, format_matchup_block, get_probable_pitchers
        matchup = await get_matchup_stats("Cincinnati Reds", opp_name)
        matchup_block = format_matchup_block(matchup, opp_name)
        pitchers = await get_probable_pitchers(game_date)
        pitcher_block = ""
        if pitchers:
            pitcher_block = f"Probable Starters:\n  Reds SP: {pitchers.get('reds_sp', 'TBD')}\n  {opp_name} SP: {pitchers.get('opp_sp', 'TBD')}"
    except Exception as e:
        logger.warning(f"Advanced stats failed: {e}")
        matchup_block = ""
        pitcher_block = ""

    prompt = f"""You are an expert MLB sabermetrics analyst writing for RedsHub. You are deeply versed in advanced baseball analytics. Your job is to find the BEST BETS — even if that means picking AGAINST the Reds. You are NOT a homer. You are a sharp bettor first.

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

{pitcher_block}

{matchup_block}

{scoring_block}

{ml_block}

{situational_block}

{umpire_block}

{alt_props_block}

CRITICAL RULES:
- Name BOTH starting pitchers by name in the first paragraph. If probable starters are listed above, USE THOSE NAMES. Do NOT say "back-end starter" or "TBD" if a name is provided.
- Use REAL stats and numbers. If you don't have a stat, skip it — do NOT make up numbers or say "data unavailable."
- Be specific and confident. Readers are bettors who need actionable analysis, not vague hedging.
- If data is missing, skip that metric silently. Never mention missing data.

Write a 500-700 word analysis covering:
1. Starting pitcher matchup — NAME BOTH STARTERS. Reference ERA, FIP, WHIP, K/9 if available.
2. Offensive outlook — reference OPS, batting average, key hitters for both sides.
3. Bullpen analysis — mention bullpen strengths/weaknesses.
4. Run line analysis — pick whichever side has the edge (Reds OR opponent). Factor in home field advantage (~54% in MLB) and starting pitcher quality.
5. Over/under analysis ({over_under} runs) — consider park factors (GABP = hitter-friendly) and scoring trends.
6. **Predicted final score** — give a specific predicted score (e.g., "Reds 6, Red Sox 4").
7. Final pick with confidence level.

IMPORTANT: Pick the BEST bet, not the Reds bet. If the opponent is the better play, say so. Readers trust honest analysis over homerism.

Reference the composite score and ML prediction when framing your confidence level.
If ML predicts total of 9.5 and book line is 8.5, that supports an Over lean.

End with a JSON block EXACTLY like this (no markdown):
PICKS_JSON_START
{{
  "spread_pick": "Reds {spread} or {opp_name} (opposite side)",
  "spread_lean": "COVER or FADE",
  "moneyline_pick": "Reds or {opp_name}",
  "moneyline_lean": "REDS or OPPONENT",
  "total_pick": "Over/Under {over_under}",
  "total_lean": "OVER or UNDER",
  "predicted_score": "Reds X, {opp_name} Y",
  "confidence": "High or Medium or Low"
}}
PICKS_JSON_END

Use markdown headers (##) for sections. Write with conviction and cite specific sabermetric stats throughout."""

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

    # Composite scoring
    try:
        from app.services.scoring_service import compute_game_score
        scoring_result = await compute_game_score(home_team, away_team, game_date, injuries)
        scoring_block = scoring_result.get("scoring_block", "")
    except Exception as e:
        logger.warning(f"Scoring service failed: {e}")
        scoring_block = ""

    # ML prediction
    try:
        from app.services.ml_scoring_service import predict_game
        ml_result = await predict_game(home_team, away_team, over_under)
        ml_block = ml_result.get("ml_block", "")
    except Exception as e:
        logger.warning(f"ML prediction failed: {e}")
        ml_block = ""

    # Advanced matchup stats
    try:
        from app.services.advanced_stats_service import get_matchup_stats, format_matchup_block
        matchup = await get_matchup_stats("Cincinnati Reds", opp_name)
        matchup_block = format_matchup_block(matchup, opp_name)
    except Exception as e:
        logger.warning(f"Advanced stats failed: {e}")
        matchup_block = ""

    # FanDuel alt prop lines
    try:
        from app.services.alt_props_service import fetch_alt_props, format_alt_props_block
        alt_props = await fetch_alt_props("Reds")
        alt_props_block = format_alt_props_block(alt_props)
    except Exception:
        alt_props_block = ""

    prompt = f"""You are a sharp MLB betting analyst for RedsHub. Your job is to find the BEST BET — even if it means picking AGAINST the Reds. You are a sharp bettor, not a fan.

Give your single strongest best bet for:
{TEAM_NAME} vs {opp_name} on {game_date}
Run Line (Reds): {spread} | Moneyline: {moneyline} | Total: {over_under}
{force_note}

{matchup_block}

{scoring_block}

{ml_block}

{alt_props_block}

Choose ONE of: Run Line, Moneyline, or Over/Under.
Write 300-400 words explaining exactly why this is the best bet. Back your argument with sabermetric reasoning — reference fWAR, FIP vs ERA gaps, wOBA splits, OPS+ against LHP/RHP, bullpen leverage stats, BABIP regression, hard hit rate, barrel rate, or park factors as relevant.

Reference the composite score and ML prediction when framing your confidence level.
If ML predicts total of 9.5 and book line is 8.5, that supports an Over lean.

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
    is_pitcher = False
    if player_stats:
        # Detect if this is a pitcher based on stats
        if player_stats.get("era") is not None or player_stats.get("innings_pitched") is not None:
            is_pitcher = True
            stat_str = (
                f"Season stats: ERA {player_stats.get('era','?')}, "
                f"SO {player_stats.get('strikeouts','?')}, WHIP {player_stats.get('whip','?')}, "
                f"IP {player_stats.get('innings_pitched','?')}, W-L {player_stats.get('wins','?')}-{player_stats.get('losses','?')}"
            )
        else:
            stat_str = (
                f"Season stats: AVG {player_stats.get('avg','?')}, "
                f"HR {player_stats.get('home_runs','?')}, RBI {player_stats.get('rbi','?')}, "
                f"OPS {player_stats.get('ops','?')}, G {player_stats.get('games_played','?')}"
            )
    else:
        # If no stats found but player is not in PROP_PLAYERS, likely a pitcher
        if player not in PROP_PLAYERS:
            is_pitcher = True

    opp = away_team if "Reds" in home_team or "Cincinnati" in home_team else home_team

    # FanDuel alt prop lines
    try:
        from app.services.alt_props_service import fetch_alt_props, format_alt_props_block
        alt_props = await fetch_alt_props("Reds")
        alt_props_block = format_alt_props_block(alt_props)
    except Exception:
        alt_props_block = ""

    if is_pitcher:
        prop_instruction = (
            f"This is a STARTING PITCHER prop. Focus on STRIKEOUTS (K's).\n"
            f"Pick a strikeout prop (e.g., Over/Under 5.5 strikeouts).\n"
            f"Analyze the opposing lineup's strikeout rate (K%), the pitcher's K/9 and SwStr%, "
            f"recent start history, and FIP vs ERA to gauge true skill level."
        )
    else:
        prop_instruction = (
            "Pick ONE prop from: hits O/U, home run, RBI, stolen bases, or total bases.\n"
            "IMPORTANT: Do NOT always pick total bases. Choose the prop where you see the biggest edge based on the matchup.\n"
            "State the line clearly and argue OVER or UNDER with conviction.\n"
            "Reference wOBA, hard hit rate, barrel rate, BABIP trends, or platoon splits as relevant."
        )

    prompt = f"""You are a sharp MLB prop analyst for RedsHub who uses sabermetrics to find edges.

Write a 300-400 word prop bet analysis for {player} ({TEAM_NAME}) against {opp} on {game_date}.
{stat_str}
Game total: {over_under}

{alt_props_block}

{prop_instruction}

End with PICKS_JSON_START
{{
  "prop_type": "e.g. Strikeouts",
  "prop_line": "e.g. Over 5.5 Strikeouts",
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
    top_stats: list, max_props: int = 3,
) -> list:
    """
    Smart prop selection using real sportsbook lines from The Odds API.
    Calculates edge vs season averages, only publishes best edge props.
    """
    articles = []

    # Fetch real prop lines from The Odds API
    try:
        from app.services.prop_lines_service import fetch_live_prop_lines
        all_lines = await fetch_live_prop_lines(home_team, away_team)
        logger.info(f"Got prop lines for {len(all_lines)} players")
    except Exception as e:
        logger.warning(f"Could not fetch prop lines: {e}")
        all_lines = {}

    # Build stats lookup
    stats_lookup = {}
    for s in top_stats:
        name = s.get("player_name", "")
        if name:
            stats_lookup[name] = s

    # Calculate edge for every available prop
    prop_edges = []
    for player, props in all_lines.items():
        player_stat = stats_lookup.get(player) or next(
            (s for s in top_stats if player.lower().split()[-1] in s.get("player_name", "").lower()), None
        )
        if not player_stat:
            continue

        gp = float(player_stat.get("games_played", 1) or 1)

        # Map prop types to season per-game averages
        hits = float(player_stat.get("hits", 0) or 0)
        hr = float(player_stat.get("home_runs", 0) or 0)
        rbi = float(player_stat.get("rbi", 0) or 0)
        sb = float(player_stat.get("stolen_bases", 0) or 0)
        k = float(player_stat.get("strikeouts", 0) or 0)

        stat_map = {
            "hits": hits / gp if gp else 0,
            "total_bases": (hits + hr * 3) / gp if gp else 0,
            "home_runs": hr / gp if gp else 0,
            "rbi": rbi / gp if gp else 0,
            "stolen_bases": sb / gp if gp else 0,
            "runs": 0,  # hard to estimate
            "strikeouts": k / max(float(player_stat.get("games_started", gp) or gp), 1),
        }

        STRONG_EDGE = 8  # Full article
        LEAN_EDGE = 5    # Quick pick card

        for prop_type, line in props.items():
            projected = stat_map.get(prop_type, 0)
            if projected == 0 or line == 0:
                continue
            edge_pct = abs(projected - line) / line * 100
            direction = "OVER" if projected > line else "UNDER"

            if edge_pct >= LEAN_EDGE:  # Changed from 8 to 5
                prop_edges.append({
                    "player": player,
                    "prop_type": prop_type,
                    "line": line,
                    "projected": round(projected, 2),
                    "edge_pct": round(edge_pct, 1),
                    "direction": direction,
                    "tier": "STRONG" if edge_pct >= STRONG_EDGE else "LEAN",
                    "player_stat": player_stat,
                })

    # Sort by edge
    prop_edges.sort(key=lambda x: -x["edge_pct"])

    strong_props = [p for p in prop_edges if p.get("tier") == "STRONG"]
    lean_props = [p for p in prop_edges if p.get("tier") == "LEAN"][:3]
    best_props = strong_props + lean_props

    if best_props:
        logger.info(f"Found {len(prop_edges)} props with edge ({len(strong_props)} STRONG, {len(lean_props)} LEAN), publishing {len(best_props)}")
        for p in best_props:
            logger.info(f"  [{p['tier']}] {p['player']} {p['prop_type']}: line={p['line']}, proj={p['projected']}, edge={p['edge_pct']}%")
    else:
        logger.info("No props with 5%+ edge — falling back to top 3 players")

    # Generate articles for best edge props, or fallback
    if best_props:
        for prop in best_props:
            try:
                art = await generate_player_prop(
                    player=prop["player"], home_team=home_team, away_team=away_team,
                    game_date=game_date, player_stats=prop["player_stat"],
                    injuries=injuries, top_stats=top_stats, over_under=over_under,
                )
                art["edge_pct"] = prop["edge_pct"]
                if prop.get("tier") == "LEAN":
                    art["article_type"] = "lean_prop"
                articles.append(art)
            except Exception as e:
                logger.error(f"Prop generation failed for {prop['player']}: {e}")
    else:
        # Fallback: generate for first 3 provided players
        for player in players[:3]:
            player_stat = stats_lookup.get(player) or next(
                (s for s in top_stats if player.lower().split()[-1] in s.get("player_name", "").lower()), None
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

async def _fetch_historical_reds_games(month: int, day: int) -> list:
    """Fetch real Reds games played on this month/day across all years from ESPN."""
    import httpx as _httpx
    games = []
    for year in range(1970, 2027):
        try:
            date_str = f"{year}{month:02d}{day:02d}"
            async with _httpx.AsyncClient(timeout=5) as client:
                r = await client.get(
                    f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}",
                    headers={"User-Agent": "Mozilla/5.0"}
                )
            if r.status_code != 200:
                continue
            data = r.json()
            for ev in data.get("events", []):
                comp = ev["competitions"][0]
                competitors = comp.get("competitors", [])
                teams = [c.get("team", {}).get("displayName", "") for c in competitors]
                if not any("Reds" in t or "Cincinnati" in t for t in teams):
                    continue
                home = competitors[0]
                away = competitors[1]
                games.append(
                    f"{year}: {away.get('team',{}).get('displayName','?')} {away.get('score','?')} "
                    f"@ {home.get('team',{}).get('displayName','?')} {home.get('score','?')}"
                )
        except Exception:
            continue
    return games


async def generate_history_article(today_str: str) -> dict:
    from datetime import datetime as dt
    d     = dt.strptime(today_str, "%Y-%m-%d")
    month = d.strftime("%B")
    day   = d.day

    verified_games = await _fetch_historical_reds_games(d.month, d.day)

    if verified_games:
        games_block = "VERIFIED GAMES (from ESPN — these are the ONLY games you may reference):\n" + "\n".join(verified_games)
    else:
        games_block = "VERIFIED GAMES: No ESPN game data found for this date."

    prompt = f"""You are a Cincinnati Reds historian writing for RedsHub.

Write a 400-500 word "This Day in Reds History" article for {month} {day}.

{games_block}

CRITICAL RULES:
- ONLY write about games from the VERIFIED GAMES list above. Do NOT invent games, opponents, or scores.
- Do NOT fabricate statistics, player performances, or game outcomes not listed above.
- If the verified games list is empty or sparse, focus on broader historical context about the Reds organization for this time of year — but do NOT invent specific game results.
- You may add factual historical context about players or seasons that are documented (e.g., a player's career arc), but never claim a game happened unless it appears in the VERIFIED GAMES list.

Include 2-3 specific memorable moments drawn only from the verified game data above. Be specific about the year and the score as listed.

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
    import httpx, json
    from app.services.mlb_service import fetch_schedule

    games    = await fetch_schedule()
    game     = next((g for g in games if str(g.game_date) == game_date and g.status == "Final"), None)
    if not game:
        return {}

    is_home    = "Reds" in game.home_team or "Cincinnati" in game.home_team
    reds_score = game.home_score if is_home else game.away_score
    opp_score  = game.away_score if is_home else game.home_score
    opp_name   = game.away_team if is_home else game.home_team
    result_str = "W" if reds_score > opp_score else "L"

    # Fetch full ESPN box score
    box_score_text = ""
    try:
        date_str = game_date.replace("-", "")
        async with httpx.AsyncClient(timeout=15) as client:
            sb_resp = await client.get(
                f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
            )
            sb_data = sb_resp.json()

        for ev in sb_data.get("events", []):
            comps = ev.get("competitions", [{}])
            comp  = comps[0]
            team_names = [c.get("team", {}).get("displayName", "") for c in comp.get("competitors", [])]
            if any("Reds" in n or "Cincinnati" in n for n in team_names):
                event_id = ev.get("id")
                if event_id:
                    bs_resp = await client.get(
                        f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/{event_id}/boxscore"
                    )
                    bs_data = bs_resp.json()
                    # Extract hitting leaders
                    players_section = bs_data.get("players", [])
                    lines = []
                    for team_section in players_section:
                        team_display = team_section.get("team", {}).get("displayName", "")
                        for stat_group in team_section.get("statistics", []):
                            if stat_group.get("name") in ("batting", "hitting"):
                                for athlete in stat_group.get("athletes", [])[:5]:
                                    name = athlete.get("athlete", {}).get("displayName", "")
                                    stats = athlete.get("stats", [])
                                    if name and stats:
                                        lines.append(f"  {name} ({team_display}): {', '.join(str(s) for s in stats[:6])}")
                    if lines:
                        box_score_text = "ESPN Box Score highlights:\n" + "\n".join(lines)
                break
    except Exception as e:
        logger.warning(f"ESPN box score fetch failed: {e}")

    # Fetch prior picks to grade (spread, total, moneyline)
    picks_section = ""
    try:
        db = get_supabase()
        if db:
            # Use separate eq() calls instead of in_() to avoid Supabase driver issues
            pred_rows = []
            for atype in ("prediction", "best_bet"):
                r = (
                    db.table("articles")
                    .select("key_picks, article_type, title")
                    .eq("game_date", game_date)
                    .eq("article_type", atype)
                    .or_("home_team.ilike.%Reds%,away_team.ilike.%Reds%,home_team.ilike.%Cincinnati%,away_team.ilike.%Cincinnati%")
                    .execute()
                )
                if r.data:
                    pred_rows.extend(r.data)

            if pred_rows:
                reds_won = reds_score > opp_score
                grade_lines = []
                for row in pred_rows:
                    picks = row.get("key_picks") or {}
                    if not picks:
                        continue
                    # Grade spread / run line
                    spread_lean = picks.get("spread_lean", "")
                    spread_pick = picks.get("spread_pick", "")
                    if spread_lean and spread_pick:
                        # Simple heuristic: COVER = Reds win (or within spread), FADE = opponent
                        covered = reds_won if spread_lean == "COVER" else not reds_won
                        grade_lines.append(f"- Run Line ({spread_pick}): {'WIN' if covered else 'LOSS'}")
                    # Grade moneyline
                    ml_lean = picks.get("moneyline_lean", "")
                    if ml_lean:
                        ml_correct = (ml_lean.lower() == "reds" and reds_won) or (ml_lean.lower() != "reds" and not reds_won)
                        grade_lines.append(f"- Moneyline ({ml_lean}): {'WIN' if ml_correct else 'LOSS'}")
                    # Grade total
                    total_lean = picks.get("total_lean", "")
                    total_pick = picks.get("total_pick", "")
                    if total_lean and total_pick:
                        actual_total = reds_score + opp_score
                        # Extract line from pick string e.g. "Over/Under 8.5"
                        ou_match = re.search(r"(\d+\.?\d*)", total_pick)
                        if ou_match:
                            ou_line = float(ou_match.group(1))
                            over_hit = actual_total > ou_line
                            lean_correct = (total_lean == "OVER" and over_hit) or (total_lean == "UNDER" and not over_hit)
                            grade_lines.append(f"- Total ({total_pick}, {total_lean}): actual {actual_total} — {'WIN' if lean_correct else 'LOSS'}")

                if grade_lines:
                    picks_section = "\n\n## How Our Picks Did\n" + "\n".join(grade_lines)
    except Exception as e:
        logger.warning(f"Picks grading failed: {e}")

    prompt = f"""You are a Cincinnati Reds beat writer for RedsHub.

Write a 400-500 word postgame analysis for:
Cincinnati Reds {reds_score} – {opp_score} {opp_name} ({game_date})
Result: {result_str}

{box_score_text}

Cover: key offensive performances, pitching summary, turning point of the game, and what it means for the Reds going forward.

Use markdown headers (##). Be insightful and fan-focused."""

    content   = await _call_claude(prompt, max_tokens=900)
    opp_short = opp_name.split()[-1].lower()
    slug      = slugify(f"reds-postgame-vs-{opp_short}-{game_date}")
    title     = f"Reds {reds_score}–{opp_score} {opp_name}: Postgame Analysis"

    # Append picks grading only when picks were found
    if picks_section:
        content = content + picks_section

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
