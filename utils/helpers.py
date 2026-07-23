"""
Shared helper functions used across ingestion, parsing, and presentation.

Why this file exists on its own: these functions have no opinion about trip
data specifically — they're generic (safe nested-dict access, timestamp
formatting). Every layer needs them, so they live in `utils/`, not inside
`parsing/` or `presentation/`, to avoid a layer depending on another layer
just to borrow a tool.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def safe_get(d, *keys, default=None):
    """
    Walk a nested dict/list structure without blowing up on a missing key,
    wrong type, or out-of-range index.

    Why this matters here specifically: trip event JSON is inconsistent
    across service groups (RIDES vs FOOD_DELIVERY vs PARCEL don't all
    populate the same fields — see trip_info.md). Without this, every single
    field access in the app would need its own try/except.
    """
    for key in keys:
        if isinstance(d, list) and isinstance(key, int):
            if key < len(d):
                d = d[key]
            else:
                return default
        elif isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d


def format_timestamp(ts):
    """
    Convert a raw event timestamp (ms or sec since epoch) into a readable
    Sri Lanka local time string. Falls back to returning the raw value if
    it isn't a valid timestamp, so a bad timestamp doesn't crash the page.
    """
    try:
        if ts > 1e12:
            ts = ts / 1000
        utc_time = datetime.fromtimestamp(ts, timezone.utc)
        sl_time = utc_time.astimezone(ZoneInfo("Asia/Colombo"))
        return sl_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def ts_to_seconds(ts):
    """Normalize a timestamp to seconds, whether it arrived in ms or sec."""
    return ts / 1000 if ts and ts > 1e12 else ts


def seconds_diff(ts1, ts2):
    """Absolute difference between two timestamps, in seconds."""
    try:
        return int(abs(ts_to_seconds(ts1) - ts_to_seconds(ts2)))
    except Exception:
        return None
