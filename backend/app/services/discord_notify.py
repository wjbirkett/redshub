"""
Discord morning recap for RedsHub.
Posts yesterday's results + what the model learned.
"""
import httpx
import logging
import os
from datetime import date, datetime, timedelta, timezone

logger = logging.getLogger(__name__)

WEBHOOK = os.environ.get(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1487607206353567895/vdZXQMOjesj4Cg5DNBCufcqefPn-OU2J8UZPGLjfQbu1hV9PIIFgKM70NRxtIZKl_swl",
)


async def send_redshub_recap():
    """Send a morning recap of yesterday's results and what the model learned."""
    if not WEBHOOK:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping recap")
        return

    port = os.environ.get("PORT", "8000")
    base = f"http://localhost:{port}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r_results = await client.get(f"{base}/api/articles/results")
            results = r_results.json()

            r_backtest = await client.get(f"{base}/api/articles/backtest")
            backtest = r_backtest.json()
    except Exception as e:
        logger.error(f"RedsHub recap fetch failed: {e}")
        return

    predictions = results.get("predictions", [])
    props = results.get("props", [])

    if not predictions:
        logger.info("RedsHub recap: no prediction results yet — skipping")
        return

    # --- Season record from backtest ---
    total_w = backtest.get("wins", 0)
    total_l = backtest.get("losses", 0)
    units = backtest.get("units", 0)
    roi = backtest.get("roi", 0)

    spread_w = backtest.get("spread_wins", 0)
    spread_l = backtest.get("spread_losses", 0)
    total_ov_w = backtest.get("total_wins", 0)
    total_ov_l = backtest.get("total_losses", 0)

    # Props W/L from results
    prop_w = sum(1 for p in props if p.get("result") == "hit")
    prop_l = sum(1 for p in props if p.get("result") == "miss")

    # --- Mood ---
    if units > 2:
        vibe = "Crushed it."
    elif units > 0:
        vibe = "Profitable day."
    elif units > -1:
        vibe = "Tough but close."
    else:
        vibe = "Rough day. Learning from it."

    # --- What the model learned ---
    lessons = []
    if spread_w + spread_l > 0:
        s_rate = spread_w / (spread_w + spread_l) * 100
        if s_rate >= 60:
            lessons.append("Run line picks are sharp — keeping current thresholds")
        elif s_rate < 45:
            lessons.append("Run line picks underperforming — tightening edge requirements")

    if total_ov_w + total_ov_l > 0:
        t_rate = total_ov_w / (total_ov_w + total_ov_l) * 100
        if t_rate >= 55:
            lessons.append("Total picks hitting — O/U projections are calibrated")
        elif t_rate < 45:
            lessons.append("Total picks need work — adjusting run projection anchoring")

    if prop_w + prop_l > 0:
        p_rate = prop_w / (prop_w + prop_l) * 100
        if p_rate >= 55:
            lessons.append(f"Props hitting at {p_rate:.0f}% — edge detection is working")
        elif p_rate < 45:
            lessons.append("Props underperforming — recalibrating player projections")

    if not lessons:
        lessons.append("Accumulating more data before adjusting strategy")

    # --- Next game ---
    next_game_line = ""
    try:
        from app.services.mlb_service import fetch_schedule

        games_raw = await fetch_schedule()
        games = [g.model_dump() if hasattr(g, "model_dump") else g for g in games_raw]
        today = date.today()
        tomorrow = today + timedelta(days=1)

        def get_date(g):
            d = g["game_date"]
            if isinstance(d, date):
                return d
            return date.fromisoformat(str(d)[:10])

        upcoming = [
            g for g in games
            if get_date(g) in (today, tomorrow) and g.get("status") != "Final"
        ]
        if upcoming:
            ng = upcoming[0]
            opp = ng.get("away_team") if "Reds" in ng.get("home_team", "") else ng.get("home_team", "")
            gt = ng.get("game_time", "TBD")
            home_away = "vs" if "Reds" in ng.get("home_team", "") else "@"
            next_game_line = f"\nNext game: Reds {home_away} {opp} at {gt} ET"
    except Exception as e:
        logger.debug(f"Could not fetch next game for recap: {e}")

    # --- Build message ---
    yesterday = str(date.today() - timedelta(days=1))

    spread_str = f"{spread_w}-{spread_l}" if spread_w + spread_l > 0 else "—"
    total_str = f"{total_ov_w}-{total_ov_l}" if total_ov_w + total_ov_l > 0 else "—"
    props_str = f"{prop_w}-{prop_l}" if prop_w + prop_l > 0 else "—"

    lines = [
        f"# \u26be RedsHub Morning Recap — {yesterday}",
        f"**{vibe}**",
        "",
        f"Season Record: {total_w}-{total_l} ({units:+.1f}u, {roi:+.1f}% ROI)",
        f"> Spread: {spread_str} | Total: {total_str} | Props: {props_str}",
    ]

    lines.append("")
    lines.append("**What the model learned:**")
    for lesson in lessons:
        lines.append(f"\u2022 {lesson}")

    if next_game_line:
        lines.append(next_game_line)

    lines.append("")
    lines.append("*redshub.com*")

    message = "\n".join(lines)

    # --- Send ---
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if len(message) > 1900:
                chunks, current = [], ""
                for line in lines:
                    if len(current) + len(line) + 1 > 1900:
                        chunks.append(current)
                        current = line
                    else:
                        current += "\n" + line if current else line
                if current:
                    chunks.append(current)
                for chunk in chunks:
                    await client.post(WEBHOOK, json={"content": chunk, "username": "RedsHub"})
            else:
                await client.post(WEBHOOK, json={"content": message, "username": "RedsHub"})
        logger.info(f"RedsHub morning recap sent for {yesterday}")
    except Exception as e:
        logger.error(f"RedsHub recap webhook failed: {e}")
