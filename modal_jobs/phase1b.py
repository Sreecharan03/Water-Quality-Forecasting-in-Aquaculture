"""Phase 1b: inspect the AquaSustain-Bench release on Modal (nothing is persisted; only a description is printed).

    modal run -m modal_jobs.phase1b::inspect_aquasustain
"""
from __future__ import annotations

import hashlib
import io
import re
import urllib.request
import zipfile

from modal_jobs.common import app, image

URL = "https://zenodo.org/api/records/21249767/files/AquaSustain-Bench-UPLOAD-THIS.zip/content"
EXPECTED_MD5 = "711d0b43e57bcc805952e5881fa3bbc4"
KEYWORDS = re.compile(r"synthetic|simulat|placeholder|real|commercial|sensitive|not included|provenance|generated|field", re.I)


@app.function(image=image, timeout=600)
def inspect_aquasustain() -> str:
    import numpy as np
    import pandas as pd
    L = []
    raw = urllib.request.urlopen(URL, timeout=120).read()
    md5 = hashlib.md5(raw).hexdigest()
    L += [f"downloaded {len(raw)} bytes; md5 {md5}; matches published: {md5 == EXPECTED_MD5}"]
    z = zipfile.ZipFile(io.BytesIO(raw))
    infos = z.infolist()
    total = sum(i.file_size for i in infos)
    L += [f"files in zip: {len(infos)}; total uncompressed {total/1e6:.2f} MB", "", "## file list (size bytes)"]
    for i in sorted(infos, key=lambda x: -x.file_size)[:60]:
        L.append(f"- {i.filename} ({i.file_size})")
    L += ["", "## provenance statements found in text files (lines matching synthetic/real/placeholder/etc., first 40)"]
    n = 0
    for i in infos:
        if i.filename.lower().endswith((".md", ".txt", ".cff", ".json")) and i.file_size < 400_000:
            for ln, line in enumerate(z.read(i).decode("utf-8", "replace").splitlines(), 1):
                if KEYWORDS.search(line) and n < 40:
                    L.append(f"[{i.filename}:{ln}] {line.strip()[:220]}")
                    n += 1
    L += ["", "## tabular data files"]
    for i in infos:
        low = i.filename.lower()
        if low.endswith((".csv", ".parquet")) and i.file_size > 0:
            try:
                df = pd.read_csv(io.BytesIO(z.read(i))) if low.endswith(".csv") else pd.read_parquet(io.BytesIO(z.read(i)))
            except Exception as e:                                           # noqa: BLE001
                L.append(f"- {i.filename}: unreadable ({e})")
                continue
            L.append(f"- {i.filename}: {df.shape[0]} rows x {df.shape[1]} cols; columns {list(df.columns)[:14]}")
            tcols = [c for c in df.columns if "time" in c.lower() or "date" in c.lower()]
            if tcols:
                t = pd.to_datetime(df[tcols[0]], errors="coerce")
                L.append(f"    time range {t.min()} to {t.max()}; median step {t.sort_values().diff().median()}")
            for c in df.columns:
                if re.fullmatch(r"(DO_mg_L|pH|Temp_C)", str(c)):
                    s = pd.to_numeric(df[c], errors="coerce")
                    L.append(f"    {c}: n={s.notna().sum()}, mean={s.mean():.3f}, sd={s.std():.3f}, min={s.min():.2f}, max={s.max():.2f}, missing={s.isna().mean()*100:.1f}%")
    npys = [i for i in infos if i.filename.lower().endswith(".npy")]
    L += ["", f"## .npy files: {len(npys)}"] + [f"- {i.filename} ({i.file_size})" for i in npys[:15]]
    return "\n".join(L)


@app.local_entrypoint()
def run():
    print(inspect_aquasustain.remote())
