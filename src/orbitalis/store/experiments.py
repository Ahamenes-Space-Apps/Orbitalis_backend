"""Experiment and trial repository.

Purpose: CRUD for ``experiments`` and ``experiment_trials`` (SDD §7.4).
Inputs: ``Database`` handle plus experiment fields.
Outputs: Rows as dicts.
Called by: research validation handler, api services, demo loader.
"""

from __future__ import annotations

import json
from typing import Any

from orbitalis.store.db import Database

_TRIAL_OUTCOMES = ("recovered", "missed")


async def put_experiment(
    db: Database,
    experiment_id: str,
    job_id: str | None,
    field_id: str,
    *,
    params: dict[str, Any],
    metrics: dict[str, Any] | None = None,
    label: str | None = None,
) -> None:
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO experiments (experiment_id, job_id, field_id, params_json, "
            "metrics_json, label) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(experiment_id) DO UPDATE SET metrics_json=excluded.metrics_json",
            (
                experiment_id,
                job_id,
                field_id,
                json.dumps(params, sort_keys=True),
                json.dumps(metrics, sort_keys=True) if metrics is not None else None,
                label,
            ),
        )


async def add_trial(
    db: Database,
    experiment_id: str,
    trial_idx: int,
    *,
    truth: dict[str, Any] | None = None,
    outcome: str,
    detection: dict[str, Any] | None = None,
    position_error_px: float | None = None,
) -> None:
    """Insert one trial. ``outcome`` is 'recovered' or 'missed' (SDD §6)."""
    if outcome not in _TRIAL_OUTCOMES:
        raise ValueError(f"invalid trial outcome {outcome!r}")
    async with db.write_tx() as conn:
        await conn.execute(
            "INSERT INTO experiment_trials (experiment_id, trial_idx, truth_json, "
            "outcome, detection_json, position_error_px) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(experiment_id, trial_idx) DO UPDATE SET "
            "outcome=excluded.outcome, detection_json=excluded.detection_json, "
            "position_error_px=excluded.position_error_px",
            (
                experiment_id,
                trial_idx,
                json.dumps(truth, sort_keys=True) if truth is not None else None,
                outcome,
                json.dumps(detection, sort_keys=True) if detection is not None else None,
                position_error_px,
            ),
        )


async def get_experiment(db: Database, experiment_id: str) -> dict[str, Any] | None:
    conn = await db.read()
    try:
        cur = await conn.execute(
            "SELECT * FROM experiments WHERE experiment_id=?", (experiment_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        exp = _exp_row(row, [d[0] for d in cur.description])
        cur = await conn.execute(
            "SELECT * FROM experiment_trials WHERE experiment_id=? ORDER BY trial_idx",
            (experiment_id,),
        )
        cols = [d[0] for d in cur.description]
        exp["trials"] = [_trial_row(r, cols) for r in await cur.fetchall()]
        return exp
    finally:
        await conn.close()


async def list_experiments(db: Database, field_id: str) -> list[dict[str, Any]]:
    conn = await db.read()
    try:
        cur = await conn.execute(
            "SELECT * FROM experiments WHERE field_id=? ORDER BY created_at", (field_id,)
        )
        cols = [d[0] for d in cur.description]
        return [_exp_row(r, cols) for r in await cur.fetchall()]
    finally:
        await conn.close()


def _exp_row(row: tuple, cols: list[str]) -> dict[str, Any]:
    d = dict(zip(cols, row, strict=True))
    for key in ("params_json", "metrics_json"):
        if d.get(key) is not None:
            d[key.removesuffix("_json")] = json.loads(d.pop(key))
        else:
            d.pop(key, None)
    return d


def _trial_row(row: tuple, cols: list[str]) -> dict[str, Any]:
    d = dict(zip(cols, row, strict=True))
    for key in ("truth_json", "detection_json"):
        if d.get(key) is not None:
            d[key.removesuffix("_json")] = json.loads(d.pop(key))
        else:
            d.pop(key, None)
    return d


__all__ = ["add_trial", "get_experiment", "list_experiments", "put_experiment"]
