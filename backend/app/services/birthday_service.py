import logging
from datetime import date, datetime
from typing import List
from app.models.schemas import PlayerBirthday
from app.services.mlb_service import fetch_roster

logger = logging.getLogger(__name__)


async def fetch_upcoming_birthdays(days_ahead: int = 7) -> List[PlayerBirthday]:
    try:
        roster = await fetch_roster()
    except Exception as e:
        logger.warning(f"Roster fetch failed for birthdays: {e}")
        return []
    today  = date.today()
    bdays  = []

    for player in roster:
        raw = player.get("BIRTH_DATE", "")
        if not raw:
            continue
        try:
            bd = datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except:
            continue

        this_year_bday = bd.replace(year=today.year)
        if this_year_bday < today:
            this_year_bday = bd.replace(year=today.year + 1)

        delta = (this_year_bday - today).days
        if 0 <= delta <= days_ahead:
            age = today.year - bd.year - (
                (today.month, today.day) < (bd.month, bd.day)
            )
            bdays.append(PlayerBirthday(
                player_name=player.get("PLAYER", ""),
                birth_date=bd,
                age=age,
                is_current_roster=True,
                position=player.get("POSITION"),
                notable=False,
            ))

    bdays.sort(key=lambda b: (b.birth_date.month, b.birth_date.day))
    return bdays
