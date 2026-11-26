# Technical evidence — IRR demo video

**Video:** "Agorail: When an AI Agent Pays an Invoice, What Proves It Was Real?"
**Rendered:** 2026-11-26 (IST) · **Final runtime:** 80.17 s, 1920×1080, 30 fps.
**Deliverables:** `dist/irr-demo.mp4` (sha256 b9ebc098801734c7…),
`dist/irr-preview-15s.mp4` (15.00 s, silent; sha256 4632d50742918834…),
`dist/captions.vtt` (18 cues), `dist/poster.png`.

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

`capture/demo_runs.py` prints, through the shipped verifier:

- **Example 2** (file example, synthetic full evidence): all three
  verdicts established.
- **Example 1** (NIC's published signed sample, dummy particulars):
  matches established; active at payment not established ("no
  payment-event evidence supplied"); signed not established ("the
  checkout carries no AP2 merchant authorization").
- **Cancelled before payment:** the shipped test suite's `Factory`
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
  durations: s1 15.46, s2 16.05, s3 16.92, s4 18.61, s5 11.54 s.
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
