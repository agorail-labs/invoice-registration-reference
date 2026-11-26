#!/usr/bin/env python3
"""Gate 2 end-to-end tests for the Invoice Registration Reference verifier.

Every test asserts the verifier's ACTUAL returned verdicts (the Gate 1
harness printed fixed verdicts; the lead's Gate 2 instruction requires
asserting computed results, including not_established outcomes when a
binding fails).

Run: python3 -m unittest discover -s verifier/tests -v
Requires: cryptography, rfc8785, jsonschema.
"""
import copy
import hashlib
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import invoice_reference_verifier as V  # noqa: E402

from cryptography.hazmat.primitives import hashes  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature  # noqa: E402
import rfc8785  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
E, N, C = V.ESTABLISHED, V.NOT_ESTABLISHED, V.CONTRADICTED

SELLER = "29ABCDE1234F1Z5"
TOTAL = 11800000
REG_AT = "2026-11-20T10:15:23+05:30"
CAP_AT = "2026-11-20T15:42:10+05:30"
OBS_AT = "2026-11-21T09:00:00+05:30"
RULE = "A cancelled IRN is not reinstated. A correction is made by a new document with its own IRN."


def b64u(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Factory:
    """Builds a complete synthetic case in memory, with fresh keys, so
    tests can mutate any input -- including producing a VALIDLY SIGNED
    status response for a different IRN."""

    def __init__(self):
        self.irp_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.merchant_key = ec.generate_private_key(ec.SECP256R1())
        self.doc_no = "EXMPL/2026-27/0042"
        self.irn = hashlib.sha256((SELLER + "2026-27" + "INV" + self.doc_no).encode()).hexdigest()
        nums = self.merchant_key.public_key().public_numbers()
        self.merchant_jwk = {"kty": "EC", "crv": "P-256",
                             "x": b64u(nums.x.to_bytes(32, "big")),
                             "y": b64u(nums.y.to_bytes(32, "big")),
                             "kid": "factory-merchant", "use": "sig", "alg": "ES256"}
        self.config = V.VerifierConfig(
            scheme_public_key=self.irp_key.public_key(),
            merchant_public_key=self.merchant_key.public_key(),
            expected_payment_id="pay_FACTORY_0001")

    def rs256(self, payload: dict) -> str:
        si = (b64u(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
              + "." + b64u(json.dumps(payload, separators=(",", ":")).encode()))
        sig = self.irp_key.sign(si.encode(), padding.PKCS1v15(), hashes.SHA256())
        return si + "." + b64u(sig)

    def artifact(self, **overrides) -> str:
        payload = {
            "iss": "SIMULATED-IRP", "AckNo": "SIMACK1", "AckDt": REG_AT, "Irn": self.irn,
            "data": {"SellerGstin": SELLER, "BuyerGstin": "29PQRST6789K1Z2",
                     "DocNo": self.doc_no, "DocTyp": "INV", "DocDt": "20/11/2026",
                     "TotInvVal": TOTAL // 100, "ItemCnt": 1, "MainHsnCode": "84713010"},
        }
        payload.update(overrides)
        return self.rs256(payload)

    def status(self, irn=None, status="active", observed_at=OBS_AT, cancelled_at=None,
               scheme_rule=RULE) -> dict:
        claims = {"simulated": True, "kind": "scheme_status_response",
                  "scheme": "in_gst_einvoice_irp",
                  "registration_identifier": irn or self.irn, "status": status,
                  "observed_at": observed_at, "cancelled_at": cancelled_at,
                  "scheme_rule": scheme_rule}
        return {"simulated": True, "claims": claims, "jws": self.rs256(claims)}

    def reference(self, artifact: str, **overrides) -> list:
        ref = {"line_item_id": "li_1",
               "document": {"number": self.doc_no, "type": "INV",
                            "issuer_tax_identity": SELLER, "issue_date": "2026-11-20",
                            "total": TOTAL},
               "registration": {"scheme": "in_gst_einvoice_irp", "identifier": self.irn,
                                "artifact_digest": "sha256:" + hashlib.sha256(artifact.encode()).hexdigest(),
                                "registered_at": REG_AT},
               "status": {"value": "active", "observed_at": "2026-11-20T15:40:00+05:30"}}
        ref.update(overrides)
        return [ref]

    def checkout_order(self, reference: list):
        checkout = {"ucp": {"version": "2026-08-25", "capabilities": {}},
                    "id": "chk_factory", "status": "completed", "currency": "INR",
                    "line_items": [{"id": "li_1",
                                    "item": {"id": "item_1", "title": "Unit", "price": TOTAL},
                                    "quantity": 1,
                                    "totals": [{"type": "subtotal", "amount": TOTAL},
                                               {"type": "total", "amount": TOTAL}]}],
                    "totals": [{"type": "subtotal", "amount": TOTAL},
                               {"type": "total", "amount": TOTAL}],
                    "invoice_reference": reference}
        canonical = rfc8785.dumps(checkout)
        si = b64u(json.dumps({"alg": "ES256", "kid": "factory-merchant"},
                             separators=(",", ":")).encode()) + "." + b64u(canonical)
        der = self.merchant_key.sign(si.encode(), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        checkout["ap2"] = {"merchant_authorization":
                           si.split(".")[0] + ".." + b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))}
        order = {"id": "ord_factory", "checkout_id": "chk_factory", "currency": "INR",
                 "invoice_reference": copy.deepcopy(reference)}
        return checkout, order

    def capture(self, **overrides) -> dict:
        pay = {"simulated": True, "kind": "provider_capture_confirmation",
               "payment_id": "pay_FACTORY_0001", "checkout_id": "chk_factory",
               "status": "captured", "amount": TOTAL, "currency": "INR",
               "captured_at": CAP_AT}
        pay.update(overrides)
        return pay

    def genuine(self):
        artifact = self.artifact()
        checkout, order = self.checkout_order(self.reference(artifact))
        bundle = {"artifact": artifact, "status_evidence": self.status(),
                  "payment_event": self.capture()}
        return checkout, order, bundle


def verdicts(result):
    return {k: v["verdict"] for k, v in result["verdicts"].items()}


class FileExamples(unittest.TestCase):
    def test_example1_operator_sample(self):
        r = V.verify_example(ROOT, "example-1-operator-sample", "example1")
        self.assertEqual(verdicts(r), {"registration_matches_invoice": E,
                                       "registration_active_at_payment": N,
                                       "signed_by_checkout_business": N})

    def test_example2_synthetic_full(self):
        r = V.verify_example(ROOT, "example-2-synthetic-full", "example2")
        self.assertEqual(verdicts(r), {"registration_matches_invoice": E,
                                       "registration_active_at_payment": E,
                                       "signed_by_checkout_business": E})

    def test_example3_production_shaped_with_timezone(self):
        r = V.verify_example(ROOT, "example-3-production-shaped-irp", "example3")
        self.assertEqual(verdicts(r), {"registration_matches_invoice": E,
                                       "registration_active_at_payment": E,
                                       "signed_by_checkout_business": E})

    def test_example3_without_configured_timezone(self):
        d = ROOT / "examples" / "example-3-production-shaped-irp"
        checkout = json.loads((d / "checkout.json").read_text())
        order = json.loads((d / "order.json").read_text())
        from dataclasses import replace
        config = replace(V.load_config(ROOT, "example3"), scheme_timezone=None)
        r = V.verify(checkout, order, V.load_bundle(d), config)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)
        self.assertIn("no documented scheme timezone", r["verdicts"]["registration_active_at_payment"]["reason"])
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)
        self.assertEqual(r["verdicts"]["signed_by_checkout_business"]["verdict"], E)


class LeadMutationsOnExample2(unittest.TestCase):
    """The lead's three mutations, asserted against the verifier's
    actual returned verdicts (not binding-check booleans)."""

    def setUp(self):
        d = ROOT / "examples" / "example-2-synthetic-full"
        self.checkout = json.loads((d / "checkout.json").read_text())
        self.order = json.loads((d / "order.json").read_text())
        self.bundle = V.load_bundle(d)
        self.config = V.load_config(ROOT, "example2")

    def test_capture_currency_mutation_active_not_established(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["payment_event"]["currency"] = "USD"
        r = V.verify(self.checkout, self.order, bundle, self.config)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)
        self.assertEqual(r["verdicts"]["signed_by_checkout_business"]["verdict"], E)

    def test_capture_payment_id_mutation_active_not_established(self):
        bundle = copy.deepcopy(self.bundle)
        bundle["payment_event"]["payment_id"] = "pay_MUTATED_9999"
        r = V.verify(self.checkout, self.order, bundle, self.config)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)
        self.assertEqual(r["verdicts"]["signed_by_checkout_business"]["verdict"], E)

    def test_order_checkout_id_mutation_signed_not_established(self):
        order = copy.deepcopy(self.order)
        order["checkout_id"] = "chk_MUTATED"
        r = V.verify(self.checkout, order, self.bundle, self.config)
        self.assertEqual(r["verdicts"]["signed_by_checkout_business"]["verdict"], N)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], E)
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)


class ConformanceCases(unittest.TestCase):
    def setUp(self):
        self.f = Factory()

    def run_case(self, checkout, order, bundle, config=None):
        return V.verify(checkout, order, bundle, config or self.f.config)

    def test_genuine(self):
        r = self.run_case(*self.f.genuine())
        self.assertEqual(verdicts(r), {"registration_matches_invoice": E,
                                       "registration_active_at_payment": E,
                                       "signed_by_checkout_business": E})

    def test_mismatch_with_signed_artifact(self):
        artifact = self.f.artifact()
        ref = self.f.reference(artifact)
        ref[0]["document"]["number"] = "EXMPL/2026-27/9999"  # artifact says 0042
        checkout, order = self.f.checkout_order(ref)
        r = self.run_case(checkout, order, {"artifact": artifact,
                                            "status_evidence": self.f.status(),
                                            "payment_event": self.f.capture()})
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], C)

    def test_cancelled_before_payment(self):
        checkout, order, bundle = self.f.genuine()
        bundle["status_evidence"] = self.f.status(
            status="cancelled", observed_at="2026-11-20T12:00:00+05:30",
            cancelled_at="2026-11-20T12:00:00+05:30")
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], C)

    def test_cancelled_exactly_at_payment(self):
        checkout, order, bundle = self.f.genuine()
        bundle["status_evidence"] = self.f.status(
            status="cancelled", observed_at=CAP_AT, cancelled_at=CAP_AT)
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], C)

    def test_cancelled_after_payment(self):
        checkout, order, bundle = self.f.genuine()
        bundle["status_evidence"] = self.f.status(
            status="cancelled", observed_at="2026-11-22T09:00:00+05:30",
            cancelled_at="2026-11-22T09:00:00+05:30")
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], E)

    def test_valid_artifact_with_only_business_claim(self):
        artifact = self.f.artifact()
        checkout, order = self.f.checkout_order(self.f.reference(artifact))
        r = self.run_case(checkout, order, {"artifact": artifact,
                                            "status_evidence": None, "payment_event": None})
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)

    def test_lookup_failure_is_not_established_never_contradicted(self):
        artifact = self.f.artifact()
        checkout, order = self.f.checkout_order(self.f.reference(artifact))
        r = self.run_case(checkout, order, {"artifact": None, "status_evidence": None,
                                            "payment_event": self.f.capture(),
                                            "lookup_outcome": "timeout"})
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], N)
        r2 = self.run_case(checkout, order, {"artifact": artifact, "status_evidence": None,
                                             "payment_event": self.f.capture(),
                                             "lookup_outcome": "timeout"})
        self.assertEqual(r2["verdicts"]["registration_active_at_payment"]["verdict"], N)

    def test_authoritative_absence_contradicts_matches(self):
        artifact = self.f.artifact()
        checkout, order = self.f.checkout_order(self.f.reference(artifact))
        bundle = {"artifact": artifact,
                  "status_evidence": self.f.status(status="not_found"),
                  "payment_event": self.f.capture()}
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], C)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)

    def test_status_not_established(self):
        artifact = self.f.artifact()
        ref = self.f.reference(artifact)
        ref[0]["status"] = {"value": "not_established", "observed_at": "2026-11-20T15:40:00+05:30"}
        checkout, order = self.f.checkout_order(ref)
        r = self.run_case(checkout, order, {"artifact": artifact, "status_evidence": None,
                                            "payment_event": self.f.capture()})
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)

    def test_registration_without_status_is_invalid(self):
        from jsonschema import Draft202012Validator
        ext = json.loads((ROOT / "schema" / "invoice_reference.json").read_text())
        validator = Draft202012Validator({"$defs": ext["$defs"],
                                          "$ref": "#/$defs/invoice_reference_entry"})
        entry = {"line_item_id": "li_1",
                 "document": {"number": "X1", "type": "INV",
                              "issuer_tax_identity": SELLER, "issue_date": "2026-11-20",
                              "total": TOTAL},
                 "registration": {"scheme": "in_gst_einvoice_irp", "identifier": "a" * 64,
                                  "artifact_digest": "sha256:" + "b" * 64}}
        self.assertTrue(list(validator.iter_errors(entry)))
        entry["status"] = {"value": "not_established", "observed_at": "2026-11-20T15:40:00+05:30"}
        self.assertFalse(list(validator.iter_errors(entry)))

    def test_same_registration_on_two_lines(self):
        artifact = self.f.artifact()
        ref = self.f.reference(artifact)
        second = copy.deepcopy(ref[0])
        second["line_item_id"] = "li_2"
        checkout, order = self.f.checkout_order(ref + [second])
        checkout["line_items"].append(
            {"id": "li_2", "item": {"id": "item_2", "title": "Unit 2", "price": TOTAL},
             "quantity": 1, "totals": [{"type": "total", "amount": TOTAL}]})
        r = self.run_case(checkout, order, {"artifact": artifact,
                                            "status_evidence": self.f.status(),
                                            "payment_event": self.f.capture()})
        self.assertFalse(r["valid"])
        self.assertTrue(any("rule 1" in x for x in r["violations"]))

    def test_allocation_does_not_add_up(self):
        artifact = self.f.artifact()
        ref = self.f.reference(artifact)
        ref[0]["allocation"] = {"amount_applied": TOTAL, "balance_before": TOTAL,
                                "balance_after": 500}
        checkout, order = self.f.checkout_order(ref)
        r = self.run_case(checkout, order, {"artifact": artifact,
                                            "status_evidence": self.f.status(),
                                            "payment_event": self.f.capture()})
        self.assertFalse(r["valid"])
        self.assertTrue(any("rule 4" in x for x in r["violations"]))

    def test_reference_changed_same_price_signature_verdict_falls(self):
        artifact = self.f.artifact()
        checkout, order = self.f.checkout_order(self.f.reference(artifact))
        checkout["invoice_reference"][0]["document"]["number"] = "EXMPL/2026-27/7777"
        r = self.run_case(checkout, order, {"artifact": artifact,
                                            "status_evidence": self.f.status(),
                                            "payment_event": self.f.capture()})
        self.assertEqual(r["verdicts"]["signed_by_checkout_business"]["verdict"], N)
        self.assertIn("does not verify", r["verdicts"]["signed_by_checkout_business"]["reason"])

    def test_validly_signed_status_for_different_irn_binds_separately(self):
        checkout, order, bundle = self.f.genuine()
        other_irn = hashlib.sha256(b"some-other-irn").hexdigest()
        bundle["status_evidence"] = self.f.status(irn=other_irn)  # same key: signature VALID
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], N)
        self.assertIn("different registration identifier",
                      r["verdicts"]["registration_active_at_payment"]["reason"])
        self.assertEqual(r["verdicts"]["registration_matches_invoice"]["verdict"], E)

    def test_unverified_status_claims_copy_is_never_evaluated(self):
        checkout, order, bundle = self.f.genuine()
        # Tamper only the readable claims copy; the JWS is untouched.
        bundle["status_evidence"]["claims"]["status"] = "cancelled"
        bundle["status_evidence"]["claims"]["cancelled_at"] = "2026-11-20T12:00:00+05:30"
        r = self.run_case(checkout, order, bundle)
        self.assertEqual(r["verdicts"]["registration_active_at_payment"]["verdict"], E)


class FileRegressions(unittest.TestCase):
    """RC2: the four verdict regressions as file-based end-to-end cases.

    Fixtures live in validation/regressions/fixture (builder:
    validation/build_regression_fixtures.py): one base bundle plus one
    variant file per broken binding, loaded from disk and run through
    the verifier exactly as shipped.
    """

    FIX = ROOT / "validation" / "regressions" / "fixture"

    def run_variant(self, variant=None):
        config = V.load_config(ROOT, "regression")
        checkout = json.loads((self.FIX / "checkout.json").read_text())
        order = json.loads((self.FIX / "order.json").read_text())
        bundle = V.load_bundle(self.FIX)
        if variant:
            vdir = self.FIX / "variants" / variant
            for f in vdir.iterdir():
                obj = json.loads(f.read_text())
                if f.name == "order.json":
                    order = obj
                elif f.name == "payment_event.json":
                    bundle["payment_event"] = obj
                elif f.name == "status_evidence.json":
                    bundle["status_evidence"] = obj
        return V.verify(checkout, order, bundle, config)

    M, A, S = ("registration_matches_invoice",
               "registration_active_at_payment",
               "signed_by_checkout_business")

    def expect(self, r, m, a, s):
        self.assertEqual(verdicts(r), {self.M: m, self.A: a, self.S: s})

    def test_base_all_established(self):
        r = self.run_variant()
        self.assertTrue(r["valid"], r["violations"])
        self.expect(r, E, E, E)

    def test_capture_currency_variant(self):
        self.expect(self.run_variant("capture-currency"), E, N, E)

    def test_capture_payment_id_variant(self):
        self.expect(self.run_variant("capture-payment-id"), E, N, E)

    def test_order_checkout_id_variant(self):
        self.expect(self.run_variant("order-checkout-id"), E, E, N)

    def test_status_different_irn_variant(self):
        r = self.run_variant("status-different-irn")
        self.expect(r, E, N, E)
        self.assertIn("different registration identifier",
                      r["verdicts"][self.A]["reason"])


if __name__ == "__main__":
    unittest.main()
