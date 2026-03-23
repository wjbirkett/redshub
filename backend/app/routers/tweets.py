from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("/")
async def get_tweets():
    # Twitter API requires elevated access. Returns empty list if not configured.
    try:
        from app.services.twitter_service import fetch_reds_tweets
        return await fetch_reds_tweets()
    except Exception:
        return []
