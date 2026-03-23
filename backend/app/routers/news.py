# routers/news.py
from fastapi import APIRouter, Query
from typing import List, Optional
from app.models.schemas import NewsItem
from app.services.news_service import fetch_all_news

router = APIRouter()

@router.get("/", response_model=List[NewsItem])
async def get_news(source: Optional[str] = Query(None), limit: int = Query(20, le=100)):
    return await fetch_all_news(source=source, limit=limit)
