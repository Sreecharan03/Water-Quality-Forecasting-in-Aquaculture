"""Source-to-Modal ingestion with provenance. Runs inside Modal containers only.

Files are fetched from an immutable commit SHA, verified against the git blob SHA
reported by GitHub, and stored write-once under raw/<source-id>/<commit-sha>/.
The manifest is written last; its existence marks the ingest as complete.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_UA = {"User-Agent": "aquatic-xai-ingest/0.1", "Accept": "application/vnd.github+json"}


def _get(url: str, retries: int = 3, timeout: int = 60) -> bytes:
    """GET with bounded retries on transient transport errors only."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500 and exc.code != 429:
                raise  # permanent (404, 403 ...): do not retry
            last = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} attempts: {url}: {last}")


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def resolve_commit(repo: str, ref: str) -> str:
    meta = json.loads(_get(f"https://api.github.com/repos/{repo}/commits/{ref}"))
    return meta["sha"]


def list_tree(repo: str, sha: str) -> list[dict]:
    tree = json.loads(_get(f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1"))
    if tree.get("truncated"):
        raise RuntimeError("GitHub tree listing truncated; cannot guarantee a complete inventory")
    return [e for e in tree["tree"] if e["type"] == "blob"]


def ingest_github(source_id: str, spec: dict, data_root: Path, force: bool = False) -> dict:
    """Download the selected files of a GitHub source. Returns the manifest dict."""
    repo = spec["repo"]
    sha = resolve_commit(repo, spec["ref"])
    raw_dir = data_root / "raw" / source_id / sha
    manifest_path = data_root / "manifests" / f"raw_{source_id}_{sha}.json"

    if manifest_path.exists() and not force:
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    prefixes = tuple(spec["include_prefixes"])
    entries = [e for e in list_tree(repo, sha) if e["path"].startswith(prefixes)]
    if not entries:
        raise RuntimeError("No files matched include_prefixes")

    files = []
    for e in sorted(entries, key=lambda x: x["path"]):
        url = f"https://raw.githubusercontent.com/{repo}/{sha}/{e['path']}"
        data = _get(url)
        if len(data) != e["size"] or git_blob_sha(data) != e["sha"]:
            raise RuntimeError(f"Integrity check failed for {e['path']}")
        dest = raw_dir / e["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        files.append({
            "path": e["path"],
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha": e["sha"],
            "url": url,
        })

    manifest = {
        "source_id": source_id,
        "repo": repo,
        "ref": spec["ref"],
        "commit_sha": sha,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "licence_state": spec["licence_state"],
        "citation": spec["citation"],
        "n_files": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.part")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(tmp, manifest_path)
    return manifest
