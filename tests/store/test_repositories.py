"""Tests for ST.02 repositories: round trips, cascade, events, field_id."""

from __future__ import annotations

from pathlib import Path

import pytest

from orbitalis.store import (
    Database,
    add_trial,
    append_event,
    cache_get,
    cache_put,
    get_candidate,
    get_experiment,
    get_field,
    get_frame,
    get_job,
    list_candidates,
    make_field_id,
    open_database,
    put_candidate,
    put_experiment,
    put_frame,
    put_job,
    replay_events,
    set_field_status,
    update_job,
    upsert_field,
)

pytestmark = pytest.mark.asyncio


async def _seed(db: Database) -> str:
    fid = make_field_id({"ra": 10.0, "dec": 20.0, "radius": 0.1})
    await upsert_field(db, fid, {"ra": 10.0, "dec": 20.0, "radius": 0.1})
    await put_frame(db, fid, "r1", array_blob=b"arr1", wavelength_um=1.5, mjd=60000.0)
    await put_job(db, "j1", "moving_object_search", {"x": 1}, field_id=fid)
    await put_candidate(db, "c1", "j1", fid, ra=10.1, dec=20.1, stack_snr=5.0)
    await put_experiment(db, "e1", "j1", fid, params={"seed": 1})
    await add_trial(db, "e1", 0, outcome="recovered", position_error_px=0.5)
    return fid


async def test_field_id_stable_and_sensitive() -> None:
    a = make_field_id({"ra": 1, "dec": 2, "r": 0.5})
    b = make_field_id({"r": 0.5, "dec": 2, "ra": 1})  # key order
    c = make_field_id({"ra": 1, "dec": 2, "r": 0.6})  # param change
    assert a == b and a != c


async def test_repository_round_trips(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        fid = await _seed(db)
        f = await get_field(db, fid)
        assert f and f["params"]["ra"] == 10.0 and f["status"] == "queued"
        fr = await get_frame(db, fid, "r1")
        assert fr and fr["array_blob"] == b"arr1" and fr["wavelength_um"] == 1.5
        j = await get_job(db, "j1")
        assert j and j["params"] == {"x": 1}
        c = await get_candidate(db, "c1")
        assert c and c["stack_snr"] == 5.0
        e = await get_experiment(db, "e1")
        assert e and e["trials"][0]["outcome"] == "recovered"
    finally:
        await db.close()


async def test_job_lifecycle(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        await put_job(db, "j2", "k", {})
        await update_job(db, "j2", status="running")
        await update_job(db, "j2", status="completed", result={"n": 3})
        j = await get_job(db, "j2")
        assert j["status"] == "completed" and j["result"] == {"n": 3}
        assert j["started_at"] and j["finished_at"]
    finally:
        await db.close()


async def test_frame_requires_array_blob(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        fid = make_field_id({})
        await upsert_field(db, fid, {})
        with pytest.raises(ValueError):
            await put_frame(db, fid, "x", array_blob=b"")
    finally:
        await db.close()


async def test_cascade_delete_field(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        fid = await _seed(db)
        async with db.write_tx() as conn:
            await conn.execute("DELETE FROM fields WHERE field_id=?", (fid,))
        assert await list_candidates(db, fid) == []
        assert await get_experiment(db, "e1") is None
        conn = await db.read()
        cur = await conn.execute("SELECT COUNT(*) FROM frames WHERE field_id=?", (fid,))
        assert (await cur.fetchone())[0] == 0
        await conn.close()
    finally:
        await db.close()


async def test_events_replay_and_prune(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        for i in range(5):
            await append_event(db, "s1", "progress", {"i": i})
        first = await replay_events(db, "s1")
        assert [e["seq"] for e in first] == [1, 2, 3, 4, 5]
        rest = await replay_events(db, "s1", after_seq=3)
        assert [e["seq"] for e in rest] == [4, 5]
        assert rest[0]["data"] == {"i": 3}
    finally:
        await db.close()


async def test_cache_ttl(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        await cache_put(db, "tap_cache", "k1", {"rows": 2}, ttl_s=3600)
        assert await cache_get(db, "tap_cache", "k1") == {"rows": 2}
        assert await cache_get(db, "tap_cache", "missing") is None
        with pytest.raises(ValueError):
            await cache_put(db, "nope", "k", {}, ttl_s=1)
    finally:
        await db.close()


async def test_field_status(tmp_path: Path) -> None:
    db = await open_database(tmp_path / "t.db")
    try:
        fid = make_field_id({"a": 1})
        await upsert_field(db, fid, {"a": 1})
        await set_field_status(db, fid, "running")
        assert (await get_field(db, fid))["status"] == "running"
        with pytest.raises(ValueError):
            await set_field_status(db, fid, "bogus")
    finally:
        await db.close()
