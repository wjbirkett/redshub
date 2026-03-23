from fastapi import APIRouter
from typing import List
from app.models.schemas import BettingLine
from app.services.odds_service import fetch_reds_lines

router = APIRouter()

@router.get("/", response_model=List[BettingLine])
async def get_betting():
    return await fetch_reds_lines()
