"""Field repository.

Purpose: CRUD for the ``fields`` aggregate root and ``field_id`` hashing.
Inputs: ``Database`` handle plus plain dicts/values.
Outputs: Rows as dicts; ``make_field_id`` for deterministic ids.
Called by: pipeline, research handlers, demo loader, api services.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from orbitalis.store.db import Database

_FIELD_STATUSES = ("queued", "running", "completed", "failed", "cancelled")


def make_field_id(params: dict[str, Any]) -> str:
    """Deterministic field id: stable for any key order/whitespace (ST-08)."""
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return "f_" + hashlib.sha256(canonical.encode()).hexdigest()[:24]


async def upsert_field(
    db: Database,
    field_id: str,
    params: dict[str, Any],
    *,
    preset: bool = False,
) -> None:
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO fields (field_id, params_json, status, preset) "
            "VALUES (?, ?, 'queued', ?) "
            "ON CONFLICT(field_id) DO UPDATE SET params_json=excluded.params_json, "
            "preset=MAX(preset, excluded.preset), updated_at=datetime('now')",
            (field_id, json.dumps(params, sort_keys=True), int(preset)),
        )


async def get_field(db: Database, field_id: str) -> dict[str, Any] | None:
    conn = await db.read()
    try:
        cur = await conn.execute("SELECT * FROM fields WHERE field_id = ?", (field_id,))
        row = await cur.fetchone()
        if row is None:
            return None
        return _field_row(row, [d[0] for d in cur.description])
    finally:
        await conn.close()


async def list_fields(db: Database, *, preset_only: bool = False) -> list[dict[str, Any]]:
    conn = await db.read()
    try:
        sql = "SELECT * FROM fields" + (" WHERE preset = 1" if preset_only else "")
        cur = await conn.execute(sql + " ORDER BY created_at")
        cols = [d[0] for d in cur.description]
        return [_field_row(r, cols) for r in await cur.fetchall()]
    finally:
        await conn.close()


async def set_field_status(
    db: Database, field_id: str, status: str, *, error_code: str | None = None
) -> None:
    if status not in _FIELD_STATUSES:
        raise ValueError(f"invalid field status {status!r}")
    async with db.write_tx() as conn:
        await conn.execute(
            "UPDATE fields SET status=?, error_code=?, updated_at=datetime('now') WHERE field_id=?",
            (status, error_code, field_id),
        )


def _field_row(row: tuple, cols: list[str]) -> dict[str, Any]:
    d = dict(zip(cols, row, strict=True))
    d["params"] = json.loads(d.pop("params_json"))
    d["preset"] = bool(d["preset"])
    return d


__all__ = ["get_field", "list_fields", "make_field_id", "set_field_status", "upsert_field"]
