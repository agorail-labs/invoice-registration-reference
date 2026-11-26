# Gate 1 validation — method and results

**Date:** 26 November 2026. **Harness:** `validation/validate_gate1.py`
(schema composition and checks), `validation/build_examples.py`
(example generation). Full output: `validation/validation-results.txt`
— **RESULT: PASS (all 31 checks)**.

## Method

1. **Definition check.** `schema/invoice_reference.json` is itself
   validated as a JSON Schema (draft 2020-12).
2. **Composition.** Checkout and order payloads are validated against
   the composed schemas: the extension's `$defs` entries for
   `dev.ucp.shopping.checkout` and `dev.ucp.shopping.order`, each an
   `allOf` over the published base schema (fetched from ucp.dev,
   version 2026-08-25) plus the extension's properties — the
   composition UCP prescribes for extensions.
3. **Strict mode (closed contract).** Every object key in every
   payload must be a property declared by one of the composed schemas
   — base checkout/order and their nested types (`line_item`, `item`,
   `total`, `link`, `ucp` metadata and capability entries), the AP2
   mandate extension (`ap2.merchant_authorization`), or this
   extension. This is the closed-contract sense of the ucp-schema
   tool's `--strict` flag ("Use `--strict` only when you need a closed
   contract: catching field name typos during development" — tool FAQ,
   read 26 November 2026). Allowed sets are listed in the harness and
   were taken from those published schemas as read that day.
4. **Rule and signature checks.** The harness checks rules 1, 2, 4 and
   6 on both examples, order-snapshot equality, artifact-digest
   binding, every signature the examples carry (with a negative
   control for the operator sample), and prints the three verdicts per
   example under the specification's definitions.

## The one substitution, stated plainly

The build order asks for validation "with UCP's schema tool in strict
mode". **The official `ucp-schema` Rust tool was not run**: it is
distributed via `cargo install ucp-schema`, and this environment has
no cargo or rustc (checked 26 November 2026). Steps 2–3 above follow
the tool's documented method (its FAQ: extensions define their
additions in `$defs[root capability name]`, composition is `allOf`,
`--strict` closes the contract). Running the official tool over these
payloads remains an open item, flagged in
`research/GATE1_REPORT.md` for the lead's decision; nothing in these
results depends on the substitution being invisible, and the results
should be read as *local composition + strict overlay*, not as an
official-tool run.

## Results (summary; full text in validation-results.txt)

- Definition: valid draft 2020-12 schema.
- Example 1 checkout and order: composed validation PASS; strict
  overlay PASS. Example 2 checkout and order: PASS; PASS.
- Rules 1, 2, 4, 6 and snapshot equality: PASS on both examples.
- Example 1: NIC sample signature verifies offline (RS256); negative
  control fails as required; reference fields match the signed payload
  wherever it binds them.
- Example 2: simulated artifact and status signatures verify; IRN
  recomputes; capture is bound to the checkout and payment id;
  active-at-payment establishment conditions hold; the AP2 merchant
  authorization verifies over the JCS-canonicalized final checkout
  with `ap2` excluded (so `invoice_reference` is covered).
- Verdicts — Example 1: matches **established**; active at payment
  **not established**; signed by the business **not established**.
  Example 2: all three **established**.

## Evidence separation

These are deterministic checks over two fixtures. They are reported
separately from the model-review measurements of the wider
invoice-registration programme (measurements 1–5), which have their
own denominators, corrected figures and exploratory runs; nothing from
those measurements is used or restated here.
