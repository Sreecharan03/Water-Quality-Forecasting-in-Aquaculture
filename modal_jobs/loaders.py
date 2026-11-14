"""Shared table loaders for Modal jobs (plain module: registers nothing on the app)."""
from __future__ import annotations

import json
from pathlib import Path

from modal_jobs.common import DATA_MOUNT, data_vol

_CACHE: dict = {}
EXT = "external/bco-988873"


def yaml_cfg(name: str) -> dict:
    import yaml
    return yaml.safe_load(Path("/root/configs", name).read_text(encoding="utf-8"))


def latest(glob: str, key: str) -> str:
    mans = sorted(Path(DATA_MOUNT, "manifests").glob(glob), key=lambda p: p.stat().st_mtime)
    return json.loads(mans[-1].read_text(encoding="utf-8"))[key]


def versions(ds: str) -> tuple[str, str]:
    data_vol.reload()
    if ds == "eluru":
        return latest("splits_sp-*.json", "split_version"), latest("features_ft-*.json", "feature_version")
    return latest("bco_splits_*.json", "split_version"), latest("bco_features_*.json", "feature_version")


def feature_cfg(ds: str) -> dict:
    if ds == "eluru":
        return yaml_cfg("features.yaml")["features"]
    c = yaml_cfg("replication_bco.yaml")
    return {"variables": ["DO", "pH", "Temp"], **c["grid"]["features"], "horizons": c["grid"]["horizons_steps"]}


def day_steps(ds: str) -> int:
    return 96 if ds == "eluru" else yaml_cfg("replication_bco.yaml")["grid"]["steps_per_day"]


def load(ds: str, sv: str, fv: str, alerts: bool = False):
    """Feature table + split assignments + daily-pattern features (+ alert labels for Eluru). Returns (T, info, cv_folds)."""
    import pandas as pd
    from aquatic_xai.alerts.labels import add_alert_columns
    from aquatic_xai.features.daily import daily_features
    key = (ds, sv, fv, alerts)
    if key not in _CACHE:
        data_vol.reload()
        if ds == "eluru":
            fdir, sdir, mpath = Path(DATA_MOUNT, "features", fv), Path(DATA_MOUNT, "splits", sv), Path(DATA_MOUNT, "manifests", f"splits_{sv}.json")
        else:
            fdir, sdir, mpath = Path(DATA_MOUNT, EXT, "features", fv), Path(DATA_MOUNT, EXT, "splits", sv), Path(DATA_MOUNT, "manifests", f"bco_splits_{sv}.json")
        feats = pd.concat([pd.read_parquet(f) for f in sorted(fdir.glob("*.parquet"))], ignore_index=True)
        a = pd.read_parquet(sdir / "assignments.parquet")
        T = feats.merge(a[["pond", "grid_idx", "window", "role", "fold", "block_day"]], on=["pond", "grid_idx"], how="inner", validate="one_to_one")
        assert len(T) == len(feats) == len(a)
        fc = feature_cfg(ds)
        parts = [daily_features(g, fc["horizons"], day=day_steps(ds)) for _, g in T.groupby("pond", sort=False)]
        T = pd.concat([T, pd.concat(parts).loc[T.index]], axis=1)
        if alerts:
            T = add_alert_columns(T, {"a": 4, "b": 12, "c": 24}, 2.0, day_steps(ds))
        man = json.loads(mpath.read_text(encoding="utf-8"))
        _CACHE[key] = (T, man["info"], man["config"]["cv_folds"])
    return _CACHE[key]
