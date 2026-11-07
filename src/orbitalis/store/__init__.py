"""SQLite repository public surface.

Purpose: Re-exports for fields, frames, jobs, candidates, experiments,
events, cutouts, cache and the Database handle.
Inputs: None at import.
Outputs: Repository functions and Database.
Called by: pipeline, research, api services, demo loader.
"""

from orbitalis.store.cache import cache_get, cache_put
from orbitalis.store.candidates import get_candidate, list_candidates, put_candidate
from orbitalis.store.cutouts import cutout_size_bytes, get_cutout, put_cutout
from orbitalis.store.db import Database, open_database
from orbitalis.store.events import append_event, replay_events
from orbitalis.store.experiments import add_trial, get_experiment, list_experiments, put_experiment
from orbitalis.store.fields import (
    get_field,
    list_fields,
    make_field_id,
    set_field_status,
    upsert_field,
)
from orbitalis.store.frames import get_frame, list_frames, put_frame
from orbitalis.store.jobs import get_job, list_jobs, put_job, update_job

__all__ = [
    "Database",
    "add_trial",
    "append_event",
    "cache_get",
    "cache_put",
    "cutout_size_bytes",
    "get_candidate",
    "get_cutout",
    "get_experiment",
    "get_field",
    "get_frame",
    "get_job",
    "list_candidates",
    "list_experiments",
    "list_fields",
    "list_frames",
    "list_jobs",
    "make_field_id",
    "open_database",
    "put_candidate",
    "put_cutout",
    "put_experiment",
    "put_frame",
    "put_job",
    "replay_events",
    "set_field_status",
    "update_job",
    "upsert_field",
]
