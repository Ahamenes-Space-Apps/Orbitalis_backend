"""Cutout repository and eviction.

Purpose: CRUD for ``cutouts`` (native-grid FITS cutouts, size-capped LRU).
Inputs: ``Database`` handle plus blob bytes.
Outputs: Rows as dicts.
Called by: gateway cutout cache, pipeline, api frame PNGs.
"""

from __future__ import annotations

from orbitalis.store.db import Database


async def put_cutout(db: Database, cutout_key: str, fits_blob: bytes) -> None:
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO cutouts (cutout_key, fits_blob, bytes) VALUES (?,?,?) "
            "ON CONFLICT(cutout_key) DO UPDATE SET fits_blob=excluded.fits_blob, "
            "bytes=excluded.bytes, fetched_at=datetime('now')",
            (cutout_key, fits_blob, len(fits_blob)),
        )


async def get_cutout(db: Database, cutout_key: str) -> bytes | None:
    conn = await db.read()
    try:
        cur = await conn.execute("SELECT fits_blob FROM cutouts WHERE cutout_key=?", (cutout_key,))
        row = await cur.fetchone()
        return row[0] if row else None
    finally:
        await conn.close()


async def cutout_size_bytes(db: Database) -> int:
    conn = await db.read()
    try:
        cur = await conn.execute("SELECT COALESCE(SUM(bytes),0) FROM cutouts")
        return (await cur.fetchone())[0]
    finally:
        await conn.close()


__all__ = ["cutout_size_bytes", "get_cutout", "put_cutout"]
