from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import news, injuries, betting, schedule, stats, tweets, birthdays, articles
from app.scheduler import start_scheduler, shutdown_scheduler

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="RedsHub API",
    description="Cincinnati Reds fan dashboard backend — MLB data, AI predictions, odds.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router,      prefix="/api/news",      tags=["News"])
app.include_router(injuries.router,  prefix="/api/injuries",  tags=["Injuries"])
app.include_router(betting.router,   prefix="/api/betting",   tags=["Betting"])
app.include_router(schedule.router,  prefix="/api/schedule",  tags=["Schedule"])
app.include_router(stats.router,     prefix="/api/stats",     tags=["Stats"])
app.include_router(tweets.router,    prefix="/api/tweets",    tags=["Tweets"])
app.include_router(birthdays.router, prefix="/api/birthdays", tags=["Birthdays"])
app.include_router(articles.router,  prefix="/api/articles",  tags=["Articles"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "RedsHub API"}
