from fastapi import APIRouter
from typing import List
from app.models.schemas import PlayerStat
from app.services.mlb_service import fetch_player_stats

router = APIRouter()

@router.get("/", response_model=List[PlayerStat])
async def get_stats():
    return await fetch_player_stats()
