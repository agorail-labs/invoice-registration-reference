# Example 1 — the operator's published signed sample

**Evidence level:** the scheme's own published sample, and nothing else.
**Scope of the verdict below:** this sample is a signed **documentation
vector** — NIC's published example for verification, with dummy
particulars — not a live registration. "Established" here means the
reference matches that signed documentation vector, nothing more.

## What is operator-published here

Only two things in this folder come from the scheme operator (NIC, the
Indian e-invoice system's operator):

- `evidence/signed_qr_code.jwt.txt` — the sample Signed QR Code printed
  in NIC's published **QR code procedure document** for the e-invoice
  system, copied byte-for-byte. The document presents this sample
  together with the public key "as given below", for anyone to verify.
  Working copy extracted 25 November 2026 from the document as mirrored
  at bizsolindia.com (the portal itself is einvoice1.gst.gov.in).
- `evidence/irp_public_key.pem` — that published public key (RSA-2048,
  SubjectPublicKeyInfo), converted to PEM. The key as published is a
  bare public key: **it carries no validity dates, because none are
  published for it** — validity dates would sit on the related DS
  certificate, which the portal distributes behind a login. The
  sample's JWT header carries `kid`
  `115F4426617A7938BE1BA06DBEE91A427584EDAB` and a matching `x5t`
  (the certificate's SHA-1 fingerprint).

## What the source says about the sample

The procedure document offers the sample as a documentation example for
verification, not as a transaction record. Its particulars are dummy
particulars: seller GSTIN `37BZNPM9430M1KL` and buyer GSTIN
`03BZNPM9430M1KL` are the same dummy PAN (`BZNPM9430M`) under two state
codes; the document is `CTDN23456`, type `INV`, dated 05/08/2020, value
16650, one item, main HSN `39231010`. **It is not a real invoice of a
real business**, and no real invoice is used anywhere in this
repository.

## Verification recorded for this fixture

Offline, against the published key (see
`validation/validation-results.txt`):

- Signature (RS256): **valid** — "Verified OK" equivalent under the
  harness's RS256 check.
- Negative control: flipping a single character in the payload makes
  the same check **fail**, so the pass is not an artifact of the setup.
- The signed payload's fields (`data`): `SellerGstin`, `BuyerGstin`,
  `DocNo`, `DocTyp`, `DocDt`, `TotInvVal`, `ItemCnt`, `MainHsnCode`,
  `Irn`; header `alg`/`kid`/`typ`/`x5t`; `iss` = "NIC". **No issue or
  expiry timestamps, and no registration time, are inside the signed
  QR payload.**

## The checkout and order in this folder

`checkout.json` and `order.json` are **constructed for this reference**
around the sample (they are not operator-published): one line item of
quantity one, total 1,665,000 paise (= ₹16,650, the artifact's
`TotInvVal` in rupees × 100), and an `invoice_reference` whose
`document` and `registration.identifier` are taken from the signed
payload. `registered_at` is **omitted**: the QR evidence supplies no
registration time at usable precision (specification section 9). The
`status` claim is `not_established`, as rule 6 permits. No allocation
is carried.

## Verdicts for this example (specification section 8)

| Verdict | Result | Why |
| --- | --- | --- |
| Registration matches the invoice | **established** | The artifact's signature verifies and every field the QR binds matches the reference. |
| Registration active at the payment event | **not established** | No authenticated status evidence and no payment-event evidence are held, and the artifact supplies no registration time. A genuine signed invoice, and the question stays open — the central demonstration of v0.1. |
| Signed by the checkout business | **not established** | This constructed checkout carries no AP2 merchant authorization. |
