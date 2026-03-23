from fastapi import APIRouter, Query
from typing import List
from app.models.schemas import PlayerBirthday
from app.services.birthday_service import fetch_upcoming_birthdays

router = APIRouter()

@router.get("/upcoming", response_model=List[PlayerBirthday])
async def get_upcoming_birthdays(days: int = Query(7, le=30)):
    return await fetch_upcoming_birthdays(days_ahead=days)
