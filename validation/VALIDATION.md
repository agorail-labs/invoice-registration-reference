# Gate 1 validation — method and results

**Date:** 26 November 2026. **Harness:** `validation/validate_gate1.py`
(schema composition and checks), `validation/build_examples.py`
(example generation). Full output: `validation/validation-results.txt`.

**Counts, corrected.** The harness run as first delivered contained
**30 passing checks** — an earlier version of this file said 31, which
double-counted the result line; the lead's reproduction at Gate 1
review established 30, and this file now matches it. After the
review-closure changes below, the harness contains **36 checks, all
passing (36/36)** in the archived output: the 30, plus an
`order.checkout_id` check per example, a status-identifier binding
check, and three mutation regression cases.

## The official tool — run by the lead

This harness did not run the official `ucp-schema` tool (this
environment has no cargo/rustc, checked 26 November 2026); steps 2–3
of the method below follow its documented composition method instead.
**The lead ran the official tool at Gate 1 review** — ucp-schema
v2.0.0, checksum-verified binary — with these results:

- The definition passed **strict lint**.
- The four payloads as first delivered were rejected by the tool's
  self-describing validator because their base checkout/order
  capability entries omitted `schema`. Adding the published base
  schema URLs to scratch copies made **all four pass strict
  validation**. UCP itself shows version-only entries in responses, so
  this is a CLI input requirement, not a protocol defect.
- The tool also rejected a payload with a missing registration status
  and one with an undeclared field, as the definition requires.

The delivered fixtures now carry the published base schema URLs in
their base capability entries, so the payloads pass the official tool
as delivered. Because the AP2 merchant signature covers `ucp`
metadata, Example 2's merchant authorization was regenerated after
that change (and verifies in the harness, check 36 set).

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
5. **Trust and binding (review closure).** Verification keys load
   from `validation/trust_keys/` and the expected payment identifier
   from `validation/trust_config.json` — verifier configuration held
   independently of the evidence bundles. Capture evidence must match
   the accepted checkout's id, total and currency and the expected
   payment id; the signed status response's registration identifier
   must equal the reference's; `order.checkout_id` is checked
   alongside snapshot equality. Three mutations of the lead's are kept
   as regression cases and must fail: a capture with a different
   currency and payment id; an order with a different `checkout_id`;
   status evidence naming a different IRN.
6. **Digest representation.** `artifact_digest` is the SHA-256 of the
   ASCII bytes of the artifact's compact JWS serialization. The
   bundled JWT files store a trailing newline (file framing); as
   first delivered, neither file matched its declared digest as
   stored, and both matched after stripping that newline. The
   definition, specification, builder, fixtures and harness now all
   state and use the compact-serialization representation.

## Results (summary; full text in validation-results.txt)

- Definition: valid draft 2020-12 schema.
- Example 1 checkout and order: composed validation PASS; strict
  overlay PASS. Example 2 checkout and order: PASS; PASS.
- Rules 1, 2, 4, 6, snapshot equality and `order.checkout_id`: PASS
  on both examples.
- Example 1: NIC sample signature verifies offline (RS256) against
  the independently configured published key; negative control fails
  as required; reference fields match the signed payload wherever it
  binds them.
- Example 2: simulated artifact and status signatures verify; IRN
  recomputes; status identifier binds; capture binds to checkout,
  expected payment id, amount and currency; all three regression
  mutations are rejected; active-at-payment establishment conditions
  hold; the AP2 merchant authorization verifies over the
  JCS-canonicalized final checkout with `ap2` excluded (so
  `invoice_reference` is covered).
- Verdicts — Example 1: matches **established** (scoped to the signed
  documentation vector, per the fixture notes); active at payment
  **not established**; signed by the business **not established**.
  Example 2: all three **established**.

## Evidence separation

These are deterministic checks over two fixtures. They are reported
separately from the model-review measurements of the wider
invoice-registration programme (measurements 1–5), which have their
own denominators, corrected figures and exploratory runs; nothing from
those measurements is used or restated here.
