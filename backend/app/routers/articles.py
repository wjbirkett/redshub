import asyncio, threading
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import date, timedelta

from app.services.article_service import (
    generate_game_preview, save_article, get_articles, get_article_by_slug, slugify,
    generate_best_bet, generate_player_prop, generate_daily_props,
    generate_history_article, generate_postgame_analysis, PROP_PLAYERS,
)
from app.services.mlb_service import fetch_schedule, fetch_injury_report, fetch_player_stats, fetch_probable_pitcher
from app.services.odds_service import fetch_reds_lines

limiter = Limiter(key_func=get_remote_address)
router  = APIRouter()

SITE_URL = "https://redshub.vercel.app"


def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj


def _get_odds_summary(odds: list, next_game: dict):
    spread = moneyline = over_under = "N/A"
    if not odds:
        return spread, moneyline, over_under
    o = odds[0]
    is_away  = "Reds" in o.get("away_team", "") or "Cincinnati" in o.get("away_team", "")
    raw_s    = o.get("spread")
    ml_home  = o.get("moneyline_home")
    ml_away  = o.get("moneyline_away")
    ou       = o.get("over_under")
    reds_spread = (-raw_s if is_away else raw_s) if raw_s is not None else None
    reds_ml     = ml_away if is_away else ml_home
    if reds_spread is not None:
        spread    = f"{reds_spread:+.1f}"
    if reds_ml is not None:
        moneyline = f"{reds_ml:+d}"
    if ou is not None:
        over_under = f"{ou}"
    return spread, moneyline, over_under


def _next_game(games: list, allow_yesterday: bool = False) -> dict | None:
    today     = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow  = today + timedelta(days=1)

    def gd(g):
        d = g["game_date"]
        if isinstance(d, date):
            return d
        return date.fromisoformat(str(d)[:10])

    game = next((g for g in sorted(games, key=lambda g: str(g["game_date"])) if gd(g) in (today, tomorrow) and g["status"] != "Final"), None)
    if not game and allow_yesterday:
        game = next((g for g in games if gd(g) in (today, yesterday)), None)
    return game


# ── Read endpoints ────────────────────────────────────────────────────────────

@router.get("/")
async def list_articles(limit: int = 20):
    return await get_articles(limit)

@router.get("/results")
async def get_results():
    from app.db import get_supabase
    db = get_supabase()
    if not db:
        return {"predictions": [], "props": []}
    # Filter to Reds games only
    pred  = db.table("prediction_results").select("*").or_(
        "home_team.ilike.%Reds%,away_team.ilike.%Reds%,home_team.ilike.%Cincinnati%,away_team.ilike.%Cincinnati%"
    ).order("game_date", desc=True).execute()
    props = db.table("prop_results").select("*").or_(
        "home_team.ilike.%Reds%,away_team.ilike.%Reds%,home_team.ilike.%Cincinnati%,away_team.ilike.%Cincinnati%"
    ).order("game_date", desc=True).execute()
    return {"predictions": pred.data or [], "props": props.data or []}

@router.get("/odds")
async def get_odds():
    lines = await fetch_reds_lines()
    return [l.model_dump() if hasattr(l, "model_dump") else l for l in lines]

@router.get("/sitemap.xml")
async def articles_sitemap():
    articles = await get_articles(limit=200)
    urls = "\n".join([
        f"""  <url>
    <loc>{SITE_URL}/predictions/{a['slug']}</loc>
    <lastmod>{(a.get('updated_at') or a.get('created_at',''))[:10]}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>"""
        for a in articles
    ])
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return Response(content=xml, media_type="application/xml")

@router.get("/backtest")
async def backtest():
    """Simulate ROI from all historical predictions."""
    from app.db import get_supabase
    db = get_supabase()
    if not db:
        return {"error": "No DB"}
    # Filter for Reds games only
    pred = db.table("prediction_results").select("*").execute()
    props = db.table("prop_results").select("*").execute()

    # Filter to Reds
    reds_preds = [p for p in (pred.data or []) if "reds" in (p.get("home_team", "") + p.get("away_team", "")).lower()]
    reds_props = [p for p in (props.data or []) if p.get("player", "") in [
        "Elly De La Cruz", "TJ Friedl", "Spencer Steer", "Tyler Stephenson",
        "Jonathan India", "Jake Fraley", "Jeimer Candelario"
    ]]

    # Simple ROI calc
    win_payout = 100 / 110  # -110 odds
    total_bets = 0
    total_profit = 0

    for r in reds_preds:
        for key in ["spread_result", "total_result"]:
            if r.get(key):
                total_bets += 1
                total_profit += win_payout if r[key] == "HIT" else -1

    for r in reds_props:
        if r.get("result"):
            total_bets += 1
            total_profit += win_payout if r["result"] == "HIT" else -1

    roi = (total_profit / max(total_bets, 1)) * 100

    return {
        "total_bets": total_bets,
        "total_profit_units": round(total_profit, 2),
        "roi_pct": round(roi, 1),
        "predictions": len(reds_preds),
        "props": len(reds_props),
    }


@router.get("/{slug}")
async def get_article(slug: str):
    article = await get_article_by_slug(slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


# ── Generate endpoints ────────────────────────────────────────────────────────

@router.post("/trigger-all")
async def trigger_all_articles():
    from app.scheduler import _run_async

    async def _gen():
        try:
            games_raw = await fetch_schedule()
            games     = [to_dict(g) for g in games_raw]
            game      = _next_game(games, allow_yesterday=True)
            if not game:
                return
            inj_raw  = await fetch_injury_report()
            injuries = [to_dict(i) for i in inj_raw]
            st_raw   = await fetch_player_stats()
            top_st   = [to_dict(s) for s in st_raw[:8]]
            odds_raw = await fetch_reds_lines()
            odds     = [to_dict(o) for o in odds_raw]
            spread, moneyline, over_under = _get_odds_summary(odds, game)
            gd       = str(game["game_date"])[:10]
            art      = await generate_game_preview(game["home_team"], game["away_team"], gd, spread, moneyline, over_under, injuries, games, top_st)
            await save_article(art)
            picks    = art.get("key_picks") or {}
            bb       = await generate_best_bet(game["home_team"], game["away_team"], gd, spread, moneyline, over_under, injuries, top_st, forced_total_lean=picks.get("total_lean"), forced_total_pick=picks.get("total_pick"))
            await save_article(bb)
            active   = [p for p in PROP_PLAYERS if not any(p.split()[-1].lower() in i.get("player_name","").lower() and "out" in i.get("status","").lower() for i in injuries)]
            # Add probable starting pitcher for strikeout props
            starter  = await fetch_probable_pitcher(game["home_team"], game["away_team"])
            if starter and starter not in active:
                active.append(starter)
            props    = await generate_daily_props(game["home_team"], game["away_team"], gd, active, over_under, injuries, top_st)
            for prop in props:
                await save_article(prop)
        except Exception as e:
            import logging; logging.getLogger(__name__).error(f"trigger-all failed: {e}", exc_info=True)

    threading.Thread(target=lambda: _run_async(_gen()), daemon=True).start()
    return {"message": "Article generation triggered for Reds"}


@router.post("/generate/next-game")
async def generate_next_game_article(force: bool = False):
    games_raw = await fetch_schedule()
    games     = [to_dict(g) for g in games_raw]
    game      = _next_game(games)
    if not game:
        raise HTTPException(status_code=404, detail="No upcoming Reds game found")

    gd   = str(game["game_date"])[:10]
    slug = slugify(f"{game['away_team']}-vs-{game['home_team']}-prediction-{gd}")
    if not force:
        existing = await get_article_by_slug(slug)
        if existing:
            return {"message": "Article already exists", "slug": slug, "article": existing}

    inj_raw  = await fetch_injury_report()
    injuries = [to_dict(i) for i in inj_raw]
    st_raw   = await fetch_player_stats()
    top_st   = [to_dict(s) for s in st_raw[:8]]
    odds_raw = await fetch_reds_lines()
    odds     = [to_dict(o) for o in odds_raw]
    spread, moneyline, over_under = _get_odds_summary(odds, game)

    article = await generate_game_preview(game["home_team"], game["away_team"], gd, spread, moneyline, over_under, injuries, games, top_st)
    saved   = await save_article(article)
    return {"message": "Article generated", "slug": saved["slug"]}


@router.post("/generate/for-date")
async def generate_for_date(game_date: str, force: bool = True):
    target   = date.fromisoformat(game_date)
    games_raw = await fetch_schedule()
    games    = [to_dict(g) for g in games_raw]

    def gd(g):
        d = g["game_date"]
        if isinstance(d, date): return d
        return date.fromisoformat(str(d)[:10])

    game = next((g for g in games if gd(g) == target), None)
    if not game:
        raise HTTPException(status_code=404, detail=f"No Reds game on {game_date}")

    inj_raw  = await fetch_injury_report()
    injuries = [to_dict(i) for i in inj_raw]
    st_raw   = await fetch_player_stats()
    top_st   = [to_dict(s) for s in st_raw[:8]]
    odds_raw = await fetch_reds_lines()
    odds     = [to_dict(o) for o in odds_raw]
    spread, moneyline, over_under = _get_odds_summary(odds, game)

    art   = await generate_game_preview(game["home_team"], game["away_team"], game_date, spread, moneyline, over_under, injuries, games, top_st)
    await save_article(art)
    picks = art.get("key_picks") or {}
    bb    = await generate_best_bet(game["home_team"], game["away_team"], game_date, spread, moneyline, over_under, injuries, top_st, forced_total_lean=picks.get("total_lean"), forced_total_pick=picks.get("total_pick"))
    await save_article(bb)
    active = [p for p in PROP_PLAYERS if not any(p.split()[-1].lower() in i.get("player_name","").lower() and "out" in i.get("status","").lower() for i in injuries)]
    # Add probable starting pitcher for strikeout props
    starter = await fetch_probable_pitcher(game["home_team"], game["away_team"])
    if starter and starter not in active:
        active.append(starter)
    props  = await generate_daily_props(game["home_team"], game["away_team"], game_date, active, over_under, injuries, top_st)
    for p in props:
        await save_article(p)
    return {"message": f"Generated {2+len(props)} articles for {game_date}", "prediction": art["slug"], "best_bet": bb["slug"], "props": [p["slug"] for p in props]}


@router.post("/generate/history")
async def generate_history(force: bool = False):
    from datetime import datetime as dt
    today_str = str(date.today())
    d         = dt.strptime(today_str, "%Y-%m-%d")
    slug      = slugify(f"this-day-in-reds-history-{d.strftime('%B')}-{d.day}")
    if not force:
        existing = await get_article_by_slug(slug)
        if existing:
            return {"message": "History article exists", "slug": slug}
    article = await generate_history_article(today_str)
    saved   = await save_article(article)
    return {"message": "History article generated", "slug": saved["slug"]}


@router.post("/resolve-results")
async def resolve_results(game_date: str = None):
    from app.services.results_service import resolve_game_predictions
    if not game_date:
        game_date = str(date.today() - timedelta(days=1))
    result = await resolve_game_predictions(game_date)
    return {"game_date": game_date, "result": result}


@router.get("/debug-trigger")
async def debug_trigger():
    import traceback
    try:
        games_raw = await fetch_schedule()
        games     = [to_dict(g) for g in games_raw]
        odds_raw  = await fetch_reds_lines()
        odds      = [to_dict(o) for o in odds_raw]
        inj_raw   = await fetch_injury_report()
        injuries  = [to_dict(i) for i in inj_raw]
        game      = _next_game(games)
        return {"games_count": len(games), "next_game": game, "odds": odds[0] if odds else None, "injuries_count": len(injuries)}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


@router.patch("/{slug}")
async def update_article(slug: str, request: Request):
    from app.db import get_supabase
    data = await request.json()
    db   = get_supabase()
    db.table("articles").select("*").eq("slug", slug).execute()
    db.table("articles").update(data).eq("slug", slug).execute()
    return {"updated": slug}


@router.delete("/{slug}")
async def delete_article(slug: str):
    from app.db import get_supabase
    db = get_supabase()
    db.table("articles").delete().eq("slug", slug).execute()
    return {"deleted": slug}
