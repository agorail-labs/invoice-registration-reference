# Technical evidence — IRR demo video

**Video:** "Agorail: When an AI Agent Pays an Invoice, What Proves It Was Real?"
**Rendered:** 2026-11-26 (IST) · **Final runtime:** 85.29 s, 1920×1080, 30 fps.
**Deliverables:** `dist/irr-demo.mp4` (sha256 c621f31e8b9b15b7…),
`dist/irr-preview-15s.mp4` (15.00 s, silent; sha256 1cf2738362f560ea…),
`dist/captions.vtt` (21 cues), `dist/poster.png`.

## What was actually run

Source: the public repository at commit `217b5bb` (the Gate 3 release
`e852200` plus the approved docs-only follow-up), extracted with
`git archive` into `src/` in this workspace. The verifier is the
shipped, unmodified code; dependencies from
`src/verifier/requirements.txt` in a fresh venv.

```bash
python3 -m verifier.invoice_reference_verifier   # capture/cli.txt
python3 capture/demo_runs.py                      # capture/demo-runs.txt
```

The driver resolves its source tree itself: from a checkout of this
repository it uses the checkout root (two levels above
`video/capture/`); in the build workspace it uses the `src/` tree
extracted from commit `217b5bb` (`git archive 217b5bb`). No other
setup is needed beyond the verifier's requirements.

`capture/demo_runs.py` prints, through the shipped verifier:

- **Example 2** (file example, synthetic full evidence): all three
  verdicts established.
- **Example 1** (NIC's published signed sample, dummy particulars):
  matches established; active at payment not established ("no
  payment-event evidence supplied"); signed not established ("the
  checkout carries no AP2 merchant authorization").
- **Cancelled before payment (separate synthetic test):** the shipped test suite's `Factory`
  construction (fresh keys, validly signed status reporting a
  cancellation at 2026-11-20T12:00:00+05:30, before the case's payment
  event) run through the same `verify()`: active at payment
  contradicted, reason "authenticated cancellation took effect at or
  before the payment event".

Every terminal line in the frames is copied verbatim from
`capture/demo-runs.txt` (selection only, no rewording); column
alignment is preserved from the capture.

## Narration and assembly

- Narration: synthesized per scene (`audio/s1..s5.mp3`, voice Helio /
  avocado_v2:MAI_03), trailing silence trimmed at −45 dB. Measured
  durations: s1 15.46, s2 18.45, s3 16.92, s4 18.80, s5 14.06 s.
  Scene durations are audio + 0.30 s, as in the SCQ/MSE demo build.
- Frames: `render/render.py` (PIL, Agorail palette, same design
  language as the SCQ/MSE demo); assembly `render/build.sh` (ffmpeg,
  per-scene fades, concat). Rebuild: `python3 render.py && bash
  build.sh && python3 make_captions.py`.
- One rendering defect was found in QC and fixed before delivery:
  the first build's word-wrap collapsed the captures' verdict-column
  alignment; the terminal renderer now preserves lines verbatim when
  they fit and wraps with the original hanging indent when they do
  not. Trailing narration silence that produced ~0.9 s gaps at scene
  boundaries was trimmed; the final cut has no silence ≥ 0.8 s at
  −45 dB.

## QC (final cut)

- Streams: video 1920×1080 @ 30 fps + AAC audio.
- blackdetect (0.5 s, pix_th 0.02): 0 black segments.
- silencedetect (−45 dB, 0.8 s): 0 silences.
- Audio peak level: −7.5 dB (no clipping).
- Frames visually inspected at t = 8, 24, 40, 57, 74 s (scenes 1–5):
  titles, chips, terminal alignment, URL rows and callouts render as
  designed; no overflow.
- Claims discipline: the video demonstrates only behavior the shipped
  verifier exhibits on the captured inputs. It claims no filing, no
  package, no adoption, and no production use.

## Corrections after review (26 November 2026)

Applied on the reviewer's notes before wider sharing; the film was
rebuilt and re-QC'd afterwards (same checks as above, all passing):

1. Scene 3 headline now reads "NIC's signed documentation sample" —
   the verifier establishes a match to the published sample with
   dummy particulars, not to a genuine invoice.
2. Scene 4 no longer says "same case": the headline, the narration
   (re-synthesized for this scene only) and the capture's section
   title all say "separate synthetic test", so the Factory
   cancellation cannot be mistaken for a fact about the NIC sample.
   The re-run capture differs from the original in exactly that one
   title line; every verdict and reason is unchanged.
3. The capture driver now resolves the checkout root as described
   above, so the captures can be regenerated from the repository
   itself; the stored captures remain the ones the frames quote.

## Public-release wording update (26 November 2026)

On Arjun's instruction, "experimental" was removed from every
public-facing surface of the v0.1 materials, and the film was
rebuilt from source and re-QC'd (0 black segments, 0 silences
>= 0.8 s at -45 dB, audio peak -7.5 dB, frames inspected):

- Release title: "Invoice Registration Reference v0.1 — Public
  Release" (README heading; video package README).
- Description: "reference implementation for verifying invoice
  registration evidence in UCP checkout and order flows" (README
  lead; GitHub repository description on publication).
- Frame footers and the poster no longer carry "experimental";
  the closing callout drops "Experimental research software".
- Scene 5 narration was re-synthesized (this scene only) to end
  with the evidence disclosure: "The demo uses simulated
  registration status and payment capture evidence. Live
  integrations supply authenticated evidence." The same disclosure
  line appears on the closing frame and in the README. The
  "nothing filed / no package" disclaimer line was removed from
  the footers, the closing callout, the narration, the README and
  the spec header on Arjun's instruction. Captions regenerated:
  19 cues.
- Untouched, as instructed: the verifier, the schema, the captured
  outputs, and all historical records (release/ and research/).

## Published-package entry point (26 November 2026, later revision)

At Arjun's direction the demo's entry point is now the published
PyPI package, `invoice-registration-reference` 0.1.0 (PyPI project
uploaded 2026-11-26; wheel and sdist). Scene 2 was rebuilt around a
real run of that package:

- `capture/scene2-run.txt` is the verbatim capture: in a clean
  venv, `python -m pip install invoice-registration-reference==0.1.0`
  from PyPI, then `python video/demo_verify.py`.
- `video/demo_verify.py` is the complete runnable script shown
  beside the video: it loads the Example 2 fixture's checkout and
  order, assembles the evidence bundle from the fixture's
  `evidence/` directory, loads the trusted keys independently from
  `validation/trust_config.json` (entry `example2`) and
  `validation/trust_keys/`, and calls
  `verify(checkout, order, evidence_bundle, config)` from the
  installed package.
- The run's output — structurally valid, and all three verdicts
  established with the same reasons as the repository verifier's
  own run — is what Scene 2 shows. Scene 3 (NIC documentation
  sample) follows immediately, unchanged.
- Scene 2 narration was re-synthesized for the new script; the
  closing frame now links the PyPI package and the runnable
  example. One layout defect found in QC (verdict rows overflowing
  the terminal box) was fixed and the film rebuilt before this
  record was written.

## Faststart rewrap (26 November 2026, after review)

The reviewed film's MP4 index (moov atom) sat at the end of the
file, and the in-app player stalled partway through. Both dist
MP4s were re-wrapped with `-movflags +faststart` (stream copy —
identical picture and audio, index moved to the front) and
`render/build.sh` now encodes with faststart directly. The full
file was verified to decode with zero errors before and after.
