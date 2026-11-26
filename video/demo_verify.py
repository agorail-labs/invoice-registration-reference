#!/usr/bin/env python3
"""Run the published verifier against the synthetic fixture (Example 2).

    python -m pip install invoice-registration-reference==0.1.0
    python video/demo_verify.py

Everything the verifier needs is loaded explicitly, in the open:

  inputs        the fixture's checkout.json and order.json
                (examples/example-2-synthetic-full/);
  evidence      the bundle the checkout points at — the scheme's
                signed artifact, the signed status evidence, and the
                payment capture — from the fixture's evidence/;
  trusted keys  held independently of the evidence, configured in
                validation/trust_config.json (entry "example2") and
                loaded from validation/trust_keys/. A live integration
                supplies its own authenticated evidence and its own
                trusted keys the same way.

The verifier itself runs fully offline.
"""
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from invoice_registration_reference import VerifierConfig, verify

ROOT = Path(__file__).resolve().parents[1]  # this file lives in video/
FIXTURE = ROOT / "examples" / "example-2-synthetic-full"
EVIDENCE = FIXTURE / "evidence"
VALIDATION = ROOT / "validation"


def b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def ec_key_from_jwk(jwk: dict):
    numbers = ec.EllipticCurvePublicNumbers(
        int.from_bytes(b64u_decode(jwk["x"]), "big"),
        int.from_bytes(b64u_decode(jwk["y"]), "big"),
        ec.SECP256R1(),
    )
    return numbers.public_key()


# -- inputs ------------------------------------------------------------
checkout = json.loads((FIXTURE / "checkout.json").read_text())
order = json.loads((FIXTURE / "order.json").read_text())

# -- evidence bundle ----------------------------------------------------
evidence_bundle = {
    "artifact": (EVIDENCE / "scheme_artifact.jwt.txt").read_text().strip(),
    "status_evidence": json.loads((EVIDENCE / "status_evidence.json").read_text()),
    "payment_event": json.loads((EVIDENCE / "payment_event.json").read_text()),
}

# -- trusted keys and expectations, configured independently ------------
trust = json.loads((VALIDATION / "trust_config.json").read_text())["example2"]
config = VerifierConfig(
    scheme_public_key=load_pem_public_key(
        (VALIDATION / trust["irp_public_key"]).read_bytes()),
    merchant_public_key=ec_key_from_jwk(json.loads(
        (VALIDATION / trust["merchant_public_key"]).read_text())),
    expected_payment_id=trust["expected_payment_id"],
)

# -- the call ------------------------------------------------------------
result = verify(checkout, order, evidence_bundle, config)

print(f"structurally valid: {result['valid']}")
LABELS = {
    "registration_matches_invoice": "registration matches invoice",
    "registration_active_at_payment": "registration active at payment",
    "signed_by_checkout_business": "signed by checkout business",
}
for key, label in LABELS.items():
    verdict = result["verdicts"][key]
    print(f"{label:<34} {verdict['verdict']}")
    print(f"{'':<34} ({verdict['reason']})")
