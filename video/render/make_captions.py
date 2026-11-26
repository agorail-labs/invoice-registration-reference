#!/usr/bin/env python3
"""Build captions.vtt from the narration sentences, timed proportionally
within each scene's measured duration (audio + 0.30s pad, as in build.sh)."""
import subprocess

SEGMENTS = [
    ("s1", ["An AI agent is told: pay this invoice.",
            "In a UCP checkout, paying is easy. Proving what was paid is not.",
            "Was the invoice really registered with the tax authority?",
            "Was that registration still active when the money moved?",
            "And did the business sign this checkout?"]),
    ("s2", ["The Invoice Registration Reference adds one capability to checkout and order: a reference to the invoice and its registration, checkable against the scheme's own signed evidence.",
            "Run the verifier on a complete synthetic case, and all three questions come back established, each with its reason."]),
    ("s3", ["Now the real thing: the tax authority's own published, signed sample.",
            "The verifier confirms the registration matches the invoice.",
            "But the sample carries no payment evidence, so was it active at payment? Not established.",
            "The verifier says what the evidence proves, and no more."]),
    ("s4", ["And when the evidence turns, so does the verdict.",
            "Same case, but the signed status says the registration was cancelled before the payment event.",
            "Active at payment: contradicted, with the cancellation named as the reason.",
            "Three verdicts, three values: established, not established, contradicted."]),
    ("s5", ["Read the specification, and run the verifier yourself.",
            "The repository is public, and the schema is live on GitHub Pages.",
            "Experimental research software: nothing filed, no package, no production claim."]),
]
PAD = 0.30

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True)
    return float(out.stdout.strip())

def ts(t):
    m, s = divmod(t, 60)
    return f"00:{int(m):02d}:{s:06.3f}"

lines = ["WEBVTT", ""]
t = 0.0
n = 0
for seg, sentences in SEGMENTS:
    scene = dur(f"../audio/{seg}.mp3") + PAD
    total_chars = sum(len(s) for s in sentences)
    cur = t
    for s in sentences:
        span = scene * len(s) / total_chars
        n += 1
        lines += [str(n), f"{ts(cur)} --> {ts(cur + span)}", s, ""]
        cur += span
    t += scene
open("../dist/captions.vtt", "w").write("\n".join(lines))
print(f"captions: {n} cues, total {t:.2f}s")
