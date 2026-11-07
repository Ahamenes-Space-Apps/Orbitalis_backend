-- ORBITALIS initial schema (SDD v1.1 section 7.4)
-- Disposable database: forward-only migrations, reset-and-rebuild is acceptable.

CREATE TABLE fields (
    field_id   TEXT PRIMARY KEY,
    params_json TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
    preset     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    error_code TEXT
);

CREATE TABLE cutouts (
    cutout_key  TEXT PRIMARY KEY,
    fits_blob   BLOB NOT NULL,
    bytes       INTEGER NOT NULL,
    fetched_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE frames (
    field_id     TEXT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    frame_ref    TEXT NOT NULL,
    wavelength_um REAL,
    mjd          REAL,
    detector     INTEGER,
    png_blob     BLOB,
    meta_json    TEXT,
    array_blob   BLOB,
    PRIMARY KEY (field_id, frame_ref)
);
CREATE INDEX idx_frames_field ON frames(field_id);

CREATE TABLE groups (
    field_id  TEXT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    group_id  TEXT NOT NULL,
    rule      TEXT,
    png_blob  BLOB,
    meta_json TEXT,
    PRIMARY KEY (field_id, group_id)
);

CREATE TABLE group_frames (
    group_id  TEXT NOT NULL,
    frame_ref TEXT NOT NULL,
    field_id  TEXT NOT NULL,
    PRIMARY KEY (field_id, group_id, frame_ref),
    FOREIGN KEY (field_id, group_id) REFERENCES groups(field_id, group_id) ON DELETE CASCADE
);

CREATE TABLE derived (
    field_id     TEXT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN ('diff','spectrum','classification')),
    payload_blob BLOB NOT NULL,
    PRIMARY KEY (field_id, kind)
);

CREATE TABLE events (
    stream_id  TEXT NOT NULL,
    seq        INTEGER NOT NULL,
    type       TEXT NOT NULL,
    data_json  TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (stream_id, seq)
);
CREATE INDEX idx_events_stream ON events(stream_id, seq);

CREATE TABLE overlay_cache (
    key         TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    fetched_at  TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_s       INTEGER NOT NULL
);

CREATE TABLE jobs (
    job_id       TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    field_id     TEXT REFERENCES fields(field_id) ON DELETE SET NULL,
    params_json  TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
    progress_json TEXT,
    result_json  TEXT,
    error_code   TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    started_at   TEXT,
    finished_at  TEXT
);
CREATE INDEX idx_jobs_field ON jobs(field_id);

CREATE TABLE candidates (
    candidate_id      TEXT PRIMARY KEY,
    job_id            TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    field_id          TEXT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    ra                REAL NOT NULL,
    dec               REAL NOT NULL,
    motion_json       TEXT,
    stack_snr         REAL,
    stack_png_blob    BLOB,
    frames_json       TEXT,
    model_score       REAL,
    model_version     TEXT,
    predicted_category TEXT,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_candidates_field ON candidates(field_id);

CREATE TABLE experiments (
    experiment_id TEXT PRIMARY KEY,
    job_id        TEXT REFERENCES jobs(job_id) ON DELETE SET NULL,
    field_id      TEXT NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    params_json   TEXT NOT NULL,
    metrics_json  TEXT,
    label         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_experiments_field ON experiments(field_id);

CREATE TABLE experiment_trials (
    experiment_id     TEXT NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    trial_idx         INTEGER NOT NULL,
    truth_json        TEXT,
    outcome           TEXT CHECK (outcome IN ('recovered','missed')),
    detection_json    TEXT,
    position_error_px REAL,
    PRIMARY KEY (experiment_id, trial_idx)
);

CREATE TABLE tap_cache (
    key          TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    fetched_at   TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_s        INTEGER NOT NULL
);
