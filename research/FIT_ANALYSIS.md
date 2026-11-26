# Fit analysis — Gate 2

How `io.github.agorail-labs.shopping.invoice_reference` sits inside
UCP and beside AP2, as implemented and verified at Gate 2. Sources:
UCP published specification 2026-08-25; AP2 v0.2.0; the Gate 1 report
(`research/GATE1_REPORT.md`) for the prior-art read.

## Fit with UCP

- **Composition.** The extension follows UCP's vendor-extension rules
  as published: reverse-domain capability name outside the reserved
  `dev.ucp.*` space; one `$defs` entry per parent capability
  (`dev.ucp.shopping.checkout`, `dev.ucp.shopping.order`); composition
  by `allOf` over the published base schemas; `extends` declared;
  protocol floor declared in `requires` (2026-08-25). The official
  `ucp-schema` v2.0.0 tool passes the definition at strict lint and
  validates all delivered payloads in strict mode (Gate 1 review).
- **Discovery shape.** Payloads carry the capability in `ucp`
  metadata with `spec` and `schema` URLs, and — after the Gate 1
  review fix — the base capability entries carry the published base
  schema URLs the official validator requires in submitted payloads.
  (UCP's own responses may show version-only entries; that is a
  presentation difference, not a conflict.)
- **Snapshot semantics.** UCP orders already treat accepted state as
  fixed at creation (compare Payment Terms: the accepted term "MUST
  NOT be modified after the order is created"). The order-side
  snapshot rule of this extension is the same shape: the checkout's
  reference is carried unchanged, and later evidence lives beside it.
- **Coexistence with Payment Terms.** The two extensions are
  orthogonal and composable. Payment Terms answers *when money for
  this checkout is due* (schedules, including deferred invoicing with
  an empty payment object). This extension answers *which
  already-issued, scheme-registered invoice a payment settles, and
  whether that registration was in effect when the money moved*. A
  checkout could carry both — a term scheduling the payment and a
  reference identifying the invoice — with no field overlap: Terms
  writes under `payment`, this extension writes a top-level
  `invoice_reference`. One friction, stated plainly: a fully deferred
  Terms checkout completes with `"payment": {}`, so there may be no
  in-checkout payment record at all; the capture evidence this
  extension's verifier needs then comes entirely from the provider,
  as the evidence register records.

## Fit with AP2

- **Signature coverage.** The AP2 mandate extension's merchant
  authorization is a detached JWS over the JCS-canonicalized checkout
  excluding only `ap2`. Placing `invoice_reference` at the top level
  puts it inside that signature with no AP2 change — verified end to
  end in Examples 2 and 3, and negatively in conformance case 13
  (change the reference after signing and the signature verdict
  falls, at unchanged price).
- **Binding complementarity.** AP2's own references chain mandates to
  mandates (the `payment.reference` constraint digest; the receipt's
  closed-mandate hash). This extension adds the external-document leg
  those digests cannot express: the verdict *signed by the checkout
  business* is precisely the composition of the two — AP2's signature
  over a checkout that carries this extension's reference, joined to
  the order by snapshot equality and `checkout_id`.
- **No AP2 change required.** Nothing in AP2 needs amendment for
  v0.1; the extension consumes the mandate extension as published.

## Limits of the fit, as they stand at Gate 2

1. **Authority binding is still prospective.** The capability's
   schema URL sits under `agorail-labs.github.io`, which the
   organisation does not yet serve. Until Gate 3 publication, a
   counterparty cannot resolve the schema from the namespace
   authority; the definition is distributed with this repository.
2. **Status evidence has no live channel in v0.1.** The verifier
   consumes the documented simulated format. The IRP's public routes
   (Search IRN) are not an authenticated, signed status response, so
   a production integration needs the scheme's or a GSP's
   authenticated channel — the one input Example 1 lacks and the
   register flags as simulated.
3. **One scheme, one currency shape.** The India profile is the only
   adapter; its offset-free AckDt is handled by the
   documented-timezone rule, but another scheme's time and status
   semantics would need their own profile section before the
   verifier's verdicts mean anything there.
4. **Checkout-total coupling.** Rule 2 ties the referred invoice
   lines to the checkout total within the narrowed scope (quantity
   one, no discount/tax/fee changing the invoice-only total). Partial
   payments of an invoice across several checkouts are expressible
   per checkout (each carries its allocation), but a single checkout
   settling several unrelated invoices is bounded by rule 1's
   one-document-per-line discipline and is not a v0.1 use case.
