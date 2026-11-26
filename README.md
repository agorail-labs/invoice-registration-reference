# invoice-registration-reference

An offline reference for invoice evidence: a UCP extension that lets a
checkout paying the business's own already-issued invoice carry a
reference to that invoice and to its registration with a tax scheme,
checkable against the scheme's own signed evidence.

**Capability:** `io.github.agorail-labs.shopping.invoice_reference`
(extends `dev.ucp.shopping.checkout` and `dev.ucp.shopping.order`)
**Version 0.1 scope:** one scheme (India's GST e-invoice / IRP), a
merchant collecting its own issued invoice, invoice lines of quantity
one, INR minor units, positive amounts, no discount, tax or fee that
changes the invoice-only total.

## Current status and known limitations

- **Gate 2 complete, private.** This repository is private until
  Gate 3. Nothing here is published, filed, or served: the
  capability's schema URL (`agorail-labs.github.io`) does not yet
  resolve, so authority binding is prospective. Publication requires
  Arjun's written approval at Gate 3.
- **Tooling: Python, approved.** The build inherited the
  organisation's TypeScript/npm convention (SCQ/MSE), but the
  delivered verifier is Python; on 26 November 2026 Arjun approved
  the Python implementation as the reference implementation for the
  first release (`release/RC1_RELEASE_DECISION.md`). Repository
  publication, Pages, and package publication remain separate
  decisions.
- **The verifier is a reference implementation**
  (`verifier/invoice_reference_verifier.py`): it computes the three
  verdicts from inputs against independently configured trust, and
  its 38-test suite passes (`conformance/CONFORMANCE.md`). Status and
  payment evidence remain the documented **simulated** formats — no
  live scheme or provider channel is integrated in v0.1.
- **Capture authentication.** The verifier's field matching (checkout
  id, expected payment id, amount, currency) *binds* capture evidence
  to the transaction; it does not *authenticate* it. A live verdict
  requires capture evidence authenticated by the caller's payment
  integration. The simulated capture format is unauthenticated by
  construction.
- **Evidence levels — read this before trusting any claim.**
  Example 1 rests on the scheme operator's published sample — a
  signed **documentation vector**, not a live registration (signature
  verified offline, with a negative control). Example 2 is
  fully synthetic, with simulated status and payment evidence in the
  documented formats, labelled `simulated` in the files themselves.
  No real invoice is used anywhere.
- **Gate 1 review closure (26 November 2026):** the official
  `ucp-schema` tool was run by the lead — definition passed strict
  lint, payloads pass strict validation as delivered (see
  `validation/VALIDATION.md`); the India no-reinstatement rule is
  pinned to GSTN's e-Invoice FAQ v1.4, question 91. Remaining Gate 2
  items are the verifier, the conformance suite and the
  production-shaped synthetic IRP case.
- Deterministic conformance results (Gate 2) will be reported
  separately from the programme's model-review measurements, with
  their denominators, corrected figures and exploratory runs
  identified as such.

## Layout

- `spec/` — normative specification (`invoice-registration-reference-v0.1.md`)
- `schema/` — the capability definition (`invoice_reference.json`),
  with separate composed definitions for checkout and for order
- `verifier/` — the Gate 2 reference verifier and its test suite
- `conformance/` — the Gate 2 conformance mapping (13 build-order
  cases plus the review carry-ins) and the recorded test output
- `research/` — Gate 1 report (Payment Terms and AP2's payment
  reference vs what this adds), the Gate 2 evidence register and fit
  analysis
- `examples/` — Examples 1–2 (Gate 1) and Example 3, the
  production-shaped synthetic IRP case (Gate 2), each with fixture
  notes and an evidence bundle
- `validation/` — Gate 1 validation harness, method and results;
  example builders; independently configured trust keys and the
  pinned cache of the published UCP schemas

## Running the verifier and tests

Requires Python 3.11+.

```sh
pip install -r verifier/requirements.txt
python3 -m unittest discover -s verifier/tests -v   # 38 tests
python3 validation/validate_gate1.py                # Gate 1 harness, 36 checks
python3 verifier/invoice_reference_verifier.py      # verdicts for Examples 1-3
```

The Gate 1 harness resolves the published UCP schemas from the
pinned cache in `validation/schema_cache/` (see
`THIRD_PARTY_NOTICES.md`), so a clean run needs no network access.

## The central demonstration

Example 1: a genuine signed invoice establishes *registration
matches*, while *active at payment* is correctly **not established** —
the signed artifact carries no registration time and no status, and no
status or payment evidence is held. Example 2 supplies the missing
inputs (all simulated) and all three verdicts are established.

## Licence

Apache License 2.0 (see `LICENSE`).
