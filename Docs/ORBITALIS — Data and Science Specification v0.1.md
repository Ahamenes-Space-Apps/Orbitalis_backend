# ORBITALIS — Data and Science Specification v0.1

Oct 30, 2026 · @zahir

## 1 Purpose, scope and document boundaries

This specification states what the SPHEREx data contains, how ORBITALIS turns it into frames, spectra and overlays, and what we can and cannot claim from it; how to build that is the SDD's job.

**It owns:** the meaning of each data product and field, coordinate, time, unit and wavelength conventions, the science steps from a user's request to a displayed frame, masking and combining rules, the spectrum method, caveats, and the validation data.

**It does not own:** software structure, endpoints, formats between our own components, UI behaviour, or ML model design (see the PRD's Appendix C for the document map).

**Every fact carries a confidence label**, so the team knows what to trust and what to re-check.

| Label | Meaning |
| --- | --- |
| Doc | Stated in IRSA's SPHEREx archive documentation or tutorials, which we opened |
| Paper | Stated in a published paper found in search results; open the source before relying on details |
| Memory | Written from general knowledge, not checked against a source; verify before use |
| Decision | A choice this specification makes; it can be changed by the team |

## 2 Instrument and survey essentials

SPHEREx images the sky through six wavelength-varying filters, so every exposure gives one wavelength per source and a full spectrum builds up over many exposures; this shapes everything we do.

| Property | Value | Label |
| --- | --- | --- |
| Detectors | Six arrays, three short-wavelength and three long-wavelength, behind linear variable filters; each exposure yields six images, one per detector | Doc |
| Image size | 2040 by 2040 pixels per detector image | Doc |
| Pixel scale | About 6.15 arcsec per pixel | Paper |
| Field of view | About 3.5 by 3.5 degrees per detector; detectors sit 0.25 degrees apart, so one exposure covers about 3.5 by 11 degrees | Paper |
| Wavelength range | 0.75 to 5.0 micrometres, in 102 channels (17 per detector) | Doc, Paper |
| Exposure time | 113.58 seconds exposure and 1.5349 seconds frame time per the Explanatory Supplement (Doc); one paper quotes about 115 seconds | Paper |
| Rate | About 600 exposures, or 3,600 detector images, per day | Doc |
| Pointing pattern | Sets of 1 to 4 exposures separated by small slews of about 11.8 arcmin, then a larger slew of about 60 degrees | Paper |
| Orbit | Low Earth, sun-synchronous polar | Paper |
| Sky coverage | The whole sky about every six months; first all-sky map complete December 2025; four all-sky surveys planned in the two-year mission | Doc, Paper |
| Channel coverage | Each of the 102 channels maps the whole sky about twice a year | Paper |
| Deep fields | Two fields revisited far more often than the rest of the sky; separate wide and deep image collections in the archive | Paper, Doc |
| Planning period | About 3.5 days of operation; observation IDs look like 2025W18\_2B\_0001\_1 | Doc |
| South Atlantic Anomaly | Images are taken there but do not count toward survey completeness; particle hits are frequent | Paper |

**What this means for ORBITALIS**

- A patch of sky is covered by many frames, observed at many different times and wavelengths; one IRSA tutorial position returned 415 images (Doc).
- Within one detector, the wavelength at a given sky position depends on where the source fell on the filter, so frames of one detector are still not strictly like-for-like; section 7 handles this.
- The dichroic pairs detectors 1 with 4, 2 with 5 and 3 with 6, so a given patch of sky falls on only one pair in each exposure: at most two images cover it, one short-wave and one long-wave (Doc). A full 102-channel spectrum therefore takes about 51 exposures, three pairs times 17 steps (Paper, an IRSA presentation). Those exposures are spread over many orbits, because a target group of 17 pointings is built from sets of 1 to 4 exposures separated by large slews (Doc). Frames of one patch can be minutes to months apart.

## 3 Data products we use

We need one main product, the Level 2 spectral image (or its cutout), and four small calibration products; everything else in the archive we leave alone.

| Product | Content | Size | Used for | Use |
| --- | --- | --- | --- | --- |
| Spectral image (multi-extension FITS, one per detector per exposure) | IMAGE (surface brightness, MJy/sr), FLAGS (bitmap), VARIANCE, ZODI (zodiacal model, not subtracted), PSF, WCS-WAVE (wavelength lookup) | About 70 MB | Source of all frames and spectra | Core |
| Spectral image cutout (from IRSA's cutout service) | The same extensions, cropped; WCS-WAVE adjusted to the crop; PSF kept unmodified; header keywords CRPIX1A and CRPIX2A locate the crop in the original | Small, scales with field of view | What we actually download | Core |
| Solid angle pixel map (calibration, per detector) | Pixel solid angle in square arcsec | About 16 MB | Converting surface brightness to flux for spectra | Core for spectra |
| Spectral WCS (calibration, per detector) | CWAVE and CBAND: central wavelength and bandwidth per pixel | About 32 MB | Science-grade wavelength per pixel; the in-file WCS-WAVE is for visualization only | Core for spectra |
| Effective PSF, ePSF (calibration, QR3) | Point-spread functions on a 21 by 21 zone grid (detector 3 uses 11 by 41), 33 by 33 pixels, oversampled by 5 | About 8 MB per detector | Spectra photometry and injected sources; supersedes the older PSF | Core for spectra and ML |
| Flux corrections (calibration, QR3) | Per-pixel factors to combine QR2 and QR3 data | Image per detector | Mixing releases in one view | Optional |
| Exposure-averaged PSF (calibration, QR2) | 121 PSFs of 101 by 101 pixels | About 6 MB per detector | Fallback where no ePSF exists | Fallback |
| Dichroic, dark, gain, non-functional pixel, non-linearity, read-noise maps; crosstalk, zodi-scaling, sky-emission templates | Instrument calibration inputs | 16 to 79 MB each | Already applied in Level 2 data | Not used |
| Mosaic cube (IRSA tool output) | 102-plane cube at a position, with hit counts and flags | Varies | Reference only; the tool has no API, so we cannot call it | Not used |

Sources: Doc (SPHEREx data products page and the IRSA introduction notebook).

**Things to remember**

- QR2 files released before 31 March 2026 had an error in the PSF header description; QR2 headers were corrected in April 2026 (Doc).
- QR1 is retired (February 2026); QR2 and QR3 are live (Doc).
- Calibration products are not served by the image search service; they come from the browsable directories or the cloud copy (Doc).

## 4 Access model and query strategy

We ask IRSA two different questions at two different costs: a cheap metadata query to learn which frames exist and when, and a costly cutout download to get the pixels.

| Tier | Service | What it returns | Measured or documented behaviour | Label |
| --- | --- | --- | --- | --- |
| Metadata | TAP tables spherex.artifact joined to spherex.plane | Cutout URL and observation time (time\_bounds\_lower, in days) for every image whose footprint contains a point; can filter by detector with energy\_bandpassname, for example SPHEREx-D2 | 16.6 seconds for 84 detector-2 images in IRSA's own example; new data visible immediately after the weekly ingest | Doc |
| Metadata | Simple Image Access v2, collections spherex\_qr2, spherex\_qr2\_deep, spherex\_qr3, spherex\_qr3\_deep | Rows with position, wavelength range, start and end time, field of view, pixel scale, exposure time, footprint, download and cloud-access links | New data appears about a day after the TAP route; a 1-arcsec cone at one position returned 415 images | Doc |
| Pixels | IRSA cutout service: the image URL plus center (degrees) and size (degrees) parameters | A multi-extension FITS cutout with the same layers as the full image; the PSF layer is returned unmodified | 84 cutouts took 1.4 minutes in series; 10 parallel workers took 6 seconds but 37 cutouts failed, against 2 failures in series | Doc |
| Pixels | Public cloud copy of full images (AWS S3 bucket nasa-irsa-spherex, anonymous read) | Whole 67 to 70 MB files | Not a cutout route; cutouts exist only for the on-site copy | Doc |
| Calibration | Browsable directories on IRSA's site and the same cloud bucket | Solid angle maps, spectral WCS, ePSF, flux corrections | Not served through the image search | Doc |

**Query strategy**

- Use TAP for discovery, not SIA: it is immediate after ingest and returns the time directly (Decision).
- Cache every TAP answer by position, release and detector set, because a 17-second query would consume most of the first-frame time budget (Decision, based on the timing above).
- Fetch cutouts in time order in small parallel batches with retries and back-off, and treat a failed cutout as a visible missing frame rather than silently dropping it. IRSA's own parallel run lost 37 of 84 frames, so the right number of workers must be measured at gate G1 (Decision).
- Never assume the set is complete: show how many frames were requested, received and rejected (Decision).
- Restrict a first request to one detector or one detector pair and a time window, and let the user widen it, to keep the frame count near 100 (Decision; section 12 explains why).

## 5 Coordinates, time, units and wavelength

Most silent errors in this project would come from mixing conventions, so this section fixes each one and names its pitfall.

| Topic | Convention we use | Pitfall | Label |
| --- | --- | --- | --- |
| Sky coordinates | ICRS, RA and Dec in decimal degrees internally; the UI also accepts sexagesimal | Images use the TAN projection with SIP distortion terms (CTYPE RA---TAN-SIP); astropy's WCS handles it | Doc, Decision |
| Pixel indexing | Astropy gives 0-based pixels; FITS headers are 1-based. To place a cutout pixel in the parent image: x\_parent = 1 + x\_cutout - CRPIX1A (same for y), with CRPIX1A and CRPIX2A from the cutout header | Off-by-one errors in PSF selection and in registration | Doc |
| Observation time | The TAP value time\_bounds\_lower, in days (almost certainly MJD; verify). The header also holds the exposure start in UTC and the elapsed time TELAPSE. We use mid-exposure = start + half the exposure | Different time fields in TAP, SIA and headers; confirm they agree | Doc, Decision |
| Surveys and epochs | The header keyword SPS\_PA\_ECL gives the observatory position angle: 0 degrees is survey 1 or 3, 180 degrees is survey 2 or 4. Surveys 1 and 2 cover the first 12.5 months, surveys 3 and 4 the second 12.5 months; targets in surveys 3 and 4 are shifted by 6 arcmin | A survey is not a six-month epoch; do not label time bins by survey number | Doc |
| Proper motion and epoch | Catalogue positions are propagated to the frame's mid-exposure time before overlay or photometry. Gaia positions are at epoch 2016.0 (verify) | Fast movers drift many pixels from catalogue positions that are years old | Memory, Decision |
| Observer position | Headers carry the spacecraft position and velocity from pipeline version 6.4.0 onward, which allows spacecraft-centred ephemerides. Version 1 uses geocentric positions | Parallax from low Earth orbit matters only for the nearest solar-system objects | Doc, Decision |
| Surface brightness to flux | Images are in MJy/sr; 1 MJy/sr equals 23.5045 microjansky per square arcsec. Multiply by the pixel solid angle in square arcsec (solid angle pixel map) to get flux density per pixel | Forgetting the solid angle map; using nominal 6.15 arcsec when pixel area varies | Doc |
| Variance | VARIANCE is in (MJy/sr) squared | Adding variances after rescaling pixels; propagate scale factors squared | Doc |
| Wavelength per pixel | For display, use the in-file WCS-WAVE table (an 11 by 11 control grid; bilinear interpolation is good to about 1 nm). For science, use CWAVE and CBAND from the Spectral WCS calibration product | Using WCS-WAVE for science; leaving SIP active on the wavelength WCS (set sip to None) | Doc |
| Zodiacal light | The ZODI layer is a model and is not subtracted from IMAGE | Treating IMAGE as background-free | Doc |
| Missing pixels | Some pixels are NaN, for example early-overflow pixels at bright stars | NaN breaking sums and sorts | Doc |
| Detector names | D1 to D6; band names look like SPHEREx-D2; a detector's wavelength range is fixed by its filter | Assuming one wavelength per frame | Doc |

## 6 From request to frames: the science pipeline

Six steps turn a requested position into combined frames, and each step has a defined input, output and failure behaviour.

&#91;embedded content: science pipeline · 6 steps\]

The table gives each step's contract; sections 7 and 8 detail the grouping and masking rules.

| Step | Input | Output | If it fails |
| --- | --- | --- | --- |
| 1 Discover | RA, Dec, field of view, releases, detector filter | List of frames: URL, detector, band, observation time, release, processing version | No rows: show a 'no coverage' state with the nearest observed times. Query error: use the cache or demo mode |
| 2 Retrieve | Frame URL, center, size | Cutout file with IMAGE, FLAGS, VARIANCE, ZODI, PSF or ePSF, and WCS-WAVE | Retry with back-off; after the last retry record a missing frame with its URL and reason |
| 3 Screen | Cutout headers | Keep or reject with a reason: astrometry flag FINAST above 1 is rejected, FINAST equal to 1 is kept with a warning, a very large masked fraction is rejected, a release the user did not select is excluded | Never drop silently; show the count and reasons of rejected frames |
| 4 Mask | FLAGS layer, masking policy (section 8), optional wavelength window | Mask array and a background-subtracted image (section 7) | Missing flags layer: reject the frame |
| 5 Register | Cleaned frame, its WCS with SIP terms, target grid | Frame resampled to a common grid centred on the request; flux-conserving for images, nearest-neighbour or interpolated for masks | Failed WCS: reject the frame |
| 6 Combine | Registered frames, variance, masks, grouping (section 7) | Coadds per group with coverage-count and variance maps; the single frames remain available for playback | A group with no valid pixels: show an empty tile with the reason |

## 7 Grouping, masking and combining frames

Frames are grouped by release, detector and time bin, masked, background-subtracted and combined with variance weights; the grouping rules matter more than the arithmetic.

**Grouping keys**

| Key | Rule | Why | Label |
| --- | --- | --- | --- |
| Release | Never combine QR1 with QR2; combine QR2 with QR3 only after applying the flux-correction product, otherwise keep them as separate groups. Positions may be mixed in a video; fluxes may not | IRSA tells users not to mix QR1 and QR2 and to take care with QR2 and QR3 | Doc, Decision |
| Detector | One detector per coadd; a colour composite uses three coadds | Each detector has its own wavelength range, noise and sensitivity | Decision |
| Time bin | User-selectable; options below | Controls both signal-to-noise and motion smearing | Decision |
| Wavelength window (optional) | Mask pixels whose per-pixel wavelength lies outside the window the user chose | Frames of one detector sample different wavelengths at a given sky position | Decision |

**Time-bin options**

| Option | What it is | Strength | Weakness |
| --- | --- | --- | --- |
| Fixed width | Calendar bins such as 7, 14 or 30 days | Simple and predictable | Bins can be empty or thin because coverage is uneven |
| Adaptive | Widen each bin until it holds a minimum number of frames | Even signal-to-noise | Bin boundaries differ between fields |
| By visit | One set of up to 4 exposures taken after the same large slew | Natural unit of the survey | Few frames per bin; low signal-to-noise |
| By survey | The four survey definitions (section 5) | Matches mission terminology | Bins last months; coarse for motion |

Proposed default: adaptive bins with a minimum frame count, to be confirmed with real coverage at gate G1 (Decision).

**How far a mover smears inside a bin** (our arithmetic; the asteroid rate is a published figure for a main-belt asteroid at 3 AU near opposition, and one visit is assumed to last about 10 minutes)

| Bin length | Star moving 10 arcsec a year (Barnard's Star-like) | Main-belt asteroid, about 20 arcsec an hour |
| --- | --- | --- |
| One exposure (114 s) | 0.00004 arcsec | 0.6 arcsec |
| One visit (about 10 min) | 0.0002 arcsec | 3.3 arcsec |
| One day | 0.03 arcsec | About 480 arcsec; beyond a typical cutout |
| 30 days | 0.8 arcsec | Not applicable |
| Six months | 5 arcsec, under one 6.15-arcsec pixel | Not applicable |

Slow movers such as the test targets survive coadds of weeks to months; asteroid-speed movers smear within minutes, so they must be viewed as single frames or searched for with shift-and-stack (see the PRD's ML Research Brief).

**Background.** The ZODI layer is a model and is not subtracted. IRSA's own demo estimates a mesh background with the sep package (64 by 64 pixel mesh) on full images. Our cutouts can be smaller than that mesh, so for small cutouts we use a sigma-clipped median or a low-order plane fit over unmasked pixels, and compare against the ZODI model during testing (Decision; Doc for the demo).

**Registration.** Convert to flux per pixel with the solid angle map, then resample to the common grid with a flux-conserving method (IRSA's demo uses reproject\_exact for images and interpolation for masks). Single bad pixels grow into multi-pixel NaN regions under interpolation, so masks are resampled conservatively and dilated by one pixel (Doc for the demo; Decision for the rest). Default output scale is the native 6.15 arcsec; a 2 times finer display grid is optional.

**Combining.** Variance-weighted mean per pixel over unmasked frames; the combined variance is the inverse of the summed weights. This assumes independent noise, which resampling and the PSF make only approximately true, so reported errors are lower bounds (Decision). Outlier rejection is optional and removes a moving source from a static-sky template, which is wanted when building a template to subtract.

## 8 Quality flags and masking policy

By default we mask every flag except SOURCE and FULLSAMPLE, as published science analyses of SPHEREx photometry do, and offer a lenient mode for users who want to see flagged pixels.

Each pixel in the FLAGS layer is an integer in which every condition is one bit; bit n has the value 2 to the power n, so SOURCE (bit 21) equals 2,097,152. The list below follows Table 16 of the Explanatory Supplement (version 2.0, pipeline R7).

| Flag | Bit | Meaning | Default policy |
| --- | --- | --- | --- |
| TRANSIENT | 0 | Transient such as a cosmic-ray hit during the exposure; also triggered by charge spilling from very bright stars; hits in the first ten seconds may be missed | Mask |
| OVERFLOW | 1 | Overflow threshold reached, about half of full-well saturation | Mask |
| SUR\_ERROR | 2 | Data-handling error onboard; combined with TRANSIENT or OVERFLOW it marks an early event | Mask |
| NONFUNC | 6 | Permanently unusable pixel | Mask |
| DICHROIC | 7 | Low-throughput corners of detectors 3 and 4 | Mask |
| MISSING\_DATA | 9 | Data lost before ingest | Mask |
| HOT | 10 | Noisy or spurious pixel in this exposure | Mask |
| COLD | 11 | Unresponsive or abnormally low in this exposure | Mask |
| FULLSAMPLE | 12 | Full sample history available; purely informational | Ignore |
| PHANMISS | 14 | Phantom-pixel correction could not be applied | Mask |
| NONLINEAR | 15 | No reliable nonlinearity correction | Mask |
| PERSIST | 17 | Persistent charge from an earlier bright exposure | Mask |
| OUTLIER | 19 | Flagged by the outlier-detection module | Mask |
| CROSSTALK | 20 | Electrical crosstalk (types 1 and 2) | Mask |
| SOURCE | 21 | Pixel mapped to a known source from the reference or solar-system catalogue | Do not mask; use as a label |
| GHOST | 22 | Optical ghost of a bright source inside the frame | Mask |
| GHOST\_FPA | 23 | Unused; to be removed in Year 2 processing | Ignore |
| GHOST\_EXT | 24 | Ghost of a bright source outside the field of view; in development | Mask |
| STREAK | 25 | Satellite streak | Mask |
| BLOOM | 26 | Source blooming | Mask |
| SNOWBALL | 27 | Very energetic cosmic-ray or decay event | Mask |
| HALO | 28 | Halo around a transient; use with caution | Mask (visible in lenient mode) |
| SATELLITE\_HALO | 29 | Halo around a satellite streak; not recommended for science | Mask |

The introduction notebook also lists PHANTOM (bit 4) and REFERENCE (bit 5) in the FLAGS header, but Table 16 does not; treat them as masked and check against the header (Doc, to verify).

**Why SOURCE is not masked.** It marks pixels within the mask radius of any known source, including the solar-system objects in IRSA's catalogue, so masking it would delete the very stars and movers we want to show. It is also a useful label for cross-matching. Its radius is set from a predicted magnitude and can be wrong (Doc).

**Frame-level screening (header keywords)**

| Keyword | Meaning | Default |
| --- | --- | --- |
| FINAST | Astrometry quality: 0 good, 1 corner offsets of a couple of pixels, higher means poor and not to be used | Reject above 1; keep 1 with a warning |
| N\_TRANSIENT with the image area | Fraction of transient pixels; the pipeline treats more than 10 percent as a high-transient image | Reject at a threshold to tune at gate G1 |
| VERSION | Pipeline version (for example 6.5.6 or 7.x) | Record on every frame; used to group and to explain differences |

IRSA also keeps a list of images with large contaminated areas (the anomaly images page); we plan to use it as a rejection list and as negative examples (section 15).

Sources: Doc (Explanatory Supplement sections 2.2, 3.2.5 and 3.2.8; introduction notebook); Paper (two analyses that drop every flag except SOURCE).

## 9 Test targets and expected motion

The three moving targets should shift by only about one to two pixels over the mission so far, so the video must make sub-pixel-scale motion legible; the two variable stars should not move.

Shifts below assume a baseline of about 1.3 years, from the start of regular science operations on 1 May 2025 (Doc) to about September 2026, and use the proper motions in the table; the pixel is 6.15 arcsec. This is our arithmetic, to be checked against measured centroids at gate G1.

| Target | What it is | Position (J2000) | Proper motion | Expected shift | Watch for | Label |
| --- | --- | --- | --- | --- | --- | --- |
| Barnard's Star | Nearest single star system, about 6 light-years away | Resolve by name | About 10.4 arcsec a year; parallax about 0.545 arcsec | About 13.5 arcsec, 2.2 pixels | Bright star: blooming, persistence | Paper |
| Epsilon Indi B | A pair of brown dwarfs orbiting the bright star Epsilon Indi A | Resolve by name | 4.68 arcsec a year (A: 4.70) | About 6.1 arcsec, 1.0 pixel | The pair is too close to resolve at this pixel size; the bright primary lies well away from it, so check for ghosts and stray light (our caution) | Paper, Memory |
| WISE 0855-0714 | Very cold, fast-moving brown dwarf | The brief gives 08h55m10.831s, -7d14m42.53s, about 133.7951, -7.2451 degrees (our conversion; epoch not stated) | 8.1 arcsec a year; parallax 0.454 arcsec, about 1 arcsec peak to peak | About 10.5 arcsec, 1.7 pixels | Extremely faint at short wavelengths; best seen at the long-wavelength detectors (to confirm) | Paper, Memory |
| RW Aurigae | Irregular variable star (the challenge names this star; a separate star, R Aurigae, is a Mira variable) | About 05h07m50s, +30d23m58s (BAA catalogue; confirm with a name resolver) | None of note | None | Brightness changes with time; magnitude range about 9.4 to 12.8 in visible light | Paper |
| R Draconis | Mira-type variable (to confirm) | Resolve by name; no verified position retrieved | None of note | None | Large brightness swings; may saturate when bright | Memory |

**Handling in the product**

- Presets store the target name and the resolver result; the position is re-resolved at runtime rather than hard-coded, except WISE 0855, whose brief coordinates are kept as a cross-check (Decision).
- For the moving targets the preset also stores proper motion so the viewer can centre on the expected position at each frame time and draw a reference crosshair (PRD FR-A6, FR-C6) (Decision).
- A catalogue position is valid only at its own epoch; the brief does not state the epoch for WISE 0855, so the search radius must allow for several arcsec of drift (Decision).

**Acceptance test at gate G1.** For each moving target, the measured centroid shift between the earliest and latest well-covered time bins should agree with the expected shift to within half a pixel; each variable star should show brightness change with time and no centroid shift (Decision).

## 10 Spectra on the fly

A spectrum here is a set of single-wavelength flux measurements, one per frame that covers the clicked position, so it is built from many frames taken at different times and is never an instantaneous spectrum.

**Method (Decision, modelled on IRSA's source-discovery notebook and published pipelines)**

1. The user clicks a position or accepts a catalogue source. For a mover, the aperture centre is set per frame from its proper motion or ephemeris, because IRSA's own photometry tool ignores proper motion (Paper).
2. For every frame covering that position, read the cutout and convert to flux density per pixel with the solid angle map (section 5).
3. Estimate the local background in an annulus around the aperture with sigma clipping, then sum the aperture and subtract (the approach used in IRSA's mosaic and source notebooks; apertures of 3, 4 and 5 pixels in the source notebook).
4. Apply the aperture correction from the position-dependent ePSF; one published pipeline sets the aperture to enclose 95 percent of the energy.
5. Reject points with masked pixels inside the aperture under the policy in section 8.
6. Assign each point the central wavelength and bandwidth from the science wavelength product at the source pixel (section 5).
7. Uncertainty: the summed VARIANCE inside the aperture plus the background noise, as a first estimate. Photometric accuracy figures are not yet read from the Explanatory Supplement (section 16).
8. Plot flux against wavelength, colour-code points by observation time, and allow CSV download.

**Limits we state in the product**

| Limit | Why | Label |
| --- | --- | --- |
| Not instantaneous | Each point comes from a different exposure, hours to months apart; variable stars and movers can change between points | Doc |
| Blends | A published pipeline discarded sources with neighbours within about 10 arcsec; the pixel is 6.15 arcsec | Paper |
| Sparse coverage | One wavelength per exposure and only two of the six detectors per exposure at a given sky position | Doc |
| Atmospheric and instrument lines | Strong helium emission near 1.083 µm in bands 1 and 2 (with leak features near 0.84, 1.25 and 1.49 µm); other lines near 0.78, 0.93, 1.13, 1.81, 2.63, 2.75, 4.03 and 4.64 µm; shuttle-glow contamination near 2.9 µm in band 4 and 4.5 µm in bands 5 and 6 | Doc |
| Detector edges | Reduced throughput and higher noise in the dichroic regions of bands 3 and 4 | Doc |
| Bright sources | Early overflow gives NaN pixels, and blooming and persistence affect neighbours | Doc |
| Mixed releases | Different gain calibrations; do not mix fluxes without the correction product | Doc |

**Display.** Flux density in microjansky by default, with AB magnitude as an option; every plot shows the aperture, the number of frames used and the number rejected (Decision).

## 11 External overlays

Every overlay is placed at the position the object had at the frame's observation time, never at its catalogue epoch, and each overlay states which epoch it uses.

| Overlay | Source and access | Epoch handling | Notes | Label |
| --- | --- | --- | --- | --- |
| Gaia stars | Gaia DR3 through a VO catalogue service (CDS or the ESA archive); SPHEREx's own astrometry is tied to Gaia DR3 with proper motions applied | Positions are at epoch 2016.0 (verify); propagate with proper motion to the frame time; skip sources with poorly constrained motion, as the pipeline does | Also the check for our registration (section 15) | Doc, Memory |
| WISE and NEOWISE | IRSA catalogue services, reachable with astroquery's IRSA module | AllWISE positions are from about 2010 and carry no motion, so fast movers sit many arcsec from where SPHEREx saw them; WISE 0855 moves about 8 arcsec a year (about 120 arcsec in 15 years, our arithmetic). Label the epoch; use a catalogue with motions if available | Overlay shows WISE as it was, not as it is | Doc, Paper |
| Known solar-system objects | SkyBoT cone search (field up to 10 degrees, given an epoch); the astroquery IMCCE wrapper calls it; small fields return in about 10 seconds | Query at each frame's mid-exposure time; results are specific to that time | Version 1 uses geocentric positions; spacecraft position in the headers allows a later improvement | Doc, Paper |
| Name resolution | A public resolver (the IRSA tools offer NED then SIMBAD) | Not applicable | Used for presets and for typed names | Doc |
| SPHEREx source flag | The SOURCE bit in the FLAGS layer | Applied by the pipeline at the frame's time | Shows pixels the pipeline already attributes to known sources, including solar-system objects | Doc |

**Rules**

- Overlays never alter pixel data; they are drawn above it and can be toggled (Decision).
- Overlay queries are cached by position and frame time, and are rate-limited like the IRSA calls (section 12) (Decision).
- An overlay that fails to load is hidden with a notice, never replaced by guessed positions (Decision).

## 12 Volume, latency and caching assumptions

A request for a typical position can mean hundreds of frames and gigabytes of transfer, because each cutout carries a PSF layer of several megabytes however small the cutout is; this makes caching and frame limits essential.

**What we know**

| Quantity | Value | Label |
| --- | --- | --- |
| Full spectral image | 67 to 70 MB (four 2040 by 2040 float32 layers is about 67 MB, our arithmetic, which matches) | Doc |
| PSF layer kept in every cutout | QR2: 101 by 101 by 121 float32, about 4.9 MB (our arithmetic); a third-party tool reports about 5 MB minimum per cutout. R7 ePSF layer: about 1.9 MB (our arithmetic) | Doc, Paper |
| Frames per position | 415 images (all detectors, 1-arcsec search, QR2 at the time of the tutorial); 84 for detector 2 alone near M101; deep fields have more; counts grow with every release | Doc |
| Metadata query | 16.6 seconds for 84 rows | Doc |
| Cutout download | 1.4 minutes in series for 84 cutouts; 10 workers took 6 seconds with 37 failures; a larger run took 5 to 7 minutes in series for 700 cutouts of 0.01 degrees | Doc |
| Availability | Calibrated images reach IRSA within 60 days of observation; ingest is weekly; image search lags about a day behind the table query | Doc |

**What a field of view costs** (four pixel layers at 4 bytes each, at 6.15 arcsec per pixel; our arithmetic)

| Field of view | Pixels per side | Pixel data per frame | With a QR2 PSF layer |
| --- | --- | --- | --- |
| 0.1 degrees | 59 | 0.06 MB | About 5 MB |
| 0.5 degrees | 293 | 1.4 MB | About 6 MB |
| 1 degree | 585 | 5.5 MB | About 10 MB |
| 2 degrees | 1171 | 22 MB | About 27 MB |
| Full image | 2040 | 67 MB | About 72 MB |

At 0.1 degrees, 400 frames cost about 2 GB, almost all of it PSF data. Ways to reduce this are an open question (section 16).

**Assumptions and limits (Decision, to validate at gate G1)**

- Default field of view 0.1 degrees; maximum 1 degree for the first release.
- A per-request cap of about 150 frames or about 1 GB; above that the user narrows detectors, time window or field of view.
- A first request covers one detector or one detector pair; the user widens it.
- At most 4 concurrent cutout requests per user and a global cap, to be tuned from measured failure rates, because IRSA's own parallel run lost almost half its frames.
- Cache keys include position, field of view, detector set, release and processing version, so a reprocessing never serves stale pixels; key granularity is an SDD decision.
- A cache hit must serve without touching IRSA; the five test targets are pre-warmed (PRD FR-I4).

## 13 Releases and acknowledgement

The data is being reprocessed while we build, so release handling must be configuration: a new release or a reprocessing should change what we serve without a code change.

| Release | What it is | Status and rules | Label |
| --- | --- | --- | --- |
| QR1 | First quick release, from July 2025 | Retired in February 2026; never combine with QR2 | Doc |
| QR2 | Reprocessed data from launch through October 2025, plus weekly releases; pipeline versions 6.4 to 6.5.6; image search collections spherex\_qr2 and spherex\_qr2\_deep | Default release for the first version; files from 6.4 to 6.5.5 carry the suffix +psffix1 after a correction of the PSF header order (an error of up to 5 percent in photometry if uncorrected) | Doc |
| QR3 | Surveys 3 and 4 and onward, pipeline R7; collections spherex\_qr3 and spherex\_qr3\_deep; releases began in September 2026 | Different gain calibration from QR2: combine only with the flux-correction product. The Supplement says the first weeks of survey 3 and 4 data (16 May to 19 July 2026) were processed with 6.5.6 and the R7 versions come with Data Release 1 | Doc |
| DR1 | Full reprocessing of surveys 1 and 2 with the R7 pipeline | Planned for late fall 2026, close to the event; processing versions and file contents may change under us | Doc |

The Explanatory Supplement version we read is 2.0 (25 August 2026); the data products page we read is dated 28 September 2026. The two differ in detail about QR3, so the configuration must be checked against the archive on the day of the event (Decision).

**Configuration we need (Decision)**

- For each release: the SIA collection names, the TAP filters, the release label, and whether it is selected by default.
- A processing-version field on every frame and in every cache key, so a reprocessing invalidates old pixels automatically.
- A switch to hide any release that is mid-reprocessing.

**Acknowledgement and citation (required by IRSA).** Display IRSA's acknowledgement wording verbatim in the product's footer and in any exported file. The text is given on IRSA's SPHEREx overview page and in section 1.6 of the Explanatory Supplement; store it in configuration and do not paraphrase it. Cite the release DOIs: 10.26131/IRSA629 for QR1 and 10.26131/IRSA652 for QR2 (Doc). We have not found a QR3 DOI (section 16).

## 14 Scientific caveats and wording rules

The product shows what SPHEREx measured and what a method suggests; these rules keep its words and visuals within what the data supports.

| Situation | Rule |
| --- | --- |
| Something moves between frames | Say 'appears to move' with the measured shift and its uncertainty; never say 'discovered'. Distance and orbit are not derived (non-goal) |
| A candidate from any method, ML or not | Call it a candidate that needs follow-up observations; show the score, the method and its version |
| Time axis | Frames are unevenly spaced in time. Playback offers frame order (default) and a true-time scale, and the timeline always shows the gaps |
| Observed versus predicted | Observed positions are filled markers; positions from a proper motion or an ephemeris are hollow and labelled |
| Brightness change between frames | Never described as variability unless frames share detector, wavelength window and calibration release; otherwise say the frames are not like-for-like |
| Spectra | Labelled as built from separate exposures at different times; never as an instantaneous spectrum |
| Coadds and denoising | Labelled with the frames combined; any learned processing is labelled and the unprocessed view is one click away |
| Masked pixels | Shown as masked, never filled in silently |
| Rejected or missing frames | The count and reasons are always visible |
| Mixed releases | Colour or label by release; no flux comparison across releases without the correction |
| Catalogue overlays | Each states its epoch and whether positions were propagated |
| Bright stars | Warn that blooming, ghosts and persistence may produce false features near bright sources |
| Sub-pixel motion | Do not claim a shift smaller than the registration accuracy measured on reference stars (section 15) |
| Planet X and similar | The tool makes no claim of detecting any such object |
| Data currency | Show the release, processing version and the date the data was last updated |

## 15 Validation data and ground truth

We validate against known objects, injected sources and reference stars, so every number we show can be checked against something independent.

| Dataset | Purpose | Source | Notes |
| --- | --- | --- | --- |
| Five test targets | End-to-end acceptance: expected shifts and brightness behaviour (section 9) | The challenge brief and catalogues | Used by gate G1 and the demo |
| Gaia reference stars in every field | Registration check: after registration, star positions should match Gaia (propagated to the frame time) within a tolerance we set at G1, proposed at half a pixel | Gaia DR3 | The pipeline itself reports sub-arcsecond astrometry for good solutions (Doc) |
| Known solar-system objects at frame times | Positive examples of movers, and a check of the overlay | SkyBoT | Ground truth for the ML track and for the overlay |
| Injected sources | Known-truth tests for coadds, denoising, spectra and mover search: add artificial stationary and moving sources of known flux into real cutouts | Our own tool using the ePSF | Records flux, position and motion; the basis of the completeness measurement in the ML Research Brief |
| Artefact examples | Negative examples and rejection tests: ghosts, stray light, streaks, cosmic-ray showers | IRSA's list of images with large contaminated areas and the Supplement's figures | Doc |
| Published spectra | Spectrum check: compare our points for known brown dwarfs with published SPHEREx spectra | Papers on SPHEREx brown-dwarf spectra | Paper |
| IRSA's own tools | Cross-check of spectra and frame lists at the same position | Spectrophotometry tool; spectral image search | Doc |

**Automatic checks (the test plan will own the full list)**

- WCS round trip: pixel to sky to pixel returns the start within a small fraction of a pixel.
- Flux conservation: total flux is unchanged by resampling (within the tolerance of the method).
- Wavelength lookup: the interpolated table agrees with astropy's spectral WCS to about 1 nm.
- Flag decoding: each documented bit is decoded to its name, and SOURCE equals 2,097,152.
- Time order: frames are sorted by observation time and the timeline matches the metadata.
- Cache determinism: the same request gives byte-identical results from the cache and from a fresh run.
- Release hygiene: a reprocessed file never reuses a cache entry made from its predecessor.

## 16 Open data questions

Fifteen questions remain; the first six decide whether the speed targets in the PRD are reachable, so settle them first, mostly at gate G1 or by asking IRSA's help desk.

- [ ] **Cutout size on the wire.** Can the cutout service leave out the PSF layer, or can we read only the layers we need? Without that, each cutout costs about 5 MB (section 12).
- [ ] **Request limits.** What are IRSA's limits and etiquette for table queries and cutouts, and may a public app proxy them? Why did 37 of 84 parallel cutouts fail?
- [ ] **Time field.** Is time\_bounds\_lower the start of exposure in MJD days, and which header keyword matches it for mid-exposure?
- [ ] **Coverage of the five targets.** How many frames, with what time spread and in which detectors, does each target have today?
- [ ] **Time-bin default.** Which adaptive rule gives readable videos on real coverage (section 7)?
- [ ] **Best detectors for the movers.** In which detectors are WISE 0855, Barnard's Star and Epsilon Indi B visible, and at what signal-to-noise?
- [ ] **Accuracy figures.** What are the astrometric and photometric accuracies per band, and the single-exposure sensitivity? We read only part of the Explanatory Supplement (sections 3.3 and 4.2 are still to read).
- [ ] **QR3 specifics.** The citation DOI, the exact collection contents, and what DR1 will change in late fall 2026.
- [ ] **Reprocessing plan.** How we detect and handle a reprocessing during the event (section 13).
- [ ] **Background method.** Sigma-clipped median, plane fit or the ZODI model for small cutouts (section 7).
- [ ] **Spectral channels product.** Whether to use it, instead of per-pixel wavelength windows, to select channels.
- [ ] **Positions of the other test targets,** including R Draconis, and which epoch the brief's WISE 0855 coordinates use.
- [ ] **Known-object lookup.** Rate limits and observer location for SkyBoT, and whether spacecraft-centred ephemerides are worth it.
- [ ] **Overlay catalogues.** Which service and catalogue version for Gaia, and a WISE catalogue with proper motions.
- [ ] **Image layer for the context map.** Whether IRSA offers a SPHEREx tiled survey; none was found, which the SDD needs for Aladin Lite.

## Sources

The first group was opened and read for this specification (as of 1 November 2026) and backs the facts labelled Doc; the second came from search results and backs the facts labelled Paper, so open each before relying on a detail. Facts labelled Memory have no source yet.

**Opened and read**

- [SPHEREx Explanatory Supplement, version 2.0 (SSDC-DP-017)](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf); only the first part (through section 3.2.10) was retrieved
- [SPHEREx Data Products, SPHEREx Archive at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products)
- [SPHEREx Data Access, SPHEREx Archive at IRSA](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access)
- [Introduction to SPHEREx Spectral Images, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-intro)
- [Download a collection of SPHEREx Spectral Image cutouts, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-cutouts)
- [SPHEREx Source Discovery Tool demo, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-source-discovery-tool-demo)
- [Understanding and Analyzing SPHEREx Mosaic Cubes, IRSA Tutorials](https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic)
- [Planet X and SPHEREx challenge page, HackAthlone 2026](https://hackathlone.com/challenges/planet-x-and-spherex)

**From search results**

- [SPHEREx survey planning software (arXiv 2508.20332)](https://arxiv.org/pdf/2508.20332): field of view, pixel scale, pointing pattern
- [SPHEREx and the VO at IRSA (IVOA presentation)](https://wiki.ivoa.net/internal/IVOA/InterOpJune2025Plenary/SPHEREx_VO_IRSA_laity_interopMay2025.pdf): a spectrum in 51 exposures
- [SPHEREx cutout capabilities (IRSA)](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/cutout_tool.html)
- [SPXQuery cutout guide](https://spxquery.readthedocs.io/en/latest/user_guide/cutouts.html): cutout file size floor
- [Photometry flag exclusions in SPHEREx brown-dwarf spectra (arXiv 2607.00543)](https://arxiv.org/pdf/2607.00543) and [a second analysis (arXiv 2607.06200)](https://arxiv.org/pdf/2607.06200)
- [A SPHEREx pipeline and spectral library for ultracool dwarfs (arXiv 2604.22012)](https://arxiv.org/pdf/2604.22012): IRSA's photometry tool ignores proper motion
- [Atmospheric diversity of giant planet analogs with SPHEREx (arXiv 2608.08908)](https://arxiv.org/pdf/2608.08908): 95 percent aperture, neighbours within 10 arcsec
- [List of stars with large proper motion](https://en.wikipedia.org/wiki/List_of_stars_with_large_proper_motion): Barnard's Star, Epsilon Indi A and B
- [Parallax and proper motion of WISE 0855-0714 (arXiv 1404.6501)](https://ar5iv.arxiv.org/html/1404.6501) and [Flux and color of WISE 0855-0714 (arXiv 2505.12105)](https://arxiv.org/pdf/2505.12105)
- [British Astronomical Association list of variables in Auriga](https://britastro.org/vss/obj-aur.html): RW Aurigae
- [SkyBoT web services](https://ssp.imcce.fr/webservices/skybot/), [astroquery IMCCE](https://astroquery.readthedocs.io/en/latest/imcce/imcce.html) and [SkyBoT cone-search timing (arXiv 1601.02087)](https://arxiv.org/pdf/1601.02087)
- [Fast algorithms for slow moving asteroids (arXiv 1901.02492)](https://arxiv.org/pdf/1901.02492v1): main-belt motion rate
- [SPHEREx Quick Release 2 data DOI](https://www.ipac.caltech.edu/doi/10.26131/IRSA652)
