"""Job repository.

Purpose: CRUD for ``jobs`` — the generic job ledger (SDD §7.4, §6.8).
Inputs: ``Database`` handle plus job fields.
Outputs: Rows as dicts.
Called by: job runner, research handlers, api services.
"""

from __future__ import annotations

import json
from typing import Any

from orbitalis.store.db import Database

_JOB_STATUSES = ("queued", "running", "completed", "failed", "cancelled")


async def put_job(
    db: Database,
    job_id: str,
    kind: str,
    params: dict[str, Any],
    *,
    field_id: str | None = None,
) -> None:
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO jobs (job_id, kind, field_id, params_json, status) "
            "VALUES (?,?,?,?, 'queued') "
            "ON CONFLICT(job_id) DO UPDATE SET kind=excluded.kind, "
            "field_id=excluded.field_id, params_json=excluded.params_json",
            (job_id, kind, field_id, json.dumps(params, sort_keys=True)),
        )


async def get_job(db: Database, job_id: str) -> dict[str, Any] | None:
    conn = await db.read()
    try:
        cur = await conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        row = await cur.fetchone()
        return _job_row(row, [d[0] for d in cur.description]) if row else None
    finally:
        await conn.close()


async def list_jobs(db: Database, field_id: str | None = None) -> list[dict[str, Any]]:
    conn = await db.read()
    try:
        if field_id is None:
            cur = await conn.execute("SELECT * FROM jobs ORDER BY created_at")
        else:
            cur = await conn.execute(
                "SELECT * FROM jobs WHERE field_id=? ORDER BY created_at", (field_id,)
            )
        cols = [d[0] for d in cur.description]
        return [_job_row(r, cols) for r in await cur.fetchall()]
    finally:
        await conn.close()


async def update_job(
    db: Database,
    job_id: str,
    *,
    status: str | None = None,
    progress: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    error_code: str | None = None,
) -> None:
    if status is not None and status not in _JOB_STATUSES:
        raise ValueError(f"invalid job status {status!r}")
    sets, args = [], []
    if status is not None:
        sets += ["status=?"]
        args.append(status)
        if status == "running":
            sets.append("started_at=COALESCE(started_at, datetime('now'))")
        if status in ("completed", "failed", "cancelled"):
            sets.append("finished_at=datetime('now')")
    if progress is not None:
        sets.append("progress_json=?")
        args.append(json.dumps(progress, sort_keys=True))
    if result is not None:
        sets.append("result_json=?")
        args.append(json.dumps(result, sort_keys=True))
    if error_code is not None:
        sets.append("error_code=?")
        args.append(error_code)
    if not sets:
        return
    args.append(job_id)
    async with db.write_tx() as conn:
        await conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id=?", args)


def _job_row(row: tuple, cols: list[str]) -> dict[str, Any]:
    d = dict(zip(cols, row, strict=True))
    for key in ("params_json", "progress_json", "result_json"):
        if d.get(key) is not None:
            d[key.removesuffix("_json")] = json.loads(d.pop(key))
        else:
            d.pop(key, None)
    return d


__all__ = ["get_job", "list_jobs", "put_job", "update_job"]
