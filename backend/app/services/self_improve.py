"""
Self-improving system for RedsHub (MLB/Reds).
- Hit rate tracking per bet type (spread, total, moneyline, props)
- ROI calculation at -110 juice
- Daily automated self-improvement analysis
"""
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

SITE_ID = "redshub"


def _ml_profit(ml_odds):
    """Calculate profit per unit risked for a moneyline bet.
    Returns multiplier: e.g. +250 -> 2.5, -200 -> 0.5, None -> flat -110."""
    if ml_odds is None:
        return 100 / 110  # flat -110
    if ml_odds > 0:
        return ml_odds / 100
    return 100 / abs(ml_odds)


def calibrate_confidence(results: list) -> dict:
    """
    Calculate hit rates per bet type from graded prediction_results.
    Uses spread_result, total_result, moneyline_result (HIT/MISS/PUSH strings).
    Reports: "Spread: X-Y (Z%), Total: X-Y (Z%), ML: X-Y (Z%)"
    """
    report = {
        "sample_size": len(results),
        "spread": {"total": 0, "hits": 0, "misses": 0, "pushes": 0, "hit_rate": 0.0},
        "total": {"total": 0, "hits": 0, "misses": 0, "pushes": 0, "hit_rate": 0.0},
        "moneyline": {"total": 0, "hits": 0, "misses": 0, "pushes": 0, "hit_rate": 0.0},
        "alerts": [],
    }

    if not results:
        report["alerts"].append("No prediction results found — nothing to calibrate")
        return report

    for market in ["spread", "total", "moneyline"]:
        key = f"{market}_result"
        resolved = [r for r in results if r.get(key)]
        hits = sum(1 for r in resolved if r[key] == "HIT")
        misses = sum(1 for r in resolved if r[key] == "MISS")
        pushes = sum(1 for r in resolved if r[key] == "PUSH")

        decided = hits + misses  # Exclude pushes from rate calc
        hit_rate = (hits / decided * 100) if decided > 0 else 0.0

        report[market] = {
            "total": len(resolved),
            "hits": hits,
            "misses": misses,
            "pushes": pushes,
            "hit_rate": round(hit_rate, 1),
        }

        # Flag concerning drift
        if decided >= 10:
            if hit_rate < 45:
                report["alerts"].append(
                    f"{market.upper()} hit rate critically low at {hit_rate:.1f}% "
                    f"({hits}-{misses}) — consider tightening edge thresholds"
                )
            elif hit_rate < 50:
                report["alerts"].append(
                    f"{market.upper()} hit rate below breakeven at {hit_rate:.1f}% "
                    f"({hits}-{misses}) — monitor closely"
                )
            elif hit_rate >= 55:
                report["alerts"].append(
                    f"{market.upper()} performing well at {hit_rate:.1f}% "
                    f"({hits}-{misses}) — current approach is effective"
                )

    # Recent trend analysis (last 10 resolved games)
    recent = sorted(
        [r for r in results if r.get("game_date")],
        key=lambda r: r["game_date"],
        reverse=True,
    )[:10]

    if len(recent) >= 5:
        recent_spread_hits = sum(1 for r in recent if r.get("spread_result") == "HIT")
        recent_spread_total = sum(1 for r in recent if r.get("spread_result") in ("HIT", "MISS"))
        if recent_spread_total >= 5:
            recent_rate = recent_spread_hits / recent_spread_total * 100
            if recent_rate < 40:
                report["alerts"].append(
                    f"TREND: Last {recent_spread_total} spread picks hitting only {recent_rate:.0f}% — "
                    f"cold streak detected"
                )

    return report


def calculate_roi(results: list) -> dict:
    """
    Calculate overall ROI across all resolved spread/total/ML picks.
    Uses actual ml_odds for moneyline profit when available, falls back to -110.
    Tracks value picks (plus odds) vs chalk picks (minus odds) separately for ML.
    """
    FLAT_PAYOUT = 100 / 110  # 0.909 at -110

    markets = {}
    total_profit = 0.0
    total_bets_count = 0

    # Value vs chalk tracking for moneyline
    value_picks = {"bets": 0, "hits": 0, "misses": 0, "profit": 0.0}
    chalk_picks = {"bets": 0, "hits": 0, "misses": 0, "profit": 0.0}

    for market in ["spread", "total", "moneyline"]:
        key = f"{market}_result"
        resolved = [r for r in results if r.get(key) in ("HIT", "MISS")]
        hits = sum(1 for r in resolved if r[key] == "HIT")
        misses = len(resolved) - hits
        bets = hits + misses

        if market == "moneyline" and bets > 0:
            # Odds-aware profit for moneyline
            profit = 0.0
            for r in resolved:
                odds = r.get("ml_odds")
                payout = _ml_profit(odds)
                is_value = odds is not None and odds > 0
                is_chalk = odds is not None and odds < -130

                if r[key] == "HIT":
                    profit += payout
                    if is_value:
                        value_picks["hits"] += 1
                        value_picks["profit"] += payout
                    elif is_chalk:
                        chalk_picks["hits"] += 1
                        chalk_picks["profit"] += payout
                else:
                    profit -= 1.0
                    if is_value:
                        value_picks["misses"] += 1
                        value_picks["profit"] -= 1.0
                    elif is_chalk:
                        chalk_picks["misses"] += 1
                        chalk_picks["profit"] -= 1.0

                if is_value:
                    value_picks["bets"] += 1
                elif is_chalk:
                    chalk_picks["bets"] += 1

            profit = round(profit, 2)
            hit_rate = round(hits / bets * 100, 1)
            roi = round(profit / bets * 100, 1)
        elif bets > 0:
            hit_rate = round(hits / bets * 100, 1)
            profit = round((hits * FLAT_PAYOUT) - misses, 2)
            roi = round(profit / bets * 100, 1)
        else:
            hit_rate = 0.0
            profit = 0.0
            roi = 0.0

        markets[market] = {
            "bets": bets,
            "hits": hits,
            "misses": misses,
            "hit_rate": hit_rate,
            "profit_units": profit,
            "roi_pct": roi,
        }
        total_profit += profit
        total_bets_count += bets

    if total_bets_count > 0:
        overall_roi = round(total_profit / total_bets_count * 100, 1)
        overall_hit_rate = round(
            sum(m["hits"] for m in markets.values()) /
            sum(m["bets"] for m in markets.values() if m["bets"] > 0) * 100, 1
        )
    else:
        overall_roi = 0.0
        overall_hit_rate = 0.0

    recommendations = []
    if total_bets_count >= 10:
        if overall_roi > 0:
            recommendations.append(
                f"Overall profitable: {overall_hit_rate}% hit rate, "
                f"+{overall_roi}% ROI on {total_bets_count} bets"
            )
        else:
            recommendations.append(
                f"Overall unprofitable: {overall_hit_rate}% hit rate, "
                f"{overall_roi}% ROI on {total_bets_count} bets — review model inputs"
            )

        # Flag any market that's dragging performance down
        for mkt, data in markets.items():
            if data["bets"] >= 5 and data["hit_rate"] < 48:
                recommendations.append(
                    f"{mkt.upper()} underperforming at {data['hit_rate']}% "
                    f"({data['hits']}-{data['misses']}) — consider adjustments"
                )

        # Value vs chalk analysis
        if value_picks["bets"] >= 3:
            vp_rate = round(value_picks["hits"] / value_picks["bets"] * 100, 1)
            recommendations.append(
                f"VALUE ML picks (plus odds): {value_picks['hits']}-{value_picks['misses']} "
                f"({vp_rate}%), {value_picks['profit']:+.2f}u"
            )
        if chalk_picks["bets"] >= 3:
            cp_rate = round(chalk_picks["hits"] / chalk_picks["bets"] * 100, 1)
            recommendations.append(
                f"CHALK ML picks (heavy favorites): {chalk_picks['hits']}-{chalk_picks['misses']} "
                f"({cp_rate}%), {chalk_picks['profit']:+.2f}u"
            )
            if chalk_picks["profit"] < 0 and chalk_picks["bets"] >= 5:
                recommendations.append(
                    "Heavy favorite ML bets are bleeding units — "
                    "consider skipping ML on lines worse than -150"
                )

    return {
        "markets": markets,
        "overall": {
            "bets": total_bets_count,
            "wins": sum(m["hits"] for m in markets.values()),
            "losses": sum(m["misses"] for m in markets.values()),
            "hit_rate": overall_hit_rate,
            "profit_units": round(total_profit, 2),
            "roi_pct": overall_roi,
        },
        "value_picks": value_picks,
        "chalk_picks": chalk_picks,
        "recommendations": recommendations,
    }


async def run_self_improvement() -> dict:
    """
    Main entry point for RedsHub self-improvement.
    1. Load prediction results from Supabase (site_id='redshub')
    2. Calculate hit rates per bet type
    3. Calculate ROI
    4. Load prop results for additional context
    Returns report with recommendations.
    """
    from app.db import get_supabase

    db = get_supabase()
    if not db:
        return {"error": "No database connection"}

    # Load prediction results
    results = []
    try:
        resp = db.table("prediction_results").select("*").eq("site_id", SITE_ID).execute()
        results = resp.data or []
        logger.info(f"Loaded {len(results)} Reds prediction results for self-improvement")
    except Exception as e:
        logger.error(f"Failed to load prediction results: {e}")
        return {"error": f"Failed to load results: {e}"}

    if not results:
        logger.info("Self-improvement: no prediction results yet — skipping")
        return {"status": "skipped", "reason": "No prediction results available"}

    # Load prop results for additional context
    try:
        props = db.table("prop_results").select("*").eq("site_id", SITE_ID).execute()
        prop_results = props.data or []
    except Exception:
        prop_results = []

    # Run calibration (hit rates per bet type)
    calibration = calibrate_confidence(results)
    logger.info(f"Calibration complete: {calibration['spread']['hit_rate']}% spread, "
                f"{calibration['total']['hit_rate']}% total, "
                f"{calibration['moneyline']['hit_rate']}% ML")

    # Run ROI calculation
    roi = calculate_roi(results)
    logger.info(f"ROI complete: {roi['overall']['hit_rate']}% hit rate, "
                f"{roi['overall']['roi_pct']}% ROI on {roi['overall']['bets']} bets")

    # Prop performance summary
    prop_summary = {"total": 0, "hits": 0, "hit_rate": 0.0}
    if prop_results:
        prop_hits = sum(1 for p in prop_results if p.get("result") == "HIT")
        prop_resolved = sum(1 for p in prop_results if p.get("result") in ("HIT", "MISS"))
        prop_summary = {
            "total": len(prop_results),
            "resolved": prop_resolved,
            "hits": prop_hits,
            "hit_rate": round(prop_hits / prop_resolved * 100, 1) if prop_resolved > 0 else 0.0,
        }

    report = {
        "status": "completed",
        "site_id": SITE_ID,
        "run_date": datetime.utcnow().isoformat(),
        "prediction_sample_size": len(results),
        "prop_sample_size": len(prop_results),
        "calibration": calibration,
        "roi": roi,
        "prop_summary": prop_summary,
        "all_recommendations": (
            calibration.get("alerts", []) +
            roi.get("recommendations", [])
        ),
    }

    logger.info(
        f"Self-improvement report: {len(report['all_recommendations'])} recommendations, "
        f"{report['prediction_sample_size']} predictions analyzed"
    )
    return report
