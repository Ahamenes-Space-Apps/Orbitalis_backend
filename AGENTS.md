# AGENTS.md — ORBITALIS

Instructions for AI coding agents working in this repository. Read this file first, every session. It is short on purpose; the full design lives in the documents listed in §1.

---

## 1. What this project is

ORBITALIS is a web tool for the NASA Space Apps challenge **"Planet X and SPHEREx"** (HackAthlone, 13–15 Nov 2026). A visitor picks a patch of sky, watches SPHEREx observations stream in from NASA's IRSA archive, scrubs through time and wavelength, searches for faint moving objects (shift-and-stack), reviews ranked **unconfirmed** candidates against the original frames, and reads how well the method performs (injection-and-recovery validation). An optional assistant answers questions grounded in stored results.


### Source-of-truth documents (in precedence order)

| Doc | Decides |
|---|---|
| PRD | What and why |
| Data & Science Specification | Science rules (flags, units, what may be combined) |
| **SDD v1.1** (`ORBITALIS_SDD.md`) | How: architecture, modules, data, API, errors, testing |
| UX Design & User Flows | Screens, states, copy, formats, accessibility |
| ML Pipeline & Features brief (ML team) | Feature scope: shift-and-stack, ranking, validation, assistant, spectra |

If two documents disagree, follow the higher one and **log the conflict in SDD Appendix D** (backend) or the UX doc section 13 (frontend/API). Never silently pick.

---

## 2. Ground rules (non-negotiable)

1. **uv, never pip.** Add dependencies with `uv add` / `uv add --dev`. Commit `uv.lock` with `pyproject.toml`. Training libraries (torch, onnx) go in the `ml` group only and never in runtime dependencies or the Docker image.
2. **`orbitalis_core` is pure.** It imports numpy/scipy/astropy/etc. only. No FastAPI, httpx, SQLite, settings, files or environment. It takes arrays and returns arrays.
3. **One door to IRSA.** Only `gateway` talks to the archive. Everything else reads from `store`.
4. **One door to SQL.** Only `store` writes SQL. Writes go through `store.db.write_tx()`. No ad-hoc `commit()`.
5. **The database is disposable.** Never put anything irreplaceable in SQLite. Deleting the file must always be safe.
6. **Long work is a job**, not a request handler. Use the in-process job runner (`jobs`). Do not add brokers, queues, worker services, Redis, gRPC, object storage, accounts or auth. SDD §1.3 lists the non-goals.
7. **Optional means optional.** The Explorer must work with no model file and no LLM key. ML ranking, the assistant and spectral classification are capability-flagged. Unfinished features ship **disabled**, never half-working.
8. **Honest science.** Candidates are `unconfirmed` (there is no confirmed state). A model score is a prediction and always travels with `model_version`. Unmatched detections in real data are **not** "false positives". See §6.
9. **No secrets in code, logs, tests, fixtures or commits.** The only real secret is `ORB_LLM_API_KEY`.
10. **Tests never touch the network.** Mock IRSA with `respx`. Live tests are marked `@pytest.mark.live` and skipped by default.

---

## 3. Commands

```bash
uv sync --locked                                   # install runtime + dev from uv.lock
uv run uvicorn orbitalis.main:app --reload --port 8080   # run the API
uv run pytest                                      # run tests (offline, < 60 s)
uv run ruff check . && uv run ruff format .        # lint and format
uv run lint-imports                                # module-boundary check
uv lock --check                                    # lock is current (CI)
uv add <pkg>            # runtime dependency (justify it in the PR)
uv add --dev <pkg>      # dev dependency
uv sync --locked --group ml                        # ML team only: training tools
uv run python scripts/bake_demo.py                 # regenerate demo_bundle from live IRSA
ORB_OFFLINE=1 uv run uvicorn orbitalis.main:app --port 8080   # demo bundle only, no IRSA
```

**Before you say you are done:** `uv run ruff check . && uv run lint-imports && uv run pytest`. Report the result honestly; do not claim a check passed that you did not run.

---

## 4. Repository map and module rules

```text
src/orbitalis_core/   PURE science: wcs, flags, calibration, align, stack, stretch,
                      shiftstack, candidates, inject, rank, spectrum, classify
src/orbitalis/        application layer
  api/        HTTP only: validate, call, shape response, map errors. No science, no SQL, no IRSA.
  gateway/    IRSA: TAP, SIA2, cutouts. Semaphore, retries, circuit breaker, single-flight, TAP cache.
  pipeline/   Builds a field: gateway + core + store. Emits SSE events.
  jobs/       Generic in-process job runner. Knows statuses and progress, nothing about science.
  research/   Job handlers: search, ranking, validation, classification. Reads store, calls core.
  assistant/  LLM client protocol, read-only tools, knowledge pack, rate/budget limits.
  store/      SQLite repositories, migrations, WAL, eviction.
  overlays/   Known objects and Planet X hypothesis overlays.
  demo/       Demo-bundle loader (same repositories as everything else).
  eventbus.py Shared per-stream broadcaster with replay.
config/       presets.yaml, releases.yaml, stack_policy.yaml (values owned by ML team), knowledge/
models/       candidate_cnn.onnx + card (optional at runtime)
ml/           training and experiments (ml group; not in the image)
demo_bundle/  pre-baked fields, candidates, experiments (generated; do not hand-edit)
tests/        mirrors src; fixtures are tiny synthetic arrays
```

### Allowed imports (enforced by import-linter)

- `orbitalis_core` → nothing from `orbitalis`.
- `gateway` → no `store`, `pipeline`, `api`, `jobs`, `research`, `assistant`.
- `store` → no `gateway`, `pipeline`, `api`.
- `api` → `pipeline`, `jobs`, `research` (submit only), `assistant`, `store` (read). Never `gateway`.
- `jobs` → generic; never imports `research`. Handlers are registered in `main.py` (composition root).
- `research` → `orbitalis_core`, `store`, job context type. Never `gateway`, `api`, `assistant`.
- `assistant` → `store` (read-only) and read side of `jobs`. Never `gateway`, `pipeline`, `research`. It cannot launch jobs.
- `eventbus` → imports nothing from the app.

### Uniform module shape

Each application module has: `__init__.py` (public surface only), `schemas.py` (pydantic models owned by the module), a service/runner file, optional `errors.py`. Other modules import from the package `__init__`, never deep files. **Every file starts with a header docstring:** *Purpose / Inputs / Outputs / Called by.* Ruff enforces `D100`/`D104`.

---

## 5. Roles

Agents work in one role at a time. Stay inside the role's files; if the task needs another role's files, say so and make the smallest necessary change, or stop and ask.

| Role | Owns | Tools and skills it uses | Responsible for |
|---|---|---|---|
| **Core science** | `orbitalis_core/*`, `tests/core` | numpy, scipy, astropy, reproject, photutils, onnxruntime; synthetic FITS fixtures | Correct, deterministic, side-effect-free functions; typed `CoreError`s; tests first |
| **Gateway & pipeline** | `gateway/*`, `pipeline/*`, `eventbus.py` | httpx, respx, asyncio; TAP/SIA2 knowledge from SDD §6.2 | Concurrency cap, backoff, breaker, single-flight, SSE order, cache-first behaviour |
| **Store & jobs** | `store/*`, `jobs/*`, `demo/*`, migrations | aiosqlite, SQL migrations | Schema, repositories, one write path, eviction, job ledger, restart sweep, bundle loader |
| **Research (ML plumbing)** | `research/*`, `config/stack_policy.yaml` consumers, `ml/*`, `models/*` | numpy, onnxruntime, torch (ml group) | Handlers, stack-policy checks, work budget, validation outcomes, model loading |
| **API** | `api/*`, `errors.py`, OpenAPI | FastAPI, sse-starlette, pydantic | Contract-first schemas, envelopes, error mapping, SSE protocol, capabilities |
| **Assistant** | `assistant/*`, `config/knowledge/*` | LLM provider SDK behind `LLMClient`, fake client for tests | Read-only tools, grounding rules, rate limits and daily cap, graceful disable |
| **Frontend** | the frontend repo/folder | Framework-agnostic; generated OpenAPI client; mock mode | Screens and states per the UX doc, honesty copy, formatters, accessibility |
| **Release** | `Dockerfile`, CI, deploy docs | docker, gcloud, HF Space config | Image builds with `--locked`, env vars, `/health` and `/capabilities` checks. **Deploys only when the human asks.** |

---

## 6. Honesty and vocabulary (code, API, UI, docs)

Use these words exactly. They are the shared language (SDD Appendix E).

| Say | Never say |
|---|---|
| **Field** (a requested sky region) | job, query, scene |
| **Frame** (one exposure/detector cutout) | image (ambiguous), slice |
| **Group** (frames combined by a rule); **stack** is the operation | "stack" as the entity |
| **Candidate** (unconfirmed moving-object possibility) | discovery, detection as a confirmed thing, object, source |
| **Job** (`queued`, `running`, `completed`, `failed`, `cancelled`) | task, run (for jobs) |
| **Experiment**, **injection**, **model score** (with `model_version`) | test, simulation, confidence/probability (unless calibrated) |
| **Observed**, **predicted**, **candidate** positions are three separate types | mixing them in one field or column |
| **Hypothesis overlay** (Planet X predicted positions) | "candidate overlay" |

Rules that code and tests must uphold:

- Every candidate has `status: "unconfirmed"`. No other value exists in v1.
- A model score is `{value, model_version, kind: "model_prediction"}`, never a bare number. `null` when no model ran.
- In validation experiments the outcome classes are `recovered`, `missed`, `preexisting`, `spurious`. Precision is "relative to injected sources in this experiment". Every result carries `experiment_id`, parameters and seed.
- Spectral results are an estimate with supporting data, or `{status: "insufficient_data", reason}`. Never a guess.
- Shift-and-stack refuses frame sets that violate `stack_policy.yaml` (`ORB-RS-002`) and searches that exceed the work budget (`ORB-RS-003`).

---

## 7. Science and data rules

- **Flags:** default mask is every bit **except** SOURCE (bit 21, value 2,097,152) and FULLSAMPLE. Masked pixels are **NaN** in arrays and **alpha 0** in PNGs, never zero.
- **Units:** imaging stays in **MJy/sr** (surface brightness) so interpolation and combination remain valid. Apply the solid-angle map **only** when extracting spectra. (Deviation from DS spec §7, logged as SDD D-03.)
- **Wavelength:** own bilinear interpolation of the WCS-WAVE lookup; output in µm.
- **Frames from one field share one common grid.** Alignment is flux-conserving for surface brightness.
- **Never mutate input arrays.** Injection and validation work on copies. Same seed gives the same result.
- **Stretch is fixed** after the first N frames (`ORB_STRETCH_FIX_N`). No per-frame re-stretching.
- **No crossfade between frames** (each has its own wavelength and detector).
- **Do not invent science values.** Stack-policy numbers, motion ranges and units, CNN training data and spectral templates belong to the ML team (SDD D-14, D-17, D-18, D-19). If a value is missing, use a clearly named placeholder constant, mark it `# TODO(ML):`, and list it in your summary.
- **IRSA facts are partly unverified.** Anything tagged **[VERIFY]** in the SDD (TAP columns, release filters, `time_bounds_lower` meaning, safe concurrency, ephemeris source) must not be treated as settled. Write code so the assumption is in one place.

---

## 8. API and error conventions

- Base path `/api/v1`. Success `{data, meta}`; error `{error:{code, message, detail}}`. IDs are opaque strings. Timestamps ISO-8601 UTC. Coordinates ICRS degrees. Wavelengths µm.
- Error codes are `ORB-{MODULE}-{SEQ}` from SDD Appendix B. Exceptions carry a code; **mapping to HTTP happens in one place** (`errors.py`), never in routers.
- `POST /fields` and `POST /jobs` are **idempotent** (`field_id` / `job_id` are deterministic hashes of canonical parameters).
- SSE: `snapshot`, `found`, `frame`, `progress`, `warning`, `done`, `error`, with `id` for `Last-Event-ID` replay and a 15 s keep-alive. Chat is `POST` with its own stream (`token`, `tool_call`, `done`, `error`).
- **Contract-first:** change `api/schemas.py` first, open the PR early, tell the frontend what changed. The generated OpenAPI is the contract, and the frontend mock is generated from it.
- Never return raw exceptions or stack traces. Unexpected errors become `ORB-SYS-001` with a request id.

---

## 9. Frontend rules (UX doc is the spec)

- Follow the UX Design & User Flows doc. Fixed strings, formats and tokens live there (sections 9, 10, 12).
- **Never imply confirmation.** Show "Unconfirmed" on every candidate view. Banned words in user-facing strings: *confirmed, discovery, found a planet, false positive* (outside experiments), *confidence* (unless calibrated).
- Gate features on `GET /capabilities`. Missing features disappear; no dead controls.
- State in the URL (`ra, dec, r, rel, f, t, sel, view, sys, exag, layers`). Stream progress and chat never go in the URL.
- Encode meaning with shape **and** text, not colour alone. Text contrast at least 4.5:1. Respect `prefers-reduced-motion`.
- Use shared formatters for RA/Dec (`10h 52m 04.2s`, `+57° 28′ 11″`), wavelength (`1.70 µm`), time (ISO date, MJD in tooltip), ids (`#042` from `ordinal`).
- Chat is a POST stream, so use streamed `fetch`, not `EventSource`. Field and job streams are GET and may use `EventSource`.
- Develop against **mock mode** (generated from OpenAPI + demo-bundle fixtures); the "mock API" banner shows only there.
- Any need the API cannot meet is a **U-number** in the UX doc section 13. Do not invent endpoints; propose them.

---

## 10. Workflows

### A. Add or change an endpoint
1. Write the test (`tests/api`) for the envelope, error codes and idempotency.
2. Change `api/schemas.py`, then the router. Router calls a service; it does no science or SQL.
3. Register new error codes (see E). Update SDD §8 and UX doc §9.1 if the contract changed.
4. Tell the frontend: what changed and whether it is breaking.

### B. Add or change a core science function
1. Write the test first with a tiny synthetic array or FITS fixture; include a known-answer case.
2. Implement in `orbitalis_core` as a pure function. Raise typed `CoreError`s. All-NaN output is an error, not a result.
3. Header docstring. No I/O, no settings.
4. Add a must-not-regress test if it enforces a rule from §6 or §7.

### C. Add a job kind
1. Add the handler in `research/` (reads `store`, calls `core`, writes through `store` repositories).
2. Validate preconditions up front (`ORB-RS-001/002/003`) before doing work. Check `ctx.check_cancelled()` between units of work; report `ctx.progress(...)`.
3. Register it in `main.py`. The job ID must be idempotent over `(kind, field_id, canonical params, input data version)`.
4. Add the result to the demo bundle script if the Research Lab should work offline.

### D. Add a table or column
1. New numbered SQL file in `store/migrations/` (forward-only). The DB is disposable, so a reset is acceptable during the hackathon, but still write the migration.
2. Repository function and a `tests/store` test. No SQL outside `store`.
3. Update SDD §7.4.

### E. Add an error code
Add to `errors.py` and SDD Appendix B (code, HTTP, meaning), add its UX wording to UX doc §8.3, add a test that the handler maps it.

### F. Add a dependency
`uv add`, one-line justification in the PR, note in SDD Appendix D if it affects image size or the runtime (for example onnxruntime). Heavy training libraries go in `ml`.

### G. Change the gateway
Keep concurrency, retry, breaker and single-flight in `gateway/limiter.py`. Update `tests/gateway` with `respx` including a failure mode. Defaults come from Appendix A env vars, not literals.

### H. Regenerate the demo bundle
Run `scripts/bake_demo.py` against live IRSA, review the diff, commit the output. Never hand-edit files in `demo_bundle/`. The bundle must contain results for every feature that is enabled.

### I. Fix a bug
Reproduce with a failing test first. Fix. Keep the test. If the cause was a wrong assumption in the SDD, correct the SDD.

---

## 11. Definition of done

- [ ] Tests added and green offline; ruff and import-linter clean.
- [ ] Header docstrings present on new files.
- [ ] Schema, error-code registry, SDD or UX doc updated if touched.
- [ ] No new dependency without a note; `uv.lock` committed.
- [ ] App still starts with no model file and no LLM key; `/capabilities` is correct.
- [ ] `ORB_OFFLINE=1` still serves every preset from the bundle.
- [ ] No banned words in user-facing text; candidates still `unconfirmed`.
- [ ] Your summary lists what you ran, what you did not run, and any `[VERIFY]` or `TODO(ML)` you relied on.

---

## 12. Git, PRs, and when to stop and ask

- Trunk-based: short-lived branches, PR to `main`, squash merge. Commit messages are imperative with a scope prefix: `core:`, `gateway:`, `store:`, `api:`, `pipeline:`, `jobs:`, `research:`, `assistant:`, `ui:`.
- **Do not commit, push, deploy, or change cloud settings unless the human asks.** Never force-push. Never rewrite history others have pulled.
- Keep PRs small and single-purpose. Describe *what changed, why, how it was tested, and what is unverified.*

**Stop and ask the human when:**
- A task needs something forbidden in §2 (a queue, a database server, auth, a new external service).
- A document conflict cannot be resolved by the precedence order.
- A science value, unit convention or threshold is missing and not safe to guess.
- A change would break the API contract the frontend already uses.
- You would need a secret, a deploy, or live-archive access you were not given.

**Never:** fabricate data or results, weaken a test to make it pass, hide a failing check, widen the work budget or concurrency to "fix" timeouts without benchmarking, or present a model score as a finding.

---

## 13. Quick reference

| Thing | Value |
|---|---|
| Python | 3.12 (`.python-version`) |
| Package manager | uv |
| Web | FastAPI + uvicorn, SSE via `sse-starlette` |
| Storage | SQLite (WAL), disposable, cap `ORB_CACHE_MAX_MB` (400) |
| IRSA concurrency | `ORB_IRSA_CONCURRENCY` (4, to be benchmarked) |
| Jobs | one running, queue of 10, timeout 600 s |
| Search budget | `ORB_SEARCH_MAX_WORK` (2e9 pixel-shifts, to be benchmarked) |
| Ranking model | `models/candidate_cnn.onnx` (missing means feature off) |
| Assistant | off unless `ORB_LLM_PROVIDER` and `ORB_LLM_API_KEY` are set |
| Hosting | Cloud Run (1 instance, `min-instances=1`) during the event; Hugging Face Space after ~10 Dec; frontend on Vercel |
| Gates | G1 end of day 1, G2 mid-event, G3 pre-demo freeze (unready features ship disabled) |
