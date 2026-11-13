"""Shared Modal wiring: app, pinned image, persistent volumes. No domain logic here."""
from __future__ import annotations

import os

import modal

DATA_VOLUME = os.environ.get("AQUATIC_DATA_VOLUME", "aquatic-xai-data")
ARTIFACT_VOLUME = os.environ.get("AQUATIC_ARTIFACT_VOLUME", "aquatic-xai-artifacts")
DATA_MOUNT = "/data"
ARTIFACT_MOUNT = "/artifacts"

app = modal.App(os.environ.get("AQUATIC_APP_NAME", "aquatic-xai-research"))

data_vol = modal.Volume.from_name(DATA_VOLUME, create_if_missing=True)
artifact_vol = modal.Volume.from_name(ARTIFACT_VOLUME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgomp1")                       # OpenMP runtime needed by LightGBM / XGBoost
    .pip_install("pandas==2.2.3", "numpy==2.1.3", "pyyaml==6.0.2", "pytest==8.3.4",
                 "pyarrow==18.1.0", "matplotlib==3.9.2", "scipy==1.14.1",
                 "scikit-learn==1.5.2", "lightgbm==4.5.0", "xgboost==2.1.3")
    .add_local_python_source("aquatic_xai", "modal_jobs", "tests")
    .add_local_dir("configs", "/root/configs")
)

VOLUMES = {DATA_MOUNT: data_vol, ARTIFACT_MOUNT: artifact_vol}
