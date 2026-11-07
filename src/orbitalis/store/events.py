"""Event log repository (SSE replay support, SDD §7.4).

Purpose: Append-only per-stream events with a bounded tail for
``Last-Event-ID`` replay.
Inputs: ``Database`` handle, stream id (field_id or job_id), event type/data.
Outputs: Rows as dicts; next ``seq`` per stream.
Called by: pipeline progress events, job runner, api SSE endpoints.
"""

from __future__ import annotations

import json
from typing import Any

from orbitalis.store.db import Database

KEEP_LAST = 500  # events retained per stream


async def append_event(db: Database, stream_id: str, event_type: str, data: dict[str, Any]) -> int:
    """Append an event; returns its seq. Old events beyond KEEP_LAST are pruned."""
    async with db.write_tx() as conn:
        cur = await conn.execute(
            "SELECT COALESCE(MAX(seq),0)+1 FROM events WHERE stream_id=?", (stream_id,)
        )
        seq = (await cur.fetchone())[0]
        await conn.execute(
            "INSERT INTO events (stream_id, seq, type, data_json) VALUES (?,?,?,?)",
            (stream_id, seq, event_type, json.dumps(data, sort_keys=True)),
        )
        await conn.execute(
            "DELETE FROM events WHERE stream_id=? AND seq <= ?",
            (stream_id, seq - KEEP_LAST),
        )
    return seq


async def replay_events(
    db: Database, stream_id: str, *, after_seq: int = 0, limit: int = 500
) -> list[dict[str, Any]]:
    """Events with ``seq > after_seq`` in order — the Last-Event-ID slice."""
    conn = await db.read()
    try:
        cur = await conn.execute(
            "SELECT * FROM events WHERE stream_id=? AND seq>? ORDER BY seq LIMIT ?",
            (stream_id, after_seq, limit),
        )
        cols = [d[0] for d in cur.description]
        out = []
        for r in await cur.fetchall():
            d = dict(zip(cols, r, strict=True))
            d["data"] = json.loads(d.pop("data_json"))
            out.append(d)
        return out
    finally:
        await conn.close()


__all__ = ["append_event", "replay_events"]
