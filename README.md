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

- **Gate 1 draft, private.** This repository is private until Gate 3.
  Nothing here is published, filed, or served: the capability's schema
  URL (`agorail-labs.github.io`) does not yet resolve, so authority
  binding is prospective. Publication requires Arjun's written
  approval at Gate 3.
- **No verifier yet.** The verifier, tests and conformance suite are
  Gate 2. `validation/` holds Gate 1 schema validation only.
- **Evidence levels — read this before trusting any claim.**
  Example 1 rests on the scheme operator's published sample
  (signature verified offline, with a negative control). Example 2 is
  fully synthetic, with simulated status and payment evidence in the
  documented formats, labelled `simulated` in the files themselves.
  No real invoice is used anywhere.
- **Known open items:** the official `ucp-schema` tool run (see
  `validation/VALIDATION.md`); a primary citation for the India
  no-reinstatement rule (see `research/GATE1_REPORT.md`, flag 2).
- Deterministic conformance results (Gate 2) will be reported
  separately from the programme's model-review measurements, with
  their denominators, corrected figures and exploratory runs
  identified as such.

## Layout

- `spec/` — normative specification (`invoice-registration-reference-v0.1.md`)
- `schema/` — the capability definition (`invoice_reference.json`),
  with separate composed definitions for checkout and for order
- `research/` — Gate 1 report: UCP's Payment Terms extension and AP2's
  payment reference, what each already does, and what this adds
- `examples/` — the two Gate 1 examples, each with fixture notes and
  an evidence bundle
- `validation/` — Gate 1 validation harness, method and results

## The central demonstration

Example 1: a genuine signed invoice establishes *registration
matches*, while *active at payment* is correctly **not established** —
the signed artifact carries no registration time and no status, and no
status or payment evidence is held. Example 2 supplies the missing
inputs (all simulated) and all three verdicts are established.

## Licence

Apache License 2.0 (see `LICENSE`).
