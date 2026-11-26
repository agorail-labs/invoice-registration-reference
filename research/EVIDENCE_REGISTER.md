# Evidence register — Gate 2

Every input the verifier relies on, where it comes from, how it is
authenticated, and what it can and cannot establish. "Configured"
means held by the verifier independently of the evidence bundle
(specification section 7).

| Evidence | Source | Authentication | Establishes | Cannot establish | Gate 2 status |
| --- | --- | --- | --- | --- | --- |
| Scheme signed artifact (signed QR JWT / signed invoice JWT) | Scheme operator (IRP), supplied separately, never inline | RS256 signature under the configured IRP key; bound to the reference by `artifact_digest` (SHA-256 over the compact JWS ASCII bytes) | Registration matches the invoice (fields the artifact binds); registration time where AckDt is present | Status at any time (the QR carries none); activity at payment by itself | Real for Example 1 (NIC's published sample — a documentation vector); simulated for Examples 2–3 |
| IRP public key | Published by NIC in the QR code procedure document (Example 1); generated for the simulated fixtures | Configured trust (`validation/trust_keys/`), never taken from the bundle | The authenticity check above | Key validity period — the published key is bare, with no published validity dates | Real (Ex 1) / simulated (Ex 2–3) |
| Status evidence | The scheme or its authorised channel | RS256 JWS under the configured scheme key; only verified claims are evaluated; the signed identifier must equal the reference's | Cancellation time; active observation time; the no-reinstatement rule statement | Anything when unsigned, mis-bound to another IRN, or replaced by the business's claim | **Simulated** in the documented Gate 1 format; no live authenticated IRN status channel is integrated in v0.1 |
| Payment event (capture) | Payment provider | In a live integration, the provider's own authenticated confirmation; in v0.1, the documented simulated format, matched against the accepted checkout (id, total, currency) and the configured expected payment id | That a capture for this checkout, amount, currency and payment id occurred, and its trusted time | The account paid, or the amount owed (outside the verifier's claims) | **Simulated** |
| Expected payment identifier | The payment integration that completed the checkout | Configured (`validation/trust_config.json`), not read from the capture evidence itself | The binding target for the capture's `payment_id` | — | Configured per example |
| AP2 merchant authorization | The checkout business | Detached JWS (ES256) over the JCS-canonicalized final checkout excluding `ap2`, under the configured merchant key | Signed by the checkout business (with snapshot equality and `order.checkout_id`) | Anything about the invoice itself | Real cryptography, simulated keys (Ex 2–3); absent in Ex 1 by construction |
| Merchant public key | The business's AP2 key publication | Configured trust (`validation/trust_keys/`) | The signature check above | — | Simulated |
| Scheme timezone (Asia/Kolkata) | Scheme documentation (IRP timestamps are IST, offset-free) | Configured (`scheme_timezone` in `trust_config.json`) | Ordering of offset-free AckDt against offset-bearing times | Ordering where no timezone is documented — the verdict is then not established | Configured for Example 3; absent-config behaviour is tested |
| No-reinstatement rule | GSTN e-Invoice FAQ v1.4, Q91 (a cancelled IRN's invoice number cannot be reused for another IRN) | Documentary — cited in specification section 9 | The second establishment path of §8.2 (active observation after the event) | — | Primary citation pinned at Gate 1 review closure |
| The business's `status` claim | The business, in the reference | None — it is a claim | Nothing by itself (never evidence) | Everything | Present in all examples; required by rule 6 so its absence is detectable |
| Lookup outcomes (timeout, refusal, "not available") | The lookup channel | n/a | Nothing — recorded as the reason for not established | Never a contradiction | Modelled via `lookup_outcome` in the verifier API |

**Separation.** This register covers deterministic verification
inputs only. The programme's model-review measurements (measurements
1–5) are not evidence for any verdict and are not restated here.
