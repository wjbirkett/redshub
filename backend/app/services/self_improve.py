"""
Self-improving system for RedsHub (MLB/Reds).
- Confidence calibration (are predictions accurate?)
- Edge threshold optimization (what edge % actually profits?)
- Weekly automated self-improvement analysis
"""
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

SITE_ID = "redshub"

# Confidence bins for calibration
CONFIDENCE_BINS = [
    (50, 55, "50-55%"),
    (55, 60, "55-60%"),
    (60, 65, "60-65%"),
    (65, 70, "65-70%"),
    (70, 100, "70%+"),
]

# Edge thresholds to test for optimization
EDGE_THRESHOLDS = [3.0, 5.0, 8.0, 10.0, 12.0, 15.0]


def calibrate_confidence(results: list) -> dict:
    """
    Check if model confidence levels match actual hit rates for Reds picks.
    Takes graded prediction_results with confidence and result fields.
    Groups by spread_result, total_result, moneyline, and props.
    Returns calibration report per bin with recommended adjustments.
    """
    # Overall confidence calibration across all bet types
    bins_report = []

    for low, high, label in CONFIDENCE_BINS:
        bin_results = [
            r for r in results
            if r.get("confidence") is not None
            and low <= float(r["confidence"]) < high
            and r.get("ml_result") in ("HIT", "MISS")
        ]

        if not bin_results:
            bins_report.append({
                "bin": label,
                "predicted": (low + high) / 2,
                "actual": None,
                "count": 0,
                "adjustment": 0,
            })
            continue

        total = len(bin_results)
        wins = sum(1 for r in bin_results if r["ml_result"] == "HIT")
        actual_rate = (wins / total) * 100
        predicted_midpoint = (low + high) / 2
        adjustment = round(actual_rate - predicted_midpoint, 1)

        bins_report.append({
            "bin": label,
            "predicted": predicted_midpoint,
            "actual": round(actual_rate, 1),
            "count": total,
            "adjustment": adjustment,
        })

    # Per-bet-type hit rates
    bet_types = {
        "spread": "spread_result",
        "total": "total_result",
        "moneyline": "ml_result",
    }
    type_report = {}
    for bet_name, field in bet_types.items():
        typed = [r for r in results if r.get(field) in ("HIT", "MISS")]
        if typed:
            hits = sum(1 for r in typed if r[field] == "HIT")
            type_report[bet_name] = {
                "count": len(typed),
                "hits": hits,
                "hit_rate": round((hits / len(typed)) * 100, 1),
            }
        else:
            type_report[bet_name] = {"count": 0, "hits": 0, "hit_rate": None}

    # Props hit rate (if prop_results field exists)
    prop_results = [r for r in results if r.get("prop_result") in ("HIT", "MISS")]
    if prop_results:
        prop_hits = sum(1 for r in prop_results if r["prop_result"] == "HIT")
        type_report["props"] = {
            "count": len(prop_results),
            "hits": prop_hits,
            "hit_rate": round((prop_hits / len(prop_results)) * 100, 1),
        }

    # Flag bins that are consistently off by >3%
    needs_adjustment = [b for b in bins_report if abs(b["adjustment"]) > 3 and b["count"] >= 5]

    report = {
        "bins": bins_report,
        "bet_type_accuracy": type_report,
        "total_graded": sum(b["count"] for b in bins_report),
        "needs_adjustment": needs_adjustment,
        "calibrated": len(needs_adjustment) == 0,
    }
    logger.info(f"Calibration report: {len(needs_adjustment)} bins need adjustment")
    return report


def optimize_edge_thresholds(results: list) -> dict:
    """
    Find optimal edge % cutoffs for STRONG/LEAN/SKIP by simulating ROI
    on Reds picks. Takes graded results with 'best_edge' and 'ml_result'.
    Returns optimal thresholds and ROI at each level.
    """
    # Filter to results with valid edge and outcome
    valid = [
        r for r in results
        if r.get("best_edge") is not None
        and r.get("ml_result") in ("HIT", "MISS")
    ]

    if len(valid) < 20:
        return {
            "error": "Not enough graded results for edge optimization",
            "count": len(valid),
        }

    # Simulate ROI at each edge threshold
    # Assume flat -110 juice (risk 110 to win 100) for simplicity
    threshold_results = []
    for threshold in EDGE_THRESHOLDS:
        picks = [r for r in valid if float(r["best_edge"]) >= threshold]
        if not picks:
            threshold_results.append({
                "threshold": threshold,
                "picks": 0,
                "wins": 0,
                "losses": 0,
                "roi": 0,
            })
            continue

        wins = sum(1 for r in picks if r["ml_result"] == "HIT")
        losses = len(picks) - wins
        # ROI at -110: win = +100, loss = -110
        profit = (wins * 100) - (losses * 110)
        total_risked = len(picks) * 110
        roi = round((profit / total_risked) * 100, 1) if total_risked > 0 else 0

        threshold_results.append({
            "threshold": threshold,
            "picks": len(picks),
            "wins": wins,
            "losses": losses,
            "roi": roi,
            "win_pct": round((wins / len(picks)) * 100, 1),
        })

    # Find optimal thresholds
    best = max(threshold_results, key=lambda x: x["roi"]) if threshold_results else {}

    # STRONG = highest ROI with >= 10 picks
    strong_candidates = [t for t in threshold_results if t["picks"] >= 10]
    optimal_strong = max(strong_candidates, key=lambda x: x["roi"])["threshold"] if strong_candidates else 10.0

    # LEAN = highest ROI threshold that has >= 25 picks
    lean_candidates = [t for t in threshold_results if t["picks"] >= 25]
    optimal_lean = max(lean_candidates, key=lambda x: x["roi"])["threshold"] if lean_candidates else 5.0

    report = {
        "optimal_strong": optimal_strong,
        "optimal_lean": optimal_lean,
        "optimal_skip_below": optimal_lean,
        "roi_at_optimal": best.get("roi", 0) if best else 0,
        "threshold_breakdown": threshold_results,
        "total_picks_analyzed": len(valid),
    }
    logger.info(f"Edge optimization: STRONG >= {optimal_strong}%, LEAN >= {optimal_lean}%")
    return report


async def run_self_improvement() -> dict:
    """
    Main entry point for RedsHub self-improvement.
    1. Load prediction results from Supabase (site_id='redshub')
    2. Calibrate confidence levels
    3. Optimize edge thresholds
    Returns report with recommendations.
    """
    from app.db import get_supabase

    report = {
        "site_id": SITE_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "calibration": None,
        "edge_optimization": None,
    }

    # Load prediction results from Supabase
    db = get_supabase()
    results = []
    if db:
        try:
            resp = db.table("prediction_results").select("*").eq("site_id", SITE_ID).execute()
            results = resp.data or []
            logger.info(f"Loaded {len(results)} Reds prediction results for self-improvement")
        except Exception as e:
            logger.error(f"Failed to load prediction results: {e}")

    if len(results) < 50:
        logger.info(f"Only {len(results)} results — need 50+ for calibration/optimization, skipping")
        report["calibration"] = {"skipped": True, "reason": f"Only {len(results)} results (need 50+)"}
        report["edge_optimization"] = {"skipped": True, "reason": f"Only {len(results)} results (need 50+)"}
    else:
        # Confidence calibration
        report["calibration"] = calibrate_confidence(results)

        # Edge threshold optimization
        report["edge_optimization"] = optimize_edge_thresholds(results)

    logger.info(f"Self-improvement run complete: {json.dumps(report, default=str)[:500]}")
    return report
