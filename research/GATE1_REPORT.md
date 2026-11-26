# Gate 1 report — what already exists, and what this extension adds

Read 26 November 2026, before Gate 1, as the build order (version 2)
requires. The first design read (25–26 November 2026) covered UCP's
vendor-extension rules, the base checkout/order schemas, the AP2 mandate
extension's binding, and the GoRoute e-invoice extension. It did **not**
cover the two items below.

Versions: UCP published specification **2026-08-25** (ucp.dev);
AP2 **v0.2.0** (2026-04-28).

## 1. UCP's published Payment Terms extension

**Name:** `dev.ucp.common.payment.terms`. **Extends:** checkout and
order. **Sources:** the extension page
(https://github.com/universal-commerce-protocol/ucp/blob/HEAD/docs/specification/payment/extensions/terms.md)
and its published schema
(https://ucp.dev/2026-08-25/schemas/common/payment_terms.json).

What it does:

- It lets a business offer the buyer a choice of **when** payment for a
  checkout is due — pay now, a deposit and the balance later, instalments,
  Net-30. "A Business selling equipment can offer Net-30 alongside
  pay-now."
- It adds two properties to `checkout.payment`: `terms[]` (response-only)
  and `selected_term_id`. A payment term is a `title`, a `description`,
  and one or more **schedules**; a schedule is one payment — a scalar
  `amount`, a buyer-facing `description` that must by itself state when
  and how it is due, an open `type` whose only well-known value is
  `immediate`, and an optional absolute RFC 3339 `due_at`.
- For the **selected** term, schedule amounts **MUST** sum to the
  checkout `total`; unselected terms are indicative and may price
  differently (a pay-now discount is carried as its own `totals` entry).
- Selection is a checkout update; the business's response is
  authoritative for all derived state, and a changed selection or a
  changed term in place is reported as a `payment_term_changed` warning.
- Where the selected term is fully deferred and needs no capture or
  instrument guarantee — the text's own example is "**deferred
  invoicing** where no tokens or instruments are submitted at checkout"
  — the platform completes with an empty payment object (`"payment":
  {}`).
- On the order, `payment.accepted_term` carries the accepted term only
  (the offered terms are not projected). "The accepted term is the
  agreement, not a running balance": its schedules **MUST** sum to the
  order total at creation, the business **MUST NOT** modify it after the
  order is created, and post-purchase changes are recorded in
  `adjustments[]`.
- Out of scope, by its own text: amounts not determinable at checkout;
  multiple currencies within one term; recurring commerce; and payment
  execution — "It does not define credential storage, future-charge
  authorization, how a Business executes capture, or mandate
  requirements."

What it already does that touches this build: it is the one place UCP
names paying by invoice at all, and it gives a checkout a disciplined
way to state *amounts and times of payments still to come*, projected
onto the order as an immutable agreement.

What it does not do: a payment term describes payments **for this
checkout's purchase**. Nothing in it identifies a document that already
exists — no document number, type, issuer or issue date; no reference
to an invoice issued before the checkout; no registration, no status,
and no evidence. Its schedules are the business's offer, not a record
of an obligation created elsewhere. A "deferred invoicing" term says
money is due later; it does not say which invoice it settles.

## 2. AP2's payment reference

AP2 v0.2 uses "reference" for two different bindings. Both are internal
to AP2; neither is a reference to a document. **Source:**
https://ap2-protocol.org/ap2/payment_mandate/ (read 26 November 2026),
with the schema property sets as rechecked in Part A of the
invoice-registration dossier (25 November 2026).

**(a) The `payment.reference` constraint** (open Payment Mandate).
"Constrains this Payment Mandate for use with a particular Checkout
Mandate (and its associated closed Mandates)." Its one property is
`conditional_transaction_id`: "Digest of the associated Open Checkout
Mandate." Evaluation: "The Checkout Mandate for the approved order MUST
contain an open Checkout Mandate with a matching hash in its delegate
chain. The hash algorithm used MUST be the `_sd_alg` algorithm for the
SD-JWT this constraint is in, or `sha-256` if undefined."

**(b) The Payment Receipt's `reference`.** "The hash of the closed
Mandate that this receipt is binding to." The receipt's full property
set is `status`, `iss`, `iat`, `reference`, `error`,
`error_description`, `payment_id`, `psp_confirmation_id`,
`network_confirmation_id` — it carries **no amount at all**, and no
field for any document.

Beside them, the closed Payment Mandate binds itself to the checkout
with `transaction_id`, the "base64url-encoded hash of the checkout_jwt
field value".

What these already do: they chain a payment authorisation to one
checkout mandate (and, through the delegate chain, to the open mandate
that authorised the agent), and a payment receipt back to the exact
closed mandate that produced it. They are the join keys between AP2's
own records.

What they do not do: every digest is over an AP2 artifact. No AP2
record carries an invoice identifier, a document type, an issue date,
an amount applied to a document, or a registration (Part A recheck,
25 November 2026: AP2 scores 0 full / 0 partial / 10 none on the ten
invoice-link items; "invoice" and "remittance" have 0 hits in the
v0.2.0 specification and schemas).

## 3. What this extension adds

Against both, `io.github.agorail-labs.shopping.invoice_reference`
adds only what neither carries:

| | Payment Terms | AP2 payment reference | This extension |
| --- | --- | --- | --- |
| Object named | Payments due under this checkout | AP2 mandates and receipts | A pre-existing invoice the checkout settles |
| Document identity (number, type, issuer tax identity, issue date, total) | No | No | Yes — `document` |
| Amount applied per document; declared balances; instalment number | Schedules state amounts due, not amounts applied to a document | No (receipt carries no amount) | Yes — `allocation`, expressly a declaration |
| Scheme registration (scheme, identifier, digest of signed artifact, registration time) | No | No | Yes — `registration` |
| Status claim, required with a registration, with `not_established` always allowed | No | No | Yes — `status`, a business claim, never evidence |
| Verdicts against scheme evidence (matches; active at the payment event; signed by the business) | No | Mandate-chain evaluation only, internal to AP2 | Yes — specification section 8 |
| Carried in the AP2-signed checkout | Its fields sit under `payment` | It *is* AP2's binding machinery | Top-level `invoice_reference`, so the merchant signature covers it; snapshot on the order |

Composition, stated plainly: Payment Terms can say *when* the money for
a checkout is due, including by deferred invoicing; AP2's references
prove *which mandate* authorised a payment and *which mandate* a
receipt answers. Neither says *which already-issued, scheme-registered
invoice* the payment settles, or whether that registration was in
effect when the money moved. That is the whole of what this extension
adds, and it adds nothing else: no account to pay, no amount-owed
claim, no new signature.

## Flags

1. **The official `ucp-schema` tool was not run.** This environment has
   no cargo/rustc (checked 26 November 2026), so the tool could not be
   installed. Composition and strict checking were performed locally
   following the tool's documented method; see
   `validation/VALIDATION.md`. Running the official tool over the two
   examples is an open item for the lead's decision.
2. **The India no-reinstatement rule** (specification sections 8.2 and
   9) rests on the Part B dossier: the 24-hour cancellation window is
   from the authority's own text; the correction route (new document
   with its own IRN, no amendment on the IRP) is marked secondary
   there. A primary citation should be pinned at Gate 2.
3. **Authority binding is prospective.** The organisation serves no
   GitHub Pages site today (verified 26 November 2026 in the design
   read), so the capability's schema URL does not yet resolve. That is
   expected before Gate 3 and blocks nothing at Gate 1.
