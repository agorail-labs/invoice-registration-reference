#!/usr/bin/env python3
"""Gate 2 fixture builder: Example 3, the production-shaped synthetic IRP case.

Example 2's simulated artifact carries a top-level RFC 3339 AckDt -- a
simulation simplification. This fixture is shaped like the published IRP
signed invoice instead: the payload's `data` is a nested object holding
the invoice fields together with AckNo and AckDt, and AckDt is in the
IRP's documented format ("2026-11-20 10:15:23", yyyy-MM-dd HH:mm:ss)
with NO timezone offset.
The verifier may use it for event ordering only under the documented
scheme timezone held in its configuration (Asia/Kolkata); the test
suite runs this fixture with and without that configuration.

Fully synthetic: keys are generated for this fixture and the private
halves discarded; public halves are written to the evidence folder for
inspection and, as independently configured trust copies, to
validation/trust_keys (see trust_config.json, entry "example3").

This script is Gate 2 fixture tooling. It is not the verifier.
"""
import hashlib
import importlib.util
import json
import pathlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
import rfc8785

ROOT = pathlib.Path(__file__).resolve().parent.parent
EX3 = ROOT / "examples" / "example-3-production-shaped-irp"
TRUST_DIR = ROOT / "validation" / "trust_keys"

spec = importlib.util.spec_from_file_location(
    "build_examples", ROOT / "validation" / "build_examples.py")
be = importlib.util.module_from_spec(spec)
spec.loader.exec_module(be)
b64u, dump, sha256_tag = be.b64u, be.dump, be.sha256_tag


def rs256_jwt(header: dict, payload: dict, key) -> str:
    signing_input = (
        b64u(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + b64u(json.dumps(payload, separators=(",", ":")).encode())
    )
    sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return signing_input + "." + b64u(sig)


def main() -> None:
    ev = EX3 / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    TRUST_DIR.mkdir(parents=True, exist_ok=True)

    seller_gstin = "29ABCDE1234F1Z5"   # synthetic (dummy PAN pattern)
    buyer_gstin = "29PQRST6789K1Z2"    # synthetic
    doc_no = "EXMPL/2026-27/0043"
    doc_typ = "INV"
    fy = "2026-27"
    total_major = 118000
    total_minor = total_major * 100
    irn = hashlib.sha256((seller_gstin + fy + doc_typ + doc_no).encode()).hexdigest()
    # AckDt in the IRP's documented format, yyyy-MM-dd HH:mm:ss, with
    # no timezone offset: NIC's Generate IRN specification gives
    # AckDt as `yyyy-MM-dd HH:mm:ss`, and ClearTax's published IRP
    # response example shows "AckDt": "2023-10-26 14:28:00"
    # (docs.cleartax.in, Cancel IRN sample govt_response; read
    # 2026-11-26). An earlier build of this fixture used a
    # dd/MM/yyyy AM/PM rendering, which is NOT a documented IRP
    # format; the Gate 2 review caught it and the fixture now proves
    # the documented form.
    ack_dt_irp = "2026-11-20 10:15:23"
    registered_at = "2026-11-20T10:15:23+05:30"    # under Asia/Kolkata
    captured_at = "2026-11-20T15:42:10+05:30"
    status_observed_at = "2026-11-21T09:00:00+05:30"

    irp_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    irp_pub_pem = irp_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    (ev / "simulated_irp_public_key.pem").write_bytes(irp_pub_pem)
    (TRUST_DIR / "ex3_irp_public_key.pem").write_bytes(irp_pub_pem)

    # Production shape: one nested `data` object holding the invoice
    # fields AND the acknowledgement (AckNo, AckDt, Irn) inside it.
    data = {
        "SellerGstin": seller_gstin,
        "BuyerGstin": buyer_gstin,
        "DocNo": doc_no,
        "DocTyp": doc_typ,
        "DocDt": "20/11/2026",
        "TotInvVal": total_major,
        "ItemCnt": 1,
        "MainHsnCode": "84713010",
        "AckNo": "SIMACK202611200043",
        "AckDt": ack_dt_irp,
        "Irn": irn,
    }
    artifact_payload = {"iss": "SIMULATED-IRP", "data": data}
    artifact = rs256_jwt({"alg": "RS256", "typ": "JWT", "kid": "simulated-irp-key-3"},
                         artifact_payload, irp_key)
    (ev / "scheme_artifact.jwt.txt").write_text(artifact + "\n")
    dump(ev / "scheme_artifact.decoded.json", artifact_payload)

    status_claims = {
        "simulated": True,
        "kind": "scheme_status_response",
        "scheme": "in_gst_einvoice_irp",
        "registration_identifier": irn,
        "status": "active",
        "observed_at": status_observed_at,
        "cancelled_at": None,
        "scheme_rule": (
            "A cancelled IRN is not reinstated. A correction is made by a new "
            "document with its own IRN."
        ),
    }
    status_jws = rs256_jwt({"alg": "RS256", "typ": "JWT", "kid": "simulated-irp-key-3"},
                           status_claims, irp_key)
    dump(ev / "status_evidence.json", {
        "simulated": True,
        "format": "Signed status response (compact JWS, RS256) from the scheme, "
                  "simulated for this example. Verify using the independently "
                  "configured scheme key (validation/trust_keys).",
        "claims": status_claims,
        "jws": status_jws,
    })

    li = "li_1"
    title = "Industrial controller unit, as invoiced"
    reference = [{
        "line_item_id": li,
        "document": {
            "number": doc_no,
            "type": doc_typ,
            "issuer_tax_identity": seller_gstin,
            "issue_date": "2026-11-20",
            "total": total_minor,
        },
        "allocation": {
            "amount_applied": total_minor,
            "balance_before": total_minor,
            "balance_after": 0,
            "instalment_number": 1,
        },
        "registration": {
            "scheme": "in_gst_einvoice_irp",
            "identifier": irn,
            "artifact_digest": sha256_tag(artifact.encode()),
            "registered_at": registered_at,
        },
        "status": {"value": "active", "observed_at": "2026-11-20T15:40:00+05:30"},
    }]
    checkout = {
        "ucp": be.ucp_block(for_order=False, with_ap2=True),
        "id": "chk_example3_production_shaped",
        "status": "completed",
        "currency": "INR",
        "line_items": [be.checkout_line(li, "item_controller_unit", title, total_minor)],
        "totals": [
            {"type": "subtotal", "amount": total_minor},
            {"type": "total", "amount": total_minor},
        ],
        "links": [{"type": "terms_of_service", "url": "https://example.com/terms"}],
        "invoice_reference": reference,
    }

    merchant_key = ec.generate_private_key(ec.SECP256R1())
    pub_numbers = merchant_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": b64u(pub_numbers.x.to_bytes(32, "big")),
        "y": b64u(pub_numbers.y.to_bytes(32, "big")),
        "kid": "merchant-simulated-key-3",
        "use": "sig",
        "alg": "ES256",
    }
    dump(ev / "merchant_public_key.jwk.json", jwk)
    dump(TRUST_DIR / "ex3_merchant_public_key.jwk.json", jwk)
    canonical = rfc8785.dumps(checkout)
    header = {"alg": "ES256", "kid": "merchant-simulated-key-3"}
    signing_input = b64u(json.dumps(header, separators=(",", ":")).encode()) + "." + b64u(canonical)
    der_sig = merchant_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    detached = signing_input.split(".")[0] + ".." + b64u((r.to_bytes(32, "big") + s.to_bytes(32, "big")))
    checkout["ap2"] = {"merchant_authorization": detached}

    order = {
        "ucp": be.ucp_block(for_order=True, with_ap2=False),
        "id": "ord_example3_production_shaped",
        "checkout_id": checkout["id"],
        "permalink_url": "https://example.com/orders/ord_example3_production_shaped",
        "currency": "INR",
        "line_items": [be.order_line(li, "item_controller_unit", title, total_minor)],
        "fulfillment": {"expectations": []},
        "totals": [
            {"type": "subtotal", "amount": total_minor},
            {"type": "total", "amount": total_minor},
        ],
        "invoice_reference": json.loads(json.dumps(reference)),
    }
    dump(EX3 / "checkout.json", checkout)
    dump(EX3 / "order.json", order)
    dump(ev / "payment_event.json", {
        "simulated": True,
        "kind": "provider_capture_confirmation",
        "format": "Simulated provider-confirmed capture, in the documented "
                  "Gate 1 format (specification section 7).",
        "provider": "Simulated Payments Provider",
        "payment_id": "pay_SIMULATED_0002",
        "checkout_id": checkout["id"],
        "status": "captured",
        "amount": total_minor,
        "currency": "INR",
        "captured_at": captured_at,
    })

    cfg_path = ROOT / "validation" / "trust_config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["example3"] = {
        "irp_public_key": "trust_keys/ex3_irp_public_key.pem",
        "merchant_public_key": "trust_keys/ex3_merchant_public_key.jwk.json",
        "expected_payment_id": "pay_SIMULATED_0002",
        "scheme_timezone": "Asia/Kolkata",
    }
    dump(cfg_path, cfg)
    print("example 3 written; IRN", irn)


if __name__ == "__main__":
    main()
