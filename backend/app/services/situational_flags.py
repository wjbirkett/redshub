"""
situational_flags.py — MLB situational edges.

Day game after night game, altitude (Coors Field), weather, travel.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ALTITUDE_PARKS = {"Colorado Rockies"}  # Coors Field = major altitude impact
HITTER_FRIENDLY = {"Cincinnati Reds", "Colorado Rockies", "Boston Red Sox", "Philadelphia Phillies"}


async def get_situational_flags(
    home_team: str,
    away_team: str,
    game_date: str,
) -> str:
    flags = []

    is_reds_home = "reds" in home_team.lower() or "cincinnati" in home_team.lower()
    opponent = away_team if is_reds_home else home_team

    # Coors Field altitude
    if not is_reds_home and home_team in ALTITUDE_PARKS:
        flags.append("COORS FIELD: Extreme hitter-friendly park — inflate all run totals +2-3 runs, lean Over heavily")

    # GABP hitter-friendly
    if is_reds_home:
        flags.append("GREAT AMERICAN BALL PARK: Hitter-friendly (park factor 1.08) — slight Over lean")

    # Hitter-friendly opponent park
    if not is_reds_home and home_team in HITTER_FRIENDLY:
        flags.append(f"HITTER PARK: {home_team}'s park favors hitters — adjust run totals up")

    if not flags:
        return ""

    lines = ["=== SITUATIONAL FLAGS ==="]
    for f in flags:
        lines.append(f"  {f}")
    lines.append("=== END SITUATIONAL FLAGS ===")
    return "\n".join(lines)
