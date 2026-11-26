#!/usr/bin/env python3
"""Build the file-based end-to-end regression fixture (Gate 3 / RC2).

One self-contained synthetic bundle plus four variant files, each
variant breaking exactly one binding. The RC2 test suite loads these
from disk and asserts the verifier's returned verdicts:

  base                    -> all three verdicts established
  capture-currency        -> active at payment: not established
  capture-payment-id      -> active at payment: not established
  order-checkout-id       -> signed by the business: not established
  status-different-irn    -> active at payment: not established
                             (status JWS validly signed, wrong IRN:
                             binding fails, not signature validity)

The status-different-irn variant needs a status response signed by
the fixture's scheme key, which is why these are generated fixtures
rather than hand edits. Private keys are discarded; public keys go to
validation/trust_keys and the binding targets to trust_config.json
under "regression". Re-running regenerates keys and signatures.
"""
import base64
import hashlib
import json
import pathlib

import rfc8785
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "validation" / "regressions" / "fixture"
CAP = "io.github.agorail-labs.shopping.invoice_reference"
BASE_CO = "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json"
BASE_ORD = "https://ucp.dev/2026-08-25/schemas/shopping/order.json"
SCHEMA_URL = ("https://agorail-labs.github.io/invoice-registration-reference/"
              "schema/invoice_reference.json")


def b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def rs256_sign(key, payload_obj):
    head = b64u(json.dumps({"alg": "RS256", "typ": "JWT"},
                           separators=(",", ":")).encode())
    body = b64u(json.dumps(payload_obj, separators=(",", ":")).encode())
    msg = f"{head}.{body}".encode()
    sig = key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    return f"{head}.{body}.{b64u(sig)}"


def main():
    irp = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    irp_pub_pem = irp.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    mk = ec.generate_private_key(ec.SECP256R1())
    mp = mk.public_key().public_numbers()
    merchant_jwk = {"kty": "EC", "crv": "P-256",
                    "x": b64u(mp.x.to_bytes(32, "big")),
                    "y": b64u(mp.y.to_bytes(32, "big")), "alg": "ES256"}

    (ROOT / "validation" / "trust_keys" / "reg_irp_public_key.pem"
     ).write_text(irp_pub_pem)
    (ROOT / "validation" / "trust_keys" / "reg_merchant_public_key.jwk.json"
     ).write_text(json.dumps(merchant_jwk, indent=2) + "\n")
    cfg_path = ROOT / "validation" / "trust_config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["regression"] = {
        "irp_public_key": "trust_keys/reg_irp_public_key.pem",
        "merchant_public_key": "trust_keys/reg_merchant_public_key.jwk.json",
        "expected_payment_id": "pay_REG_0001",
        "scheme_timezone": "Asia/Kolkata"}
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")

    seller, doc_no, doc_date = "29ABCDE1234F1Z5", "REG/2026-27/0001", "2026-11-20"
    total_minor = 11800000
    irn = hashlib.sha256(f"{seller}2026-27INV{doc_no}".encode()).hexdigest()
    other_irn = hashlib.sha256(b"a-different-invoice").hexdigest()
    data = {"SellerGstin": seller, "DocNo": doc_no, "DocTyp": "INV",
            "DocDt": "20/11/2026", "TotInvVal": total_minor // 100,
            "ItemCnt": 1, "AckNo": 112610000000003,
            "AckDt": "2026-11-20 10:15:23", "Irn": irn}
    artifact = rs256_sign(irp, {"data": data})
    digest = "sha256:" + hashlib.sha256(artifact.encode("ascii")).hexdigest()

    entry = {"line_item_id": "li_1",
             "document": {"number": doc_no, "type": "INV",
                          "issuer_tax_identity": seller,
                          "issue_date": doc_date, "total": total_minor},
             "registration": {"scheme": "in_gst_einvoice_irp",
                              "identifier": irn, "artifact_digest": digest,
                              "registered_at": "2026-11-20T10:15:23+05:30"},
             "status": {"value": "active",
                        "observed_at": "2026-11-21T09:00:00+05:30"}}
    caps = {
        "dev.ucp.shopping.checkout": [{"version": "2026-08-25", "schema": BASE_CO}],
        CAP: [{"version": "2026-11-26",
               "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.order"],
               "spec": SCHEMA_URL, "schema": SCHEMA_URL}],
        "dev.ucp.common.payment.ap2_mandate": [{
            "version": "2026-08-25", "extends": "dev.ucp.shopping.checkout",
            "spec": "https://ucp.dev/2026-08-25/specification/payment/extensions/ap2-mandates",
            "schema": "https://ucp.dev/2026-08-25/schemas/common/payment_ap2_mandate.json"}]}
    checkout = {
        "ucp": {"version": "2026-08-25", "capabilities": caps,
                "payment_handlers": {}},
        "id": "chk_reg_001", "status": "completed",
        "currency": "INR",
        "line_items": [{"id": "li_1", "quantity": 1,
                        "item": {"id": "svc_1", "title": "Advisory services"},
                        "totals": [{"type": "total", "amount": total_minor}]}],
        "totals": [{"type": "total", "amount": total_minor}],
        "invoice_reference": [entry]}
    canon = rfc8785.dumps({k: v for k, v in checkout.items() if k != "ap2"})
    mh = b64u(json.dumps({"alg": "ES256"}, separators=(",", ":")).encode())
    der = mk.sign(f"{mh}.{b64u(canon)}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    # AP2 merchant authorization is a DETACHED JWS: header..signature.
    checkout["ap2"] = {"merchant_authorization": f"{mh}..{b64u(raw)}"}
    order = {
        "ucp": {"version": "2026-08-25", "capabilities": {
            "dev.ucp.shopping.order": [{"version": "2026-08-25", "schema": BASE_ORD}],
            CAP: caps[CAP]}},
        "id": "ord_reg_001", "checkout_id": "chk_reg_001",
        "currency": "INR",
        "line_items": [{"id": "li_1", "quantity": 1,
                        "item": {"id": "svc_1", "title": "Advisory services"},
                        "totals": [{"type": "total", "amount": total_minor}]}],
        "totals": [{"type": "total", "amount": total_minor}],
        "invoice_reference": [entry]}

    def status_jws(for_irn):
        claims = {"registration_identifier": for_irn, "status": "active",
                  "cancelled_at": None,
                  "observed_at": "2026-11-21T09:00:00+05:30",
                  "no_reinstatement": True}
        return {"format": "simulated-irp-status-jws-v1",
                "jws": rs256_sign(irp, claims), "claims": claims}

    capture = {"format": "simulated-capture-v1", "payment_id": "pay_REG_0001",
               "checkout_id": "chk_reg_001", "status": "captured",
               "amount": total_minor, "currency": "INR",
               "captured_at": "2026-11-20T15:42:10+05:30"}

    ev = OUT / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    (OUT / "checkout.json").write_text(json.dumps(checkout, indent=2) + "\n")
    (OUT / "order.json").write_text(json.dumps(order, indent=2) + "\n")
    (ev / "scheme_artifact.jwt.txt").write_text(artifact + "\n")
    (ev / "scheme_artifact.decoded.json").write_text(
        json.dumps({"data": data}, indent=2) + "\n")
    (ev / "status_evidence.json").write_text(
        json.dumps(status_jws(irn), indent=2) + "\n")
    (ev / "payment_event.json").write_text(json.dumps(capture, indent=2) + "\n")
    (ev / "merchant_public_key.jwk.json").write_text(
        json.dumps(merchant_jwk, indent=2) + "\n")
    (ev / "simulated_irp_public_key.pem").write_text(irp_pub_pem)

    variants = {
        "capture-currency": ("payment_event.json",
                             {**capture, "currency": "USD"}),
        "capture-payment-id": ("payment_event.json",
                               {**capture, "payment_id": "pay_OTHER_9999"}),
        "order-checkout-id": ("order.json",
                              {**order, "checkout_id": "chk_DIFFERENT"}),
        "status-different-irn": ("status_evidence.json", status_jws(other_irn)),
    }
    for name, (fname, obj) in variants.items():
        d = OUT / "variants" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text(json.dumps(obj, indent=2) + "\n")
    print("regression fixture written; IRN", irn)


if __name__ == "__main__":
    main()
