#!/usr/bin/env python3
"""Render all frames for the IRR demo video (1920x1080).

Every terminal line rendered here is copied verbatim from the captured
runs in ../capture/ (see ../EVIDENCE.md). Design follows the Agorail
demo: dark navy, Agorail blue/cyan brand accents, DejaVu Sans / Mono.
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
os.makedirs(OUT, exist_ok=True)

BG_TOP = (8, 19, 31)
BG_BOT = (12, 30, 48)
PANEL = (13, 24, 38)
PANEL_EDGE = (35, 66, 92)
TEXT = (234, 243, 250)
MUTED = (159, 180, 200)
FAINT = (100, 128, 154)
CYAN = (70, 209, 232)
BLUE = (47, 140, 201)
GREEN = (63, 185, 80)
RED = (255, 123, 114)
AMBER = (242, 166, 90)
CHIP = (18, 38, 56)

SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def bg():
    img = Image.new("RGB", (W, H), BG_TOP)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    return img


def header(d, kicker):
    d.text((90, 56), "A G O R A I L", font=font(SANSB, 34), fill=TEXT)
    d.rectangle([90, 108, 240, 114], fill=CYAN)
    d.text((90, 132), kicker, font=font(SANS, 25), fill=MUTED)


def footer(d, note="Public v0.1 offline reference"):
    d.text((90, H - 58), note, font=font(SANS, 23), fill=FAINT)


def rounded(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def wrap(text, fnt, max_w, d):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def terminal(d, box, title, lines, line_h=44, fsize=27, title_size=24):
    x0, y0, x1, y1 = box
    rounded(d, box, 18, fill=PANEL, outline=PANEL_EDGE, width=2)
    d.ellipse([x0 + 28, y0 + 24, x0 + 48, y0 + 44], fill=(255, 95, 86))
    d.ellipse([x0 + 62, y0 + 24, x0 + 82, y0 + 44], fill=(255, 189, 46))
    d.ellipse([x0 + 96, y0 + 24, x0 + 116, y0 + 44], fill=(39, 201, 63))
    d.text((x0 + 140, y0 + 20), title, font=font(SANS, title_size), fill=MUTED)
    d.line([x0, y0 + 66, x1, y0 + 66], fill=PANEL_EDGE, width=2)
    f = font(MONO, fsize)
    y = y0 + 92
    max_w = x1 - x0 - 72
    for text, color in lines:
        if d.textlength(text, font=f) <= max_w:
            d.text((x0 + 36, y), text, font=f, fill=color)
            y += line_h
        else:
            indent = text[: len(text) - len(text.lstrip())]
            for i, seg in enumerate(wrap(text.strip(), f, max_w - d.textlength(indent, font=f), d)):
                d.text((x0 + 36, y), (indent if i == 0 else indent) + seg, font=f, fill=color)
                y += line_h
    return y


def callout(d, box, text, accent=CYAN, fsize=29):
    x0, y0, x1, y1 = box
    rounded(d, box, 14, fill=CHIP, outline=PANEL_EDGE, width=2)
    d.rectangle([x0, y0, x0 + 10, y1], fill=accent)
    f = font(SANS, fsize)
    y = y0 + 22
    for seg in wrap(text, f, x1 - x0 - 70, d):
        d.text((x0 + 36, y), seg, font=f, fill=TEXT)
        y += 40
    return y


def save(img, name):
    img.save(os.path.join(OUT, name))
    print("frame", name)


# ---------------------------------------------------------------- S1
def scene1(questions=False):
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "INVOICE REGISTRATION REFERENCE — A UCP EXTENSION")
    d.text((90, 250), "When an AI agent pays an invoice,", font=font(SANSB, 74), fill=TEXT)
    d.text((90, 340), "what proves it was real?", font=font(SANSB, 74), fill=TEXT)
    rounded(d, [90, 500, 1250, 640], 18, fill=PANEL, outline=PANEL_EDGE, width=2)
    d.text((126, 528), "USER  →  AI AGENT", font=font(SANSB, 24), fill=CYAN)
    d.text((126, 566), "“Pay this invoice.”", font=font(SANS, 36), fill=TEXT)
    if questions:
        chips = [
            ("Really registered?", "with the tax authority — or just a PDF?"),
            ("Active at payment?", "registered once is not active when paid"),
            ("Signed by the business?", "does the signature cover this checkout?"),
        ]
        x = 90
        for title, sub in chips:
            rounded(d, [x, 730, x + 540, 890], 16, fill=CHIP, outline=PANEL_EDGE, width=2)
            d.rectangle([x, 730, x + 10, 890], fill=AMBER)
            for i, seg in enumerate(wrap(title, font(SANSB, 30), 470, d)):
                d.text((x + 34, 758 + i * 38), seg, font=font(SANSB, 30), fill=TEXT)
            for i, seg in enumerate(wrap(sub, font(SANS, 24), 470, d)):
                d.text((x + 34, 806 + i * 30), seg, font=font(SANS, 24), fill=MUTED)
            x += 570
    footer(d)
    return img


save(scene1(False), "s1_a.png")
save(scene1(True), "s1_b.png")

# ---------------------------------------------------------------- S2
S2_LINES = [
    ("$ python -m pip install invoice-registration-reference==0.1.0", TEXT),
    ("Successfully installed cffi-2.1.1 cryptography-50.0.2 invoice-registration-reference-0.1.0 pycparser-3.12 rfc8785-0.1.4 tzdata-2026.6", MUTED),
    ("$ python video/demo_verify.py", TEXT),
    ("from invoice_registration_reference import verify", CYAN),
    ("result = verify(checkout, order, evidence_bundle, config)", TEXT),
    ("structurally valid: True", TEXT),
    ("registration matches invoice       established", GREEN),
    ("registration active at payment     established", GREEN),
    ("signed by checkout business        established", GREEN),
]


def scene2(nlines):
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "THE PUBLISHED PACKAGE — PYPI, VERSION 0.1.0")
    d.text((90, 196), "Install it. Call verify. Get three verdicts.", font=font(SANSB, 52), fill=TEXT)
    terminal(d, [90, 290, 1830, 840], "published package run — clean venv, fixture: examples/example-2-synthetic-full",
             S2_LINES[:nlines])
    if nlines >= 9:
        callout(d, [90, 855, 1830, 995],
                "Your integration supplies the evidence and trusted keys. The verifier checks them offline — every verdict with its reason attached.")
    footer(d)
    return img


for i, n in enumerate([2, 5, 9]):
    save(scene2(n), f"s2_{'abc'[i]}.png")

# ---------------------------------------------------------------- S3
S3_LINES = [
    ("== Example 1 - NIC's published signed sample (examples/example-1-operator-sample)", MUTED),
    ("   structurally valid: True", TEXT),
    ("registration matches invoice       established", GREEN),
    ("registration active at payment     not_established", AMBER),
    ("                                      (no payment-event evidence supplied)", MUTED),
    ("signed by checkout business        not_established", AMBER),
]


def scene3(nlines):
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "THE SAME VERIFIER — THE TAX AUTHORITY'S OWN SIGNED SAMPLE")
    d.text((90, 196), "NIC's signed documentation sample — and an honest gap", font=font(SANSB, 52), fill=TEXT)
    terminal(d, [90, 300, 1830, 740], "shipped verifier, unmodified — NIC published sample, dummy particulars",
             S3_LINES[:nlines])
    if nlines >= 6:
        callout(d, [90, 790, 1830, 920],
                "The match is proven. The sample carries no payment evidence, so active-at-payment stays not established — the verifier claims only what the evidence shows.", accent=AMBER)
    footer(d)
    return img


for i, n in enumerate([3, 5, 6]):
    save(scene3(n), f"s3_{'abc'[i]}.png")

# ---------------------------------------------------------------- S4
S4_LINES = [
    ("== Separate synthetic test, signed status: cancelled before the payment event", MUTED),
    ("   structurally valid: True", TEXT),
    ("registration matches invoice       established", GREEN),
    ("registration active at payment     contradicted", RED),
    ("                                      (authenticated cancellation took effect at or before the payment event)", MUTED),
    ("signed by checkout business        established", GREEN),
]


def scene4(nlines):
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "WHEN THE EVIDENCE TURNS — CANCELLED BEFORE PAYMENT")
    d.text((90, 196), "In a separate synthetic test. One signed fact changes the verdict.", font=font(SANSB, 46), fill=TEXT)
    terminal(d, [90, 300, 1830, 740], "test-suite construction (Factory), run through the same verifier",
             S4_LINES[:nlines])
    if nlines >= 6:
        callout(d, [90, 790, 1830, 920],
                "Established, not established, contradicted — verdicts follow the evidence, with the reason attached. Never a guess.", accent=RED)
    footer(d)
    return img


for i, n in enumerate([3, 5, 6]):
    save(scene4(n), f"s4_{'abc'[i]}.png")

# ---------------------------------------------------------------- S5
def scene5():
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "INVOICE REGISTRATION REFERENCE — V0.1")
    d.text((90, 250), "Read it. Run it.", font=font(SANSB, 74), fill=TEXT)
    d.text((90, 340), "Check the verdicts yourself.", font=font(SANSB, 74), fill=TEXT)
    rows = [
        ("PyPI package", "pypi.org/project/invoice-registration-reference"),
        ("Runnable example", "github.com/agorail-labs/invoice-registration-reference/blob/main/video/demo_verify.py"),
        ("Repository", "github.com/agorail-labs/invoice-registration-reference"),
    ]
    y = 500
    for label, url in rows:
        rounded(d, [90, y, 1830, y + 96], 16, fill=PANEL, outline=PANEL_EDGE, width=2)
        d.text((126, y + 16), label.upper(), font=font(SANSB, 22), fill=CYAN)
        d.text((126, y + 48), url, font=font(MONO, 26), fill=TEXT)
        y += 116
    callout(d, [90, y + 4, 1830, y + 130],
            "Offline Python reference · 38 verifier tests · 36 schema-harness checks.", accent=BLUE)
    d.text((90, y + 146), "The demo uses simulated registration status and payment capture evidence. Live integrations supply authenticated evidence.",
           font=font(SANS, 24), fill=MUTED)
    footer(d)
    return img


save(scene5(), "s5_a.png")

# ---------------------------------------------------------------- poster
def poster():
    img = bg()
    d = ImageDraw.Draw(img)
    header(d, "INVOICE REGISTRATION REFERENCE — A UCP EXTENSION")
    d.text((90, 300), "When an AI agent pays an invoice,", font=font(SANSB, 80), fill=TEXT)
    d.text((90, 396), "what proves it was real?", font=font(SANSB, 80), fill=TEXT)
    d.text((90, 540), "Three verdicts — established, not established, contradicted —", font=font(SANS, 40), fill=MUTED)
    d.text((90, 596), "each with its reason, from the scheme's own signed evidence.", font=font(SANS, 40), fill=MUTED)
    d.text((90, 760), "github.com/agorail-labs/invoice-registration-reference", font=font(MONO, 34), fill=CYAN)
    footer(d)
    return img


save(poster(), "poster.png")

manifest = {
    "s1": ["s1_a.png", "s1_b.png"],
    "s2": ["s2_a.png", "s2_b.png", "s2_c.png"],
    "s3": ["s3_a.png", "s3_b.png", "s3_c.png"],
    "s4": ["s4_a.png", "s4_b.png", "s4_c.png"],
    "s5": ["s5_a.png"],
}
with open(os.path.join(OUT, "manifest.json"), "w") as fh:
    json.dump(manifest, fh, indent=2)
print("manifest written")
