# Example 3 — production-shaped synthetic IRP case (Gate 2)

**Evidence level:** fully synthetic, in the published IRP shape.
Nothing here is a real invoice, registration, payment or key.

## Why this fixture exists

Example 2's simulated artifact carries a top-level RFC 3339 `AckDt`
with an offset — a simulation simplification that cannot exercise the
real IRP parser (Gate 1 review, item 3). This fixture is shaped like
the published IRP signed invoice:

- The JWT payload's `data` is **one nested object** holding the
  invoice fields (SellerGstin, BuyerGstin, DocNo, DocTyp, DocDt,
  TotInvVal, ItemCnt, MainHsnCode) **and** the acknowledgement —
  AckNo, **AckDt** and Irn — inside it.
- `AckDt` is `"20/11/2026 10:15:23 AM"`: the IRP's own format, with
  **no timezone offset**.
- The reference's `registered_at` (`2026-11-20T10:15:23+05:30`) is
  that AckDt read under **Asia/Kolkata**, the scheme's documented
  timezone, held in the verifier's configuration
  (`trust_config.json`, entry `example3`).

## Expected verifier behaviour (asserted in the test suite)

- **With** `scheme_timezone: "Asia/Kolkata"` configured: all three
  verdicts established — the offset-free AckDt orders before the
  capture (15:42 IST).
- **Without** a configured timezone: *active at payment* is
  **not established** (the registration time cannot be ordered),
  while *matches* and *signed by the business* remain established.

## Keys

Simulated IRP (RSA) and merchant (EC P-256) keys were generated for
this fixture; private halves discarded. The harness and verifier use
the independently configured copies in `validation/trust_keys/`
(`ex3_irp_public_key.pem`, `ex3_merchant_public_key.jwk.json`), not
the copies in this folder.
