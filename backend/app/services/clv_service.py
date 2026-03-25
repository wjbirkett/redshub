"""
clv_service.py — Closing Line Value tracking and Kelly Criterion bet sizing.

CLV = whether your bet beats the closing line. Positive CLV = long-term profit.
Kelly Criterion = optimal bet sizing based on edge vs implied odds.
"""
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# In-memory store: game_date -> {opening_spread, opening_ou, closing_spread, closing_ou, bet_spread, bet_ou}
_line_history: Dict[str, Dict] = {}


def store_opening_line(game_date: str, spread: float, over_under: float):
    """Store the first line we see (opening line)."""
    if game_date not in _line_history:
        _line_history[game_date] = {
            "opening_spread": spread,
            "opening_ou": over_under,
            "bet_spread": spread,  # Assume we bet at opening
            "bet_ou": over_under,
        }


def store_closing_line(game_date: str, spread: float, over_under: float):
    """Store the last line before game time (closing line)."""
    if game_date in _line_history:
        _line_history[game_date]["closing_spread"] = spread
        _line_history[game_date]["closing_ou"] = over_under
    else:
        _line_history[game_date] = {
            "closing_spread": spread,
            "closing_ou": over_under,
        }


def get_clv(game_date: str) -> Dict[str, Any]:
    """Calculate CLV for a game."""
    entry = _line_history.get(game_date, {})
    if not entry:
        return {}

    result = {}
    bet_spread = entry.get("bet_spread")
    close_spread = entry.get("closing_spread")
    bet_ou = entry.get("bet_ou")
    close_ou = entry.get("closing_ou")

    if bet_spread is not None and close_spread is not None:
        # Positive CLV = line moved in our favor after we bet
        spread_clv = close_spread - bet_spread
        result["spread_clv"] = round(spread_clv, 1)
        result["spread_beat_close"] = spread_clv > 0

    if bet_ou is not None and close_ou is not None:
        ou_clv = close_ou - bet_ou
        result["ou_clv"] = round(ou_clv, 1)

    return result


def format_clv_summary(line_history: Dict) -> str:
    """Format CLV summary for dashboard/prompt."""
    if not line_history:
        return ""

    games_with_clv = [v for v in line_history.values() if "closing_spread" in v and "bet_spread" in v]
    if not games_with_clv:
        return ""

    beat_count = sum(1 for g in games_with_clv if (g.get("closing_spread", 0) - g.get("bet_spread", 0)) > 0)
    total = len(games_with_clv)
    avg_clv = sum(g.get("closing_spread", 0) - g.get("bet_spread", 0) for g in games_with_clv) / total

    return (
        f"CLV Summary: {beat_count}/{total} bets beat closing line ({round(beat_count/total*100)}%), "
        f"Avg CLV: {avg_clv:+.1f} pts"
    )


def kelly_criterion(
    model_prob: float,
    implied_prob: float,
    odds: float = -110,
    fraction: float = 0.25,
    max_bet: float = 0.05,
) -> Dict[str, Any]:
    """
    Calculate Kelly Criterion bet size.

    Args:
        model_prob: Our model's probability (0-1)
        implied_prob: Sportsbook implied probability (0-1)
        odds: American odds (e.g., -110)
        fraction: Kelly fraction (0.25 = quarter Kelly, safer)
        max_bet: Maximum fraction of bankroll to risk

    Returns:
        dict with edge, kelly_fraction, recommended_units, confidence_tier
    """
    edge = model_prob - implied_prob

    if edge <= 0:
        return {
            "edge": round(edge * 100, 1),
            "kelly_fraction": 0,
            "recommended_units": 0,
            "confidence_tier": "NO BET",
            "reason": "No edge — model agrees with or is worse than the book",
        }

    # Convert American odds to decimal
    if odds < 0:
        decimal_odds = 1 + (100 / abs(odds))
    else:
        decimal_odds = 1 + (odds / 100)

    # Kelly formula: f = (bp - q) / b
    # where b = decimal_odds - 1, p = model_prob, q = 1 - model_prob
    b = decimal_odds - 1
    kelly = (b * model_prob - (1 - model_prob)) / b

    # Apply fractional Kelly for safety
    adjusted_kelly = kelly * fraction
    bet_fraction = min(max(adjusted_kelly, 0), max_bet)

    # Convert to units (assuming 1 unit = 1% of bankroll)
    units = round(bet_fraction * 100, 1)

    # Confidence tiers
    if edge >= 0.08:
        tier = "STRONG"
        units = max(units, 2.0)
    elif edge >= 0.04:
        tier = "MODERATE"
        units = max(units, 1.0)
    elif edge >= 0.02:
        tier = "LEAN"
        units = min(units, 1.0)
    else:
        tier = "SMALL"
        units = min(units, 0.5)

    return {
        "edge": round(edge * 100, 1),
        "kelly_fraction": round(kelly, 4),
        "recommended_units": units,
        "confidence_tier": tier,
        "reason": f"{round(edge*100, 1)}% edge, {tier} confidence → {units}u bet",
    }


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    else:
        return 100 / (odds + 100)


def format_kelly_block(
    spread_prob: Optional[float] = None,
    total_prob: Optional[float] = None,
    spread_odds: int = -110,
    total_odds: int = -110,
) -> str:
    """Format Kelly sizing recommendations as a prompt block."""
    lines = ["=== BET SIZING (Kelly Criterion) ==="]

    if spread_prob is not None:
        implied = american_to_implied_prob(spread_odds)
        kelly = kelly_criterion(spread_prob / 100, implied, spread_odds)
        lines.append(f"Spread: {kelly['reason']}")

    if total_prob is not None:
        implied = american_to_implied_prob(total_odds)
        kelly = kelly_criterion(total_prob / 100, implied, total_odds)
        lines.append(f"Total: {kelly['reason']}")

    lines.append("")
    lines.append("Use these tiers for unit sizing:")
    lines.append("  STRONG (8%+ edge): 2-3u | MODERATE (4-8%): 1-2u | LEAN (2-4%): 0.5-1u | NO BET (<2%): pass")
    lines.append("=== END BET SIZING ===")
    return "\n".join(lines)
