"""
collect_league_data.py — Build league-wide MLB training dataset.

Pulls all MLB games from recent seasons with team stats.
Uses MLB Stats API (free, no key).

Usage: cd backend && python -m app.services.collect_league_data
"""
import os
import time
import logging
import httpx
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
OUTPUT_CSV = os.path.join(MODELS_DIR, "league_training_data.csv")
MLB_API = "https://statsapi.mlb.com/api/v1"

SEASONS = [2023, 2024, 2025]
REDS_TEAM_ID = 113


def fetch_season_schedule(season: int) -> list:
    """Fetch all games for a season."""
    logger.info(f"Fetching {season} schedule...")
    url = f"{MLB_API}/schedule"
    params = {
        "sportId": 1,
        "season": str(season),
        "gameType": "R,P",  # Regular + Playoffs
        "hydrate": "linescore,team",
    }
    resp = httpx.get(url, params=params, timeout=30)
    data = resp.json()

    games = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            if game.get("status", {}).get("abstractGameState") != "Final":
                continue

            home = game.get("teams", {}).get("home", {})
            away = game.get("teams", {}).get("away", {})

            linescore = game.get("linescore", {})
            home_runs = linescore.get("teams", {}).get("home", {}).get("runs")
            away_runs = linescore.get("teams", {}).get("away", {}).get("runs")

            if home_runs is None or away_runs is None:
                # Try score from team data
                home_runs = home.get("score", 0)
                away_runs = away.get("score", 0)

            home_id = home.get("team", {}).get("id")
            away_id = away.get("team", {}).get("id")

            games.append({
                "game_id": game.get("gamePk"),
                "game_date": game.get("officialDate", game.get("gameDate", "")[:10]),
                "season": season,
                "game_type": game.get("gameType", "R"),
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_team": home.get("team", {}).get("name", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "home_runs": int(home_runs) if home_runs else 0,
                "away_runs": int(away_runs) if away_runs else 0,
                "home_won": int(int(home_runs or 0) > int(away_runs or 0)),
                "total_runs": int(home_runs or 0) + int(away_runs or 0),
                "margin": int(home_runs or 0) - int(away_runs or 0),
                "is_reds_game": int(home_id == REDS_TEAM_ID or away_id == REDS_TEAM_ID),
                "home_wins": home.get("leagueRecord", {}).get("wins", 0),
                "home_losses": home.get("leagueRecord", {}).get("losses", 0),
                "away_wins": away.get("leagueRecord", {}).get("wins", 0),
                "away_losses": away.get("leagueRecord", {}).get("losses", 0),
            })

    logger.info(f"  Got {len(games)} completed games for {season}")
    return games


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add rolling features."""
    df = df.sort_values("game_date").reset_index(drop=True)

    for window in [5, 10]:
        p = f"roll{window}"
        df[f"{p}_home_runs"] = df["home_runs"].shift(1).rolling(window, min_periods=3).mean()
        df[f"{p}_away_runs"] = df["away_runs"].shift(1).rolling(window, min_periods=3).mean()
        df[f"{p}_total"] = df["total_runs"].shift(1).rolling(window, min_periods=3).mean()
        df[f"{p}_margin"] = df["margin"].shift(1).rolling(window, min_periods=3).mean()

    # EWM recency
    df["ewm5_home_runs"] = df["home_runs"].shift(1).ewm(span=5, min_periods=3).mean()
    df["ewm5_total"] = df["total_runs"].shift(1).ewm(span=5, min_periods=3).mean()
    df["ewm5_margin"] = df["margin"].shift(1).ewm(span=5, min_periods=3).mean()

    # Win streak
    streaks = []
    current = 0
    for won in df["home_won"]:
        streaks.append(current)
        current = current + 1 if won == 1 else 0
    df["home_win_streak"] = streaks

    # Scoring trend
    r5 = df["home_runs"].shift(1).rolling(5, min_periods=3).mean()
    r15 = df["home_runs"].shift(1).rolling(15, min_periods=8).mean()
    df["scoring_trend"] = r5 - r15

    # Win percentages
    df["home_win_pct"] = df["home_wins"] / (df["home_wins"] + df["home_losses"]).clip(lower=1)
    df["away_win_pct"] = df["away_wins"] / (df["away_wins"] + df["away_losses"]).clip(lower=1)
    df["win_pct_diff"] = df["home_win_pct"] - df["away_win_pct"]

    return df


def main():
    all_games = []
    for season in SEASONS:
        try:
            games = fetch_season_schedule(season)
            all_games.extend(games)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed {season}: {e}")

    if not all_games:
        logger.error("No data!")
        return

    df = pd.DataFrame(all_games)
    df = df.sort_values("game_date").reset_index(drop=True)
    df = add_rolling_features(df)

    os.makedirs(MODELS_DIR, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n{'='*50}")
    print(f"MLB DATA COLLECTION COMPLETE")
    print(f"{'='*50}")
    print(f"Total games: {len(df)}")
    print(f"Reds games: {df['is_reds_game'].sum()}")
    print(f"Columns: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
