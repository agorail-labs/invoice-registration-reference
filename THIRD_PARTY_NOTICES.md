# Third-party notices

This repository is licensed under the Apache License 2.0 (see
`LICENSE`). It also contains or reproduces the following third-party
material, retained with its upstream licensing and provenance.

## UCP published schemas (vendored cache)

`validation/schema_cache/` holds an unmodified copy of the published
JSON Schemas of the Universal Commerce Protocol (UCP), version
2026-08-25 — 46 files fetched from https://ucp.dev/2026-08-25/schemas/
on 26 November 2026 and pinned so validation runs are reproducible
(the live fetch path intermittently truncates responses).

- Project: Universal Commerce Protocol — https://ucp.dev,
  https://github.com/universal-commerce-protocol/ucp
- Licence: Apache License 2.0 (the UCP project's licence; the full
  text is the same licence as this repository's `LICENSE`).
- These files are upstream material, not part of this extension's own
  specification, and are used only as validation inputs (the base
  schemas this extension composes over).

## NIC published sample and public key (Example 1)

`examples/example-1-operator-sample/evidence/` reproduces the sample
Signed QR Code and the IRP public key printed in NIC's published QR
code procedure document for the Indian e-invoice system (portal:
einvoice1.gst.gov.in), which publishes the sample and the key for
anyone to verify with. The sample carries dummy particulars and is
used as a signed documentation vector, as its fixture notes record.
No real invoice is used anywhere in this repository.

## Development dependencies (not vendored)

The verifier and harnesses run on `cryptography`, `rfc8785` and
`jsonschema` (see `verifier/requirements.txt`), installed by the user
from PyPI under their own licences; no dependency code is included in
this repository.
