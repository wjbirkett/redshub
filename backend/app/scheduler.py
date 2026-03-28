from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio, logging, threading

logger    = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def refresh_news():
    from app.services.news_service import refresh_news as rn
    _run_async(rn())


def refresh_injuries():
    from app.services.mlb_service import fetch_injury_report
    _run_async(fetch_injury_report())


def refresh_odds():
    from app.services.odds_service import fetch_reds_lines
    _run_async(fetch_reds_lines())


def generate_article(force: bool = False):
    """
    Runs every 15 minutes. Generates pre-game articles when we are
    40-70 minutes before first pitch (after MLB 1-hr lineup card deadline).
    MLB games typically start 6:40-7:10pm ET (22:40-23:10 UTC).
    """
    import threading
    from datetime import date, datetime, timezone, timedelta
    from app.services.article_service import (
        generate_game_preview, generate_best_bet, generate_daily_props,
        save_article, get_article_by_slug, slugify, PROP_PLAYERS,
    )
    from app.services.mlb_service import fetch_schedule, fetch_injury_report, fetch_player_stats, fetch_probable_pitcher
    from app.services.odds_service import fetch_reds_lines
    import httpx

    REDS_ESPN_ID = "17"
    ESPN_BASE    = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb"

    async def _generate():
        try:
            today   = date.today()
            now_utc = datetime.now(timezone.utc)

            # Find today's game + first pitch time via ESPN
            url = f"{ESPN_BASE}/teams/{REDS_ESPN_ID}/schedule"
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp     = await client.get(url)
                    raw_data = resp.json()
            except Exception as e:
                logger.error(f"ESPN MLB schedule fetch failed: {e}")
                return

            today_event    = None
            game_time_utc  = None
            for event in raw_data.get("events", []):
                raw_date = event.get("date", "")
                try:
                    event_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                    if event_date in (today, today + timedelta(days=1)):
                        comp        = event["competitions"][0]
                        status_name = comp.get("status", {}).get("type", {}).get("name", "")
                        if "FINAL" not in status_name:
                            today_event = event
                            try:
                                game_time_utc = datetime.strptime(raw_date, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                            except:
                                try:
                                    game_time_utc = datetime.strptime(raw_date[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                                except:
                                    # Default MLB game: 7pm ET = 23:00 UTC
                                    game_time_utc = datetime(today.year, today.month, today.day, 23, 0, tzinfo=timezone.utc)
                            break
                except:
                    continue

            if not today_event:
                logger.info("Cron: no Reds game today — skipping")
                return

            minutes_until = (game_time_utc - now_utc).total_seconds() / 60
            logger.info(f"Cron: Reds game at {game_time_utc.isoformat()}, {minutes_until:.0f} min to first pitch")

            if not force and not (40 <= minutes_until <= 70):
                logger.info(f"Cron: not in generation window ({minutes_until:.0f} min) — skipping")
                return

            games_raw  = await fetch_schedule()
            games      = [g.model_dump() if hasattr(g, "model_dump") else g for g in games_raw]
            tomorrow   = today + timedelta(days=1)

            def get_date(g):
                d = g["game_date"]
                if isinstance(d, date): return d
                return date.fromisoformat(str(d)[:10])

            next_game = next((g for g in games if get_date(g) in (today, tomorrow) and g["status"] != "Final"), None)
            if not next_game:
                logger.info("Cron: could not find Reds game in schedule")
                return

            gd   = str(get_date(next_game))
            slug = slugify(f"{next_game['away_team']}-vs-{next_game['home_team']}-prediction-{gd}")
            # Check by slug AND by site_id+game_date to prevent duplicate generation
            if not force:
                from app.db import get_supabase as _get_db
                _db = _get_db()
                if _db:
                    _ex = _db.table("articles").select("slug").eq("site_id", "redshub").eq("game_date", gd).eq("article_type", "prediction").execute()
                    if _ex.data:
                        logger.info(f"Cron: prediction article already exists for {gd} (site_id check)")
                        return
                elif await get_article_by_slug(slug):
                    logger.info(f"Cron: articles already exist for {gd}")
                    return

            injuries = [i.model_dump() if hasattr(i, "model_dump") else i for i in await fetch_injury_report()]
            top_st   = [s.model_dump() if hasattr(s, "model_dump") else s for s in (await fetch_player_stats())[:8]]
            odds     = [o.model_dump() if hasattr(o, "model_dump") else o for o in await fetch_reds_lines()]

            spread = moneyline = over_under = "N/A"
            if odds:
                o        = odds[0]
                is_away  = "Reds" in o.get("away_team","") or "Cincinnati" in o.get("away_team","")
                raw_s    = o.get("spread")
                ml_home  = o.get("moneyline_home")
                ml_away  = o.get("moneyline_away")
                ou       = o.get("over_under")
                reds_s   = (-raw_s if is_away else raw_s) if raw_s is not None else None
                reds_ml  = ml_away if is_away else ml_home
                if reds_s  is not None: spread    = f"{reds_s:+.1f}"
                if reds_ml is not None: moneyline = f"{reds_ml:+d}"
                if ou      is not None: over_under = f"{ou}"

            art  = await generate_game_preview(next_game["home_team"], next_game["away_team"], gd, spread, moneyline, over_under, injuries, games, top_st)
            # Double-check before saving to guard against race conditions
            if not force and await get_article_by_slug(art.get("slug", slug)):
                logger.info(f"Cron: article {art.get('slug')} appeared during generation — skipping save")
            else:
                await save_article(art)
            picks = art.get("key_picks") or {}
            bb    = await generate_best_bet(next_game["home_team"], next_game["away_team"], gd, spread, moneyline, over_under, injuries, top_st, forced_total_lean=picks.get("total_lean"), forced_total_pick=picks.get("total_pick"))
            await save_article(bb)

            active = [p for p in PROP_PLAYERS if not any(p.split()[-1].lower() in i.get("player_name","").lower() and "out" in i.get("status","").lower() for i in injuries)]
            # Add probable starting pitcher for strikeout props
            starter = await fetch_probable_pitcher(next_game["home_team"], next_game["away_team"])
            if starter and starter not in active:
                active.append(starter)
            props  = await generate_daily_props(next_game["home_team"], next_game["away_team"], gd, active, over_under, injuries, top_st)
            for prop in props:
                await save_article(prop)
            logger.info(f"Cron: generated {2+len(props)} articles for {gd}")

        except Exception as e:
            logger.error(f"Cron: article generation failed: {e}", exc_info=True)

    _run_async(_generate())


def generate_history_article():
    from datetime import date, datetime
    from app.services.article_service import generate_history_article as gen_hist, save_article, get_article_by_slug, slugify
    from app.services.mlb_service import fetch_schedule

    async def _generate():
        try:
            today     = date.today()
            today_str = str(today)
            games_raw = await fetch_schedule()
            games     = [g.model_dump() if hasattr(g, "model_dump") else g for g in games_raw]

            def gd(g):
                d = g["game_date"]
                if isinstance(d, date): return d
                return date.fromisoformat(str(d)[:10])

            if any(str(gd(g)) == today_str and g["status"] != "Final" for g in games):
                logger.info("Cron: game today — skipping history article")
                return

            dt    = datetime.strptime(today_str, "%Y-%m-%d")
            slug  = slugify(f"this-day-in-reds-history-{dt.strftime('%B')}-{dt.day}")
            if await get_article_by_slug(slug):
                logger.info(f"Cron: history article already exists for {today_str}")
                return

            article = await gen_hist(today_str)
            await save_article(article)
            logger.info(f"Cron: history article generated for {today_str}")
        except Exception as e:
            logger.error(f"Cron: history article failed: {e}")

    _run_async(_generate())


def resolve_results():
    from app.services.results_service import resolve_game_predictions
    from datetime import date, timedelta

    async def _resolve():
        yesterday = str(date.today() - timedelta(days=1))
        result    = await resolve_game_predictions(yesterday)
        logger.info(f"Results resolved for {yesterday}: {result}")

    _run_async(_resolve())


def generate_postgame_article():
    """Runs every 15 min. Generates postgame ~3hrs after first pitch."""
    threading.Thread(target=lambda: _run_async(_postgame_check()), daemon=True).start()


async def _postgame_check():
    try:
        import httpx
        from datetime import date as dt, timedelta, datetime, timezone
        from app.services.article_service import generate_postgame_analysis, save_article
        from app.db import get_supabase

        now_utc   = datetime.now(timezone.utc)
        REDS_ESPN_ID = "17"
        for check_date in [dt.today(), dt.today() - timedelta(days=1)]:
            ds = check_date.strftime("%Y%m%d")
            async with httpx.AsyncClient(timeout=15) as client:
                r    = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={ds}")
                data = r.json()

            for ev in data.get("events", []):
                comp = ev["competitions"][0]
                ids  = [x.get("team",{}).get("id") for x in comp.get("competitors",[])]
                if REDS_ESPN_ID not in ids:
                    continue
                if not comp.get("status",{}).get("type",{}).get("completed", False):
                    continue
                try:
                    tip_utc = datetime.fromisoformat(ev.get("date","").replace("Z","+00:00"))
                except:
                    continue
                minutes_since = (now_utc - tip_utc).total_seconds() / 60
                if not (30 <= minutes_since <= 360):
                    continue
                game_date = ev.get("date","")[:10]
                db = get_supabase()
                if db:
                    ex = db.table("articles").select("slug").eq("game_date", game_date).eq("article_type","postgame").execute()
                    if ex.data:
                        return
                article = await generate_postgame_analysis(game_date)
                if article and article.get("slug"):
                    await save_article(article)
                    logger.info(f"Postgame: article saved for {game_date}")
                return
    except Exception as e:
        logger.error(f"Postgame generation failed: {e}", exc_info=True)


def run_self_improvement():
    from app.services.self_improve import run_self_improvement as rsi
    _run_async(rsi())


def start_scheduler():
    _scheduler.add_job(refresh_news,              CronTrigger(minute="*/15"))
    _scheduler.add_job(refresh_injuries,          CronTrigger(hour="*/3"))
    _scheduler.add_job(refresh_odds,              CronTrigger(hour="*/1"))
    _scheduler.add_job(generate_article,          CronTrigger(minute="*/15"))
    # History on off-days, noon ET (17:00 UTC)
    _scheduler.add_job(generate_history_article,  CronTrigger(hour=17, minute=0, timezone="UTC"))
    # Resolve results at 4am UTC (midnight ET)
    _scheduler.add_job(resolve_results,           CronTrigger(hour=4,  minute=0, timezone="UTC"))
    _scheduler.add_job(generate_postgame_article, CronTrigger(minute="*/15"))
    # Self-improvement: Sundays at 8am UTC
    _scheduler.add_job(run_self_improvement,      CronTrigger(day_of_week="sun", hour=8, minute=0, timezone="UTC"))
    _scheduler.start()
    logger.info("RedsHub scheduler started")


def shutdown_scheduler():
    _scheduler.shutdown()
