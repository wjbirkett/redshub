"""
retrain_v2.py — Train MLB prediction models on league-wide data.

Usage: cd backend && python -m app.services.retrain_v2
"""
import os
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
import joblib

warnings.filterwarnings("ignore")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
CSV_PATH = os.path.join(MODELS_DIR, "league_training_data.csv")

FEATURES = [
    "is_reds_game",
    "home_win_pct", "away_win_pct", "win_pct_diff",
    "roll5_home_runs", "roll5_away_runs", "roll5_total", "roll5_margin",
    "roll10_home_runs", "roll10_away_runs", "roll10_total", "roll10_margin",
    "ewm5_home_runs", "ewm5_total", "ewm5_margin",
    "home_win_streak", "scoring_trend",
]


def main():
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found. Run collect_league_data.py first.")
        return

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} games")

    features = [f for f in FEATURES if f in df.columns]
    print(f"Using {len(features)} features")

    df_clean = df.dropna(subset=["home_runs", "away_runs"])
    X = df_clean[features].fillna(0)
    y_home = df_clean["home_runs"]
    y_away = df_clean["away_runs"]

    tscv = TimeSeriesSplit(n_splits=5)

    try:
        import xgboost as xgb
        HomeModel = lambda: xgb.XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42, verbosity=0)
    except ImportError:
        from sklearn.ensemble import GradientBoostingRegressor
        HomeModel = lambda: GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)

    # Home runs model
    print("\nTraining HOME RUNS model...")
    home_model = HomeModel()
    maes = []
    for train_idx, test_idx in tscv.split(X):
        home_model.fit(X.iloc[train_idx], y_home.iloc[train_idx])
        preds = home_model.predict(X.iloc[test_idx])
        maes.append(mean_absolute_error(y_home.iloc[test_idx], preds))
    home_mae = round(np.mean(maes), 2)
    home_model.fit(X, y_home)
    joblib.dump(home_model, os.path.join(MODELS_DIR, "home_runs_model.pkl"))
    print(f"  MAE: {home_mae} runs")

    # Away runs model
    print("Training AWAY RUNS model...")
    away_model = HomeModel()
    maes = []
    for train_idx, test_idx in tscv.split(X):
        away_model.fit(X.iloc[train_idx], y_away.iloc[train_idx])
        preds = away_model.predict(X.iloc[test_idx])
        maes.append(mean_absolute_error(y_away.iloc[test_idx], preds))
    away_mae = round(np.mean(maes), 2)
    away_model.fit(X, y_away)
    joblib.dump(away_model, os.path.join(MODELS_DIR, "away_runs_model.pkl"))
    print(f"  MAE: {away_mae} runs")

    meta = {
        "trained_at": datetime.utcnow().isoformat(),
        "features": features,
        "home_runs": {"cv_mae": home_mae, "n_samples": len(X)},
        "away_runs": {"cv_mae": away_mae, "n_samples": len(X)},
    }
    with open(os.path.join(MODELS_DIR, "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n{'='*50}")
    print(f"MLB MODELS TRAINED")
    print(f"{'='*50}")
    print(f"Samples: {len(X)}")
    print(f"Features: {len(features)}")
    print(f"Home runs MAE: {home_mae}")
    print(f"Away runs MAE: {away_mae}")


if __name__ == "__main__":
    main()
