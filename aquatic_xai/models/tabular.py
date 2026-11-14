"""Tier-0/1 tabular models with a common interface. Fitted on training rows only."""
from __future__ import annotations

import numpy as np


def feature_columns(specs: list[dict], aware: bool) -> list[str]:
    """Quality-blind = history + rolling + time. Quality-aware adds the quality group; nothing else differs."""
    groups = {"history", "rolling", "time"} | ({"quality"} if aware else set())
    return [s["name"] for s in specs if s["group"] in groups]


def make_model(algo: str, params: dict, seed: int):
    if algo == "ridge":
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        # imputation medians and scaling are fitted on the training rows only (they are part of the pipeline)
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=params["alpha"]))
    if algo == "lightgbm":
        import lightgbm as lgb
        return lgb.LGBMRegressor(**params, random_state=seed, n_jobs=2, verbose=-1)
    if algo == "xgboost":
        import xgboost as xgb
        return xgb.XGBRegressor(**params, random_state=seed, n_jobs=2)
    raise ValueError(algo)


def fit_predict(algo: str, params: dict, seed: int, X_train: np.ndarray, y_train: np.ndarray, X_eval: np.ndarray) -> np.ndarray:
    m = make_model(algo, params, seed)
    m.fit(X_train, y_train)
    return np.asarray(m.predict(X_eval), dtype=float)


def fit_predict_proba(params: dict, seed: int, X_train: np.ndarray, y_train: np.ndarray, X_eval: np.ndarray) -> np.ndarray:
    """LightGBM classifier with the same fixed settings as the regressors; returns P(event)."""
    import lightgbm as lgb
    m = lgb.LGBMClassifier(**params, random_state=seed, n_jobs=2, verbose=-1)
    m.fit(X_train, y_train.astype(int))
    return np.asarray(m.predict_proba(X_eval)[:, 1], dtype=float)
