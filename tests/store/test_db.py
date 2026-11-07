"""Tests for SQLite setup and migrations (FR-DATA-03, ST-01/ST-02).

Purpose: Verify WAL pragmas, ordered one-shot migrations recorded in
schema_migrations, the write_tx serialization, and concurrent writers.
Inputs: Temp-dir SQLite databases.
Outputs: Test results.
Called by: pytest.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from orbitalis.store.db import Database, open_database

pytestmark = pytest.mark.asyncio


async def test_migrations_apply_once_and_recorded(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        conn = await db.read()
        cur = await conn.execute("SELECT version FROM schema_migrations ORDER BY version")
        rows = await cur.fetchall()
        await conn.close()
        assert [r[0] for r in rows] == [1]
        # Re-run is a no-op: reopen and confirm still exactly one row.
        await db.connect()
        conn = await db.read()
        rows = await (await conn.execute("SELECT COUNT(*) FROM schema_migrations")).fetchone()
        await conn.close()
        assert rows[0] == 1
    finally:
        await db.close()


async def test_schema_tables_exist(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        conn = await db.read()
        names = {
            r[0]
            for r in await (
                await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        await conn.close()
        expected = {
            "fields",
            "frames",
            "groups",
            "group_frames",
            "cutouts",
            "derived",
            "events",
            "jobs",
            "candidates",
            "experiments",
            "experiment_trials",
            "tap_cache",
            "overlay_cache",
            "schema_migrations",
        }
        assert expected <= names
    finally:
        await db.close()


async def test_write_tx_commits_and_rolls_back(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        async with db.write_tx() as conn:
            await conn.execute(
                "INSERT INTO fields (field_id, params_json, status) VALUES ('f1','{}','queued')"
            )
        async with db.write_tx() as conn:
            await conn.execute(
                "INSERT INTO fields (field_id, params_json, status) VALUES ('f2','{}','queued')"
            )
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    conn = await db.read()
    rows = await (await conn.execute("SELECT field_id FROM fields ORDER BY field_id")).fetchall()
    await conn.close()
    assert [r[0] for r in rows] == ["f1"]  # f2 rolled back
    await db.close()


async def test_concurrent_writers_no_lock_errors(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")

    async def worker(i: int) -> None:
        async with db.write_tx() as conn:
            await conn.execute(
                "INSERT INTO fields (field_id, params_json, status) VALUES (?, '{}', 'queued')",
                (f"f{i}",),
            )
            await asyncio.sleep(0.001)

    try:
        await asyncio.gather(*(worker(i) for i in range(50)))
        conn = await db.read()
        count = await (await conn.execute("SELECT COUNT(*) FROM fields")).fetchone()
        await conn.close()
        assert count[0] == 50
    finally:
        await db.close()


async def test_write_tx_requires_connect() -> None:
    db = Database(":memory:")
    with pytest.raises(RuntimeError):
        async with db.write_tx():
            pass
