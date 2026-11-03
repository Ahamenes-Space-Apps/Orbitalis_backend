# ORBITALIS — Product Requirements Document (PRD) v0.1

Oct 28, 2026 · @zahir

## 01 Executive Summary

ORBITALIS (provisional name) is a public web tool where anyone types sky coordinates and watches SPHEREx observations of that patch play as a short video, so moving objects stand out.

The NASA Space Apps challenge asks for exactly this loop: the user enters Right Ascension and declination, the tool shows a series of SPHEREx images of that patch, and motion becomes easy to spot. Our MVP delivers that loop for any coordinates, with a shareable URL, per-detector image combination and frame metadata. Optional extras (spectra on the fly, Gaia and WISE overlays, quality-flag display) are layered in by priority in Section 05, and the team scopes an ML research track in parallel (see the ML Research Brief tab).

The gap we fill: IRSA's existing SPHEREx tools return file lists, mosaic cubes and photometry jobs that can run for minutes. As far as our review shows, none plays a field as a time-lapse for a non-expert. Time-to-first-frame and clarity are therefore the product.

**Scope decisions made so far**

- Core product is a field viewer (coordinates in, video out). A Stellarium-style all-sky timeline map is a stretch goal. ML is an open research track that the team scopes and decides on together (Section 05 Module H and the ML Research Brief tab).
- Context map uses Aladin Lite; backend is Python; no accounts, no monetization.
- Team of six: two frontend, two backend (one is the project lead and lead developer), one ML engineer, and a sixth role still to be confirmed for the 48-hour HackAthlone event, 13 to 15 November 2026 at TUS Athlone.

Technical design lives in the SDD; this PRD defines what must be true, not how.

## 02 Problem Statement, Goals & Non-Goals

SPHEREx produces thousands of detector images a day, and spotting a moving or changing object in them by hand is impractical for anyone but specialists.

Three facts make this hard. Each exposure samples a different wavelength for a given object, so frames of one patch are not like-for-like. A single position can be covered by hundreds of files (one IRSA tutorial position returned 415 overlapping images). And the motion of nearby test targets is small, about one to two 6.15-arcsecond pixels over the mission so far (computed from catalogue proper motions; see the Data and Science Specification, section 9). The challenge statement notes that volunteers found most known comets and brown dwarfs by comparing images over time, so making that comparison effortless has direct value.

**Goals**

| ID | Goal | Evidence it is met |
| --- | --- | --- |
| G1 | Any valid coordinates produce a video of SPHEREx frames quickly | All five test targets play end to end |
| G2 | Motion is legible even when it is only one to two pixels | A first-time user spots the moving test target |
| G3 | The 102 bands are used sensibly: frames combined per detector and compared across time | Coadd and subtract features work and are explained |
| G4 | Every view is shareable and embeddable by URL | URL round-trip tests pass |
| G5 | A new data release is picked up without code changes | Release added by configuration only |
| G6 | The tool is scientifically honest about what it shows | Provenance visible; no discovery claims |
| G7 (open) | The team selects and delivers at most one or two ML capabilities that serve the brief, each with measured performance | Research-review decision recorded; metrics reported for anything shipped |

**Non-goals**

- Claiming discoveries, including any 'Planet X' detection. The tool surfaces objects that merit follow-up.
- Ingesting or mirroring the full SPHEREx archive. Data is fetched per field.
- Replacing IRSA's science tools or doing publication-grade photometry.
- User accounts, saved workspaces, or any personal data.
- Orbit determination, tracklet linking, or formal object classification.
- Native mobile apps. Desktop browsers first; tablets usable.
- Monetization (see Section 03).

## 03 Value Proposition & Sustainability Rationale

ORBITALIS has no revenue model, by design: its value is public access to NASA data, and its 'return' is how well it serves the challenge brief and the people who use it.

**Value delivered**

- Citizen scientists and students get a one-step way to do what volunteers did by hand: compare images over time.
- Researchers get a fast quick-look of what SPHEREx saw at a position, with metadata and spectra, before committing to heavy analysis.
- The SPHEREx community gets a reference for a public, embeddable, URL-driven viewer that new releases can feed.

**Alignment with the challenge brief**

The official judging criteria were not available when this was written (see Section 13). Until they are, we map features to the brief's own objectives and optional considerations.

| Brief item | Where we address it |
| --- | --- |
| Enter RA/Dec, see a series of images like a video | Modules A, B, C |
| Test on five named targets | Module A presets; success metric M1 |
| Easy to update with new releases | FR-B5, FR-B4 |
| Use the 102 bands; combine per detector; spectra on the fly | Modules D, E |
| Add or subtract images across time | FR-D3, FR-D4 |
| Choose the field of view | FR-A1 |
| Overlay Gaia and WISE | FR-F2 |
| Show metadata such as contamination flags | Module G |
| Query by URL for embedding | FR-A3, FR-A4 |
| Use Astropy and Aladin | Section 08 |

**Sustainability path (replaces the business model)**

- Open source under a permissive licence (to be chosen; Section 13), so the community can adopt and extend it.
- Near-zero running cost: no accounts, no database of user data, data fetched from IRSA and cached.
- Release handling is configuration, so upkeep after the event is small.
- Required SPHEREx data acknowledgement and DOI citation are shown in the product (FR-G4). IRSA asks for this wherever its data is used.
- Good-citizen behaviour toward IRSA: caching and rate limiting, so a popular demo does not strain a public archive.

## 04 Target Users & Personas

Our primary user is a curious non-expert who wants to see the sky change without learning archive tools; four personas cover the range, and the first two drive design decisions.

| Persona | Who they are | What they want | Their success moment |
| --- | --- | --- | --- |
| P1 Citizen scientist (primary) | Volunteer in the style of Backyard Worlds; comfortable blinking images, not coding | Enter a position, see motion, share a find | Spots the drifting source and sends a link to a friend |
| P2 Student or educator (primary) | University student or teacher using the tool in a class or demo | A clear, guided way to see what 'proper motion' means with real NASA data | Plays Barnard's Star and explains why it moves |
| P3 Professional astronomer | Researcher doing a quick look before deeper analysis | Fast frames, per-detector coadds, spectra, flags, exportable context | Confirms coverage and quality at a position in under a minute |
| P4 Evaluator | Hackathon judge or NASA reviewer with a few minutes | A working demo that matches the brief, with clear scientific honesty | Runs a test target from a link and sees every brief item addressed |

**Design implications**

- P1 and P2 need plain language, sensible defaults and no required setup. Advanced controls stay available but out of the way.
- P3 needs numbers and provenance on demand: wavelength, time, detector, release, flags.
- P4 needs the five test targets one click away and a dependable demo path that works even if the archive is slow.

## 05 Functional Requirements: Product Modules

The product has nine modules; every Must requirement below is in the MVP, and the MVP is done when all Musts pass. Priorities follow MoSCoW (Must, Should, Could; definitions in Appendix B). Requirement IDs are stable so the SDD, test plan and UX documents can trace to them.

### Module A: Field Query & Sharing

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-A1 | The user can enter RA and Dec (decimal degrees or sexagesimal) and a field of view; invalid input shows a clear correction message | Must |
| FR-A2 | The user can enter a target name, resolved to coordinates by a public name resolver | Should |
| FR-A3 | Every view state (position, field of view, detector, time bin, mode) is encoded in the URL; opening the URL reproduces the view | Must |
| FR-A4 | An embed mode removes page chrome so the viewer fits inside other sites | Should |
| FR-A5 | One-click presets load the five brief test targets: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis | Must |
| FR-A6 | For known movers, the user can centre the field on the target's expected position at a chosen epoch | Could |

### Module B: Data Retrieval & Frame Assembly

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-B1 | Find every SPHEREx spectral image in the configured releases that covers the requested field | Must |
| FR-B2 | Retrieve a cutout per image sized to the field of view, with retries and a per-frame failure state | Must |
| FR-B3 | Frames appear in the viewer progressively as they arrive; the user sees progress and can start playback early | Must |
| FR-B4 | Results are cached by position, field of view, detector set, release and processing version; a cache hit makes repeat views near-instant | Must |
| FR-B5 | Supported releases are defined in configuration; adding a release needs no code change | Must |
| FR-B6 | The user can include or exclude deep-field images | Should |
| FR-B7 | Frames from different releases are reconciled using the archive's published flux-correction products, or the mismatch is clearly flagged | Should |
| FR-B8 | Every frame carries provenance: observation ID, detector, observation time, wavelength range, release and processing version | Must |
| FR-B9 | A per-request cap on frames and data volume (proposed about 150 frames or 1 GB); above it the user is told and offered ways to narrow detectors, time window or field of view | Must |
| FR-B10 | A first request covers one detector or one detector pair; the user can widen it | Must |
| FR-B11 | The counts of frames requested, received, rejected and missing are always visible, with reasons | Must |
| FR-B12 | Frames are screened on header quality keywords (astrometry flag, masked fraction) using the rules in the Data and Science Specification, section 7 | Should |
| FR-B13 | A reprocessing of a release is detected through the processing version, and the affected cache entries are refreshed | Should |

### Module C: Time-lapse Viewer

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-C1 | Frames play in time order as a video with play, pause, step, speed and loop | Must |
| FR-C2 | A timeline shows when observations occurred, including gaps, and lets the user jump to any frame | Must |
| FR-C3 | All frames are registered to one sky grid so stationary sources do not shift between frames | Must |
| FR-C4 | Pan, zoom and a consistent brightness stretch across frames, with the stretch adjustable | Must |
| FR-C5 | A blink comparator toggles between two chosen frames or frame groups | Should |
| FR-C6 | A fixed reference crosshair at a chosen sky position makes small motions visible | Should |
| FR-C7 | Detectors can be viewed side by side | Could |
| FR-C8 | The current view can be exported as an animated image | Could |
| FR-C9 | Playback offers frame order (default) and a true-time scale, because frames are unevenly spaced in time | Should |

### Module D: Image Operations

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-D1 | Frames are grouped by detector and by time bin, and each group is combined (coadded) to improve signal-to-noise | Must |
| FR-D2 | The user chooses detectors or a wavelength range and the time-bin size | Must |
| FR-D3 | The user can subtract one combined image from another to show change | Should |
| FR-D4 | The user can add chosen groups into one image | Should |
| FR-D5 | Pixels flagged as bad are excluded before frames are combined, following the masking policy in the Data and Science Specification (section 8) | Must |
| FR-D6 | Three detectors can be mapped to colour channels to form a composite | Could |

### Module E: Spectra on the Fly

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-E1 | Clicking a position produces a spectrum (flux versus wavelength) measured from the available frames | Should |
| FR-E2 | Each spectrum point states its wavelength and uncertainty source, and the method is documented in the UI | Should |
| FR-E3 | Spectrum points are colour-coded by observation time so changes in a mover or variable star are visible | Should |
| FR-E4 | The spectrum can be downloaded as CSV | Could |

### Module F: Context & Overlays

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-F1 | A sky context map shows where the field sits, with the SPHEREx footprint | Must |
| FR-F2 | Gaia and WISE catalogue sources can be overlaid on the viewer | Should |
| FR-F3 | Known solar-system objects expected in the field at each frame time can be overlaid | Should |
| FR-F4 | Clicking an overlaid source shows its catalogue identity and basic data | Should |
| FR-F5 | An all-sky map with a time scrubber that animates known moving objects | Could |

### Module G: Metadata & Quality

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-G1 | A panel shows full metadata for the current frame | Must |
| FR-G2 | Contamination and quality flags can be shown as an overlay with counts | Should |
| FR-G3 | The user can exclude heavily flagged frames | Should |
| FR-G4 | The SPHEREx data acknowledgement and release citation are visible in the product | Must |

### Module H: ML Research Track (open for team decision)

ML is an open research track, not a committed deliverable: the team chooses directions together, and the product must work fully without it. Candidate directions, evidence and decision criteria are in the ML Research Brief tab.

Open the brief: ML Research Brief

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-H1 | The product is fully functional with every ML feature switched off; no core requirement depends on ML | Must |
| FR-H2 | The team selects ML directions at a research review, using the criteria in the ML Research Brief, and records the decision in Section 13 | Must |
| FR-H3 | Any ML output is labelled as model-generated, with a score and a model version; candidates are never worded as confirmed objects | Must, if ML ships |
| FR-H4 | Each shipped ML capability has documented performance on injected sources and on known real objects, visible in the app or its documentation | Must, if ML ships |
| FR-H5 | The unprocessed, non-ML view is always one click away from any ML-processed view | Must, if ML ships |
| FR-H6 | Each selected direction is turned into its own requirement set before building starts | Must, if ML ships |
| FR-H7 | ML inference runs on a CPU at demo time, or its results are precomputed for the presets | Should, if ML ships |

### Module I: Guidance & Resilience

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-I1 | A short first-run guide explains what the video shows and how to read motion | Must |
| FR-I2 | Plain-language tooltips explain terms such as detector, coadd and flag | Should |
| FR-I3 | Empty and error states (no coverage, archive unreachable, partial frames) explain what happened and what to try | Must |
| FR-I4 | A pre-computed demo mode serves the five test targets if the archive is slow or unreachable | Must |

## 06 Non-Functional Requirements

Speed to the first frame and scientific honesty matter most; every numeric target below is provisional until the data-access feasibility gate (Section 10) gives real timings.

| ID | Category | Requirement | Target |
| --- | --- | --- | --- |
| NFR-1 | Performance | Time from submit to first visible frame, cached field | 3 s or less |
| NFR-2 | Performance | Time to first visible frame, uncached field at default field of view | 30 s or less to the first frame (the metadata query alone took 16.6 s in IRSA's example) and about 2 minutes for the default set, with a progress indicator throughout |
| NFR-3 | Performance | Playback stays smooth once frames are loaded | 30 frames per second on a mid-range laptop |
| NFR-4 | Reliability | One failed frame or one slow archive call does not block the others | Per-frame isolation, retries, partial results shown |
| NFR-5 | Reliability | Demo mode keeps all five test targets working if the archive is down | 100 percent of presets |
| NFR-6 | Usability | Landing to playing video for a first-time user | 3 interactions or fewer |
| NFR-7 | Usability | Technical terms explained where they first appear | Tooltip or inline note |
| NFR-8 | Accessibility | Controls usable by keyboard; colour never the only signal; contrast checked | WCAG 2.1 AA as a target for controls and text |
| NFR-9 | Compatibility | Current desktop Chrome, Firefox, Safari; tablet usable | Verified before freeze |
| NFR-10 | Scientific integrity | Units, wavelength, observation time and release shown wherever data is shown | No unlabeled data |
| NFR-11 | Scientific integrity | Observed values are visually distinct from interpolated or predicted ones | Consistent marker convention |
| NFR-12 | Scientific integrity | No wording claims discovery or classification beyond what was measured | Reviewed copy |
| NFR-13 | Maintainability | New release supported by configuration; science logic testable without the web layer | Config-only release test; unit tests on core functions |
| NFR-14 | Resource etiquette | Requests to IRSA are cached, de-duplicated and rate-limited | No unbounded fan-out per user |
| NFR-15 | Privacy | No accounts, no personal data stored; only anonymous aggregate usage if any | None collected by default |
| NFR-16 | Licensing | All dependencies and the project licence are compatible and listed | Checked before release |

## 07 Assumptions & Constraints

The plan rests on seven assumptions we must test early, and on six constraints we cannot change.

**Assumptions** (each is verified at the feasibility gate or in testing)

| ID | Assumption | How we check it |
| --- | --- | --- |
| A1 | IRSA's search and cutout services are available and fast enough for interactive use | Gate 1 timings on the five targets |
| A2 | Every test target has enough SPHEREx coverage to make a meaningful video | Gate 1 frame counts and time spread |
| A3 | Test-target motion over the mission so far is about 1 to 2 pixels of 6.15 arcsec (Barnard's Star 2.2, WISE 0855 1.7, Epsilon Indi B 1.0; catalogue proper motions times about 1.3 years; Data and Science Specification, section 9) | Measure with known proper motions |
| A4 | Combining frames per detector gives clearer images than single frames | Visual and signal-to-noise comparison |
| A5 | Aladin Lite can host our overlays and context layers without custom engine work | Early prototype at hackathon start |
| A6 | A cached, precomputed demo mode is acceptable for the five presets | Confirm with organizers |
| A7 | The browser can render and play the number of frames per field at the chosen field of view | Stress test at largest field of view |

**Constraints**

- **Time.** 48 hours at the event (13 to 15 November 2026, HackAthlone at TUS Athlone; NASA's global event runs 14 to 15 November). Organizers have said planning was permitted and coding opened on 28 October; we will reconfirm.
- **Team.** Six people with the roles in Section 01; integration capacity is limited.
- **Stack.** Python backend, Aladin Lite for the context map. No unnecessary technologies.
- **Data.** Public SPHEREx data via IRSA only. Archive behaviour (latency, data lag of about a day on some services, release changes) is outside our control.
- **Calibration.** Different releases use different calibrations; flux comparison across releases needs the archive's correction products. IRSA also plans a full reprocessing (DR1) for late fall 2026, close to the event, so file contents and processing versions may change under us.
- **Science.** We present observations and candidates, not discoveries.

## 08 Dependencies

The product depends mainly on IRSA's public services, so its availability and speed are our largest external risk.

| Dependency | What we use it for | Owner | If it fails |
| --- | --- | --- | --- |
| [IRSA SPHEREx image search (SIA2) and metadata tables (TAP)](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access) | Find images covering a field; observation times and wavelength ranges | IPAC/IRSA | Demo mode; cached results |
| [IRSA cutout service](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access) | Per-field image cutouts (about 5 MB each at minimum because the PSF layer is included; 10 parallel requests lost 37 of 84 cutouts in IRSA's own demo) | IPAC/IRSA | Retry; reduce field of view; cached frames |
| [SPHEREx data products and calibration files](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products) | Flags, wavelength maps, solid-angle maps, PSFs, flux corrections | IPAC/IRSA | Degrade features (spectra, reconciliation) |
| IRSA public cloud copy of the data (AWS Open Data) | Alternate read path for full images | IPAC/IRSA | Use cutout service only |
| Astropy, photutils, reproject, astroquery | WCS handling, registration, photometry, archive queries | Open-source community | None expected; pin versions |
| [Aladin Lite](https://aladin.cds.unistra.fr/AladinLite/doc/API) and HiPS surveys | Context map, backdrop survey, catalogue overlays | CDS Strasbourg | Plain image viewer without context map |
| SkyBoT solar-system object service | Known asteroids and comets in the field at frame time | IMCCE | Hide F3 overlay |
| Gaia and AllWISE catalogue access (via a VO catalogue service) | Overlay sources | Public archives | Hide F2 overlay |
| Hosting and network for the demo | Serve the app at the event and for judges | Team | Local demo mode; recorded fallback |
| Team availability and skills | Delivery across 48 hours | Project lead | Cut Should and Could items first |

## 09 Technical Architecture Requirements

This section states what the architecture must guarantee; how it does so (components, endpoints, formats, algorithms) is decided in the SDD.

| ID | Requirement | Why it matters |
| --- | --- | --- |
| TAR-1 | Separate fast metadata queries (which images, when, which wavelength) from slow pixel retrieval (cutouts) | The timeline and coverage can appear before pixels arrive |
| TAR-2 | Frames stream to the browser progressively; the viewer never waits for the full set | Supports FR-B3 and NFR-2 |
| TAR-3 | A caching layer keyed by position, field of view, detector set, release and processing version, with invalidation when a release or a reprocessing changes | Supports FR-B4, FR-B5, NFR-1 |
| TAR-4 | Supported releases and archive endpoints are configuration, not code | Supports FR-B5 and G5 |
| TAR-5 | Science logic (registration, coadd, subtract, photometry, flags) lives in a library independent of the web layer and is unit-testable | Supports NFR-13 and the test plan |
| TAR-6 | Astropy is the reference for coordinate and wavelength transformations; any alternative must reproduce its results | The spectral wavelength map uses a rarely supported format, and errors here are silent |
| TAR-7 | The browser receives display-ready frames plus the numeric information needed for hovering values and measuring spectra | Keeps the viewer fast without losing science value |
| TAR-8 | The backend exposes a small, documented HTTP interface whose parameters mirror the URL scheme | Supports FR-A3, FR-A4 and embedding |
| TAR-9 | Per-frame failure isolation, retries with backoff, and timeouts sized to the archive's behaviour | Supports NFR-4 |
| TAR-10 | A pre-computed demo bundle for the five test targets ships with the app | Supports FR-I4 and NFR-5 |
| TAR-11 | Request volume to IRSA is bounded per user and de-duplicated across users | Supports NFR-14 |
| TAR-12 | The ML component, if shipped, runs behind a stable interface and can be switched off without affecting the core viewer | Keeps a stretch feature from putting the MVP at risk |
| TAR-13 | Structured logs capture timings (search, cutout, assembly, render) to find slow steps | Needed for the performance gate |
| TAR-14 | One repeatable command builds and runs the whole system locally and in the demo environment | Reduces integration risk in 48 hours |

## 10 Phased Delivery Strategy

Delivery runs in five phases separated by four go or no-go gates; if a gate slips, Should and Could items are cut before any Must.

&#91;embedded content: phased delivery roadmap · 5 phases, 4 gates\]

Phases run left to right; each diamond is a gate with its pass criterion beneath. Hour counts are hours of the 48-hour event. Phase 0 assumes coding is permitted from 28 October as organizers indicated; if it is not, Phase 0 stays at design and read-only probes, and gate G1 moves into the first hours of the event.

| Phase | Window | Scope (requirement IDs) | Exit gate |
| --- | --- | --- | --- |
| P0 Prepare | 28 Oct to 12 Nov | PRD, data and science spec, SDD, UX flows and wireframes, test plan, repository and tooling; a data probe on the five targets; ML research sprint and review | G1: all five targets return frames, with search and cutout timings recorded; the first six open data questions in the Data and Science Specification are answered |
| P1 Skeleton | Hours 0 to 12 | Thin versions of FR-A1, A3, A5, B1 to B5, B8 to B12, C1 to C4, I3 | G2: one test target plays end to end from a URL |
| P2 Core features | Hours 12 to 30 | FR-D1, D2, D5, F1, G1, G4, I1, I4; then Should items by value: D3, D4, F2, F3, E1 to E3, G2, G3, B6, B7 | G3: all Musts pass; scope frozen |
| P3 Polish | Hours 30 to 42 | Testing on all five targets, accessibility pass, copy review, performance fixes; selected ML work (Module H) only if it passed the research review and has a validation plan | G4: code freeze, demo mode verified, rehearsed once |
| P4 Freeze and demo | Hours 42 to 48 | Demo script, rehearsal, documentation, submission | Submission delivered |

After the event: choose a licence, publish the repository with a README, and document the release procedure so new data releases can be added by configuration.

## 11 Success Metrics

We succeed if all five test targets play end to end from a link and a first-time user can spot the mover within a minute; ten metrics make that checkable.

| ID | Metric | Target | How measured | Tier |
| --- | --- | --- | --- | --- |
| M1 | Test targets that play end to end from a URL | 5 of 5 | Scripted run before each gate | Core |
| M2 | Time to first frame (cached, then uncached) | 3 s and 30 s or less | Logged timings (TAR-13) | Core |
| M3 | First-time users who identify the moving test target within 60 seconds | 4 of 5 testers | Informal usability test during polish phase | Core |
| M4 | URL round-trip fidelity (open link reproduces the view) | 100 percent of tested views | Automated check | Core |
| M5 | Time to add a new data release | 1 hour or less, configuration only | Dry run with a second release | Core |
| M6 | Must requirements passing at feature freeze | 100 percent | Test plan results at G3 | Core |
| M7 | Consecutive clean demo rehearsals | 3 | Rehearsal log | Core |
| M8 | Accessibility: keyboard-complete main path, no critical automated findings | Pass | Checker plus manual pass | Core |
| M9 | Brief items addressed (Section 03 table) | 8 of 10 at least | Checklist at submission | Core |
| M10 | ML (if shipped): the metrics defined in the ML Research Brief for each shipped capability, validated on injected sources and known objects | Set at the research review | Held-out injected set; test targets | Stretch |

Metrics M1 to M9 decide whether the MVP shipped; M10 is reported only if Module H ships.

## 12 Risks & Mitigations

The two risks most likely to hurt the demo are slow archive access and motion that is too small to see; both have a mitigation built into the plan.

| ID | Risk | Likelihood | Impact | Mitigation | Owner (proposed) |
| --- | --- | --- | --- | --- | --- |
| R1 | IRSA search or cutout calls are slow or time out | High | High | Progressive frames, caching, retries, demo mode for presets (FR-B3, B4, I4); per-request frame and volume caps (FR-B9, B10); measure at G1 | Backend |
| R2 | Test-target motion is only about one to two pixels and hard to see in a video | High | High | Per-detector coadds, fixed crosshair, blink comparator, subtraction (FR-D1, C5, C6, D3); user testing in polish phase | Frontend, Backend |
| R3 | Frames at different wavelengths look inconsistent, so stationary stars appear to change | High | Medium | Group by detector and time bin before comparing; label wavelength on every frame; explain in the guide | Backend |
| R4 | A test target has few frames or large time gaps | Medium | High | Inspect coverage at G1; show gaps on the timeline; choose field of view to include more frames | Lead |
| R5 | Releases use different calibrations, so flux comparisons mislead | Medium | Medium | Use published flux-correction products or flag the mismatch (FR-B7); processing version in every cache key (TAR-3), because IRSA plans a full reprocessing (DR1) for late fall 2026 | Backend |
| R6 | Scope creep into the all-sky map or heavy ML | High | High | MoSCoW cut line; G3 scope freeze; ML behind a switch (TAR-12) | Lead |
| R7 | ML direction underdelivers, is chosen late, or training data is thin | Medium | Low | Directions chosen at the research review against stated criteria; cut at hour 12 if not on track; report honestly; core viewer unaffected | ML |
| R8 | Integration pain between frontend and backend in 48 hours | Medium | High | Agree the interface in the SDD in Phase 0; mock data; one-command run (TAR-14) | Lead |
| R9 | Rule ambiguity on when coding may start | Medium | Medium | Confirm in writing with organizers (Section 13) | Lead |
| R10 | Aladin Lite cannot support a needed overlay or interaction | Medium | Medium | Early prototype; fall back to our own canvas layer over Aladin's map | Frontend |
| R11 | Venue network or hosting fails during judging | Medium | High | Local demo build with bundled demo data; recorded walkthrough as last resort | Lead |
| R12 | Wording over-claims scientific findings | Low | High | Copy review against NFR-12; candidate language only | Lead, ML |

## 13 Open Questions & Pending Decisions

Sixteen items remain open; the first four block planning or the gates and should be settled first. Tick an item when decided and record the decision in the relevant document.

- [ ] **Coding start.** Get written confirmation from organizers that coding is allowed from 28 October (the event page said before the hackathon starts; the organizers' message said before 28 October).
- [ ] **Judging criteria and submission format.** Obtain the official criteria and what must be submitted; update Section 03 and Section 11 to match.
- [ ] **Sixth team member.** Five roles are named (two frontend, two backend, one ML); confirm the sixth role and assign module owners.
- [ ] **Releases in scope.** QR2 only, or QR2 and QR3; confirm the correct acknowledgement text and citation for each (FR-G4).
- [ ] **Project name.** Keep ORBITALIS or rename before the demo.
- [ ] **Licence.** Choose the open-source licence for the repository.
- [ ] **Hosting and demo mode.** Where the app runs at the event, and whether judges accept a precomputed demo mode for the five presets.
- [ ] **Deep-field data.** Include by default, or only on request (FR-B6).
- [ ] **Field of view limits.** The Data and Science Specification proposes 0.1 degrees by default and 1 degree at most for the first release; confirm, balancing the brief's tracking benefit against transfer time.
- [ ] **Test-target positions.** The brief gives coordinates only for WISE 0855; the Data and Science Specification (section 9) proposes resolving the others by name at runtime and storing their proper motions; R Draconis still has no verified position.
- [ ] **Sub-pixel motion display.** How the viewer makes one-to-two-pixel motion legible (expected shifts are in the Data and Science Specification, section 9; decided in the UX and SDD documents).
- [ ] **ML research review.** Which direction or directions from the ML Research Brief, with what data, compute and owner, decided at the team's research review by 12 November.
- [ ] **All-sky timeline map (FR-F5).** Keep as Could or drop to a post-event idea.

* [ ] **Cutout size and archive limits.** Ask IRSA whether the cutout service can leave out the PSF layer, what request limits apply, and why parallel cutouts failed so often in IRSA's own demo (Data and Science Specification, section 16).
* [ ] **Per-request caps.** Confirm the proposed cap of about 150 frames or 1 GB and the one-detector-pair first request (FR-B9, FR-B10).
* [ ] **Reprocessing during the event.** IRSA plans a full reprocessing (DR1) for late fall 2026; decide how we detect and handle it (FR-B13).

## Appendix A: Glossary

Terms are listed alphabetically; each is used with this meaning across the PRD, SDD, UX and test documents.

| Term | Meaning |
| --- | --- |
| Aladin Lite | A browser sky viewer from CDS Strasbourg that displays HiPS surveys and catalogue overlays |
| Brown dwarf | An object too massive to be a planet but too light to burn like a star; faint in near-infrared and often fast-moving when nearby |
| Coadd | Combining several images of the same field into one to improve signal-to-noise |
| Cutout | A small piece of a large image around a chosen sky position |
| Declination (Dec) | The north-south sky coordinate, in degrees |
| Detector (band) | One of SPHEREx's six detector arrays, each covering a wavelength range; each exposure produces one image per detector |
| Ephemeris | A table of an object's predicted positions over time |
| Exposure | One SPHEREx pointing; it yields six spectral images, one per detector |
| FITS / MEF | The standard astronomy image file format; a multi-extension FITS file holds several image and table layers |
| Flags | Per-pixel status codes marking bad, contaminated or processed pixels |
| Gaia | ESA's star-position and motion survey, used as an overlay catalogue |
| HiPS | Hierarchical Progressive Survey: a tiled format that lets viewers zoom through all-sky image sets |
| IRSA | NASA/IPAC Infrared Science Archive, which hosts SPHEREx data |
| Linear variable filter (LVF) | A filter whose wavelength changes smoothly across the detector, so each pixel sees a different colour |
| Mover | A source whose sky position changes between observations |
| Proper motion | A star's apparent sky motion caused by its real motion through the Galaxy |
| Parallax | Apparent shift of a nearby object caused by Earth's orbit around the Sun |
| Quick Release (QR2, QR3) | IRSA's weekly SPHEREx data releases; QR2 and QR3 use different calibrations |
| Real/bogus | A classification of whether a detected change is a genuine astronomical event or an artefact |
| Resolving power (R) | Wavelength divided by the smallest resolvable wavelength difference |
| RA | Right Ascension: the east-west sky coordinate, in degrees or hours |
| SIA2 / TAP | Standard virtual-observatory protocols for finding images (SIA2) and querying tables (TAP) |
| SkyBoT | A service that lists known solar-system objects in a sky field at a given time |
| Spectral image | A SPHEREx calibrated image from one detector for one exposure, in which wavelength varies across the image |
| WCS | World Coordinate System: the mapping between image pixels and sky coordinates (and, for SPHEREx, wavelength) |
| WISE / AllWISE | NASA's infrared sky survey and its catalogue, used as an overlay |

## Appendix B: Object & Requirement Taxonomy

This appendix replaces a product-category taxonomy with the two classifications the project actually needs: the kinds of sky objects users will look at, and the conventions used to label requirements.

**B.1 Sky object categories**

| Category | Examples | What users see across frames | Role in the product |
| --- | --- | --- | --- |
| Asteroids | Known main-belt and near-Earth objects | A point source at different positions between exposures, hours to days apart | Overlay of known objects (FR-F3); mover highlighting (Module H) |
| Comets | Active comets; interstellar comet 3I/ATLAS | Moving source, possibly extended, with spectral features from gas and dust | Spectra on the fly (Module E); demonstration target idea |
| High proper-motion stars | Barnard's Star | Slow, steady drift of a few pixels over the mission | Brief test target (FR-A5) |
| Brown dwarfs | WISE 0855, Epsilon Indi B | Faint at short wavelengths, bright at long ones; steady drift | Brief test targets; shows why per-detector views matter |
| Variable stars | RW Aurigae, R Draconis | Fixed position, changing brightness over time | Brief test targets; spectra versus time (FR-E3) |
| Distant solar-system bodies | Hypothetical Planet X | Large parallax-driven drift if bright enough; brightness unknown | Motivation only; no detection claims (non-goal) |
| Extragalactic sources | Galaxies, quasars, supernovae | Fixed position; supernovae may brighten or fade | Context; supernova-type variability noted, not targeted |
| Instrument artefacts | Persistent charge, hot and cold pixels, transient hits, South Atlantic Anomaly effects, crosstalk | Spots that appear in single frames and are not real sources | Flag overlay and frame exclusion (FR-G2, G3); negative class for ML |

**B.2 Requirement conventions**

| Convention | Definition |
| --- | --- |
| Must | Required for the MVP; the MVP is not complete without it |
| Should | Important and planned; first to be done after all Musts |
| Could | Desirable if time allows; the first items cut |
| Won't (this release) | Explicitly out of scope; listed under Non-goals |
| ID scheme | FR-Xn functional (X is the module letter A to I, for example FR-C3), NFR-n non-functional, TAR-n architecture, Gn goals, An assumptions, Rn risks, Mn metrics |
| Tier | Core (counts toward MVP success) or Stretch (reported if delivered) |

## Appendix C: Referenced Documents & Document Boundaries

Each document owns one kind of decision; where documents disagree, the PRD wins on what and why, the SDD on how, and the test plan on how it is verified.

**C.1 Project document set**

| Document | Owns | Does not own | Status |
| --- | --- | --- | --- |
| PRD (this document) | Goals, users, requirements, priorities, metrics, risks, open questions | Design, algorithms, interface details | Draft v0.1 |
| Data and science specification (draft v0.1 exists as a separate document) | What each SPHEREx product contains, how frames are grouped and combined, scientific caveats, ground-truth sources | Code structure, UI | Not started |
| SDD (software design, including the interface contract) | Components, data flow, caching, formats, endpoints, deployment | Product scope, priorities | Not started |
| ML research brief (tab in this document), then ML specification and model card | Task definition, training and evaluation data, metrics, limits of the model | Viewer behaviour | Not started |
| UX documents (user flows, information architecture, wireframes, visual language) | Screens, flows, interactions, copy, accessibility design | Data processing | Not started |
| Test plan (including test-first criteria and scientific validation) | How each requirement is verified; test data; acceptance checks per gate | What the requirements are | Not started |
| Delivery plan and demo runbook | Roles, schedule inside the 48 hours, demo script, fallback procedure | Requirements | Not started |
| Draft concept plan v0.1 (teammate's original ORBITALIS plan) | Original concept and vision | Superseded by this PRD where they conflict, notably the whole-sky epoch model and discovery-centred scope | Reference only |

**C.2 External sources**

Pages opened and read for this PRD (as of 28 October 2026):

- [Planet X and SPHEREx challenge page, HackAthlone 2026](https://hackathlone.com/challenges/planet-x-and-spherex)
- [SPHEREx Data Products, SPHEREx Archive at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products)
- [SPHEREx Data Access, SPHEREx Archive at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access)
- [SPHEREx tutorial notebooks index, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex/)
- [Introduction to SPHEREx Spectral Images, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro)
- [SPHEREx Source Discovery Tool demo, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo)
- [Understanding and Analyzing SPHEREx Mosaic Cubes, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic)

The full challenge statement (objectives, test targets, optional considerations) was supplied by the team on 28 October 2026. Proper-motion figures quoted in Section 07 are approximate, from memory, and must be verified from catalogues before use.
