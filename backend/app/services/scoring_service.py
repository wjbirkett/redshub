"""
scoring_service.py — Rules-based composite game scorer for RedsHub.

Computes 0-100 score from 5 MLB-specific factors:
  - Starting pitcher matchup (35%)
  - Team batting strength (25%)
  - Bullpen advantage (15%)
  - Home/Away + park factor (15%)
  - Rest/schedule factor (10%)
"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Park factors (runs multiplier — >1.0 = hitter-friendly)
PARK_FACTORS = {
    "Cincinnati Reds": 1.08,  # GABP is hitter-friendly
    "Colorado Rockies": 1.38, "Boston Red Sox": 1.05,
    "Arizona Diamondbacks": 1.03, "Philadelphia Phillies": 1.02,
    "Milwaukee Brewers": 1.01, "Chicago Cubs": 1.00,
    "Toronto Blue Jays": 1.00, "Atlanta Braves": 0.99,
    "Los Angeles Angels": 0.99, "Houston Astros": 0.98,
    "New York Yankees": 0.98, "Minnesota Twins": 0.97,
    "Kansas City Royals": 0.97, "Chicago White Sox": 0.97,
    "San Francisco Giants": 0.96, "Cleveland Guardians": 0.96,
    "Detroit Tigers": 0.96, "St. Louis Cardinals": 0.96,
    "Pittsburgh Pirates": 0.95, "San Diego Padres": 0.95,
    "Tampa Bay Rays": 0.95, "Los Angeles Dodgers": 0.95,
    "Seattle Mariners": 0.94, "New York Mets": 0.94,
    "Washington Nationals": 0.94, "Oakland Athletics": 0.93,
    "Baltimore Orioles": 0.97, "Texas Rangers": 1.01,
    "Miami Marlins": 0.93,
}


async def compute_game_score(
    home_team: str,
    away_team: str,
    game_date: str,
    reds_injuries: Optional[List[Dict]] = None,
    opponent_injuries_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute composite 0-100 score for Reds' chances."""
    is_reds_home = "reds" in home_team.lower() or "cincinnati" in home_team.lower()
    opponent = away_team if is_reds_home else home_team

    # Fetch advanced stats for both teams
    try:
        from app.services.advanced_stats_service import get_matchup_stats
        matchup = await get_matchup_stats("Cincinnati Reds", opponent)
        reds_stats = matchup.get("reds_season") or {}
        opp_stats = matchup.get("opp_season") or {}
    except Exception:
        reds_stats = {}
        opp_stats = {}

    # Factor 1: Pitching advantage (35 pts max)
    reds_era = float(reds_stats.get("era") or 4.5)
    opp_era = float(opp_stats.get("era") or 4.5)
    era_diff = opp_era - reds_era  # positive = Reds pitching better
    pitching_score = min(35, max(0, 17.5 + era_diff * 3.5))
    pitching_detail = f"ERA: Reds {reds_era:.2f} vs {opponent} {opp_era:.2f} (diff {era_diff:+.2f})"

    # Factor 2: Batting strength (25 pts max)
    reds_ops = float(reds_stats.get("ops") or .700)
    opp_ops = float(opp_stats.get("ops") or .700)
    ops_diff = reds_ops - opp_ops
    batting_score = min(25, max(0, 12.5 + ops_diff * 50))
    batting_detail = f"OPS: Reds {reds_ops:.3f} vs {opponent} {opp_ops:.3f} (diff {ops_diff:+.3f})"

    # Factor 3: Bullpen (15 pts max)
    reds_whip = float(reds_stats.get("whip") or 1.30)
    opp_whip = float(opp_stats.get("whip") or 1.30)
    whip_diff = opp_whip - reds_whip  # positive = Reds bullpen better
    bullpen_score = min(15, max(0, 7.5 + whip_diff * 10))
    bullpen_detail = f"WHIP: Reds {reds_whip:.2f} vs {opponent} {opp_whip:.2f}"

    # Factor 4: Home/Away + park (15 pts max)
    park = PARK_FACTORS.get(home_team, 1.0)
    if is_reds_home:
        home_score = 10.0 + (park - 1.0) * 50  # GABP bonus
    else:
        home_score = 5.0 - (park - 1.0) * 25  # Opponent park impact
    home_score = min(15, max(0, home_score))
    home_detail = f"{'Home (GABP)' if is_reds_home else f'Away ({home_team})'} | Park factor: {park:.2f}"

    # Factor 5: Schedule (10 pts max) — neutral default
    schedule_score = 5.0
    schedule_detail = "Schedule: neutral"

    # Composite
    composite = round(pitching_score + batting_score + bullpen_score + home_score + schedule_score, 1)

    if composite >= 65:
        lean = "Reds"
        confidence = "High" if composite >= 75 else "Moderate"
    elif composite <= 35:
        lean = "Opponent"
        confidence = "High" if composite <= 25 else "Moderate"
    else:
        lean = "Close matchup"
        confidence = "Low"

    factors = {
        "pitching": {"score": round(pitching_score, 1), "max": 35, "detail": pitching_detail},
        "batting": {"score": round(batting_score, 1), "max": 25, "detail": batting_detail},
        "bullpen": {"score": round(bullpen_score, 1), "max": 15, "detail": bullpen_detail},
        "home_park": {"score": round(home_score, 1), "max": 15, "detail": home_detail},
        "schedule": {"score": round(schedule_score, 1), "max": 10, "detail": schedule_detail},
    }

    scoring_block = _build_scoring_block(composite, lean, confidence, factors)

    return {
        "composite_score": composite,
        "lean": lean,
        "confidence": confidence,
        "factors": factors,
        "scoring_block": scoring_block,
    }


def _build_scoring_block(composite, lean, confidence, factors):
    lines = [
        "=== REDSHUB COMPOSITE GAME SCORE ===",
        f"Score: {composite}/100 | Lean: {lean} | Confidence: {confidence}",
        "",
        "Factor Breakdown:",
    ]
    for name, data in factors.items():
        label = name.replace("_", " ").title()
        lines.append(f"  [{label}] {data['score']}/{data['max']} — {data['detail']}")
    lines += [
        "",
        "Instructions: Reference this score when framing confidence. Lead with the strongest factor.",
        "=== END COMPOSITE SCORE ===",
    ]
    return "\n".join(lines)
