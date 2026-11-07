# ORBITALIS — Test Plan (TESTS.md)

Companion to SDD v1.1 (§12 Testing strategy), the UX Design & User Flows doc (§15 Acceptance) and `AGENTS.md`.
This file is the working catalogue: what to test, with which fixtures, what "pass" means, and what must be green at each gate.

---

## 0. How to use this document

- **Agents and developers:** find your module in §4, write the listed cases first (TDD for `core`, `gateway`, `store`, `jobs`, `research`), then implement.
- **Reviewers:** check the PR against the case IDs it claims to cover and against §5 (must-not-regress).
- **Lead:** use §10 to decide whether a gate is passed.
- **Priorities:** **P0** = blocks the demo or breaks an honesty rule; **P1** = must pass before the pre-demo freeze (G3); **P2** = nice to have.
- Numbers marked *(initial)* are starting tolerances to tune at gate G1 with real data; change them here when they change.

---

## 1. Strategy

| Principle | Consequence |
|---|---|
| Fast and offline | The whole default suite runs in under 60 s with no network. Anything slower or networked is marked and skipped by default. |
| Test where the risk is | Most cases sit in `orbitalis_core` (science correctness), `gateway` (IRSA misbehaviour) and `research`/`jobs` (long work, honesty rules). |
| Known answers over snapshots | Science tests use synthetic data whose right answer is known by construction, not saved outputs. |
| Honesty is tested | Rules like "candidates are unconfirmed" and "unmatched real detections are not false positives" have tests, not just prose. |
| Degradation is tested | Each rung of the degradation ladder and each optional feature's off-state has a test. |
| Contract is tested | OpenAPI snapshot and error-code coverage fail the build when the contract drifts silently. |

### Test pyramid

| Layer | Share of effort | Runs | Tools |
|---|---|---|---|
| Unit (core, pure functions) | ~40% | every commit | pytest, numpy testing, synthetic arrays |
| Component (gateway, store, jobs, research, pipeline, assistant) | ~35% | every commit | pytest-asyncio, respx, temp SQLite, fakes |
| API / contract | ~15% | every commit | FastAPI TestClient or httpx ASGI, SSE reader helper |
| End-to-end browser flows | ~8% | on PR to `main` and before gates | browser automation against mock mode; one live smoke |
| Live archive smoke | ~2% | manual, marked `live` | real IRSA, minimal calls |

---

## 2. Environment and tooling

### 2.1 Backend

| Item | Setting |
|---|---|
| Runner | `uv run pytest` |
| Config | `[tool.pytest.ini_options]` `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Markers | `live` (real IRSA, skipped by default), `slow` (> 2 s each, run in CI nightly or pre-gate), `bench` (benchmarks, never in default run) |
| HTTP mocking | `respx` for every `httpx` call. Any un-mocked outbound request fails the test (autouse fixture asserts no real network). |
| Time | A fake clock fixture for backoff, breaker cool-down, TTLs, job timeouts, throttling. No `sleep` in tests. |
| Randomness | Every stochastic test takes an explicit seed. |
| Database | Temp-dir SQLite per test; migrations applied from scratch. |
| Lint gates | `ruff check`, `ruff format --check`, `lint-imports`, `uv lock --check` |

### 2.2 Frontend

| Item | Setting |
|---|---|
| Component tests | Framework's standard runner (stack-agnostic): render components with fixtures from the mock |
| Mock mode | API mock generated from the OpenAPI schema, filled from demo-bundle fixtures, with `slow`, `failing`, `offline` and `capabilities-off` variants |
| E2E | Browser automation for flows F1–F7 (UX doc §7) |
| Accessibility | Automated checks (axe-style) on every page and state, plus a manual keyboard walkthrough |
| Visual snapshots | Stored images for: empty, building, degraded, offline, error, failed job |

### 2.3 CI stages (in order)

1. `uv sync --locked` and `uv lock --check`
2. `ruff check` and `ruff format --check`
3. `lint-imports`
4. `pytest` (default: no `live`, `slow`, `bench`)
5. OpenAPI snapshot check
6. Frontend lint, type check, component tests
7. Browser flows in mock mode (PRs to `main`)
8. Docker build with `--locked` (main)
9. Nightly / pre-gate: `pytest -m slow`, accessibility full pass

Coverage **targets** (reported, not a build failure): `orbitalis_core` ≥ 85% lines; `gateway`, `store`, `jobs`, `research` ≥ 80%; others informational. Branch coverage matters more than line coverage for `limiter.py` and `policy.py`.

---

## 3. Fixtures and test data

| Fixture | What it is | Used by |
|---|---|---|
| `make_frame(shape, wcs, source=None, noise=0.0, seed)` | Builds a synthetic aligned frame (float32, NaN mask) with an optional Gaussian source of given flux and position | core, research, pipeline |
| `make_moving_series(n, start, velocity_px, flux, noise, seed)` | N frames with one source moving at a known sub-pixel velocity; returns frames and truth | shiftstack, inject, research |
| `make_fits_cutout(...)` | Tiny multi-extension FITS (IMAGE, FLAGS, VARIANCE, ZODI, PSF, WCS-WAVE) in bytes | gateway, core.flags/wcs, pipeline |
| `flags_with_bits(bits)` | Flag array with chosen bits set (SOURCE bit 21, others) | core.flags |
| `irsa_tap_fixture.json`, `irsa_tap_empty.json`, `irsa_tap_malformed.json` | Recorded or hand-built TAP responses (84-row case, empty, broken) | gateway |
| `FakeClock` | Controllable time | gateway, jobs, store, assistant |
| `FakeLLMClient` | Scripted stream and tool calls; records what it was sent | assistant |
| `stub_model.onnx` | Tiny ONNX model returning deterministic scores; plus a "bad shape" variant | rank |
| `mini_bundle/` | Two presets with frames, one search result, one experiment | demo, offline |
| `capabilities_off` | Settings with no model file, no LLM key, jobs enabled | api, frontend |

Rules: fixtures are tiny (arrays ≤ 64×64, ≤ 12 frames unless the test is about scale). Never commit real IRSA FITS files larger than a few tens of KB; record trimmed cutouts only. Recorded responses are scrubbed of anything that looks like a credential.

---

## 4. Case catalogue by layer

### 4.1 `orbitalis_core` (unit)

| ID | Case | Expected | Pri |
|---|---|---|---|
| CORE-FLG-01 | Default mask for every single-bit flag | All bits masked **except** SOURCE (bit 21 = 2,097,152) and FULLSAMPLE | P0 |
| CORE-FLG-02 | Apply default mask to an image | Masked pixels are NaN, never 0 | P0 |
| CORE-FLG-03 | Decode a combined flag value | Returns the exact set of named bits | P1 |
| CORE-WCS-01 | Wavelength at lookup nodes | Equals the table value; between nodes equals bilinear interpolation (own implementation) | P0 |
| CORE-WCS-02 | Pixel outside the table | `CoreError`, not extrapolation — `wavelength_at`/`bandwidth_at` raise `InvalidInputError`; `*_map` variants return NaN per-pixel and raise `EmptyResultError` if all pixels are outside (SDD D-23) | P1 |
| CORE-CAL-01 | Constant surface-brightness image through alignment | Output stays constant within 1% *(initial)*; unit remains MJy/sr | P0 |
| CORE-CAL-02 | Solid-angle map at 6.15″/px | ≈ 8.89 × 10⁻¹⁰ sr per pixel, within 1% | P1 |
| CORE-CAL-03 | Imaging pipeline output | Never has solid angle applied; only `spectrum` does | P0 |
| CORE-ALN-01 | Identity reprojection | Array unchanged within float tolerance; footprint all valid | P1 |
| CORE-ALN-02 | Known integer shift | Content shifts by exactly that many pixels; edge pixels NaN | P1 |
| CORE-STK-01 | Sigma-clipped combine with one outlier frame | Outlier rejected; NaN ignored; all-NaN pixel stays NaN | P0 |
| CORE-STK-02 | Difference of identical frames | Zero within tolerance; mask is the union of inputs | P1 |
| CORE-STR-01 | `fit_stretch` then `apply_stretch` | Deterministic for the same inputs; parameters unchanged after the freeze point | P0 |
| CORE-SHS-01 | Moving series, noise-free | Best trial velocity within 0.25 px/frame *(initial)* of truth; stacked peak at expected position | P0 |
| CORE-SHS-02 | Moving series with noise, fixed seed | Recovered velocity within 0.5 px/frame *(initial)*; stack SNR above threshold | P0 |
| CORE-SHS-03 | Pure noise, fixed seed | Number of candidates above threshold ≤ agreed bound (set at G1) | P1 |
| CORE-SHS-04 | Source shifted off the frame edge | Treated as missing (NaN), **no wrap-around** | P0 |
| CORE-SHS-05 | Frames with masked regions | Depth reduces there; stack not poisoned; no NaN leak into valid pixels | P0 |
| CORE-SHS-06 | Sub-pixel shift | Total flux preserved within 2% *(initial)* | P1 |
| CORE-SHS-07 | Work estimate | Equals trials × frames × pixels | P1 |
| CORE-CND-01 | Peak extraction on a score map with two peaks and a shoulder | Two candidates; neighbours de-duplicated; threshold respected | P1 |
| CORE-INJ-01 | `inject` | Input arrays byte-identical before and after (hash check); output is a copy | P0 |
| CORE-INJ-02 | Same seed twice; different seed | Identical outputs; different outputs | P1 |
| CORE-INJ-03 | Injected flux | Aperture sum at the injected position matches requested flux within 5% *(initial)* | P1 |
| CORE-INJ-04 | `match` on hand-made lists | Correct `recovered`, `missed`, `preexisting`, `spurious` assignment, including a detection that is also in the baseline | P0 |
| CORE-INJ-05 | `metrics` on a hand-computed set | Recall, precision (relative to injected), median position error and per-bin completeness equal the hand values exactly | P0 |
| CORE-RNK-01 | `load_model` with a missing path | Returns `None` (feature off), no exception | P0 |
| CORE-RNK-02 | `Ranker.score` with the stub model | Scores in [0, 1], each carrying `model_version`; order preserved | P0 |
| CORE-RNK-03 | Wrong cutout shape | `CoreError` | P1 |
| CORE-SPC-01 | `extract` on a series with known flux per wavelength | Sorted by wavelength; solid angle applied; errors propagated | P1 |
| CORE-CLS-01 | `classify` with too few points or low SNR | Returns `None` with reason `insufficient_data` | P0 |
| CORE-CLS-02 | `classify` near the edge of coverage | Never extrapolates beyond measured wavelength range | P1 |
| CORE-ERR-01 | Any all-NaN result | Raises `CoreError` (`ORB-CORE-002` at the API), never an empty success | P0 |

### 4.2 `gateway`

| ID | Case | Expected | Pri |
|---|---|---|---|
| GW-01 | Cutout URL construction | `{uri}?center={ra},{dec}d&size={deg}` with correct formatting and defaults (0.1°) | P0 |
| GW-02 | TAP request | Query uses the artifact/plane join with `CONTAINS(POINT('ICRS', ra, dec), p.poly)`; parameters encoded; ordering by time | P0 |
| GW-03 | Concurrency cap | With 20 simultaneous requests and limit 4, the observed in-flight count never exceeds 4 | P0 |
| GW-04 | Retry policy | Retries on 429, 5xx and timeouts with exponential backoff and jitter (fake clock); no retry on other 4xx | P0 |
| GW-05 | Retry limit | Gives up after 3 attempts with the right code | P1 |
| GW-06 | Circuit breaker | Opens after N consecutive failures; calls fail fast with `ORB-GW-003`; half-open after cool-down; closes on success | P0 |
| GW-07 | Single-flight | Five concurrent identical requests produce one upstream call; all callers get the result; one failure fails all consistently | P0 |
| GW-08 | TAP cache | Hit within TTL makes no upstream call; expired entry refetches | P1 |
| GW-09 | Timeouts | TAP and cutout timeouts map to `ORB-GW-004` | P1 |
| GW-10 | Non-FITS or truncated body | `ORB-GW-002`; nothing stored | P1 |
| GW-11 | Health | `ok`, `degraded`, `offline` follow the breaker and recent failure rate | P1 |
| GW-12 | Cutout URI host allowlist *(proposed addition; see §11)* | A TAP row pointing at a non-IRSA host is rejected and never fetched | P0 |
| GW-13 | Empty and malformed TAP | Empty gives an empty list; malformed gives `ORB-GW-001` | P1 |

### 4.3 `store`

| ID | Case | Expected | Pri |
|---|---|---|---|
| ST-01 | Migrations | Apply in order once; re-running is a no-op; recorded in `schema_migrations` | P0 |
| ST-02 | Concurrent writers via `write_tx()` | 50 concurrent writes complete with no "database is locked" | P0 |
| ST-03 | Repository round trips | fields, frames (with required `array_blob`), cutouts, groups, derived, jobs, candidates, experiments, events | P0 |
| ST-04 | Eviction | Over the cap: oldest cutouts go first, then oldest frames not in preset fields; preset fields and their jobs, candidates and experiments are untouched | P0 |
| ST-05 | Cascade | Deleting a field removes its jobs, candidates, experiments and trials | P1 |
| ST-06 | Events | Only the last N per stream are kept; replay from a `Last-Event-ID` returns the right slice | P0 |
| ST-07 | Disposable | Deleting the database file then starting the app recreates the schema and reloads the bundle | P0 |
| ST-08 | `field_id` | Same for any key order and whitespace; changes when any parameter changes | P0 |
| ST-09 | Frame without array | Rejected | P1 |

### 4.4 `jobs`

| ID | Case | Expected | Pri |
|---|---|---|---|
| JOB-01 | Status transitions | `queued → running → completed`, plus `failed` and `cancelled` paths; illegal transitions rejected | P0 |
| JOB-02 | Idempotent submit | Same kind, field and parameters return the existing job (and its stored result) | P0 |
| JOB-03 | Queue cap | Beyond `ORB_JOBS_QUEUE_MAX` raises `ORB-JOB-002`; running work unaffected | P0 |
| JOB-04 | Timeout | Job exceeding `ORB_JOB_TIMEOUT_S` becomes `failed` with `ORB-JOB-003` (fake clock) | P0 |
| JOB-05 | Cancel | Cancelling queued or running jobs ends them `cancelled`; partial results remain | P1 |
| JOB-06 | Restart sweep | Rows left `queued`/`running` by a previous process become `failed` with `ORB-JOB-004` at startup | P0 |
| JOB-07 | Progress throttling | No more than about 2 persisted updates per second | P2 |
| JOB-08 | Max running | With limit 1, a second job waits until the first ends | P0 |
| JOB-09 | Handler exception | Job fails with a code; the runner keeps processing the queue | P0 |
| JOB-10 | No subscribers | A job runs to completion with nobody connected | P0 |

### 4.5 `research` (handlers and policy)

| ID | Case | Expected | Pri |
|---|---|---|---|
| RS-01 | Stack policy | Compatible set accepted; each violation (release, detector, wavelength span, time span) rejected with `ORB-RS-002` and a reason per frame | P0 |
| RS-02 | Field not ready | Search on a field without enough frames raises `ORB-RS-001` before any work | P0 |
| RS-03 | Work budget | Over-budget request raises `ORB-RS-003` before computing | P0 |
| RS-04 | Search handler output | Stores candidates with `ordinal`, `status = unconfirmed`, `model_score = null` (when not ranked), stack PNG, motion vector, frames list with predicted positions | P0 |
| RS-05 | Ranking handler | Fills `model_score`, `model_version`, `predicted_category`; with no model raises `ORB-ML-001` and leaves candidates untouched | P0 |
| RS-06 | Validation handler | Runs baseline plus injections; every trial has an outcome class; `metrics_json` contains parameters and seed; same seed gives identical metrics | P0 |
| RS-07 | Validation honesty | Detections matching nothing known and absent from the baseline are `spurious`; those in the baseline are `preexisting`; none are called false positives in real data | P0 |
| RS-08 | Classification handler | Insufficient data completes the job with `{status: "insufficient_data", reason}` | P0 |
| RS-09 | No gateway | Handlers run with the gateway patched to raise; they still succeed from the store | P0 |
| RS-10 | Candidate id stability | Same field, parameters and position give the same `candidate_id`; `ordinal` stable per job | P1 |

### 4.6 `pipeline`

| ID | Case | Expected | Pri |
|---|---|---|---|
| PL-01 | State machine | `queued → running → completed/failed/cancelled`; retry and resubmit transitions | P0 |
| PL-02 | Cache first | When cutouts and frames exist, no gateway call is made | P0 |
| PL-03 | Order | Frames processed spread across time and wavelength first, then gaps filled | P1 |
| PL-04 | Stretch freeze | Parameters fit after `ORB_STRETCH_FIX_N` frames and identical afterwards | P0 |
| PL-05 | Shared build and grace | Two subscribers share one build; the last leaving starts the grace timer; the build is cancelled after `ORB_GRACE_S` (fake clock); re-subscribing in time keeps it | P0 |
| PL-06 | Caps | Beyond max frames, radius or active fields: `ORB-PL-002` or clamp as specified | P1 |
| PL-07 | Failing frames | Failed cutouts are skipped with a `warning`; `total` is reduced; the run still completes | P0 |
| PL-08 | Ladder | Breaker open: cached frames served; no cache: nearest preset from the bundle; no bundle: `ORB-SYS-002` | P0 |
| PL-09 | Event order | `snapshot` first; `found` before any `frame`; terminal `done` or `error` last | P0 |

### 4.7 `api` (contract)

| ID | Case | Expected | Pri |
|---|---|---|---|
| API-01 | Envelopes | Every success is `{data, meta}`; every failure `{error:{code, message, detail}}` | P0 |
| API-02 | Error mapping | Table-driven: each code in SDD Appendix B returns its HTTP status and body shape | P0 |
| API-03 | Idempotency | Repeated `POST /fields` and `POST /jobs` return the same ids | P0 |
| API-04 | SSE | Correct media type; `id` per event; `Last-Event-ID` replays the missed events; keep-alive comment appears (fake clock) | P0 |
| API-05 | Frame PNG | Luminance-plus-alpha mode; masked pixels have alpha 0 | P0 |
| API-06 | Candidates list | Sorted by `rank_value`; each has `status: unconfirmed`; `model_score` is an object with `model_version` or `null` | P0 |
| API-07 | `/capabilities` with nothing optional | No model file, no key: ranking, assistant, classification all `enabled: false`; Explorer endpoints all succeed | P0 |
| API-08 | CORS | Only configured origins allowed; no wildcard | P0 |
| API-09 | Input validation | Radius above cap, bad coordinates, unknown release: 422 with `ORB-API-001` and field details | P0 |
| API-10 | `/health` | Maps ladder rung to `ok`/`degraded`/`offline` | P1 |
| API-11 | OpenAPI snapshot | Generated schema equals the committed snapshot; a diff fails the build until the snapshot and SDD are updated | P0 |
| API-12 | Job endpoints | Poll and SSE agree; cancel on a finished job returns `ORB-API-003` | P1 |
| API-13 | Unknown ids | 404 `ORB-API-002` for field, frame, job, candidate, experiment | P1 |
| API-14 | No leakage | Error bodies never include stack traces or secrets; `ORB-SYS-001` includes a request id | P0 |

### 4.8 `assistant`

| ID | Case | Expected | Pri |
|---|---|---|---|
| AS-01 | Tool loop with the fake client | Tool calls reach read-only tools; results are passed back; the stream emits `token`, `tool_call`, `done` | P0 |
| AS-02 | Read-only | No registered tool can write, launch a job or call the gateway (inspect the tool registry; attempt via a malicious fake call) | P0 |
| AS-03 | Loop cap | Never more than `ORB_ASSISTANT_MAX_TOOL_ITERS` iterations | P0 |
| AS-04 | Limits | Per-IP rate limit returns `ORB-AS-002`; daily cap returns `ORB-AS-003` (fake clock) | P0 |
| AS-05 | Disabled | No key or provider: `/capabilities` says off; chat returns `ORB-AS-001`; nothing else affected | P0 |
| AS-06 | Secret handling | The key never appears in logs, responses or error details (capture logs, search for it) | P0 |
| AS-07 | Context ids | The client sends ids; the server resolves them; unknown ids produce an empty tool result and the model is told | P1 |
| AS-08 | Data not instructions | Tool output containing "ignore previous instructions" is passed as data inside the documented wrapper and does not change the tool set or limits | P0 |
| AS-09 | Grounding prompt | The system prompt sent to the model contains the grounding rules (unconfirmed, scores are predictions, figures only from tools) | P1 |
| AS-10 | Manual eval | Ten fixed questions on the demo field are graded by a human: figures match stored results, scores called predictions, "I don't have that" when data is absent | P1 |

### 4.9 `demo` and offline

| ID | Case | Expected | Pri |
|---|---|---|---|
| DM-01 | Bundle load | Loads through the normal repositories; fields marked `preset`; protected from eviction | P0 |
| DM-02 | Offline run | With `ORB_OFFLINE=1`, every preset opens; its stored search, candidates, ranking scores and experiment are all retrievable | P0 |
| DM-03 | Integrity | Manifest hashes match files; a corrupted file fails startup loudly, not silently | P1 |
| DM-04 | Bundle completeness | For every enabled feature, each preset has results (checked by a script before gates) | P0 |

### 4.10 Frontend (component, contract, E2E)

| ID | Case | Expected | Pri |
|---|---|---|---|
| FE-01 | Formatters | RA `10h 52m 04.2s`, Dec `+57° 28′ 11″` (arcsecond mark correct), galactic `l/b`, wavelength `1.70 µm`, ids `#042` | P0 |
| FE-02 | Galactic conversion | The field centre (RA 163.0175°, Dec +57.4697°) converts to l ≈ 149.39°, b ≈ +53.09° within 0.01° | P1 |
| FE-03 | Motion sentence | Generated from data; "sub-pixel" only when the real shift is under one pixel; ×1 button present | P0 |
| FE-04 | Capability gating | With all optional features off, no ranking column, no assistant launcher, no dead buttons | P0 |
| FE-05 | Error copy | Every code in UX doc §8.3 renders its wording from a fixture | P0 |
| FE-06 | Banned words | A scan of user-facing strings finds none of the banned words in UX doc §12.2 | P0 |
| FE-07 | Unconfirmed badge | Every candidate view (queue row, tooltip, drawer, table) shows it | P0 |
| FE-08 | URL state | Copying the URL and opening it in a fresh context restores field, frame, selection, view, system, exaggeration | P0 |
| FE-09 | Streaming layout | Frames arriving cause no layout shift above 0.1; scrubber ticks appear as `frame` events arrive; the candidate list does not reorder during a stream | P1 |
| FE-10 | Chat stream | Streamed `fetch` renders tokens, shows `tool_call` chips, supports Stop | P1 |
| FE-11 | Contrast and encoding | Tokens meet contrast; every category has shape plus text | P1 |
| FE-12 | Keyboard | Tasks T1–T3 completable without a mouse; map and scrubber key bindings work | P1 |
| FE-13 | Reduced motion | No autoplay or pulse; progress still updates | P2 |

#### End-to-end flows (mock mode unless stated)

| ID | Flow (UX doc §7) | Pass |
|---|---|---|
| E2E-F1 | First visit: preset → scrub → Candidates → open candidate → Methods | Reaches stack-vs-originals and the validation card with no console errors |
| E2E-F2 | New field from coordinates with streaming | Scrub works before `done`; `done` chip appears |
| E2E-F3 | Run search → review → compare → copy link | Job card goes through statuses; list appears on completion |
| E2E-F4 | Methods and limits experiment view | Metrics carry experiment label, parameters and seed |
| E2E-F5 | Assistant question | Context chip shown; streamed answer; footnote present |
| E2E-F6 | Degraded and offline | Banner text matches ladder; presets keep working |
| E2E-F7 | Shared link on a cold cache | "Rebuilding this view", then identical state |
| E2E-LIVE | One live smoke (manual): real TAP + one cutout + a preset | Completes within targets in §7.1 |

---

## 5. Must-not-regress list → tests

These come from SDD §12.3. A red test here blocks merge regardless of priority.

| # | Rule | Tests |
|---|---|---|
| 1 | SOURCE bit 21 not in default mask; all other bits are | CORE-FLG-01 |
| 2 | Masked pixels NaN in arrays, alpha 0 in PNGs | CORE-FLG-02, API-05 |
| 3 | Imaging stays MJy/sr; solid angle only in spectra | CORE-CAL-01, CORE-CAL-03 |
| 4 | `field_id` stable for identical parameters | ST-08 |
| 5 | Stretch fixed after the freeze point | CORE-STR-01, PL-04 |
| 6 | Gateway never exceeds configured concurrency | GW-03 |
| 7 | Observed, predicted and candidate positions are separate types | static type check plus RS-04; import-linter |
| 8 | `orbitalis_core` imports nothing from `orbitalis` | `lint-imports` |
| 9 | Cold start, empty cache, `ORB_OFFLINE=1` serves every preset with its stored results | DM-02 |
| 10 | Injection and validation never mutate stored data | CORE-INJ-01 |
| 11 | Candidates always `unconfirmed`; scores always with `model_version` | API-06, RS-04, FE-07 |
| 12 | Unmatched real detections are not false positives | CORE-INJ-04, RS-07, FE-06 |
| 13 | Shift-and-stack refuses incompatible sets and over-budget jobs | RS-01, RS-03 |
| 14 | No model file and no LLM key: app starts, features off, Explorer passes | API-07, FE-04 |
| 15 | Assistant tools are read-only | AS-02 |

---

## 6. Science validation (beyond unit tests)

Unit tests prove the code does what it says. These prove the **method** is worth showing.

| Check | How | Pass criterion | Gate |
|---|---|---|---|
| Recovery on synthetic series | Known-answer series at several fluxes and speeds | Completeness curve is monotonic in flux; recovery near the nominal threshold matches design | G1 |
| Injection into real cutouts | Validation job on a real preset field (200 injections cap) | Metrics stored with seed; reproducible; plausible position errors (sub-pixel to ~1 px) | G2 |
| Baseline sanity | Un-injected search on a real field | Candidate count reported honestly; none presented as findings | G2 |
| Ranking model check | Held-out synthetic set | Score separates injected from noise better than stack SNR alone, or the UI says it does not (decision by ML team) | G2 |
| Stack-policy sanity | Policy applied to a real frame list | Rejection reasons make sense to the ML engineer | G1 |
| Unit and flag spot-check | One frame compared against an independent astropy calculation | Wavelength, solid angle, mask agree | G1 |

The ML engineer signs these off; results go in the Methods and limits tab.

---

## 7. Non-functional tests

### 7.1 Performance (benchmarks, `bench` marker, run before each gate)

| Measure | Target *(initial)* | How |
|---|---|---|
| Preset first frame | < 1 s | Offline bundle, timed browser flow |
| Cold field first frame | < 20 s | Live smoke |
| Cold field, 80 frames | < 3 min | Live smoke |
| Moving-object search within the work budget | < 60 s | Benchmark on the target instance size |
| Ranking 100 candidates | < 10 s | Benchmark |
| Validation, 100 injections | < 5 min | Benchmark |
| Memory per active field | < 300 MB | Process memory during a build |
| Work-budget calibration | Choose `ORB_SEARCH_MAX_WORK` so a maximal allowed search meets the 60 s target | G1 benchmark; update Appendix A |

### 7.2 Resilience (fault injection with `respx`; one live drill)

| Fault | Expected behaviour |
|---|---|
| TAP timeout | `ORB-GW-004`; retries; ladder moves to cached or demo |
| 429 burst on cutouts | Backoff, lower effective concurrency, `warning` events, run completes |
| Persistent 500 | Breaker opens; `ORB-GW-003`; banner "showing cached data" |
| 20% of cutouts fail | Rung 2: frames skipped, `total` reduced, run completes |
| Truncated FITS | Frame skipped with `ORB-CORE-001` warning |
| Slow-drip response | Timeout fires; no stuck connections |
| Process restart mid-job | On startup the job is `failed` `ORB-JOB-004`; resubmission reuses stored work |
| Database file deleted | App rebuilds; bundle reloads; presets work |
| Cache full | Eviction frees space; presets untouched; no crash |

### 7.3 Load and soak

- 10 simultaneous viewers on one preset from the bundle: p95 frame fetch within target.
- 3 simultaneous cold fields (the cap) plus 1 running job: no timeouts beyond defined codes; memory below the instance limit.
- 30-minute soak with periodic scrubbing and one job every 5 minutes: no memory growth trend, no stuck jobs.

### 7.4 Security and abuse (proportionate to a hackathon)

| Check | Expected |
|---|---|
| CORS | Only the configured Vercel and local origins |
| Secret exposure | `ORB_LLM_API_KEY` absent from logs, responses, `/health`, `/capabilities`, client bundle |
| Input limits | Radius, frames, injections, tokens, message length all capped; oversized input returns 422 |
| SSRF | Gateway fetches only allowlisted IRSA hosts (GW-12) |
| Assistant abuse | Rate limit and daily cap hold; spend limit set at the provider |
| Dependency hygiene | `uv lock --check` passes; no unpinned runtime installs in the image |

### 7.5 Accessibility

Automated check on each page and key state, plus manual keyboard and screen-reader pass on F1–F3. Target WCAG 2.2 AA (UX doc §11). No serious issue open at G3.

---

## 8. UX acceptance and usability tests

Acceptance criteria A1–A10 (UX doc §15.1) map to cases:

| A-ID | Criterion | Cases |
|---|---|---|
| A1 | Preset < 1 s; cold field < 20 s | §7.1, E2E-LIVE |
| A2 | Newcomer finds top candidate and explains the score in 60 s | Usability T1 |
| A3 | "Unconfirmed" everywhere; no banned words | FE-06, FE-07 |
| A4 | No dead controls with features off | FE-04, API-07 |
| A5 | Offline works end to end | E2E-F6, DM-02 |
| A6 | URL restores state | FE-08, E2E-F7 |
| A7 | Keyboard-only T1–T3 | FE-12 |
| A8 | Contrast and automated accessibility | FE-11, §7.5 |
| A9 | No layout shift above 0.1 while streaming | FE-09 |
| A10 | Every error code has its wording | FE-05 |

**Usability sessions** (UX doc §15.2): five people outside the team, tasks T1–T5, think-aloud, run at G2 and G3. Record time, errors and quotes; fix the top three problems after each round. Success is "can state what the score means and that candidates are unconfirmed", not just reaching the screen.

---

## 9. Defects, triage and reporting

| Severity | Meaning | Rule |
|---|---|---|
| S1 | Breaks the demo, loses data, violates an honesty rule, leaks a secret | Fix before anything else; blocks the gate |
| S2 | Feature unusable or wrong results with a workaround | Must be fixed or the feature ships **disabled** by G3 |
| S3 | Wrong wording, cosmetic, edge case | Fix if cheap |
| S4 | Idea or polish | Backlog |

Every bug gets a failing test first, then the fix. A bug report states: steps, expected, actual, build or commit, mode (mock, offline, live), and screenshot or log. Test results at each gate are summarised in one short table: suites run, passed, failed, skipped, open S1/S2.

---

## 10. Gate exit criteria

| Gate | Must be green | Allowed to be open |
|---|---|---|
| **G1** (end of day 1) | CI stages 1–5 pass; all P0 cases for `core` (flags, wcs, calibration, stack, stretch), `gateway`, `store`, `pipeline`; one live smoke completes one field end to end; benchmark of the work budget recorded; synthetic shift-and-stack known-answer tests pass; contract snapshot committed (including U-05 and U-06 if accepted) | P1 and P2 cases; research, ranking, assistant tests may still be stubs |
| **G2** (mid-event) | Everything in G1; all P0 for `jobs`, `research`, `api`, `demo`, frontend flows F1–F4 in mock and live; validation run on a real preset with stored metrics; first usability round done | Ranking and assistant may be unfinished, but must be correctly **off** in `/capabilities` |
| **G3** (pre-demo freeze) | All P0 and P1 pass; must-not-regress list (§5) fully green; performance targets met or the limit documented; offline rehearsal (E2E-F6) passes; accessibility pass with no serious issue; second usability round done; no open S1; no open S2 on an **enabled** feature | P2 cases; S3/S4 |

At G3 any feature failing its P0/P1 cases is switched off through `/capabilities` and removed from the demo script, not shipped half-working.

---

## 11. Open items and assumptions

| ID | Item | Owner |
|---|---|---|
| T-01 | Initial tolerances marked *(initial)* are guesses; set from real runs at G1 | ML engineer |
| T-02 | Noise-only candidate bound (CORE-SHS-03) needs the threshold chosen by the ML team (SDD D-14/D-17) | ML engineer |
| T-03 | **Proposed SDD addition:** gateway host allowlist (`ORB_IRSA_ALLOWED_HOSTS`) so TAP-provided URIs cannot point elsewhere (GW-12). Add to SDD §6.2 and Appendix A if accepted | Lead |
| T-04 | Recorded IRSA fixtures need one live capture session; trim and scrub them | Backend |
| T-05 | OpenAPI snapshot depends on UX gaps U-02, U-04, U-05, U-06, U-12 being decided | Lead, frontend |
| T-06 | Browser automation tool and visual-snapshot approach depend on the frontend stack | Frontend |
| T-07 | Live smoke needs organizers' confirmation that IRSA calls during the event are acceptable at our concurrency (SDD D-02) | Lead |
| T-08 | Assistant manual evaluation set (AS-10) needs the demo field and questions fixed (UX-2, UX-8) | ML engineer |
