"""Shared utilities for the build_*.py replay-processing scripts.

Consolidates duplicated patterns: archive download/caching, zstd tar
iteration, game filtering, card-family helpers, index builders, and
common output routines.
"""
import io
import json
import os
import tarfile
import urllib.request

import zstandard

BASE_URL = "https://huggingface.co/datasets/sharpobject/yxp_replays/resolve/main"
HERE = os.path.dirname(os.path.abspath(__file__))
REPLAYS = os.environ.get("REPLAYS_DIR") or r"D:\Coding\yxp_replays_analyze\replays"
CACHE = os.environ.get("DECK_CACHE") or os.path.join(
    os.environ.get("CLAUDE_JOB_DIR", HERE), "tmp")


# ---------------------------------------------------------------------------
# Card-family helpers
# ---------------------------------------------------------------------------

def fam(c):
    """Strip level digits so all levels of a card map to one family id."""
    return c - ((c // 10000) % 100) * 10000


def level_of(c):
    """Extract the 1-based level from a card id."""
    return (c // 10000) % 100 + 1


# ---------------------------------------------------------------------------
# Archive download / caching
# ---------------------------------------------------------------------------

def download(name):
    """Return a local path for the archive *name*, downloading if needed."""
    local = os.path.join(REPLAYS, name + ".tar.zst")
    if os.path.exists(local) and os.path.getsize(local) > 1_000_000:
        return local
    dst = os.path.join(CACHE, name + ".tar.zst")
    if os.path.exists(dst) and os.path.getsize(dst) > 1_000_000:
        return dst
    os.makedirs(CACHE, exist_ok=True)
    tmp = dst + ".part"
    urllib.request.urlretrieve(f"{BASE_URL}/{name}.tar.zst", tmp)
    os.replace(tmp, dst)
    return dst


def download_local_only(name):
    """Return a local path if the archive exists locally, else ``None``."""
    local = os.path.join(REPLAYS, name + ".tar.zst")
    if os.path.exists(local):
        return local
    return None


# ---------------------------------------------------------------------------
# Replay iteration
# ---------------------------------------------------------------------------

def iter_replays(path):
    """Yield each replay's ``data`` dict from a ``.tar.zst`` archive."""
    with open(path, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    tf = tarfile.open(fileobj=io.BytesIO(raw))
    for m in tf.getmembers():
        if not m.name.endswith(".json"):
            continue
        try:
            yield json.load(tf.extractfile(m))["data"]
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Side / win detection
# ---------------------------------------------------------------------------

def home_side(rd, uid):
    """Return ``'p1'`` or ``'p2'`` for the file-owner's side, or ``None``."""
    if rd["p2"]["publicData"]["uid"] == uid:
        return "p2"
    if rd["p1"]["publicData"]["uid"] == uid:
        return "p1"
    return None


# ---------------------------------------------------------------------------
# Build-config helpers
# ---------------------------------------------------------------------------

def build_archives(default_first, default_last, step=1000):
    """Read BUILD_FIRST / BUILD_LAST env overrides and return (first, last, archives)."""
    first = int(os.environ.get("BUILD_FIRST", default_first))
    last = int(os.environ.get("BUILD_LAST", default_last))
    archives = [f"{n}" for n in range(first, last + 1, step)]
    return first, last, archives


def build_env():
    """Return common env-var overrides: (version_filter, out_dir)."""
    version_filter = os.environ.get("VERSION_FILTER") or None
    out_dir = os.environ.get("OUT_DIR") or "data"
    return version_filter, out_dir


def season_index(seasons):
    """Return a {season_mec: index} mapping."""
    return {s: i for i, s in enumerate(seasons)}


# ---------------------------------------------------------------------------
# Game filtering
# ---------------------------------------------------------------------------

def is_valid_game(d, season_idx, version_filter, min_score):
    """Return True if the game passes the standard season/version/score filter."""
    if d.get("seasonMec") not in season_idx:
        return False
    if version_filter and d.get("version") != version_filter:
        return False
    if d.get("beginRankScore", 0) < min_score:
        return False
    if not (d.get("roundStats") or []):
        return False
    return True


# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------

class AutoIndex:
    """Auto-incrementing id-to-compact-index mapping."""

    def __init__(self):
        self._map = {}

    def __getitem__(self, key):
        i = self._map.get(key)
        if i is None:
            i = self._map[key] = len(self._map)
        return i

    def __contains__(self, key):
        return key in self._map

    def __len__(self):
        return len(self._map)

    @property
    def mapping(self):
        return dict(self._map)

    def inverted(self):
        """Return {index: key} dict."""
        return {i: k for k, i in self._map.items()}

    def ordered_keys(self):
        """Return keys sorted by their compact index."""
        inv = self.inverted()
        return [inv[i] for i in sorted(inv)]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_json(path, obj, separators=(",", ":"), indent=None):
    """Write *obj* as JSON, creating parent dirs as needed. Return file size."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=separators, indent=indent)
    return os.path.getsize(path)


def accumulate(vec, win, hi):
    """Accumulate a win/game count into a [w, g, w6, g6] vector."""
    vec[0] += win
    vec[1] += 1
    if hi:
        vec[2] += win
        vec[3] += 1
