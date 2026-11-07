"""Frame repository.

Purpose: CRUD for ``frames`` rows; ``array_blob`` is required (ST-09).
Inputs: ``Database`` handle plus frame metadata and blobs.
Outputs: Rows as dicts.
Called by: pipeline (frame ingest), research handlers, demo loader.
"""

from __future__ import annotations

import json
from typing import Any

from orbitalis.store.db import Database


async def put_frame(
    db: Database,
    field_id: str,
    frame_ref: str,
    *,
    array_blob: bytes,
    wavelength_um: float | None = None,
    mjd: float | None = None,
    detector: int | None = None,
    png_blob: bytes | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Insert or replace a frame. ``array_blob`` is mandatory (ST-09)."""
    if not array_blob:
        raise ValueError("frame requires a non-empty array_blob")
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO frames (field_id, frame_ref, wavelength_um, mjd, detector, "
            "png_blob, meta_json, array_blob) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(field_id, frame_ref) DO UPDATE SET "
            "wavelength_um=excluded.wavelength_um, mjd=excluded.mjd, "
            "detector=excluded.detector, png_blob=excluded.png_blob, "
            "meta_json=excluded.meta_json, array_blob=excluded.array_blob",
            (
                field_id,
                frame_ref,
                wavelength_um,
                mjd,
                detector,
                png_blob,
                json.dumps(meta, sort_keys=True) if meta is not None else None,
                array_blob,
            ),
        )


async def get_frame(db: Database, field_id: str, frame_ref: str) -> dict[str, Any] | None:
    conn = await db.read()
    try:
        cur = await conn.execute(
            "SELECT * FROM frames WHERE field_id=? AND frame_ref=?", (field_id, frame_ref)
        )
        row = await cur.fetchone()
        return _frame_row(row, [d[0] for d in cur.description]) if row else None
    finally:
        await conn.close()


async def list_frames(db: Database, field_id: str) -> list[dict[str, Any]]:
    conn = await db.read()
    try:
        cur = await conn.execute("SELECT * FROM frames WHERE field_id=? ORDER BY mjd", (field_id,))
        cols = [d[0] for d in cur.description]
        return [_frame_row(r, cols) for r in await cur.fetchall()]
    finally:
        await conn.close()


def _frame_row(row: tuple, cols: list[str]) -> dict[str, Any]:
    d = dict(zip(cols, row, strict=True))
    d["meta"] = json.loads(d.pop("meta_json")) if d.get("meta_json") else None
    return d


__all__ = ["get_frame", "list_frames", "put_frame"]
