# ORBITALIS — UX Design & User Flows

Nov 3, 2026 · @zahir

## 1. Purpose and inputs

This document turns the frontend team's Explorer mock into a full UX design for ORBITALIS: every screen, flow and state, tied to the SDD v1.1 endpoints, plus the gaps that must be settled before screens are final.

It is stack-agnostic. React, Next, Nuxt or anything else works; the doc defines behaviour, data and wording, not components or libraries. The design is desktop-first (judges will use laptops), with a graceful tablet and read-only phone view.

| Input | What this doc takes from it |
| --- | --- |
| PRD | Audience (judges, curious public, researchers), the challenge's required behaviour (RA/Dec entry, image series, movers), optional extras (spectra, overlays, URL coordinates). |
| Data and Science Spec | Flag policy, units, what "combine" may mean, release handling. |
| SDD v1.1 | The API contract: `/fields`, `/jobs`, `/candidates`, `/experiments`, `/capabilities`, `/assistant/chat`, error codes, vocabulary (Appendix E). |
| ML Pipeline and Features brief | Two work areas (Explorer, Research Lab) plus an assistant; Research Lab = shift-and-stack, candidate ranking, validation, spectra. |
| Frontend mock (screenshot) | The look and layout the team already chose: top bar, candidate queue, sky map with markers, filter chips, motion-exaggeration slider. Running on a mock API against a synthetic validation field. |

**How to read it.** Mock elements are tagged **Keep**, **Change** or **Add**. A need the SDD cannot serve yet is tagged **U-nn** and collected in section 13. Endpoints appear as `GET /path`; everything under `/api/v1`.

## 2. UX principles

The design optimises for one outcome: a judge sees a believable moving-object candidate within a minute, understands why it is ranked, and cannot mistake a prediction for a discovery.

1. **Never a blank screen.** Presets load in one click; a new field shows a skeleton, then frames as they stream, then results. Partial data is a normal state, not an error.
2. **Honest by construction.** Candidates are *unconfirmed*; a score is a *model prediction* with a version; unmatched real detections are not "false positives". The wording is part of the interface, not decoration (section 12).
3. **Originals one click away.** Any stacked or ranked result can be compared with the original frames it came from, at the predicted position.
4. **Every number explains itself.** Hover or focus shows unit, source and, for scores, what produced them. No unlabelled figures.
5. **Shape, colour and text together.** Moving = solid ring, variable = dashed ring, each also labelled. Nothing relies on colour alone.
6. **Optional features disappear cleanly.** `GET /capabilities` decides what is shown. A missing model or LLM key hides ranking scores or the assistant; it never leaves a dead control.
7. **State lives in the URL.** Coordinates, release, time position, selected candidate and sky view are in the address, so a link reproduces the screen (a challenge extra: embeddable coordinates).
8. **Motion is truthful.** Real shifts are often sub-pixel, so the UI may exaggerate motion but must say by how much and show the real figure computed from data.
9. **Works offline from the bundle.** If the archive is down the UI says so once, then behaves normally on demo data.

## 3. The frontend mock

The mock gets the hard part right, a dense honest sky view beside a ranked queue, but it covers one of the five things a visitor must do and shows classes the SDD cannot yet produce.

&#91;image: Frontend team's Explorer mock: candidate queue, sky map with moving and variable markers, motion slider\]

### 3.1 Annotated inventory

| # | Element in the mock | Decision | Backed by |
| --- | --- | --- | --- |
| 1 | Top bar: logo, tabs Explorer / Candidates / Methods and limits | **Keep.** Mapped to the ML brief's areas in section 4. | n/a |
| 2 | Banner "Synthetic validation field · ground truth known · mock API" | **Keep, make data-driven.** One mode banner: synthetic, live, cached, demo. "mock API" shows in dev builds only. | `GET /health`, `GET /fields/{id}` (`preset`), `GET /experiments/{id}` |
| 3 | Cursor readout `RA 10h 52m 04.2s · Dec +57° 28' 11°` | **Keep, fix** the arcsecond mark (shows ° instead of ″). | frame WCS (U-05) |
| 4 | Equatorial / Galactic toggle | **Keep.** Frontend-only conversion; axes relabel. | none |
| 5 | Candidate queue panel, "ranked by score S", collapse chevron | **Change.** Remove the duplicated header, define S, add an "unconfirmed" cue. | `GET /fields/{id}/candidates` |
| 6 | Filter chips All 31 / Moving 11 / Variable 20 | **Change.** Moving maps to SDD candidates. Variable has no SDD source (U-01). | candidates list, `meta` counts |
| 7 | "Hide known objects" toggle | **Keep.** Known objects are muted markers when shown. | `GET /fields/{id}/overlays/known` (shape: U-08) |
| 8 | Ranked rows: rank, `#042`, class tag, score and bar | **Change.** Add basis (model score or stack SNR), "unconfirmed", short id from `ordinal` (U-12). | candidate list |
| 9 | Map layer chips: Stationary 509 / Moving 11 / Variable 20 / Trails | **Change.** Move to a layer control that never covers map content. Stationary needs a source list (U-01). | candidates; trails from `frames` |
| 10 | Markers: solid orange ring = moving, dashed purple ring = variable, larger glow = selected | **Keep** the encoding; add text labels at readable contrast and a motion arrow. | candidate position |
| 11 | Slider "Motion exaggerated ×25 so it is visible. Real shifts are sub-pixel." | **Keep.** The sentence must be computed from data, not hard-coded (U-11). | candidate `motion`, frame `mjd` |
| 12 | Sky view toggle Aladin Lite / Simple | **Keep both.** Aladin = online HiPS context; Simple = offline canvas using our own frames. Both need the field's WCS (U-05). | `GET /fields/{id}` grid |
| 13 | Zoom +/−, reticle button | **Keep.** Reticle recentres on the field, or on the selection if one exists. | none |
| 14 | Axes: RA ticks on top (east left), Dec ticks on left | **Keep, fix.** Top ticks repeat `10h 53m` three times; add seconds at this zoom and label every other tick. | frame WCS |

### 3.2 Defects to fix before wiring real data

- The panel header "Candidate queue · ranked by score S" appears twice (panel title and list title).
- The layer chips sit on the map and the marker `187` overlaps the "Stationary" chip.
- "Score S" is undefined, and a bare `0.92` on a progress bar reads as a verdict. It must say *model prediction* and which model.
- Purple marker labels measure roughly 2.5 to 3.4:1 against the map background in the screenshot (a JPEG, so approximate), below the 4.5:1 needed for small text. Lighten them (section 10).
- Dec readout uses ° where ″ is meant (see row 3).

### 3.3 What the mock does not cover yet

| Needed (PRD, challenge, SDD) | In the mock? | Designed in |
| --- | --- | --- |
| Enter an object name or RA/Dec; pick a preset | No | 5.1 |
| See observations as an image series with a time and wavelength scrubber | No | 5.3 |
| Field build progress while data streams in | No | 5.2, 8 |
| Per-frame metadata: date, wavelength, detector, flags | No | 5.3 |
| Run a moving-object search; watch job progress | No | 6.1 |
| Candidate detail: stack versus original frames, motion, spectrum | No | 6.2 |
| Validation results and limits (tab exists, content does not) | Partly | 6.3 |
| AI assistant panel with selection as context | No | 6.4 |
| Degraded, offline and error states | No | 8 |
| Shareable URL state | No | 4.3 |

## 4. Information architecture

Three tabs, one persistent assistant panel, and a URL that reproduces the screen. The tab names are the frontend team's; each maps to an area in the ML brief and to specific SDD endpoints.

### 4.1 Tabs and what they are for

| Tab | ML brief area | Job to be done | Main endpoints |
| --- | --- | --- | --- |
| Explorer | Explorer | Pick or enter a field, watch observations arrive, scrub through time and wavelength, see candidates and known objects on the sky. | `GET /presets`, `GET /resolve`, `POST /fields`, `GET /fields/{id}/events`, `/frames/*`, `/overlays/{kind}`, `/candidates` |
| Candidates | Research Lab (search and review) | Run a moving-object search, optionally rank, review the list, compare stack with original frames, open a spectrum. | `POST /jobs`, `GET /jobs/{id}`, `GET /fields/{id}/candidates`, `GET /candidates/*`, `GET /fields/{id}/spectrum` |
| Methods and limits | Research Lab (validation) and About | Explain the method in plain words, show validation experiments, the model card, the stack policy and what the tool cannot claim. | `GET /experiments/*`, `GET /capabilities`, `GET /releases` |
| Assistant (panel) | Assistant | Ask about whatever is selected; answers grounded in stored results. | `POST /assistant/chat` |

A spectrum is not a tab. It opens from a selected candidate or from a clicked sky position, in the detail drawer (section 6.2).

### 4.2 Always-visible chrome

- **Field chip** (new): name or coordinates, radius, release, for example `RA 10h52m Dec +57°28′ · r 0.1° · QR2`. Click opens field entry (5.1).
- **Mode banner** (kept): synthetic, live, cached or demo, from field state and health.
- **Cursor readout** and **Equatorial / Galactic** toggle (kept).
- **Assistant launcher**: a docked button; hidden when the assistant is disabled.
- **Capability-aware menu items**: only features that `GET /capabilities` reports as enabled.

### 4.3 URL state

The address is the source of truth for navigation. Because `POST /fields` is idempotent by parameters, a link can carry parameters instead of an id and still work on any machine.

| Parameter | Meaning | Example |
| --- | --- | --- |
| `ra`, `dec`, `r` | ICRS degrees and radius in degrees | `ra=163.017&dec=57.469&r=0.1` |
| `rel` | Data release | `rel=qr2` |
| `f` | `field_id` once known (optional) | `f=9f2c1a7b3d4e5f60` |
| `t` | Selected frame, as `frame_ref` | `t=qr2.2025W…D3` |
| `sel` | Selected candidate | `sel=c_41ab…` |
| `view` | `aladin` or `simple` | `view=simple` |
| `sys` | `eq` or `gal` | `sys=eq` |
| `exag` | Motion exaggeration | `exag=25` |
| `layers` | Comma list of visible layers | `layers=moving,trails` |

Stream progress, job progress and chat history are never in the URL.

### 4.4 Capability gating

| `GET /capabilities` says | The UI does |
| --- | --- |
| `ranking.enabled = false` | Queue sorted by stack SNR and titled "ranked by stack SNR"; no model score column; no Run ranking control. |
| `assistant.enabled = false` | Launcher hidden; nothing else changes. |
| `classification.enabled = false` | Spectrum shows measurements only; no spectral-type estimate section. |
| Queue full (`ORB-JOB-002`) | Run buttons disabled with a short reason and retry hint. |
| Health `offline` | Demo banner; presets only; Run search enabled only if the bundle holds results for that preset. |

## 5. Explorer screens

The Explorer takes a visitor from nothing to frames streaming over a sky map with candidates on top in three interactions: choose a field, watch it build, scrub through it.

### 5.1 Field entry (Add)

Shown as the landing state when the URL has no field, and as a popover from the field chip.

- **Search box** accepts an object name or coordinates (degrees, or `10h52m04s +57d28m11s`). The client parses coordinates itself; names call `GET /resolve?q=` after a short pause and offer suggestions. A resolved result shows the coordinates and a "Use these" button.
- **Radius** selector (0.05°, 0.1° default, 0.25°, up to the server cap, 0.5°). Values above the cap are clamped with a one-line reason.
- **Release** selector from `GET /releases`.
- **Preset cards** from `GET /presets`: name, one line on why it is interesting, thumbnail. The challenge's test targets (Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis) are the suggested set. A preset opens in about a second from the demo bundle.
- **Submit** calls `POST /fields`, updates the URL, opens the event stream. `ORB-API-001` errors appear inline under the offending input.

### 5.2 Field build, streaming

The screen is never empty while data arrives. Each SSE event has a defined visual effect.

| Event | What the visitor sees |
| --- | --- |
| `snapshot` | Any cached frames appear at once; the scrubber ticks for them are filled. |
| `found` | Header line "Found 84 observations" and a progress bar at 0 of 84. If it takes longer than 10 s, the line reads "Archive is slow, still trying". |
| `frame` | A filled tick appears on the scrubber at its date. The first frame fades in over the skeleton; later frames never move the view or change the stretch. |
| `progress` | Stage text such as "Downloading cutouts, 23 of 84" beside the bar. |
| `warning` | A quiet counter ("2 skipped") that opens a log drawer. No modal. |
| `done` | The bar collapses to a chip: `84 frames · QR2 · 14 Jun to 28 Oct`. Run search becomes available. |
| `error` | An inline panel with the plain-language reason and a Retry button. Frames already received stay usable. |

If the visitor leaves, the stream closes and the backend stops after a short grace period. Returning to the same URL resumes through the idempotent `POST /fields` and `Last-Event-ID` replay, with the note "Loading resumed".

### 5.3 Sky view and frame viewer

Layers, bottom to top:

1. Background: Aladin Lite (online context) or Simple (dark canvas, works offline).
2. Frame image: the selected frame PNG, placed by the field's common WCS (U-05). Masked pixels are transparent.
3. Known objects, muted (`overlays/known`).
4. Hypothesis overlay for Planet X, dotted (`overlays/hypothesis`).
5. Candidate markers: solid ring = moving, dashed ring = variable (U-01), selected = larger with halo.
6. Trails (path of a candidate across frames).
7. Cursor readout and axes.

**Layer control** is a collapsible panel docked beside the map, not chips on top of it. It holds the layer toggles with counts, opacity for the frame image, Trails, and Hide known objects (the same switch as in the queue).

**Scrubber** (Add), a bar along the bottom:

- A track with one tick per frame, ordered by **Time** (default) or **Wavelength**, switchable. Hollow ticks are frames not loaded yet; clicking one shows a spinner and "waiting for this frame".
- Play and pause, speed 1 to 8 frames per second, step with the arrow keys.
- A frame chip: date, wavelength in µm, detector, release. A Flags button shows `flags.png` over the frame.
- **Show** selector: *Single frame*, *Group* (from `GET /fields/{id}/groups`, by wavelength band or time window) or *Difference* (`/diff.png` with two pickers, a and b). The original frames always stay available.
- The stretch is fixed after the first frames, so playback does not flicker. A small label states it.

**Candidate markers while scrubbing.** At frame time *t* a marker is drawn at `position + k × rate × (t − t_ref)` along its motion direction, where *k* is the exaggeration slider. The marker for the stack epoch sits at the detected position; `t_ref` must come from the API (U-04).

**Interactions**

- Click a marker or a queue row: select. The URL updates, the row and marker highlight together, the detail drawer opens (6.2).
- Hover a marker: tooltip `#042 · moving · model 0.92 · unconfirmed`.
- Click empty sky: a small popover with coordinates (copy) and "Spectrum here" when a spectrum can be extracted (`GET /fields/{id}/spectrum?ra=&dec=`).
- Scroll or +/− zoom; the reticle recentres on the selection, or the field if nothing is selected.
- If Aladin Lite fails to load or the archive is offline, the view switches to Simple with a toast.

### 5.4 Candidate queue (Keep, Change)

- One header: **Candidates** with the subtitle "unconfirmed · ranked by model score (cnn-0.1)", or "ranked by stack SNR" when no model ran. The collapse chevron stays.
- Filter chips: All N, Moving N and, only if U-01 is accepted, Variable N. A sort menu: Score, SNR, Rate, Ordinal.
- **Row**: rank, `#ordinal`, class tag, rate in arcsec per day, then the score. Model scores show a bar on a fixed 0 to 1 scale; SNR shows a number only, so a stack SNR is never compared against a model probability. A second line gives SNR and the number of frames used.
- Hover a row to highlight its marker; selecting a row selects the marker.
- **Empty, no search yet:** "No search has been run for this field." with a Run moving-object search button (disabled with the reason until the field has built, `ORB-RS-001`).
- **Empty, search found nothing:** "No moving-object candidates above threshold. That is a valid result; see Methods and limits for how sensitive the search is."
- Lists over 200 rows are virtualised.

## 6. Candidates, detail, methods and assistant

These screens carry the ML team's work: run a search, judge the results against the original data, read how well the method performs, and ask questions in plain language.

### 6.1 Candidates tab: run a moving-object search

A wide layout: search panel on the left, results in the centre, detail drawer on the right when a row is open. The Explorer queue (5.4) is the compact form of the same list.

**Search panel**

- **Field**: defaults to the current field.
- **Frames**: "All compatible frames (N)" by default. "Choose frames" lists frames; ones the stack policy rejects are greyed with the reason from the `ORB-RS-002` detail. The original frames are never hidden.
- **Motion range**: a two-handle rate slider in arcsec per day and a position-angle range (full circle by default), with named presets. Preset values wait on the ML team (D-17).
- **Grid density**: Coarse, Normal, Fine. A too-large request returns `ORB-RS-003`; the form keeps its values and says "narrow the motion range or radius" (U-07 asks the API for an estimate so this can be shown before running).
- **Rank after search**: a checkbox, shown only if `ranking.enabled`.
- **Run** calls `POST /jobs` (`moving_object_search`). The same settings on the same field return the existing job and its results, so the UI says "Showing results from an earlier identical run".

**Job card** (under the form): a status chip (`queued`, `running`, `completed`, `failed`, `cancelled`), a progress bar with the stage name from `progress.stage`, elapsed time, and Cancel. Poll `GET /jobs/{id}` every second, or use `GET /jobs/{id}/events`. A failed job shows its code in plain words (section 8) and a Run again button. A job list for the field (`GET /jobs?field_id=`) lets people reopen earlier runs.

**Results table** columns: rank, `#ordinal`, class, RA and Dec, rate, position angle, stack SNR, model score (with version in the column header), frames used, an open button. Actions: copy link, download CSV (built in the browser from the list response).

### 6.2 Candidate detail

A right-hand drawer in the Explorer and a split pane in Candidates. Header: `#042`, class, an **Unconfirmed** badge that is always visible, position, and buttons Select on map, Copy link, Ask assistant.

1. **Stack versus originals** (the main view). Left: `GET /candidates/{id}/stack.png`, captioned "Shift-and-stack of 41 frames at 12.4″/day". Right: the original frame cutout at the predicted position (`GET /candidates/{id}/frames/{frame_ref}.png`) with a crosshair, a frame stepper (arrow keys), a Blink button that alternates first and last frame, and a filmstrip of all frames (lazy-loaded thumbnails). Whether the source is visibly shifting in the originals is the visual evidence; the UI never states it.
2. **Motion.** Rate, position angle, start and end position, time baseline in days, and the **real displacement over that baseline in arcsec and pixels**, computed from the data. This is the source of the "real shifts are sub-pixel" sentence beside the slider (U-11).
3. **Scores.** Stack SNR with a one-line definition. Model score with `model_version` and predicted category, plus a "What does this mean?" popover: "A prediction from a model trained on synthetic sources. It ranks candidates for inspection and does not confirm them." `null` shows "Not ranked".
4. **Spectrum** (only when available). Chart of flux against wavelength in µm with error bars. If `classification.enabled` and enough data exist, an estimated spectral type with its probabilities, labelled *estimate*; otherwise "Not enough data for a spectral type" with the reason. A moving object's spectrum must follow its path through the frames, which `GET /fields/{id}/spectrum?ra=&dec=` cannot do (U-09).
5. **Provenance.** Job id, search parameters, release, stack policy used, model version, and the frame list (date, wavelength, detector). A Copy as text button gives a block someone can paste into notes.

Loading shows skeletons. Frames not yet stored show "not loaded" in the stepper rather than failing the whole view.

### 6.3 Methods and limits

The tab where credibility is earned. A sticky table of contents on the left, sections with anchors.

1. **What ORBITALIS does.** The five core steps (search, retrieve, check quality, prepare, display) and shift-and-stack in a short plain paragraph with one small illustration.
2. **Data.** The release in use, the flag policy in one sentence, and the stack policy values: what is combined and what never is. Source: `GET /releases` and the policy (U-10).
3. **Validation.** One card per experiment from `GET /fields/{id}/experiments`: label, parameters, seed, date. Inside: recall, precision relative to injected sources, position error, and completeness against brightness and against speed as two line charts (a table of counts below with the outcome classes recovered, missed, preexisting, spurious). A fixed line states *Results apply to this experiment only.* A Run validation button starts a `validation` job for people who want to see it run.
4. **Model.** Model card: version, input size, how the training examples were made, intended use, known failure modes (U-10).
5. **Limits.** A fixed list: candidates are unconfirmed; scores are predictions; real shifts are often sub-pixel; QR2 and QR3 differ and DR1 reprocessing is expected; only the selected field and release are searched; unmatched detections in real data are not called false positives; spectral types need enough coverage; confirmation needs independent follow-up outside this tool.
6. **Credits.** NASA, IRSA and SPHEREx acknowledgement with the data release versions in use.

### 6.4 Assistant panel

A right-hand dock available in every tab, opened from the launcher and hidden when `assistant.enabled` is false.

- **Context chips** at the top show what the answers will use: field, frame, candidate, job, experiment. Defaults to the current selection and updates when it changes, with an inline note in the transcript. Each chip can be removed. The client sends ids only (`POST /assistant/chat` with `context`).
- **Starter prompts** depend on the selection: "Why is #042 ranked first?", "What does 1.7 µm mean here?", "How was this validated?", "What can this tool not tell me?"
- **Streaming**: text appears as `token` events arrive; a `tool_call` event shows a chip such as "looked up candidate #042". A Stop button aborts the stream. The client uses a streamed `fetch` because the call is a POST (D-21).
- **Linking**: `#ordinal` and frame references in answers become links that select that object, but only if it exists in the loaded data.
- **Standing footnote**: "AI answer based on this field's stored results. Candidates are unconfirmed." The panel also notes that messages go to a hosted model provider.
- **Errors**: `ORB-AS-002` "Too many questions; try again in a minute", `ORB-AS-003` "The daily assistant limit is used up; it resets tomorrow", `ORB-AS-001/004` "The assistant is unavailable right now", and the rest of the app keeps working.
- Chat history lives in memory for the session, with a Clear button. There are no accounts.

## 7. User flows

Seven flows cover the product. The main journey, a visitor going from a field to candidates to evidence, is drawn first; the table gives every flow with its failure branches.

&#91;embedded content: main journey · 11 steps in 3 rows\]

Read the rows left to right, then right to left, then left to right. The highlighted step, comparing the stack with the original frames, is the one that turns a ranked number into evidence.

### 7.1 Flow catalogue

| ID | Flow | Steps | Ends when | If it goes wrong |
| --- | --- | --- | --- | --- |
| F1 | First visit (judge) | Landing, open a preset, scrub frames, open Candidates, open one candidate, read Methods and limits | The visitor has seen stack beside originals and the validation card | Archive offline: demo banner, same path on bundled data |
| F2 | New field from coordinates | Field entry, type or paste a name or RA/Dec, `POST /fields`, event stream, scrub while frames arrive | The `done` chip appears | `ORB-API-001` inline; `ORB-PL-002` retry later; slow archive note; partial frames stay usable |
| F3 | Moving-object search and review | Candidates tab, set motion range and frames, Run, watch the job card, review the queue, open a candidate, compare, copy the link | A candidate has been compared with its originals | `ORB-RS-001/002/003` inline; failed or timed-out job offers Run again; queue full disables Run briefly |
| F4 | Check how good the method is | Methods and limits, pick an experiment, read recall, precision and completeness, optionally Run validation | The visitor can state what the numbers apply to | No experiment yet: "No validation run for this field" with Run validation, or a link to the synthetic field |
| F5 | Ask the assistant | Select a candidate, open the dock, choose a starter question, read the streamed answer, follow a linked reference | An answer is shown with its context chip | `ORB-AS-001/002/003/004` messages; the rest of the app is unaffected |
| F6 | Degraded or offline session | Health turns `degraded` or `offline`, banner appears, visitor continues on cached or demo data | The visitor can finish the demo | Last rung `ORB-SYS-002`: full-page retry |
| F7 | Open a shared link | URL parameters, idempotent `POST /fields`, state restored (frame, selection, view) | The screen matches the sender's | Field no longer cached: "Rebuilding this view" and a normal build |

## 8. States, feedback and degradation

Every wait, partial result and failure has a defined look. Fields and jobs share one status vocabulary, so the interface uses the same five words everywhere.

### 8.1 Status chips

| Status | Chip text and icon | Meaning to the visitor |
| --- | --- | --- |
| `queued` | Queued, clock | Accepted, waiting for a free slot. |
| `running` | Running, animated bar | Working; the stage name is shown. |
| `completed` | Completed, check | Finished; results are ready. |
| `failed` | Failed, cross | Stopped with a reason and a Retry or Run again action. |
| `cancelled` | Cancelled, dash | Stopped on request; partial results stay. |

Each chip carries text and an icon, never colour alone.

### 8.2 Degradation banners

The mode banner follows `GET /health` and the SDD's degradation ladder. One line, polite live region, dismissible for the session but it returns if the state changes.

| Ladder rung | Health | Banner text | What changes |
| --- | --- | --- | --- |
| 0 to 1 | `ok` | none (slow-archive notes appear in the build header only) | nothing |
| 2 | `degraded` | "Some observations could not be downloaded (3 of 84). Results use the rest." | Chip with a log link; counts reflect what loaded. |
| 3 | `degraded` | "The archive is not responding. Showing cached data." | Amber banner; Run search still works on cached frames. |
| 4 | `offline` | "Archive unavailable. Showing demo data." | Presets only; Run search only where the bundle holds results. |
| 5 | error `ORB-SYS-002` | Full-page: "ORBITALIS can't load its demo data. Try again." | Retry button; nothing else is shown. |

### 8.3 Error codes in plain words

The API returns `{error:{code, message, detail}}`. The UI maps the code to its own wording and never shows raw `message` text as the only explanation.

| Code | Shown as | Wording | Recovery |
| --- | --- | --- | --- |
| `ORB-API-001` | Inline | "Check the highlighted fields." | Fix and resubmit. |
| `ORB-API-002` | Panel | "We can't find that item. It may have been cleared." | Rebuild from the URL parameters. |
| `ORB-API-003` | Toast | "That run has already finished." | None needed. |
| `ORB-GW-001`, `-002`, `-004` | Toast or inline | "The archive didn't respond in time." | Retry. |
| `ORB-GW-003` | Banner | "The archive is busy; pausing requests for a moment." | Automatic retry. |
| `ORB-PL-001` | Panel | "Processing failed for this field." | Retry; copy details. |
| `ORB-PL-002` | Panel | "Too many fields are being built right now. Try again in a minute." | Retry button after a delay. |
| `ORB-PL-003` | Inline | "Loading was cancelled." | Resume button. |
| `ORB-ST-001`, `-002` | Toast | "Storage problem; results may load slower." | Retry. |
| `ORB-CORE-001` | Warning counter | "One observation file was unreadable and was skipped." | None. |
| `ORB-CORE-002` | Panel | "No usable pixels remain here after quality masking." | Choose another region. |
| `ORB-OV-001` | Layer note | "Known-object overlay is unavailable right now." | Layer disabled. |
| `ORB-JOB-002` | Inline | "The analysis queue is full. Try again in a minute." | Run disabled briefly. |
| `ORB-JOB-003` | Job card | "The search took too long and was stopped. Narrow the motion range or use fewer frames." | Run again. |
| `ORB-JOB-004` | Job card | "The server restarted during your search. Run it again; earlier work is kept." | Run again. |
| `ORB-RS-001` | Inline | "Wait for the field to finish loading before searching." | Button enables on `done`. |
| `ORB-RS-002` | Inline list | "Some selected frames can't be combined:" followed by the reasons. | Edit selection. |
| `ORB-RS-003` | Inline | "That search is too large. Narrow the motion range, radius or density." | Edit form. |
| `ORB-ML-001` | Note | "Ranking isn't available; results are ordered by stack SNR." | None. |
| `ORB-ML-002` | Note | "Ranking failed; candidates are shown unranked." | Retry ranking. |
| `ORB-AS-001`, `-004` | Panel | "The assistant is unavailable right now." | Rest of app unaffected. |
| `ORB-AS-002` | Panel | "Too many questions; try again in a minute." | Wait. |
| `ORB-AS-003` | Panel | "The daily assistant limit is used up; it resets tomorrow." | None. |
| `ORB-SYS-001` | Panel | "Something went wrong on our side." Shows a copyable request id from `detail`. | Retry. |
| `ORB-SYS-002` | Full page | See 8.2. | Retry. |

### 8.4 Loading and waiting rules

- Acknowledge every action within 100 ms (pressed state, optimistic chip). Show a spinner only after 300 ms.
- After 10 s of waiting, say what is happening ("Archive is slow, still trying"). After 60 s, offer Keep waiting or Cancel.
- Skeletons keep the layout stable: a dark map placeholder with a faint grid, grey queue rows, an empty scrubber track.
- Streaming never moves things under the cursor. New frames append to the scrubber. The candidate list changes only when a job completes, not row by row.
- A first visit to a preset shows a one-time hint: "Demo data, loaded instantly. Enter coordinates to query the live archive."

## 9. Data-to-UI contract

Every screen element has one source in the SDD, and every displayed quantity has one format. Where the SDD has no source yet, the item points to a U-number in section 13.

### 9.1 Endpoint to component matrix

| Endpoint | Used by | When called | Notes |
| --- | --- | --- | --- |
| `GET /health` | Mode banner | On load, then every 30 s and after any failure | Rung to banner (8.2). |
| `GET /capabilities` | App shell | On load | Gates ranking, assistant, classification, job limits. |
| `GET /releases`, `GET /presets` | Field entry, Methods | Once, cached |  |
| `GET /resolve` | Field entry | Debounced typing | Falls back to a local name list server-side. |
| `POST /fields` | Field entry, URL load | Every navigation to a field | Idempotent; safe to repeat. |
| `GET /fields/{id}` | Field chip, scrubber init, map grid | After the POST, and on reload | Needs the common grid (U-05). |
| `GET /fields/{id}/events` | Build progress | While building or while a build is live | `Last-Event-ID` resume. |
| `GET /fields/{id}/frames/{ref}.png`, `/meta`, `/flags.png` | Frame viewer | On scrub; prefetch the next two frames | Frame list for reloads is missing (U-06). |
| `GET /fields/{id}/groups`, `/groups/{gid}.png`, `/diff.png` | Show selector | On choice |  |
| `GET /fields/{id}/overlays/{kind}` | Layers | On first toggle on | `known`, `hypothesis`; payload shape U-08. |
| `POST /jobs`, `GET /jobs/{id}`, `/events`, `/cancel`, `GET /jobs?field_id=` | Candidates tab | On Run, then poll or stream | Four job kinds. |
| `GET /fields/{id}/candidates`, `/candidates/{id}`, `/stack.png`, `/frames`, `/frames/{ref}.png` | Queue, detail | On job completion; on open |  |
| `GET /fields/{id}/experiments`, `/experiments/{id}` | Methods | On tab open |  |
| `GET /fields/{id}/spectrum` | Sky popover | On click | Candidate spectrum missing (U-09). |
| `POST /assistant/chat` | Assistant | On send | Streamed `fetch`. |

### 9.2 Formats and units

| Quantity | Display | Notes |
| --- | --- | --- |
| Right ascension | `10h 52m 04.2s`; degrees in the tooltip | ICRS. Axes add seconds when zoomed in. |
| Declination | `+57° 28′ 11″` | Fix the mock's ° in place of ″. |
| Galactic | `l 149.391°, b +53.089°` | Three decimals. Client conversion only. |
| Field size | Degrees when 0.1° or more, arcmin below |  |
| Time | `2025-06-14`; full UTC time and MJD in the tooltip |  |
| Wavelength | `1.70 µm` | Two decimals. |
| Image brightness | MJy/sr | Spectrum units come from the API; confirm in the DS spec. |
| Rate and angle | `12.4″/day`, `83° (east of north)` | Convention pending (D-17). |
| Scores | Model `0.92` with version; stack SNR `6.1` | Never on the same scale. |
| Candidate id | `#042`, zero-padded `ordinal` | Full `candidate_id` in copy and provenance. |
| Detector | `D3` |  |

### 9.3 Motion exaggeration and the real-shift sentence

The sentence beside the slider is generated, not typed.

- Displayed offset at frame time *t*: `k × rate × (t − t_ref)`, with *k* from the slider.
- Real shift over the field: `rate × (t_last − t_first)`, shown in arcsec and in pixels of the field grid.
- Text: "Motion exaggerated ×25. Real shift over this field's 48 days: 0.4 px (2.5″)." If the real shift is a pixel or more: "Real shifts are visible at this scale."
- Default *k* is the smallest value that makes the largest candidate move about 3 pixels on screen, capped at 100. A ×1 "true motion" button is always present.

### 9.4 Coordinates and projection

- The map uses the field's common tangent-plane grid (reference point, pixel scale, rotation, size). Frame PNGs are already aligned to it by the backend, so placing an image is a single fixed transform and the client needs no per-frame WCS.
- RA increases to the left. Axes and the cursor readout derive from the same grid.
- Equatorial and Galactic: a fixed rotation matrix in the client (no library). The API stays ICRS only. Switching relabels the axes and grid lines and converts marker positions.
- Aladin Lite is set from the field centre and size. Simple view draws the field outline and our frames only.

### 9.5 Images

- Frame PNGs are luminance plus alpha. Alpha 0 means masked and must stay transparent. A "show masked pixels" option draws a faint hatch.
- The stretch is fixed on the server after the first frames. The client may offer brightness and contrast sliders as a display curve only; it never re-stretches per frame.
- Prefetch the next two frames when scrubbing, keep up to 50 decoded frames in memory, and cancel pending fetches when the user scrubs quickly.
- A pixel-value readout under the cursor needs the `/array` endpoint; it is optional and depends on the image contract decision (D-06).

## 10. Visual system and motion

Keep the mock's night-sky look. The tokens below were sampled from the screenshot, so treat them as starting values; two are corrected because the sampled purple fails contrast for small text.

### 10.1 Colour tokens

| Token | Value | Use | Contrast on map background |
| --- | --- | --- | --- |
| `bg.map` | `#10182b` | Sky area | n/a |
| `bg.panel` | `#0c1220` | Side panels | n/a |
| `bg.bar` | `#090d18` | Top bar | n/a |
| `bg.row.selected` | `#16203b` | Selected queue row | n/a |
| `bg.control` | `#1c2540` | Active segmented control, banner | n/a |
| `text.primary` | `#e8ecf6` | Headings, values | 14.96:1 |
| `text.secondary` | `#9aa3b8` | Labels, axes | 6.99:1 |
| `text.muted` | `#7b8499` | Hints, 14 px and above only | 4.72:1 |
| `accent.moving` | `#feb832` | Moving rings, selected halo, slider handle (sampled) | 10.20:1 |
| `accent.variable` | `#a5a1f0` (**proposed**) | Variable rings and labels. The mock's sampled purple is about `#7a76c3`, roughly 3.4:1 or lower. | 7.54:1 |
| `state.ok` | `#5fd0a8` (proposed) | Completed chip icon | 9.33:1 |
| `state.error` | `#ff6b6b` (proposed) | Failed chip icon, error text | 6.37:1 |

The hypothesis colour is chosen at build time and checked with the same contrast calculation.

### 10.2 Encodings

Every category is distinguished by shape and label as well as colour.

| Meaning | Shape | Colour | Label |
| --- | --- | --- | --- |
| Moving candidate | Solid ring | `accent.moving` | `#042` |
| Variable (if U-01 accepted) | Dashed ring | `accent.variable` | `#023` |
| Stationary source (if U-01 accepted) | Small filled dot, no ring | `text.secondary` | none |
| Known object | Small hollow diamond | `text.muted` | Name on hover |
| Planet X hypothesis | Open square on a dotted path | a cool hue distinct from the above | Name on hover |
| Selected | Larger ring, halo, thicker stroke | same as its class | Always labelled |
| Trail | Thin line fading towards earlier frames, arrowhead at the latest | same as its class | none |
| Masked pixel | Transparent; optional faint hatch | n/a | Legend entry |

### 10.3 Type and layout

- Sans-serif for text; monospace with tabular numerals for coordinates, ids and scores, as in the mock.
- Sizes: map labels 12 px or more, body 14 px, queue primary text 15 px.
- Layout: top bar 56 px; queue panel 280 to 320 px and collapsible; detail drawer 360 to 420 px; scrubber 72 px; the map takes the rest. **Nothing overlays the map**: every control is docked to a panel edge.
- Below 1100 px the queue becomes a bottom sheet and the drawer a full-height overlay.

### 10.4 Motion

- Hover and press 120 ms; frame fade-in 200 ms; panel slide 300 ms.
- **No crossfade between frames during playback.** Each exposure has its own wavelength and detector, and blending two of them would draw an image that never existed.
- `prefers-reduced-motion`: no autoplay, no pulses, progress still updates without animation.
- A marker pulses once when newly selected, then stays still.

## 11. Accessibility and responsive behaviour

The target is WCAG 2.2 AA. The candidate queue is the accessible twin of the map: anything possible on the map is possible from the list.

### 11.1 Requirements

| Area | Requirement |
| --- | --- |
| Contrast | Text 4.5:1 (large text 3:1); non-text UI parts 3:1. Tokens in 10.1 are checked before build. |
| Colour independence | Shape and text carry every category (10.2). |
| Keyboard | All controls reachable; visible 2 px focus ring. Order: top bar, queue, map, scrubber, drawer, assistant. |
| Map keys | Focus the map: arrows pan, `+`/`−` zoom, Tab cycles candidates in rank order, Enter opens detail, Esc closes the drawer or popover. Scrubber: left/right step, Space play or pause. |
| Screen readers | The map region has a live text summary ("31 candidates, 11 moving"); markers have labels; frame images get alt text from metadata ("SPHEREx frame, 1.70 µm, 14 Jun 2025, detector 3"); each chart has a "View as table" switch. |
| Live regions | Build progress announced at most every 10 percent (polite); errors assertive; banners polite. |
| Flashing | Playback starts paused. Default 2 frames per second, maximum 8, with a note that high speeds flicker. |
| Touch targets | At least 24 px, 44 px on touch devices. |
| Zoom and reflow | Usable at 200 percent text size; panels reflow at 400 percent zoom. |
| Time limits | None. Jobs run on the server and can be reopened. |

### 11.2 Responsive behaviour

| Width | Layout | Available |
| --- | --- | --- |
| 1280 px and up | Queue left, map centre, drawer right, scrubber bottom, assistant dock | Everything |
| 1100 to 1279 px | Drawer and assistant overlay the map | Everything |
| 768 to 1099 px | Queue as a bottom sheet; touch pan and pinch zoom | Everything |
| Below 768 px | Single column, read-only | Presets, frames and scrubber, candidate list and detail, Methods. Run search and Run validation show "Open on a larger screen to run analyses." The assistant is a full-screen sheet. |

## 12. Microcopy and honesty language

Wording does scientific work the interface cannot, so these strings are fixed and shared by every screen. Tone: plain, short, second person.

### 12.1 Fixed strings

| Where | Text |
| --- | --- |
| Candidate badge, always visible | **Unconfirmed** |
| Queue subtitle, ranked | "Ranked by model score (cnn-0.1). Unconfirmed." |
| Queue subtitle, unranked | "Ranked by stack SNR. Unconfirmed." |
| Model score tooltip | "A prediction from a model trained on synthetic sources. It helps rank candidates for inspection. It does not confirm anything." |
| Stack SNR tooltip | "Signal-to-noise of the combined image at this position along this path." |
| Moving tag tooltip | "Position changes across observations at a consistent rate." |
| Variable tag tooltip (if U-01) | "Brightness changes across observations." |
| Synthetic banner | "Synthetic validation field. Sources were injected with known positions and brightness." |
| Live, cached, demo banners | "Live archive data · QR2" / "Cached data" / "Demo data" |
| Validation footer | "Results apply to this experiment only." |
| Precision caption | "Precision is measured against the sources injected in this experiment." |
| Real-data note | "Detections in real data that match nothing known are listed as candidates, not as errors." |
| Spectrum, estimate | "Estimate" label on any spectral type; otherwise "Not enough data for a spectral type" with the reason. |
| Assistant footnote | "AI answer based on this field's stored results. Candidates are unconfirmed." |

### 12.2 Words to use and avoid

| Use | Avoid |
| --- | --- |
| candidate, possible mover | discovery, found a planet, confirmed |
| model score, prediction | confidence, probability (unless calibrated) |
| recovered, missed, spurious (in experiments) | false positive (in real data) |
| stack SNR | significance, detection level |
| archive, data release | server, backend |
| "the search" | "the AI" for non-ML steps |

### 12.3 One-line glossary (tooltips)

| Term | Gloss |
| --- | --- |
| SPHEREx | NASA's infrared all-sky survey telescope; each exposure sees the sky at a different wavelength. |
| RA / Dec | Sky coordinates, like longitude and latitude. |
| Wavelength | The colour of infrared light, in micrometres (µm). |
| Detector | One of the instrument's six cameras. |
| Release (QR2) | A versioned batch of processed data from the archive. |
| MJy/sr | Surface brightness: how much infrared light arrives from a patch of sky. |
| Shift-and-stack | Shifting images to follow a guessed path, then adding them, so a faint mover can stand out. |
| Injection | Adding an artificial source with known properties to real data, to test the search. |
| Completeness | The share of injected sources that the search recovered. |

## 13. Gaps versus the SDD

The design needs fourteen changes or decisions the SDD v1.1 does not cover. Two block real data on the map (U-05, U-06), and one decides whether the mock's Stationary and Variable classes exist at all (U-01). Accepted items go into SDD v1.2 with a change-log row.

| ID | The UI needs | SDD v1.1 today | Proposed change | Priority | Owner |
| --- | --- | --- | --- | --- | --- |
| U-01 | Stationary and Variable classes (mock shows 509 and 20) | Only moving candidates and a model `predicted_category` | **Decision.** Recommend v1 = Moving only plus known objects, and the chips for the other classes hidden. Stretch: `GET /fields/{id}/sources` returning stationary sources from detection on the combined image, with a variability index from per-frame photometry. | Decision | Lead, ML eng |
| U-02 | A defined "score S" for ordering and display | `model_score` can be null; `stack_snr` always present | Candidate list returns `rank_value {value, basis: model_score or stack_snr}` and `meta.sorted_by`. | High | Lead |
| U-03 | To view the synthetic validation field with truth (the mock's whole scenario) | Experiments store metrics and trial rows, no map view | Make the showcase trial a viewable synthetic field (`synthetic: true`, preset) with overlay kind `truth` (injected position, path, outcome per source). | High | ML eng, Backend 2 |
| U-04 | Marker positions at each frame time | Candidate `frames_json` holds predicted x/y only | Add `motion.reference_mjd` and `predicted_ra`, `predicted_dec` per frame. | High | Lead |
| U-05 | To place images and draw axes | No grid or WCS in any response | `GET /fields/{id}` returns `grid {center ra/dec, pixel_scale_arcsec, rotation_deg, width, height}`; `stack.png` and per-frame cutouts return `extent {center, size}`. | **Blocker** | Backend 2 |
| U-06 | A frame list for the scrubber after a reload | Frames only arrive as SSE events or one by one | `GET /fields/{id}/frames` with `frame_ref, mjd, wavelength_um, detector, release, has_png`, sorted by time. | **Blocker** | Backend 2 |
| U-07 | To warn before a too-large search | `ORB-RS-003` only after submit | `GET /capabilities` or `POST /jobs/estimate` returns `{work, budget, ok}` for given parameters. | Medium | Lead |
| U-08 | A payload for known and hypothesis overlays | Kinds named, no shape | `{items:[{id, name, type, ra, dec, path?:[{mjd, ra, dec}]}], source, as_of}`; moving known objects need a path or an `?mjd=` parameter. | Medium | Backend 2 |
| U-09 | A spectrum for a moving candidate | `GET /fields/{id}/spectrum?ra=&dec=` is fixed-position | `GET /candidates/{id}/spectrum` follows the predicted path; points carry `wavelength_um, flux, flux_err, unit, frame_ref`. Depends on D-19. | Medium | ML eng |
| U-10 | Methods content that cannot drift from the code | Not exposed | `GET /methods`: stack policy, flag policy, model card, release notes. | Medium | Lead |
| U-12 | A short stable id for display (`#042`) | Hash `candidate_id` only | Add `ordinal`, 1-based per job, in detection order. | Low | Lead |
| U-13 | A mock server that matches the real API | Frontend uses a hand-built mock | Generate the mock from the FastAPI OpenAPI schema; fill with demo-bundle fixtures; validate responses against the schema in tests. | High | Frontend, Lead |
| U-14 | Reliable links from assistant answers | Plain text stream | The `done` event carries `references` (ids the answer mentions). | Low | Backend 2 |
| U-15 | Words for the model's `predicted_category` | `source`, `noise`, `artefact` | Fixed UI strings: "Looks like a source", "Looks like noise", "Looks like an artefact", shown beside the model score. Confirm with the ML team. | Medium | ML eng, Frontend |

U-11 (the real-shift sentence) needs no API change of its own; it is computed once U-04, U-05 and U-06 exist. It replaces the mock's hard-coded sentence.

## 14. Frontend implementation notes

These notes hold for any framework. They say what the code must do, not which library does it.

### 14.1 Four kinds of state

| State | Lives in | Rule |
| --- | --- | --- |
| Navigation | URL (4.3) | Source of truth; links reproduce the screen. |
| Server data | A cache keyed by endpoint and ids | Fetched on demand, never edited locally. A typed client is generated from the SDD's OpenAPI. |
| Streams | Reducers fed by SSE or streamed fetch | Field and job streams are GET and can use the browser's `EventSource` with automatic `Last-Event-ID`. Chat is a POST and needs a streamed `fetch` parser. |
| UI | Component state | Panel open, hover, slider values (the slider value is also in the URL as `exag`). |

### 14.2 Structure

- **App shell**: top bar, mode banner, capability provider (`/capabilities`, `/health`), assistant dock.
- **Explorer page**: field entry; sky view made of background, frame, overlay, marker, trail and readout layers; layer panel; candidate queue; scrubber; detail drawer.
- **Candidates page**: search panel, job card, results table, detail pane (the same detail component as the drawer).
- **Methods page**: table of contents, experiment cards, model card, limits.
- **Shared**: status chip, score cell, unit and coordinate formatters (9.2), error-to-copy mapper (8.3).

### 14.3 Rendering

- Frames and markers draw on a canvas or WebGL surface. A few hundred markers are fine; if U-01 brings in hundreds of stationary sources, keep them as one batched layer with a spatial index for hit testing.
- Aladin Lite loads lazily as a background only. If it fails or the archive is offline, switch to Simple without losing selection or time position.
- Frame fetches are cancellable, prefetch two frames ahead, and keep up to 50 decoded frames.

### 14.4 Mock mode

A single setting chooses `mock` or `live`. Mock mode serves responses generated from the OpenAPI schema and filled from demo-bundle fixtures (U-13), including streams and a slow, a failing and an offline variant. The "mock API" banner appears only in mock mode.

### 14.5 Budgets

| Measure | Budget |
| --- | --- |
| First useful paint on a preset | under 2 s |
| Frame swap while scrubbing, frames prefetched | under 100 ms |
| Main-thread long tasks during playback | none over 50 ms |
| Initial JavaScript, excluding Aladin Lite | under 300 kB compressed |
| Layout shift while frames stream in | under 0.1 |

### 14.6 Testing

- Browser flows for the demo script (15.3) and the five usability tasks, run in mock mode, plus one live smoke test.
- Stored visual snapshots for the key states: empty, building, degraded, offline, error, failed job.
- Accessibility checks (automated plus keyboard walkthrough) on every page.
- Contract tests: every mock response validates against the OpenAPI schema; every error code in 8.3 has a fixture.
- A text scan fails the build if banned words from 12.2 appear in user-facing strings.

### 14.7 Build order

Aligned with SDD section 15.6. Anything not ready at G3 ships disabled through `/capabilities`.

| Gate | Frontend scope | Needs from backend |
| --- | --- | --- |
| G1 | Shell, field entry, build stream, frame viewer with scrubber, mode banner, mock mode | U-05, U-06, `POST /fields`, events |
| G2 | Candidate queue and markers, search panel and job card, detail drawer, Methods validation view | Jobs, candidates, experiments, U-02, U-04, U-12 |
| G3 | Assistant, spectrum, polish, offline rehearsal, accessibility pass | Assistant stream, U-09 if classification goes ahead |

## 15. Acceptance, demo script and open decisions

The UX is done when ten acceptance checks pass, five usability tasks succeed with people outside the team, and the three-minute demo runs without a dead control.

### 15.1 Acceptance criteria

| ID | Criterion | How it is checked |
| --- | --- | --- |
| A1 | A preset shows its first frame in under 1 s; a cold field in under 20 s. | Timed browser flow |
| A2 | A newcomer finds the top candidate and explains the score within 60 s. | Usability task T1 |
| A3 | Every candidate view shows "Unconfirmed"; no banned word from 12.2 appears. | Text scan in the build |
| A4 | With no model and no LLM key, no dead controls remain. | Mock with all capabilities false |
| A5 | With health `offline`, presets and bundled results work end to end. | Mock offline variant |
| A6 | Opening a copied URL in a fresh tab restores field, frame and selection. | Browser flow |
| A7 | Tasks T1 to T3 complete by keyboard alone. | Manual walkthrough |
| A8 | Tokens pass contrast; automated accessibility check reports no serious issue. | CI |
| A9 | Frames streaming in cause no layout shift above 0.1. | Browser metric |
| A10 | Every error code in 8.3 renders its wording from a fixture. | Component tests |

### 15.2 Usability tasks

Five people who are not on the project, one after another, thinking aloud. Run once at G2 and again at G3; fix the top three problems after each round.

| Task | Success |
| --- | --- |
| T1. Open a preset and find the highest-ranked moving candidate. Say what its number means. | Says it is a model prediction and unconfirmed. Under 60 s. |
| T2. Enter coordinates and wait for the field. Say when it is usable. | Starts scrubbing while frames still arrive. |
| T3. Run a moving-object search and open a candidate. Say whether the original frames show the source moving. | Uses Blink or the stepper; does not treat the stack as proof. |
| T4. Find out how well the search works on injected sources. | Reaches the validation card and reads recall with its experiment label. |
| T5. Ask the assistant why a candidate ranks high. | Notices the context chip and the unconfirmed note. |

### 15.3 Three-minute demo script

| Time | On screen | Say |
| --- | --- | --- |
| 0:00 to 0:20 | Landing, open the demo preset (instant, from the bundle) | "SPHEREx maps the whole sky, one wavelength per exposure. This is our window into it." |
| 0:20 to 0:50 | Scrub by time, then by wavelength; toggle flags | "Every original frame stays available; we never hide the data." |
| 0:50 to 1:30 | Candidates: show the stored search, then the queue; select the top candidate; hover the score | "A search for faint movers. The score is a model's prediction, and every candidate is unconfirmed." |
| 1:30 to 2:10 | Detail: stack beside originals; Blink; the real-shift sentence | "The stack makes it visible. Check it against the originals. The real shift is under a pixel, so we exaggerate it and say so." |
| 2:10 to 2:35 | Methods and limits: completeness chart | "We inject fake sources and measure what we recover. This is how we know when to trust it." |
| 2:35 to 2:50 | Assistant: "Why is #042 ranked first?" | "Plain-language answers, drawn from the stored results." |
| 2:50 to 3:00 | Enter live coordinates; frames stream in | "Any patch of sky, live from the archive." |

If the live archive is slow, stay on presets; the banner says so and the story still holds. The preset to open must be a field whose stored search returns a clean candidate (UX-2).

### 15.4 Open decisions

| ID | Decision | Recommendation | Owner | By |
| --- | --- | --- | --- | --- |
| UX-1 | Are Stationary and Variable classes in v1? (U-01) | No; Moving only, plus known objects | Lead, ML eng | G1 |
| UX-2 | Which preset is the demo field? | The one whose stored search gives a clean candidate | ML eng, Lead | G2 |
| UX-3 | Default sky view | Aladin Lite when online, Simple when not or on failure | Frontend | G1 |
| UX-4 | Rate and angle units shown (D-17) | Arcsec per day, degrees east of north | ML eng | G1 |
| UX-5 | Image contract: PNG only or PNG plus array (D-06) | PNG; array only if the pixel readout is wanted | Frontend | G1 |
| UX-6 | Phone support | Read-only, as in 11.2 | Frontend | G2 |
| UX-7 | Third tab name | Keep "Candidates" in the UI; "Research Lab" stays the name in docs | Team | G1 |
| UX-8 | Assistant starter questions and knowledge pack (D-16) | Five questions, written by the ML engineer | ML eng | G2 |
