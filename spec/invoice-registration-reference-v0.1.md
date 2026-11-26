# Invoice Registration Reference — Specification v0.1

**Status:** Gate 1 draft. Private until Gate 3. Nothing in this document is
published, and no part of it has been filed with any standards body.
**Capability:** `io.github.agorail-labs.shopping.invoice_reference`
**Capability version:** `2026-11-26` (dated, independent of this package's
version)
**Extends:** `dev.ucp.shopping.checkout`, `dev.ucp.shopping.order`
**Protocol floor:** UCP `2026-08-25` or later (declared in the definition's
`requires`)
**Definition:** `schema/invoice_reference.json`

## 1. Purpose

An offline reference for invoice evidence. A checkout that pays an invoice
the business itself already issued can carry, at the top level of the
checkout, a reference to that invoice and to the invoice's registration
with a tax scheme, in a form a verifier can check against the scheme's own
signed evidence.

The central demonstration of version 0.1: **a genuine signed invoice can
establish registration while the verifier correctly leaves "active at
payment" unresolved.** Registration and status-at-payment are different
facts, with different evidence, and this specification keeps them apart.

## 2. Scope

Version 0.1 covers exactly:

- One scheme: India's registered invoices — the GST e-invoice system and
  its Invoice Registration Portal (IRP), scheme identifier
  `in_gst_einvoice_irp`, registration identifier the IRN.
- A merchant collecting **its own issued invoice**. The business that
  signs the checkout is the issuer of the invoice.
- Invoice lines of quantity one, amounts in INR minor units, positive
  amounts, with no discount, tax or fee that changes the invoice-only
  total.

Outside the verifier's claims, and outside this specification:

- Collection for another issuer.
- The account to pay. No field of this extension names an account, and no
  verdict speaks to whether a payment went to the right account.
- The amount actually owed. An allocation is a declaration (section 4);
  paying a face amount does not establish what was owed.
- Delivery, fulfilment, and the goods or services themselves.

## 3. Terms

- **Reference** — an `invoice_reference` entry: one checkout line item
  referred to one invoice document.
- **Artifact** — the scheme's signed artifact for the registration (for
  the IRP, a signed QR code JWT or a signed invoice response JWT).
  Artifacts are supplied separately to authorised verifiers (section 5).
- **Payment event** — the one event of version 0.1 (section 7).
- **Authenticated** — evidence whose origin and integrity a verifier can
  check cryptographically or through an authenticated scheme or provider
  channel. A claim by the business is never authenticated evidence of the
  fact claimed.
- **Verdict** — one of *established*, *not established*, *contradicted*,
  always with a reason (section 8).

## 4. The object

`invoice_reference` sits at the **top level of the checkout**, as an array
of entries, so the AP2 mandate extension's signature covers it: that
extension's merchant signature is computed over the complete checkout
excluding only the `ap2` field. The extension adds no signature of its
own (rule 8).

| Group | Fields | Standing |
| --- | --- | --- |
| Link | `line_item_id` | Identifies the one checkout line item this entry refers to. |
| `document` | `number`, `type`, `issuer_tax_identity`, `issue_date`, `total` | The business's statement of the invoice, checked against scheme evidence. `total` is in INR minor units. |
| `allocation` (optional) | `amount_applied`, `balance_before`, `balance_after`, `instalment_number` (optional) | **A declaration.** Its figures are the business's; the verifier checks only their internal arithmetic (rule 4). |
| `registration` (optional) | `scheme`, `identifier`, `artifact_digest`, `registered_at` (optional) | `artifact_digest` is `sha256:` + the hex SHA-256 of **the ASCII bytes of the artifact's compact JWS serialization**. Storage framing is not part of the artifact: a trailing newline in a file holding the artifact is not hashed. The definition, the fixtures and the verifier all use this one representation. `registered_at` is present only where the scheme evidence supplies a registration time at usable precision. |
| `status` | `value` (`active` / `cancelled` / `not_established`), `observed_at`, `cancelled_at` (where the claim is cancelled) | **A claim by the business.** Never evidence by itself. Required when a registration is present (rule 6). |

**Raw scheme artifacts are not carried inline.** A signed invoice code
holds the buyer's tax identity and invoice values; inline, it would
travel into the mandate and the order. Artifacts go separately to
authorised verifiers, bound to the reference only by `artifact_digest`.

## 5. The order

The order keeps the checkout's `invoice_reference` as a **snapshot,
unchanged**. Later status evidence is stored beside the snapshot — in the
evidence bundle, not in the order — and never overwrites it. The original
signed checkout is preserved: the verifier compares the snapshot and the
reference against the final checkout accepted for completion, even when
the amount is unchanged (rule 7), and checks that the order's
`checkout_id` is that checkout's id.

## 6. Rules

1. Each entry refers to exactly one checkout line item. No line item is
   referred to twice, and no registration identifier or document appears
   on two lines (a document is identified by its number together with its
   issuer's tax identity).
2. Each invoice line's total equals the amount applied to it, and the
   invoice lines sum to the checkout total, within the scope of
   section 2. Where an entry carries no `allocation`, the amount applied
   by that line is its line item total. Where it carries one,
   `amount_applied` is that amount.
3. A document carries its number, type, the issuer's tax identity, its
   issue date and its total.
4. An allocation's figures are declared. The declared balance after
   equals the declared balance before less the amount applied.
5. A registration carries its scheme, its identifier and the digest of
   its signed artifact.
6. **Where a registration is present, a status is present.**
   `not_established` is always allowed. Omission is invalid.
7. The reference is compared against the final checkout accepted for
   completion, even when the amount is unchanged.
8. The extension adds no signature of its own.

## 7. The payment event and the evidence bundle

The one payment event of version 0.1 is **capture confirmed by the
payment provider, bound to the checkout and the payment identifier**.
Where no trusted time for that event is supplied, the verifier returns
"not established" for anything that depends on it.

A verifier takes three inputs: the final checkout, the order snapshot,
and an **evidence bundle** holding

- the scheme's signed artifact;
- authenticated status evidence bound to the same registration
  identifier; and
- evidence of the payment event.

Two things are **verifier configuration, never taken from the bundle**:
the trust keys (the scheme's key and the business's key are configured
independently — a key that arrives inside the evidence it is meant to
check proves nothing), and the payment identifier the verifier expects
for the checkout's payment session, which comes from the payment
integration. Capture evidence is matched against the accepted checkout:
its id, the checkout total, the checkout currency, and that expected
payment identifier. Status evidence counts only where the registration
identifier inside the **signed** status response equals the reference's
registration identifier.

In version 0.1 the status and payment evidence are **simulated in a
documented format, and labelled so**:

- *Status evidence (simulated format):* a JSON object with `simulated:
  true`, `kind: "scheme_status_response"`, the registration identifier,
  `status`, `observed_at`, `cancelled_at` (or null), the scheme rule
  relied on, and a compact JWS (RS256) over those claims under the
  scheme key supplied in the bundle, in a `jws` field beside a readable
  `claims` copy. A live integration supplies the scheme's own
  authenticated status response in this place.
- *Payment event (simulated format):* a JSON object with `simulated:
  true`, `kind: "provider_capture_confirmation"`, the provider,
  `payment_id`, `checkout_id`, `status: "captured"`, `amount`,
  `currency`, and `captured_at`. A live integration supplies the
  provider's own authenticated capture confirmation in this place.

## 8. The verifier

Three verdicts, each *established*, *not established* or *contradicted*,
with a reason.

### 8.1 Registration matches the invoice

- **Established** when the artifact's signature verifies and the
  identifier, supplier's tax identity, document number, type, issue date
  and total match wherever the scheme's evidence binds them.
- **Contradicted** by a verified mismatch, or by an authoritative
  negative response of known scope.
- A timeout, a refusal, a retention gap or a generic "not available" is
  **not established** — never contradicted.

### 8.2 Registration active at the payment event

Uses authenticated times only. The registration's effective interval is
**[registration time, cancellation time)**: it is in effect at the
payment event if and only if the registration time is at or before the
event and no cancellation took effect at or before it.

- **Contradicted** when an authenticated cancellation took effect at or
  before the payment event. A cancellation exactly at the event
  contradicts.
- **Established** when the authenticated registration time is at or
  before the event **and** either an authenticated cancellation falls
  after it, or an authenticated observation of active status at or after
  the event is supported by the scheme's documented rule that a
  cancelled registration cannot be reinstated.
- A claim by the business alone, a missing registration time or a
  missing payment time is **not established**.

### 8.3 Signed by the checkout business

- **Established** only when the AP2 mandate extension's merchant
  signature over the final checkout verifies **and** the order's snapshot
  equals that checkout's reference **and** the order's `checkout_id` is
  that checkout's id.
- Otherwise **not established** (a signature that fails to verify is a
  failed check on this verdict's input, reported in the reason; this
  specification does not make it "contradicted", because the verdict is
  about what the evidence establishes).

### 8.4 Times, precision, conflicts

- Times are compared as instants. A time is usable only at the precision
  the evidence states: where two times' ordering cannot be decided at
  the stated precision (for example a date-only registration time against
  a payment event on that date), anything depending on that ordering is
  **not established**.
- Conflicting authenticated evidence yields **not established**, with
  the conflict reported in the reason. A verifier never resolves a
  conflict between two authenticated sources by preferring one silently.
- The business's `status` claim never moves any verdict in either
  direction.
- **Scheme timestamps without an offset.** The IRP's registration time
  (AckDt) arrives with **no timezone offset** (section 9). An adapter
  may use such a timestamp for event ordering only under a documented
  timezone for the scheme — for the IRP, Asia/Kolkata — recorded with
  the verifier's configuration. Where no timezone is documented, any
  verdict depending on that ordering is **not established**.

## 9. Scheme profile: India (GST e-invoice / IRP)

From the scheme's published material, as read for this reference
(Part B dossier, 25 November 2026):

- Registration returns an acknowledgement (AckNo, AckDt), the IRN — a
  SHA-256 hash of GSTIN + financial year + document type + document
  number — a signed invoice JWT and a signed QR-code JWT (RS256).
- The **signed QR payload binds**: seller GSTIN, buyer GSTIN, document
  number, document type, document date, total invoice value (in rupees;
  the verifier converts to minor units), item count, main HSN code, and
  the IRN. It carries **no registration time and no timestamps** — so
  for a QR artifact, `registered_at` is omitted and "active at payment"
  cannot be established from the artifact alone. The signed invoice
  response does carry a registration time, but in the published format
  **AckDt sits inside the signed invoice's nested `data` object and
  carries no timezone offset**; it is usable for ordering only under
  the documented-timezone rule of section 8.4. (Example 2's simulated
  artifact carries a top-level RFC 3339 `AckDt` instead — a simulation
  simplification, recorded in its fixture notes; it does not exercise
  the real IRP parser. A production-shaped synthetic case is a Gate 2
  deliverable, Annex A.)
- Anyone can check the signature offline against the published IRP
  public key; public web routes (Verify Signed Invoice, Search IRN)
  exist; API retrieval is login-only for the taxpayer/GSP.
- The whole IRN can be cancelled within 24 hours (not with an active
  e-way bill). There is no amendment on the IRP: corrections go through
  GSTR-1 or a new credit/debit note with its own IRN. **A cancelled IRN
  is not reinstated** — the rule section 8.2 relies on. Primary
  citation: GSTN's *e-Invoice FAQ, version 1.4* (30 March 2021),
  question 91 — "Can an invoice number of a cancelled IRN be used
  again? No. Once an IRN is cancelled, the concerned invoice number
  cannot be used again to generate another e-invoice/IRN (even within
  the permitted cancellation window)", because the IRN is a unique
  string of supplier GSTIN, document number, document type and
  financial year: a cancelled registration cannot return under the
  same identifier. Current status is public via Search IRN; the
  signed QR carries no status field, so the artifact alone never
  establishes status.
- **Scope of Example 1's verdict.** NIC's published sample is a signed
  **documentation vector** — an example printed for verification, with
  dummy particulars, not a live registration. Example 1's "established"
  verdict for *registration matches the invoice* is scoped accordingly:
  the reference matches that signed documentation vector. Live
  registration facts are what the synthetic example and the Gate 2
  suite address.

## 10. UCP fit

- Separate definitions for checkout and for order: the definition's
  `$defs` carries one entry per parent capability
  (`dev.ucp.shopping.checkout`, `dev.ucp.shopping.order`), each an
  `allOf` composition over the published base schema, as UCP extension
  composition prescribes.
- The protocol floor is declared in the definition (`requires`:
  protocol and both parent capabilities at minimum `2026-08-25`).
- The capability version is dated (`2026-11-26`) and independent of
  this package's version.
- Authority binding is prospective until Gate 3: the name
  `io.github.agorail-labs.shopping.invoice_reference` is valid under
  UCP's published reverse-domain pattern and binds to a schema served
  from `agorail-labs.github.io`, a host the organisation does not yet
  serve a site from. Publication is Gate 3, on Arjun's written approval.
- Composed checkout and order payloads for both examples were validated
  locally in strict mode; method and results are in
  `validation/VALIDATION.md`.

## Annex A (informative; Gate 2): conformance cases

Each mapped to a rule, to be built at Gate 2: Genuine. Mismatch with the
signed artifact. Cancelled before the payment event. Cancelled exactly
at it. Cancelled after it. A valid signed artifact with only the
business's status claim. Lookup failure. Authoritative absence. Status
not established. Registration without a status. The same registration on
two lines. Allocation that does not add up. A signed checkout whose
reference changed while the price stayed the same. **A production-shaped
synthetic IRP case** — signed invoice in the published shape, AckDt
nested in `data` with no offset, ordered under the documented
Asia/Kolkata timezone — so the real IRP parser, not only the simulation
format, is exercised. The Gate 1 harness's binding regressions (capture
with a wrong currency and payment id; an order with a wrong
`checkout_id`; status evidence for a different IRN) are carried into the
suite as regression cases.
