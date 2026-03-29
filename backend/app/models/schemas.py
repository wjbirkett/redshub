from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class NewsItem(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None


class InjuryReport(BaseModel):
    player_id: int
    player_name: str
    team: str = "Cincinnati Reds"
    status: str
    reason: str
    updated_at: datetime


class BettingLine(BaseModel):
    game_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker: str
    spread: Optional[float] = None          # run line (usually ±1.5)
    moneyline_home: Optional[int] = None
    moneyline_away: Optional[int] = None
    over_under: Optional[float] = None


class Game(BaseModel):
    game_id: int
    game_date: date
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    arena: Optional[str] = None             # ballpark name
    broadcast: Optional[str] = None
    game_datetime: Optional[str] = None     # full ISO UTC string from ESPN


class TeamStanding(BaseModel):
    team_name: str
    conference: str                          # "NL" or "AL"
    division: str                            # "Central", "East", "West"
    wins: int
    losses: int
    win_pct: float
    games_back: float
    conference_rank: int                     # division rank


class PlayerStat(BaseModel):
    player_id: int
    player_name: str
    position: Optional[str] = None
    games_played: int
    # Batting
    avg: Optional[float] = None
    home_runs: Optional[int] = None
    rbi: Optional[int] = None
    ops: Optional[float] = None
    stolen_bases: Optional[int] = None
    at_bats: Optional[int] = None
    # Pitching
    era: Optional[float] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    strikeouts: Optional[int] = None
    whip: Optional[float] = None
    innings_pitched: Optional[float] = None
    saves: Optional[int] = None


class Tweet(BaseModel):
    tweet_id: str
    author_handle: str
    author_name: str
    text: str
    created_at: datetime
    url: str
    likes: int = 0
    retweets: int = 0


class PlayerBirthday(BaseModel):
    player_name: str
    birth_date: date
    age: int
    is_current_roster: bool
    position: Optional[str] = None
    notable: bool = False
