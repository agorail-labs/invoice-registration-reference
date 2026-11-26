# Invoice Registration Reference

An independent UCP extension and offline Python verifier for a merchant collecting its own previously issued invoice. The extension carries the invoice and its registration reference through Checkout and Order. The verifier reports whether the registration matches the invoice, whether it was active at payment capture, and whether the checkout business signed the reference.

[Specification](https://agorail-labs.github.io/invoice-registration-reference/spec/invoice-registration-reference-v0.1.md) · [Schema](https://agorail-labs.github.io/invoice-registration-reference/schema/invoice_reference.json) · [PyPI](https://pypi.org/project/invoice-registration-reference/) · [Demo](https://agorail-labs.github.io/invoice-registration-reference/video/dist/irr-demo.mp4)

The capability `io.github.agorail-labs.shopping.invoice_reference` extends `dev.ucp.shopping.checkout` and `dev.ucp.shopping.order` and requires UCP 2026-08-25 or later. The v0.1 profile covers India's GST e-invoice scheme, invoice lines of quantity one, positive amounts in INR minor units, and checkout totals without adjustments that change the invoice-only amount.

## Run the example

From a checkout of this repository with Python 3.11 or later:

```sh
python -m pip install invoice-registration-reference==0.1.1
python video/demo_verify.py
```

The [example script](video/demo_verify.py) loads the checkout, order, evidence and independently configured trust before calling the verifier.

```python
from invoice_registration_reference import verify

result = verify(checkout, order, evidence_bundle, config)
```

The complete synthetic fixture returns three `established` verdicts. NIC's signed documentation sample establishes a registration match. Its activity at capture remains `not_established` because the fixture supplies no payment event.

## Evidence and scope

The demo uses simulated registration status and payment capture evidence. Live integrations supply authenticated evidence, including capture evidence authenticated by the caller's payment integration. Matching the checkout ID, payment ID, amount and currency binds capture evidence to the transaction. Authentication is a separate step.

The verifier operates offline. Its inputs describe invoice registration evidence, rather than payment destination, amount owed, or delivery of goods or services. See the [evidence register](research/EVIDENCE_REGISTER.md) and [conformance mapping](conformance/CONFORMANCE.md) for source provenance and test coverage.

## Run the conformance suite

```sh
python -m pip install -r verifier/requirements.txt
python -m unittest discover -s verifier/tests -v
python validation/validate_gate1.py
```

The source suite has 38 verifier tests and 36 schema-harness checks. The harness resolves the published UCP schemas from a pinned cache. See the [validation record](validation/VALIDATION.md) for schema-composition and strict-validation results.

## Licence

[Apache License 2.0](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for the bundled schemas and sample provenance.
