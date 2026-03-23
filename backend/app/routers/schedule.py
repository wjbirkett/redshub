from fastapi import APIRouter
from typing import List
from app.models.schemas import Game, TeamStanding
from app.services.mlb_service import fetch_schedule, fetch_standings

router = APIRouter()

@router.get("/games", response_model=List[Game])
async def get_schedule():
    return await fetch_schedule()

@router.get("/standings", response_model=List[TeamStanding])
async def get_standings():
    return await fetch_standings()
