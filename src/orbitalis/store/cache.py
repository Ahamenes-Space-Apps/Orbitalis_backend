"""TAP and overlay cache repositories.

Purpose: TTL-checked key/value caches for TAP responses and overlays
(SDD §7.4 ``tap_cache`` / ``overlay_cache``).
Inputs: ``Database`` handle, cache key, JSON payload, ttl seconds.
Outputs: Decoded payloads or ``None`` on miss/expiry.
Called by: gateway (TAP), overlays module.
"""

from __future__ import annotations

import json
import time
from typing import Any

from orbitalis.store.db import Database

_TABLES = ("tap_cache", "overlay_cache")


async def cache_put(db: Database, table: str, key: str, payload: Any, *, ttl_s: int) -> None:
    if table not in _TABLES:
        raise ValueError(f"unknown cache table {table!r}")
    async with db.write_tx() as conn:
        await conn.execute(
            f"INSERT INTO {table} (key, payload_json, fetched_at, ttl_s) "
            "VALUES (?,?,datetime('now'),?) "
            "ON CONFLICT(key) DO UPDATE SET payload_json=excluded.payload_json, "
            "fetched_at=excluded.fetched_at, ttl_s=excluded.ttl_s",
            (key, json.dumps(payload, sort_keys=True), ttl_s),
        )


async def cache_get(db: Database, table: str, key: str) -> Any | None:
    """Return the payload if present and unexpired, else ``None``."""
    if table not in _TABLES:
        raise ValueError(f"unknown cache table {table!r}")
    conn = await db.read()
    try:
        cur = await conn.execute(
            f"SELECT payload_json, fetched_at, ttl_s FROM {table} WHERE key=?", (key,)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        payload_json, fetched_at, ttl_s = row
        age = time.time() - _parse_sqlite_time(fetched_at)
        if age > ttl_s:
            return None
        return json.loads(payload_json)
    finally:
        await conn.close()


def _parse_sqlite_time(stamp: str) -> float:
    from datetime import UTC, datetime

    return datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC).timestamp()


__all__ = ["cache_get", "cache_put"]
