"""
umpire_service.py — Fetch umpire assignments and tendencies.

Umpires with tight strike zones = more walks = more runs.
Umpires with wide zones = more strikeouts = fewer runs.
"""
import logging
from typing import Dict
import httpx

logger = logging.getLogger(__name__)

# Known umpire tendencies (from UmpireScorecards.com public data)
UMPIRE_TENDENCIES = {
    "angel hernandez": {"zone": "inconsistent", "over_rate": 52, "note": "Unpredictable zone, higher walk rates"},
    "cb bucknor": {"zone": "wide", "over_rate": 47, "note": "Wide zone, more K's, lean Under"},
    "joe west": {"zone": "wide", "over_rate": 46, "note": "Wide zone, pitcher-friendly"},
    "laz diaz": {"zone": "tight", "over_rate": 54, "note": "Tight zone, more walks/hits, lean Over"},
    "marvin hudson": {"zone": "average", "over_rate": 50, "note": "Neutral"},
    "ron kulpa": {"zone": "wide", "over_rate": 48, "note": "Pitcher-friendly zone"},
    "mark wegner": {"zone": "tight", "over_rate": 53, "note": "Hitter-friendly, higher scoring"},
    "dan bellino": {"zone": "average", "over_rate": 51, "note": "Slightly above average scoring"},
    "james hoye": {"zone": "average", "over_rate": 50, "note": "Neutral"},
    "pat hoberg": {"zone": "consistent", "over_rate": 49, "note": "Very accurate, neutral impact"},
}


async def get_umpire_context(game_date: str) -> str:
    """Try to get umpire assignment from ESPN."""
    try:
        ds = game_date.replace("-", "")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={ds}")
            data = resp.json()

        for ev in data.get("events", []):
            comp = ev["competitions"][0]
            teams = [c.get("team", {}).get("id") for c in comp.get("competitors", [])]
            if "17" in teams:  # Reds ESPN ID
                event_id = ev["id"]
                # Get umpire from summary
                async with httpx.AsyncClient(timeout=10) as client:
                    summary = await client.get(f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={event_id}")
                    sdata = summary.json()

                officials = sdata.get("gameInfo", {}).get("officials", [])
                if not officials:
                    return ""

                lines = ["=== UMPIRE CREW ==="]
                hp_ump = next((o for o in officials if "plate" in o.get("position", {}).get("displayName", "").lower()), None)
                if hp_ump:
                    name = hp_ump.get("displayName", "")
                    lines.append(f"Home Plate: {name}")
                    tendency = UMPIRE_TENDENCIES.get(name.lower())
                    if tendency:
                        lines.append(f"  Zone: {tendency['zone']} | Over rate: {tendency['over_rate']}% | {tendency['note']}")

                for o in officials:
                    if o != hp_ump:
                        lines.append(f"  {o.get('position', {}).get('displayName', '?')}: {o.get('displayName', '?')}")

                lines.append("=== END UMPIRE CREW ===")
                return "\n".join(lines)
        return ""
    except Exception as e:
        logger.debug(f"Umpire fetch failed: {e}")
        return ""
