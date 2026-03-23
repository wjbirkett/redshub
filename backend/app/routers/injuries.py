from fastapi import APIRouter
from typing import List
from app.models.schemas import InjuryReport
from app.services.mlb_service import fetch_injury_report

router = APIRouter()

@router.get("/", response_model=List[InjuryReport])
async def get_injuries():
    return await fetch_injury_report()
