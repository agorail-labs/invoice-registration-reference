# Invoice Registration Reference

An offline Python reference verifier for invoice-registration evidence carried in UCP checkout and order payloads. Version 0.1 models a merchant collecting its own already-issued invoice in INR under India's GST e-invoice scheme.

```python
from invoice_registration_reference import VerifierConfig, verify
```

Call `verify(checkout, order, evidence_bundle, config)` with parsed, schema-validated payloads, the evidence bundle described in the specification, and an independently configured `VerifierConfig`. The result reports whether the invoice registration matches, whether it was active at payment, and whether the checkout business signed the reference.

Run the repository's fixtures and conformance suite for runnable examples. Status and capture fixtures are simulated. Matching capture fields binds a capture to a checkout; live capture evidence requires authentication by the caller's payment integration. The verifier operates offline and does not initiate payments or resolve invoice evidence from a live registry.

- [Source, examples, and conformance suite](https://github.com/agorail-labs/invoice-registration-reference)
- [Specification](https://agorail-labs.github.io/invoice-registration-reference/spec/invoice-registration-reference-v0.1.md)
- [Capability schema](https://agorail-labs.github.io/invoice-registration-reference/schema/invoice_reference.json)
