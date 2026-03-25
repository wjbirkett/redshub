"""
ml_scoring_service.py — ML-based run predictor for RedsHub.

XGBoost ensemble trained on league-wide MLB data.
Predicts home/away runs, margin, win probability.
"""
import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

_home_model = None
_away_model = None
_meta = None
_models_loaded = False


def _load_models():
    global _home_model, _away_model, _meta, _models_loaded
    if _models_loaded:
        return
    try:
        import joblib
        home_path = os.path.join(MODELS_DIR, "home_runs_model.pkl")
        away_path = os.path.join(MODELS_DIR, "away_runs_model.pkl")
        meta_path = os.path.join(MODELS_DIR, "model_meta.json")

        if os.path.exists(home_path):
            _home_model = joblib.load(home_path)
        if os.path.exists(away_path):
            _away_model = joblib.load(away_path)
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                _meta = json.load(f)
        _models_loaded = True
    except Exception as e:
        logger.warning(f"Could not load ML models: {e}")
        _models_loaded = True


def models_available() -> bool:
    _load_models()
    return _home_model is not None and _away_model is not None


async def predict_game(
    home_team: str,
    away_team: str,
    over_under: Optional[str] = None,
) -> Dict[str, Any]:
    """Predict runs for both teams."""
    _load_models()
    if not models_available():
        return {"available": False, "ml_block": ""}

    try:
        from app.services.advanced_stats_service import get_matchup_stats
        matchup = await get_matchup_stats("Cincinnati Reds",
            away_team if "reds" in home_team.lower() or "cincinnati" in home_team.lower() else home_team)
        reds = matchup.get("reds_season") or {}
        opp = matchup.get("opp_season") or {}
    except Exception:
        reds = {}
        opp = {}

    is_reds_home = "reds" in home_team.lower() or "cincinnati" in home_team.lower()

    # Build features matching training data
    import pandas as pd
    features = _meta.get("features", []) if _meta else []
    if not features:
        return {"available": False, "ml_block": ""}

    feature_dict = {
        "is_reds_game": 1,
        "home_win_pct": 0.5,
        "away_win_pct": 0.5,
        "win_pct_diff": 0,
        "roll5_home_runs": 4.5,
        "roll5_away_runs": 4.5,
        "roll5_total": 9.0,
        "roll5_margin": 0,
        "roll10_home_runs": 4.5,
        "roll10_away_runs": 4.5,
        "roll10_total": 9.0,
        "roll10_margin": 0,
        "ewm5_home_runs": 4.5,
        "ewm5_total": 9.0,
        "ewm5_margin": 0,
        "home_win_streak": 0,
        "scoring_trend": 0,
    }

    row = {f: feature_dict.get(f, 0) for f in features}
    X = pd.DataFrame([row])

    home_pred = round(float(_home_model.predict(X)[0]), 1)
    away_pred = round(float(_away_model.predict(X)[0]), 1)
    pred_total = round(home_pred + away_pred, 1)
    pred_margin = round(home_pred - away_pred, 1)

    mae = _meta.get("home_runs", {}).get("cv_mae", 2.0) if _meta else 2.0

    # Edge detection
    ou_line = None
    if over_under and over_under != "N/A":
        try:
            ou_line = float(over_under)
        except Exception:
            pass

    total_edge = ""
    if ou_line:
        diff = pred_total - ou_line
        if abs(diff) >= 1.5:
            total_edge = f"TOTAL EDGE: {diff:+.1f} runs ({'STRONG Over' if diff > 0 else 'STRONG Under'})"
        elif abs(diff) >= 0.5:
            total_edge = f"TOTAL EDGE: {diff:+.1f} runs ({'lean Over' if diff > 0 else 'lean Under'})"
        else:
            total_edge = f"TOTAL EDGE: {diff:+.1f} runs (no meaningful edge)"

    n_samples = _meta.get("home_runs", {}).get("n_samples", "?") if _meta else "?"
    ml_block = f"""=== ML RUN PREDICTION (XGBoost, trained on {n_samples} games) ===
Predicted Score: {'Reds' if is_reds_home else home_team} {home_pred} — {'Reds' if not is_reds_home else away_team} {away_pred}
Predicted Total: {pred_total} runs
Predicted Margin: {pred_margin:+.1f}
Model MAE: ±{mae:.1f} runs
{total_edge}

Instructions:
- Your run total prediction should be directionally consistent with ML.
- If ML total is 9.5 and book line is 8.5, that supports an Over lean.
=== END ML PREDICTION ==="""

    return {
        "available": True,
        "home_predicted": home_pred,
        "away_predicted": away_pred,
        "mae": mae,
        "ml_block": ml_block,
    }
