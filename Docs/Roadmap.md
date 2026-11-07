# Roadmap — ORBITALIS backend and ML

Execution plan for the team and any coding agent. This file orders the work; it
does not redefine requirements. If this file disagrees with the PRD, SDD or
`AGENTS.md`, those documents win.

- **Last updated:** 2026-11-06
- **Last recorded commit:** `c1aa350` (`develop`, PR #3 merged)
- **Open PR:** #4 `feature/shift-and-stack` (`5d8f608`), reviewed, changes requested
- **Current gate:** G1 (proposed 2026-11-08)
- **Scope:** backend (`orbitalis`, `orbitalis_core`) and ML (`ml/`, `models/`, `research`). No UI/UX tasks.
- **Event:** NASA Space Apps, HackAthlone, 13–15 Nov 2026 (7 days from today)

Read first, in this order:

1. `Docs/…PRD…` — what and why.
2. `Docs/ORBITALIS_SDD.md` — architecture, modules, API, errors, build order (§15.6).
3. `AGENTS.md` — how agents work in this repo.
4. `Docs/Tests.md` — test case IDs and how to write tests.
5. `roadmap/traceability.csv` — the live requirement scorecard.
6. This roadmap — the order to build in.

---

## 1. Status snapshot

### 1.1 Scorecard

`traceability.csv` tracks 55 rows:

| Status | Count |
| --- | ---: |
| Done | 3 |
| In review | 1 |
| Partial | 7 |
| Scaffolded | 20 |
| Not started | 24 |

Done: `FR-CORE-01` (flags), `DOC-01` (SDD v1.1), `DOC-02` (AGENTS.md, Tests.md).
In review: `FR-RS-01` (shift-and-stack, PR #4).

### 1.2 Code state

`develop` is the scaffold plus one real module. 73 Python files exist; only the
flags module and its tests have content. Everything else is a stub with the
SDD-prescribed layout.

| Area | State | What exists |
| --- | --- | --- |
| `core.flags` | **Done** | `bits.py`, `mask.py`, `decode`, `default_mask`, NaN application. 31 tests pass (PR #3) |
| `core.shiftstack` | **In review** | PR #4: `shifting`, `combining`, `search`, `models`, `errors`; 43 new tests (74 total on the branch) |
| `core.wcs`, `calibration`, `align`, `stack`, `stretch` | Stub | Empty `__init__.py` |
| `core.candidates`, `inject`, `rank`, `classify`, `spectrum` | Stub | Empty `__init__.py` |
| `gateway` | Stub | `client`, `cutout`, `limiter`, `tap`, `schemas` files, no logic |
| `store` | Stub | `cache`, `db`, `fields`, `frames`, `jobs`, `candidates`, `cutouts`, `experiments`; migrations folder empty |
| `jobs`, `pipeline`, `eventbus` | Stub | Files exist, no logic |
| `research` | Stub | `classification`, `policy`, `ranking`, `search`, `validation`, `schemas` |
| `assistant` | Stub | `knowledge`, `limits`, `llm`, `service`, `tools` |
| `api` | Stub | Routers for fields, frames, jobs, candidates, experiments, overlays, assistant, health |
| `demo`, `overlays` | Stub | Package only |
| `ml/` | Stub | `train_ranker.py`, empty notebooks folder |
| CI | Partial | Workflow exists; checks commented out (`1a43c4b`); `check_boundaries.sh` exists |

Quality gates on `develop`: 31 tests pass. Lint, type and import-linter results
are **not recorded**; ruff and lint-imports could not be run in the review
environment. Run them locally before every PR.

### 1.3 What “done” means here

A task is done only when all of the following are true:

- [ ] The behaviour lives in the module the task names (SDD §6, §14.3).
- [ ] At least one test names the requirement or task ID (see `Docs/Tests.md`).
- [ ] `uv run ruff check` and `ruff format --check` pass.
- [ ] Type check passes (mypy or pyright, as configured).
- [ ] `uv run pytest` passes, offline and seeded.
- [ ] `scripts/check_boundaries.sh` (import-linter) passes.
- [ ] `__init__.py` holds the public surface only; each module has the §5.2 header docstring.
- [ ] No new dependency without a purpose line (SDD §4.4).
- [ ] Typed exceptions only; no bare `except Exception`; no silent partial output.
- [ ] Results are deterministic for a fixed seed.
- [ ] `traceability.csv` is updated in the same PR.
- [ ] Open ambiguities are added to SDD Appendix D, not left in a comment.
- [ ] This roadmap's task marker is updated.

---

## 2. How agents must work

1. **Pick the first unblocked task** in the order of §6. Do not start a later gate's work while an earlier gate is red.
2. **Read the requirement and its SDD section before writing code.** Cite the ID in the branch, PR and test.
3. **One task per branch and PR**, under about 400 changed lines. Conventional Commits, e.g. `feat(core): per-pixel best map in shiftstack`.
4. **PRs only.** No direct pushes to `develop` or `main`, even if the rule can be bypassed.
5. **Do not edit the SDD silently.** Propose the change; the lead updates SDD and its change log.
6. **Do not invent thresholds.** Put values in `config/*.yaml` or settings, tagged `PROVISIONAL(G#)`, until a measurement fixes them.
7. **Never weaken a test, lint or CI step to get green.** Fix the cause. Re-enable the commented CI checks as soon as G1 is green.
8. **Tests are offline.** IRSA is mocked (respx); no wall-clock dependence; seeds are fixed.
9. **Honesty rules are not negotiable:** candidates are always `unconfirmed`; model scores always carry `model_version`; unmatched real detections are never called false positives.
10. **When blocked, record a decision item (D-xx), take the SDD default and continue** with an independent task.

### Status markers

| Marker | Meaning |
| --- | --- |
| `[ ]` | Not started |
| `[~]` | In progress, partial or in review |
| `[x]` | Done |
| `[!]` | Blocked; the reason is beside it |

Update the marker and append the commit hash when a task closes. Do not renumber
tasks; append new ones. Task IDs use a dot (`CORE.01`) so they are never confused
with test case IDs (`CORE-01`) in `Docs/Tests.md`.

---

## 3. Dependency order

```text
core (flags, wcs, calibration, align, stack, stretch)
   └── core.shiftstack ── core.candidates ── core.inject
                                   └── core.rank (onnxruntime)   core.classify
gateway ─┐
store ───┼── pipeline ── jobs ── research ── api
core ────┘                          └── assistant (read-only)
overlays, demo ── api
```

Rules that never bend:

- `orbitalis_core` imports nothing from `orbitalis` (Must-not-regress #8).
- The gateway is the only module that talks to IRSA.
- `assistant` is read-only: no writes, no jobs, no IRSA.
- `inject` works on copies only.

### Critical path to G1

```text
CORE.02..06 → GW.01..03 → ST.01..02 → PL.01 → API.01..03 → G1
CORE.07 (CoreError) ─┘        JOB.01 → RS.01 (shiftstack on synthetic)
```

The ML engineer's shift-and-stack work runs in parallel with the data pipeline
until the two meet in `research.search` (RS.03).

---

## 4. Gates and milestones

Gate dates are **proposed** and need the lead's confirmation.

| Gate | Proposed date | Scope | Exit criteria |
| --- | --- | --- | --- |
| G1 | Sun 8 Nov | Core pipeline and Explorer data path; job runner; shift-and-stack on synthetic data | A preset field builds from IRSA (or fixtures), frames stream over SSE, a synthetic search job returns candidates; search budget benchmarked |
| G2 | Tue 10 Nov | Real-field search; injection-and-recovery; ranking (stretch) | A search on a real preset field completes inside budget; an experiment reports the four outcome classes; go/no-go on classification (D-19) |
| G3 | Wed 11 Nov | Freeze | Everything not ready ships **disabled** via `/capabilities`; demo bundle contains results for everything enabled; cold start with `ORB_OFFLINE=1` serves every preset |
| Event | 13–15 Nov | Demo and fixes only | No new features |

| Milestone | Scope | Gate |
| --- | --- | --- |
| M0 Scaffold and norms | Repo, SDD, AGENTS.md, Tests.md, flags | Closed |
| M1 Science core | wcs, calibration, align, stack, stretch, shiftstack | G1 |
| M2 Data path | gateway, store, pipeline, jobs, api basics | G1 |
| M3 Search | candidates, research.search, job endpoints | G1 → G2 |
| M4 Validation | inject, metrics, experiments | G2 |
| M5 ML | ranking model, ONNX, rank integration | G2 stretch → G3 |
| M6 Assistant | LLM client, knowledge pack, tools | G3 |
| M7 Hardening | demo bundle, offline mode, CI, performance | G3 |
| M8 Spectral classification | Only if data and templates exist | G3 optional |

---

## 5. Phase plans

### M0 — Scaffold and norms

**Status:** `[x]` closed.

- **DOC.01** `[x]` SDD v1.1 with the ML brief incorporated.
- **DOC.02** `[x]` `AGENTS.md` and `Docs/Tests.md` in the repo.
- **CORE.01** `[x]` Flags (FR-CORE-01). Commit `c1aa350` (PR #3).
  Decode, `default_mask` (all bits masked except SOURCE bit 21 and FULLSAMPLE;
  unknown bits masked), NaN application, split into `bits.py` and `mask.py`.
  Follow-up: add a test that an unknown bit is masked by default.

### M1 — Science core (G1)

Read SDD §6.1 and Appendix D-03. Core code is pure NumPy/SciPy/astropy: no I/O,
no settings, no web. Tests use tiny synthetic arrays.

- **CORE.07** `[~]` `CoreError` hierarchy (FR-CORE-07).
  One base class in `orbitalis_core`, subclasses per failure, codes mapped to
  `ORB-CORE-001/002` at the API boundary. All-NaN output raises. Do this first:
  PR #4 and every later core module depend on it.
  Base landed on `feature/core-07-coreerror` (`CoreError`, `InvalidInputError`,
  `EmptyResultError`, `check_not_all_nan`). Remaining: retrofit `shiftstack`
  errors on PR #4 to derive from `CoreError` (RS.01 item 7).
- **CORE.02** `[x]` WCS wavelength map (FR-CORE-02). Branch `feature/core-02-wcs`.
  Own bilinear interpolation of the WCS-WAVE lookup; `WaveTab`,
  `wavelength_map`/`wavelength_at`/`bandwidth_*` in µm. Astropy not used for
  the spectral axis. Verified against a real QR2 IRSA cutout (max error
  0.21 nm vs astropy WAVE-TAB). Note: Tests.md CORE-WCS-02 says `CoreError`
  for out-of-table pixels while this task's acceptance says NaN — implemented
  both: `wavelength_at` raises `InvalidInputError`, `wavelength_map` returns
  NaN outside the grid.
- **CORE.03** `[x]` Calibration (FR-CORE-03). Branch `feature/core-03-calibration`.
  `solid_angle_map` (per-pixel sr from WCS corners, ~8.89e-10 sr at 6.15″/px,
  sums to footprint) and `subtract_zodi` (NaN-aware, inputs untouched,
  all-NaN raises). `to_surface_brightness` is a documented stub — no caller
  exists while imaging stays MJy/sr (D-03 default; ML sign-off still pending).
  ZODI verified not subtracted from IMAGE on a QR2 cutout; `subtract_zodi` is
  opt-in only. Follow-ups: **CORE.03a** directed converters
  (`flux_to_surface_brightness`, `surface_brightness_to_flux`) when CORE.08
  and VAL.01 need them.
- **CORE.04** `[ ]` Align (FR-CORE-04).
  `to_common_grid` using `reproject`, flux-conserving for surface brightness,
  returns array and footprint.
  Acceptance: a shifted synthetic image lands on the target grid; flux conserved.
- **CORE.05** `[ ]` Stack and difference (FR-CORE-05).
  Sigma-clipped mean/median; mask and variance propagation.
  Acceptance: clipped outlier removed; variance matches analytic value.
- **CORE.06** `[ ]` Stretch (FR-CORE-06).
  `fit_stretch` and `apply_stretch`; parameters frozen after N frames.
  Acceptance: later frames never change fitted parameters.
- **RS.01** `[~]` Shift-and-stack (FR-RS-01), PR #4 (`5d8f608`).
  Done in the PR: module split, correct shift sign, NaN fill at edges, budget check
  before compute, input not mutated, 43 tests.
  **Requested changes (from review), in priority order:**
  1. Return a per-pixel best score map and per-pixel best trial index (running
     max), not a global `best_index`. Make the full per-trial cube opt-in.
     A bright static star currently wins: measured best trial is zero motion,
     score 895, and the faint mover scores 24.
  2. Handle static sources (static-model subtraction before the search, or
     documented exclusion of the zero-motion trial).
  3. Mask scores where coverage is below a configured fraction of frames.
  4. Stop NaN spreading under interpolation (1 NaN became 13); shift a validity
     mask and re-NaN below a weight threshold.
  5. One canonical name per concept; no alias sprawl; no broad `except Exception`.
  6. Validate once up front; vectorise `combine`; benchmark and set
     `ORB_SEARCH_MAX_WORK` (probe: 110–130 s at 2e9 on the review machine,
     above the 60 s target).
  7. Errors derive from `CoreError` (CORE.07).
  8. float32 maps.
  Acceptance: tests for static star plus faint mover, NaN under integer and
  sub-pixel shift, coverage mask, work budget, determinism; ruff and
  import-linter pass.
- **RS.02** `[ ]` Motion convention (FR-RS-03).
  Close D-17: units (SDD proposes arcsec/day; PR uses px/day), position-angle
  sign, reference time, grid density and velocity prior. Write it in the
  `shiftstack` docstring and `/jobs` schema.
  Acceptance: one conversion function with a round-trip test; documented in SDD.

### M2 — Data path (G1)

Read SDD §6.2–6.4, §7, §9. Network only inside `gateway`, mocked in tests.

- **GW.01** `[ ]` TAP query (FR-DATA-01).
  Resolve a position to frames; filter by release/deep; verify column names and
  `time_bounds_lower` against live IRSA once (D-01), then freeze them in fixtures.
  Acceptance: recorded TAP response parsed to typed `FrameRef`s; failure maps to `ORB-GW-001`.
- **GW.02** `[ ]` Cutout fetch (FR-DATA-02).
  httpx async; semaphore (default 4); retries with backoff; circuit breaker.
  Measure safe concurrency (D-02).
  Acceptance: never exceeds concurrency; breaker opens and recovers; timeout maps to `ORB-GW-004`.
- **GW.03** `[ ]` Cutout validation.
  Reject corrupt FITS (`ORB-CORE-001`); extract image, FLAGS, VARIANCE, WCS-WAVE.
- **ST.01** `[ ]` SQLite setup and migrations (FR-DATA-03).
  WAL, schema from SDD §7.4, migration runner; the folder is empty today.
  Acceptance: fresh DB builds; second run is a no-op.
- **ST.02** `[ ]` Repositories (FR-DATA-03).
  Fields, frames, cutouts, jobs, candidates, experiments; `field_id` is a stable
  hash independent of key order (Must-not-regress #4); cache eviction.
- **PL.01** `[ ]` Field builder (FR-DATA-04).
  gateway → core (flags, wcs, calibration, align, stretch) → store, emitting
  progress events; degradation ladder (SDD §11.2); cancellation at boundaries.
  Acceptance: a fixture field builds end to end; cancel leaves no partial state.
- **JOB.01** `[ ]` Job runner (FR-JOB-01).
  Statuses queued/running/completed/failed/cancelled; idempotent `job_id`; fixed
  worker pool; typed handler registry.
- **JOB.02** `[ ]` Timeouts and restart (FR-JOB-02).
  `ORB-JOB-002/003/004`; jobs left `running` after a restart become `failed`.
- **API.01** `[ ]` Field and frame endpoints, capabilities (FR-API-01/03/05).
  Error envelope, `/capabilities`, frame PNG (LA mode, alpha 0 where masked) plus meta.
- **API.02** `[ ]` SSE (FR-API-02).
  `Last-Event-ID` replay for fields and jobs.

**Exit (G1):** a preset field builds from fixtures, frames stream over SSE, flags
and masks are visible in meta, the search budget is benchmarked and recorded.

### M3 — Search (G1 → G2)

Read SDD §6.1, §6.9, §8.2b. Owner: ML engineer, with backend support on plumbing.

- **RS.03** `[ ]` Candidate extraction (FR-RS-04).
  Peak finding on the best score map; position, motion vector, stack SNR;
  centroid refinement; exclude edge and low-coverage pixels.
  Blocked on RS.01 item 1.
- **RS.04** `[ ]` Stack policy (FR-RS-05).
  `check_combinable` from `config/stack_policy.yaml`; `ORB-RS-002` with a reason
  per offending frame. Values from the ML team (D-14).
- **RS.05** `[ ]` Search handler (FR-RS-07, FR-RS-02).
  `research.search`: frame selection, policy, work-budget check (`ORB-RS-003`),
  `shiftstack.search`, `candidates.extract`, persist. Candidates are always `unconfirmed`.
- **RS.06** `[ ]` Job and candidate endpoints (FR-RS-07).
  `POST /jobs` (`moving_object_search`), `/fields/{id}/candidates`, `/candidates/*`;
  per-frame cutouts rendered on demand from stored arrays.
- **RS.07** `[ ]` Synthetic search end-to-end test.
  Inject a mover into a fixture field, run the job, recover it. This is the G1 exit test.
- **RS.09** `[ ]` Decide when `subtract_zodi` runs before `moving_object_search`.
  Nothing currently decides it; the ZODI model is a smooth background, and
  whether to subtract it interacts with the static-source problem in PR #4
  review item 2. Decide with the ML engineer before RS.05 wires the handler.
- **RS.08** `[ ]` Real preset search (G2).
  Run on a real preset field, tune the work budget, bake the result into the demo bundle.

**Exit (G2 part):** a real search completes inside the budget; results are
reproducible for a fixed seed; every candidate is `unconfirmed`.

### M4 — Validation (G2)

Read SDD §6.1 (`inject`), §6.9. Closes D-15.

- **VAL.01** `[ ]` Injection (FR-VAL-01).
  PSF-based injection into copies of arrays; deterministic with a seed.
  Acceptance: input arrays bit-identical afterwards (Must-not-regress #10).
- **VAL.02** `[ ]` Matching and outcome classes (FR-VAL-02).
  `recovered`, `missed`, `preexisting`, `spurious` at `ORB_MATCH_RADIUS_PX`.
  Acceptance: table-driven tests for each class.
- **VAL.03** `[ ]` Metrics (FR-VAL-03).
  Recall; precision relative to injected sources; position error; completeness
  by flux and speed bin.
- **VAL.04** `[ ]` Experiment job and endpoints (FR-VAL-04).
  Store seed, parameters and `experiment_id`; results labelled as relative to
  injected sources in this experiment.
- **VAL.05** `[ ]` Bundled experiment for each preset (G3 dependency).

### M5 — ML ranking (G2 stretch → G3)

Read SDD §6.1 (`rank`), §11.4. The runtime image carries onnxruntime only; torch
stays in the `ml` group (D-18).

- **ML.01** `[ ]` Training data and labels (D-18).
  Build labelled cutouts from validation experiments (injected = positive,
  recovered/spurious = labelled by `inject`). Document the split; hold out a test set.
- **ML.02** `[ ]` Train and export (`ml/train_ranker.py`).
  Small CNN; fixed cutout size; export ONNX; write `model_version`; record metrics.
  Acceptance: ONNX output matches torch within tolerance on a fixed batch.
- **ML.03** `[ ]` Runtime ranker (FR-ML-01).
  `load_model` returns `None` if the file is absent; `score` returns
  `ModelScore{value, model_version, kind}`; never a bare number.
- **ML.04** `[ ]` Ranking job and capability flag (FR-ML-02).
  `POST /jobs` (`candidate_ranking`); `ORB-ML-001/002`; app starts without the model.
- **ML.05** `[ ]` Honest evaluation.
  Report ranker precision/recall on held-out injected data only; state that it
  says nothing about real unconfirmed candidates.

Go/no-go for freezing the model: G3. If it is not ready, ship it disabled.

### M6 — Assistant (G3)

Read SDD §6.10, §8.6, §10.3. Decide D-13 (provider) before starting.

- **AS.01** `[ ]` `LLMClient` protocol, fake client for tests, one provider adapter.
- **AS.02** `[ ]` Knowledge pack (D-16).
  Curated docs in `config/knowledge/`; fits in the system prompt; ML engineer writes content.
- **AS.03** `[ ]` Read-only tools (FR-AS-02).
  List candidates, read experiment results, explain flags. None writes or launches jobs.
- **AS.04** `[ ]` Streaming chat endpoint with rate limit and daily budget (FR-AS-01/03).
- **AS.05** `[ ]` Degradation: no key or provider down returns `ORB-AS-001`; Explorer unaffected.

### M7 — Hardening and demo (G3)

- **OPS.01** `[ ]` Re-enable CI checks (NFR-05): ruff, types, pytest, import-linter. Branch protection stays on.
- **OPS.02** `[ ]` Demo bundle (FR-OPS-02, FR-DATA-05).
  `scripts/bake_demo.py` bakes frames, a search result and an experiment per preset.
  Acceptance: cold start with empty cache and `ORB_OFFLINE=1` serves every preset (Must-not-regress #9).
- **OPS.03** `[ ]` Container and deploy (FR-OPS-01).
  Build image (no torch); deploy to Cloud Run with `min-instances=1` (D-20); smoke test; verify flags against current gcloud help (D-09).
- **OPS.04** `[ ]` Performance pass (NFR-03).
  Measure against SDD §13.3; record numbers in the traceability notes.
- **OPS.05** `[ ]` Must-not-regress suite.
  One test per item in SDD §12.3; fail CI if one is missing.
- **OPS.06** `[ ]` Pre-demo checklist and incident drill (SDD §15.4–15.5).

### M8 — Spectral classification (optional)

Decision at G2 (D-19). Skip entirely if templates or data are not available.

- **CORE.08** `[ ]` `spectrum.extract` (FR-CORE-08): solid angle applied here only; wavelength-sorted points with errors.
- **ML.06** `[ ]` `classify` (FR-ML-03): returns `None` with `insufficient_data` below minimum points or SNR; never extrapolates.

---

## 6. Current next tasks

The immediate unblocked queue, in order:

1. **RS.01** address PR #4 review items 1–4, then merge. (ML engineer / Ake544)
2. **CORE.07** `CoreError` base; then retrofit shiftstack. (Lead)
3. **RS.02** close D-17, the motion convention. (ML engineer)
4. **GW.01 / GW.02** and **ST.01** in parallel. (Lead / Backend 2)
5. **CORE.02–06** science core, split between Backend 2 and the ML engineer.
6. **JOB.01** job runner skeleton so `research.search` has somewhere to run.
7. **CORE.01 follow-up:** unknown-bit test.

Do not start `RS.03` before RS.01 item 1 lands. Do not start M5 training before
VAL.02 can label outcomes.

---

## 7. Known traps

| Area | Trap | Rule |
| --- | --- | --- |
| Flags | Treating SOURCE bit 21 as bad | It stays unmasked; all other bits, including unknown ones, are masked |
| Flags | Zero-filling masked pixels | Masked means NaN in arrays, alpha 0 in PNGs |
| Calibration | Converting to Jy early | Imaging stays in MJy/sr; solid angle only in spectrum extraction |
| Shift-and-stack | Global best trial | A bright star wins; keep a per-pixel best map and handle static sources |
| Shift-and-stack | Interpolating NaNs | Shift a validity mask; re-NaN below a weight threshold |
| Shift-and-stack | Unbenchmarked budget | `2e9` is a guess; set it from measured px-shifts per second |
| Shift-and-stack | Unit mix-up | One motion convention (D-17), one conversion function |
| Candidates | A "confirmed" state | There is none in v1; always `unconfirmed` |
| Validation | Calling unmatched real detections false positives | Only the four outcome classes; precision is relative to injected sources |
| Validation | Mutating inputs | `inject` works on copies |
| ML | Bare score | Always pair with `model_version` |
| ML | Evaluating on training data | Hold out; ranker metrics do not describe real candidates |
| ML | torch in the image | Runtime has onnxruntime only |
| Gateway | Concurrency creep | One semaphore; never exceed the setting (IRSA failed 37/84 at 10 parallel) |
| Gateway | Calling IRSA elsewhere | Only the gateway talks to IRSA |
| Jobs | Scale-to-zero | `min-instances=1` for the whole event window |
| Assistant | A tool that writes | Read-only; none launches jobs or contacts IRSA |
| Core | Importing `orbitalis` | Import-linter must stay green |
| Process | Pushing to `develop` | Use PRs; the 8c094b0 push bypassed the rule |
| Process | Disabling CI to move faster | Fix the cause; re-enable the commented checks |

---

## 8. Cross-cutting backlog

These can land with any milestone but must not distract from the critical path:

- **X-01** `[ ]` Traceability checker: fail CI when a row has no test or an invalid status.
- **X-02** `[ ]` GW-12 host allowlist test and SDD addition (T-03 in Tests.md).
- **X-03** `[ ]` Benchmarks for `shiftstack` and `rank` (pytest-benchmark or a script) before optimising.
- **X-04** `[ ]` Property tests: shift round trip, mask idempotence, stack permutation invariance.
- **X-05** `[ ]` Log the GHOST_FPA spec conflict in SDD Appendix D.
- **X-06** `[ ]` Apply accepted UX gaps (U-01…U-15) to SDD v1.2 as API changes.
- **X-07** `[ ]` Write the ML spec (DOC-03) so D-11 can close.
- **X-08** `[ ]` Keep `traceability.csv` and this roadmap in step with every merge.

---

## 9. Open decisions that affect sequencing

| Item | Affects | Default until resolved | Owner | Needed by |
| --- | --- | --- | --- | --- |
| D-01 TAP columns and `time_bounds_lower` | GW.01 | Use SDD names; verify once | Lead | G1 |
| D-02 IRSA concurrency | GW.02 | 4 | Lead | G1 |
| D-03 solid angle deviation | CORE.03 | Imaging MJy/sr; spectra only | ML eng | G1 |
| D-06 image contract | API.01 | PNG plus JSON meta | Frontend | G1 |
| D-14 stack policy values | RS.04 | Same release; conservative spans | ML eng | G1 |
| D-17 motion units and convention | RS.02, RS.01 | arcsec/day, PA east of north (PR uses px/day) | ML eng | G1 |
| D-15 outcome definitions | VAL.02 | Four classes as in SDD | ML eng | G2 |
| D-18 ranker data and size | ML.01 | Labels from injection | ML eng | G1 |
| D-19 classification go/no-go | M8 | No-go unless templates exist | ML eng | G2 |
| D-13 LLM provider | M6 | Assistant disabled | Lead + ML | G1 |
| D-16 knowledge pack form | AS.02 | In-prompt pack | ML + Backend 2 | G2 |
| D-04 overlay source | FR-OV-01 | Local list only | Backend 2 | G1 |
| D-20 min-instances credit | OPS.03 | min=1 | Lead | G1 |
| D-12 coding-start rule | scaffolding | Confirm with organisers | Lead | now |

---

## 10. Roadmap maintenance

- Update the status snapshot when a gate closes or a PR merges.
- Mark tasks in place; do not renumber.
- Append the commit hash and test IDs to a closed task.
- If a task splits, add `CORE.03a` / `CORE.03b`.
- If a task is blocked, mark `[!]` and name the blocking task or decision.
- Keep this file free of secrets and unmeasured claims; every number here was measured or comes from the SDD.
