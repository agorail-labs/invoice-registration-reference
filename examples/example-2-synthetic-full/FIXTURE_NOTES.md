# Example 2 — fully synthetic, all three verdicts established

**Evidence level:** complete inputs, every one of them synthetic.
Nothing in this folder is a real invoice, a real registration, a real
payment, or a real key.

## What is synthetic, and how

- The merchant ("seller GSTIN" `29ABCDE1234F1Z5`, a dummy PAN pattern),
  the buyer GSTIN, the invoice `EXMPL/2026-27/0042` dated 2026-11-20,
  total ₹118,000 (11,800,000 paise), one line item of quantity one.
- The IRN is computed as the scheme documents its inputs: a SHA-256
  hash of GSTIN + financial year + document type + document number.
- `evidence/scheme_artifact.jwt.txt` is a **simulated** signed invoice
  artifact (RS256 JWT, `iss: "SIMULATED-IRP"`) signed by a simulated
  IRP RSA key generated for this example. Unlike the QR artifact of
  Example 1 it carries `AckDt`, which supplies `registered_at`
  (2026-11-20T10:15:23+05:30) at usable precision. **Format
  simplification, stated plainly:** here `AckDt` is a top-level
  RFC 3339 timestamp with an offset. In the published IRP format,
  AckDt sits inside the signed invoice's nested `data` object and
  carries **no timezone offset** — so this example is fine as a
  simulation but cannot validate the real IRP parser. Gate 2 adds a
  production-shaped synthetic case in the published shape, ordered
  under the documented Asia/Kolkata timezone (specification
  sections 8.4 and 9, Annex A).
- `evidence/status_evidence.json` is **simulated authenticated status
  evidence** in the documented Gate 1 format (specification
  section 7): claims signed as a compact JWS by the simulated IRP key —
  status `active`, observed 2026-11-21T09:00:00+05:30 (after the
  payment), `cancelled_at: null`, and the scheme rule relied on (a
  cancelled IRN is not reinstated).
- `evidence/payment_event.json` is a **simulated provider-confirmed
  capture** in the documented format: `pay_SIMULATED_0001`, bound to
  this checkout, ₹118,000, captured 2026-11-20T15:42:10+05:30.
- The checkout's `ap2.merchant_authorization` is a real detached JWS
  (ES256) over the JCS-canonicalized final checkout excluding `ap2`,
  made with a merchant key generated for this example. Only the public
  JWK is in the bundle (`evidence/merchant_public_key.jwk.json`).
- **All private keys were generated for this example and discarded.**
  Only public keys are included, so the signatures verify but cannot
  be re-made.
- The harness does **not** verify with the keys in this folder: it
  loads independently configured copies from
  `validation/trust_keys/` (with the expected payment id in
  `validation/trust_config.json`), because a key arriving inside the
  evidence it is meant to check would prove nothing.

The business's `status` claim in the reference says `active` as
observed at 15:40 on 2026-11-20. Note that the claim is not what
establishes anything: the establishment below rests on the signed
artifact, the signed status evidence and the capture, per the
specification.

## Verdicts for this example (specification section 8)

| Verdict | Result | Establishment path |
| --- | --- | --- |
| Registration matches the invoice | **established** | Artifact signature verifies; identifier, supplier GSTIN, document number, type, date and total all match; IRN recomputes from its documented inputs. |
| Registration active at the payment event | **established** | Authenticated registration time (10:15:23) is at or before the capture (15:42:10), and an authenticated observation of active status after the event (next day 09:00) is supported by the scheme's documented rule that a cancelled IRN is not reinstated. |
| Signed by the checkout business | **established** | The AP2 merchant authorization verifies over the final checkout (which includes `invoice_reference` at top level), and the order's snapshot equals the checkout's reference exactly. |

All checks are in `validation/validation-results.txt`.

## Which inputs a live integration would need

This example is the checklist, in concrete form:

1. The **final checkout as accepted for completion**, with the AP2
   mandate extension negotiated, and the business's signing key
   available to verifiers.
2. The **scheme's signed artifact** for the invoice (IRP signed invoice
   response or signed QR code), supplied separately from the checkout,
   with the IRP public key / DS certificate to check it.
3. An **authenticated status response** from the scheme (or its
   authorised channel) bound to the same IRN, carrying an observation
   time — the one input Example 1 does not have, and the one that
   decides "active at payment".
4. The **payment provider's authenticated capture confirmation**,
   bound to the checkout and the payment identifier, with a trusted
   capture time.
5. The **order**, whose `invoice_reference` snapshot is compared
   against the signed checkout's.
