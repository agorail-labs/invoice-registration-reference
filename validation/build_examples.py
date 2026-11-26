#!/usr/bin/env python3
"""Gate 1 example builder for invoice-registration-reference v0.1.

Generates the two Gate 1 examples deterministically in structure (keys for
Example 2 are generated fresh on each run and only the public halves are
written into the example; the private halves are discarded).

Example 1 wraps the Indian e-invoice operator's (NIC) published signed
QR-code sample. The artifact file is copied byte-for-byte from the working
copy extracted from NIC's published QR code procedure document
(~/workspace/einvoice-verify/sample_signed_qrcode.txt, extracted
2026-11-25). No real invoice is used.

Example 2 is fully synthetic: a simulated IRP (RSA) key signs a simulated
signed-invoice artifact and a simulated status response; a simulated
merchant (EC P-256) key produces the AP2 mandate extension's detached-JWS
merchant authorization over the JCS-canonicalized checkout (excluding
`ap2`), per the UCP AP2 Mandates extension.

This script is Gate 1 tooling only. It is not the verifier (Gate 2).
"""
import base64
import hashlib
import json
import pathlib
import shutil

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
import rfc8785

ROOT = pathlib.Path(__file__).resolve().parent.parent
EX1 = ROOT / "examples" / "example-1-operator-sample"
EX2 = ROOT / "examples" / "example-2-synthetic-full"
CAP_NAME = "io.github.agorail-labs.shopping.invoice_reference"
CAP_VERSION = "2026-11-26"
SCHEMA_URL = "https://agorail-labs.github.io/invoice-registration-reference/schema/invoice_reference.json"
SPEC_URL = "https://agorail-labs.github.io/invoice-registration-reference/spec/invoice-registration-reference-v0.1"
UCP_VERSION = "2026-08-25"


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sha256_tag(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


# artifact_digest is defined over the ASCII bytes of the artifact's
# compact JWS serialization itself (specification section 4, as tightened
# at Gate 1 review). Files store the artifact with a trailing newline;
# that newline is file framing, not part of the artifact, and is never
# hashed. The builder hashes the stripped compact string, and the
# harness does the same.


def dump(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


CHECKOUT_SCHEMA_URL = "https://ucp.dev/2026-08-25/schemas/shopping/checkout.json"
ORDER_SCHEMA_URL = "https://ucp.dev/2026-08-25/schemas/shopping/order.json"
TRUST_DIR = ROOT / "validation" / "trust_keys"


def ucp_block(for_order: bool, with_ap2: bool) -> dict:
    # Base capability entries carry the published base schema URLs. UCP
    # responses may show version-only entries, but the official ucp-schema
    # validator requires the schema URL in submitted payloads (lead's
    # Gate 1 review, 2026-11-26). Because the AP2 merchant signature
    # covers ucp metadata, Example 2 is re-signed after any change here.
    caps = {
        "dev.ucp.shopping.checkout": [{"version": UCP_VERSION, "schema": CHECKOUT_SCHEMA_URL}],
        CAP_NAME: [{
            "version": CAP_VERSION,
            "extends": ["dev.ucp.shopping.checkout", "dev.ucp.shopping.order"],
            "spec": SPEC_URL,
            "schema": SCHEMA_URL,
        }],
    }
    if for_order:
        caps = {
            "dev.ucp.shopping.order": [{"version": UCP_VERSION, "schema": ORDER_SCHEMA_URL}],
            CAP_NAME: caps[CAP_NAME],
        }
    if with_ap2:
        caps["dev.ucp.common.payment.ap2_mandate"] = [{
            "version": UCP_VERSION,
            "extends": "dev.ucp.shopping.checkout",
            "spec": "https://ucp.dev/2026-08-25/specification/payment/extensions/ap2-mandates",
            "schema": "https://ucp.dev/2026-08-25/schemas/common/payment_ap2_mandate.json",
        }]
    block = {"version": UCP_VERSION, "capabilities": caps}
    if not for_order:
        block["payment_handlers"] = {}
    return block


def checkout_line(li_id: str, item_id: str, title: str, amount: int) -> dict:
    return {
        "id": li_id,
        "item": {"id": item_id, "title": title, "price": amount},
        "quantity": 1,
        "totals": [
            {"type": "subtotal", "amount": amount},
            {"type": "total", "amount": amount},
        ],
    }


def order_line(li_id: str, item_id: str, title: str, amount: int) -> dict:
    return {
        "id": li_id,
        "item": {"id": item_id, "title": title, "price": amount},
        "quantity": {"original": 1, "total": 1, "fulfilled": 0},
        "totals": [
            {"type": "subtotal", "amount": amount},
            {"type": "total", "amount": amount},
        ],
        "status": "processing",
    }


# ---------------------------------------------------------------- Example 1
def build_example1() -> None:
    ev = EX1 / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    src = pathlib.Path.home() / "workspace" / "einvoice-verify" / "sample_signed_qrcode.txt"
    artifact = src.read_text().strip()
    (ev / "signed_qr_code.jwt.txt").write_text(artifact + "\n")

    header_b64, payload_b64, _sig = artifact.split(".")
    header = json.loads(b64u_decode(header_b64))
    payload = json.loads(b64u_decode(payload_b64))
    data = json.loads(payload["data"])
    assert header["alg"] == "RS256" and payload["iss"] == "NIC"

    # NIC's published IRP public key (bare SubjectPublicKeyInfo, base64),
    # as printed in the QR code procedure document.
    key_b64 = (
        "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArxd93uLDs8HTPqcSPpxZrf0"
        "Dc29r3iPp0a8filjAyeX4RAH6lWm9qFt26CcE8ESYtmo1sVtswvs7VH4Bjg/FDlRpd+MnAlX"
        "uxChij8/vjyAwE71ucMrmZhxM8rOSfPML8fniZ8trr3I4R2o4xWh6no/xTUtZ02/yUEXbphw3"
        "DEuefzHEQnEF+quGji9pvGnPO6Krmnri9H4WPY0ysPQQQd82bUZCk9XdhSZcW/am8w"
        "BulYokITRMVHlbRXqu1pOFmQMO5oSpyZU3pXbsx+OxIOc4EDX0WMa9aH4+snt18WA"
        "XVGwF2B4fmBk7AtmkFzrTmbpmyVqA3KO2IjzMZPw0hQIDAQAB"
    )
    der = base64.b64decode(key_b64)
    pem = serialization.load_der_public_key(der).public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (ev / "irp_public_key.pem").write_bytes(pem)
    # Verifier trust configuration is independent of the evidence bundle:
    # the harness loads keys from validation/trust_keys, never from an
    # example's evidence folder (lead's Gate 1 review, item 1).
    TRUST_DIR.mkdir(parents=True, exist_ok=True)
    (TRUST_DIR / "nic_irp_public_key.pem").write_bytes(pem)
    dump(ev / "signed_qr_code.decoded.json", {"header": header, "payload": payload, "data": data})

    total_minor = int(data["TotInvVal"]) * 100  # QR TotInvVal is in rupees
    dd, mm, yyyy = data["DocDt"].split("/")
    issue_date = f"{yyyy}-{mm}-{dd}"
    amount = total_minor
    li = "li_1"
    title = f"Goods as invoiced on {data['DocNo']} (main HSN {data['MainHsnCode']})"
    reference = [{
        "line_item_id": li,
        "document": {
            "number": data["DocNo"],
            "type": data["DocTyp"],
            "issuer_tax_identity": data["SellerGstin"],
            "issue_date": issue_date,
            "total": total_minor,
        },
        "registration": {
            "scheme": "in_gst_einvoice_irp",
            "identifier": data["Irn"],
            "artifact_digest": sha256_tag(artifact.encode()),
            # No registered_at: the signed QR payload carries no registration
            # time at usable precision (see fixture notes).
        },
        "status": {
            "value": "not_established",
            "observed_at": "2020-08-06T09:00:00+05:30",
        },
    }]
    checkout = {
        "ucp": ucp_block(for_order=False, with_ap2=False),
        "id": "chk_example1_operator_sample",
        "status": "completed",
        "currency": "INR",
        "line_items": [checkout_line(li, "item_" + data["MainHsnCode"], title, amount)],
        "totals": [
            {"type": "subtotal", "amount": amount},
            {"type": "total", "amount": amount},
        ],
        "links": [{"type": "terms_of_service", "url": "https://example.com/terms"}],
        "invoice_reference": reference,
    }
    order = {
        "ucp": ucp_block(for_order=True, with_ap2=False),
        "id": "ord_example1_operator_sample",
        "checkout_id": checkout["id"],
        "permalink_url": "https://example.com/orders/ord_example1_operator_sample",
        "currency": "INR",
        "line_items": [order_line(li, "item_" + data["MainHsnCode"], title, amount)],
        "fulfillment": {"expectations": []},
        "totals": [
            {"type": "subtotal", "amount": amount},
            {"type": "total", "amount": amount},
        ],
        "invoice_reference": json.loads(json.dumps(reference)),
    }
    dump(EX1 / "checkout.json", checkout)
    dump(EX1 / "order.json", order)
    print("example 1 written; IRN", data["Irn"])


# ---------------------------------------------------------------- Example 2
def build_example2() -> None:
    ev = EX2 / "evidence"
    ev.mkdir(parents=True, exist_ok=True)

    seller_gstin = "29ABCDE1234F1Z5"   # synthetic (dummy PAN pattern)
    buyer_gstin = "29PQRST6789K1Z2"    # synthetic
    doc_no = "EXMPL/2026-27/0042"
    doc_typ = "INV"
    fy = "2026-27"
    issue_date = "2026-11-20"
    total_major = 118000
    total_minor = total_major * 100
    # IRN computed as the scheme documents its inputs: a SHA-256 hash of
    # GSTIN + financial year + document type + document number (simulated).
    irn = hashlib.sha256((seller_gstin + fy + doc_typ + doc_no).encode()).hexdigest()
    registered_at = "2026-11-20T10:15:23+05:30"
    captured_at = "2026-11-20T15:42:10+05:30"
    status_observed_at = "2026-11-21T09:00:00+05:30"

    # Simulated IRP key (RSA-2048, RS256, as the real scheme uses).
    irp_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    irp_pub_pem = irp_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (ev / "simulated_irp_public_key.pem").write_bytes(irp_pub_pem)
    TRUST_DIR.mkdir(parents=True, exist_ok=True)
    (TRUST_DIR / "simulated_irp_public_key.pem").write_bytes(irp_pub_pem)

    def rs256_jwt(header: dict, payload: dict, key) -> str:
        signing_input = (
            b64u(json.dumps(header, separators=(",", ":")).encode())
            + "."
            + b64u(json.dumps(payload, separators=(",", ":")).encode())
        )
        sig = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
        return signing_input + "." + b64u(sig)

    artifact_payload = {
        "iss": "SIMULATED-IRP",
        "AckNo": "SIMACK202611200042",
        "AckDt": registered_at,
        "Irn": irn,
        "data": {
            "SellerGstin": seller_gstin,
            "BuyerGstin": buyer_gstin,
            "DocNo": doc_no,
            "DocTyp": doc_typ,
            "DocDt": "20/11/2026",
            "TotInvVal": total_major,
            "ItemCnt": 1,
            "MainHsnCode": "84713010",
        },
    }
    artifact = rs256_jwt({"alg": "RS256", "typ": "JWT", "kid": "simulated-irp-key-1"},
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
    status_jws = rs256_jwt({"alg": "RS256", "typ": "JWT", "kid": "simulated-irp-key-1"},
                           status_claims, irp_key)
    dump(ev / "status_evidence.json", {
        "simulated": True,
        "format": "Signed status response (compact JWS, RS256) from the scheme, "
                  "simulated for this example. A live integration supplies the "
                  "scheme's own authenticated status response in this place.",
        "claims": status_claims,
        "jws": status_jws,
        "verification_key": "simulated_irp_public_key.pem",
    })

    li = "li_1"
    title = "Industrial controller unit, as invoiced"
    reference = [{
        "line_item_id": li,
        "document": {
            "number": doc_no,
            "type": doc_typ,
            "issuer_tax_identity": seller_gstin,
            "issue_date": issue_date,
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
        "status": {
            "value": "active",
            "observed_at": "2026-11-20T15:40:00+05:30",
        },
    }]
    checkout = {
        "ucp": ucp_block(for_order=False, with_ap2=True),
        "id": "chk_example2_synthetic",
        "status": "completed",
        "currency": "INR",
        "line_items": [checkout_line(li, "item_controller_unit", title, total_minor)],
        "totals": [
            {"type": "subtotal", "amount": total_minor},
            {"type": "total", "amount": total_minor},
        ],
        "links": [{"type": "terms_of_service", "url": "https://example.com/terms"}],
        "invoice_reference": reference,
    }

    # AP2 mandate extension merchant authorization: detached JWS (ES256)
    # over the JCS-canonicalized checkout excluding `ap2`.
    merchant_key = ec.generate_private_key(ec.SECP256R1())
    pub_numbers = merchant_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": b64u(pub_numbers.x.to_bytes(32, "big")),
        "y": b64u(pub_numbers.y.to_bytes(32, "big")),
        "kid": "merchant-simulated-key-1",
        "use": "sig",
        "alg": "ES256",
    }
    dump(ev / "merchant_public_key.jwk.json", jwk)
    dump(TRUST_DIR / "merchant_public_key.jwk.json", jwk)
    canonical = rfc8785.dumps(checkout)
    header = {"alg": "ES256", "kid": "merchant-simulated-key-1"}
    signing_input = b64u(json.dumps(header, separators=(",", ":")).encode()) + "." + b64u(canonical)
    der_sig = merchant_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    detached = signing_input.split(".")[0] + ".." + b64u(raw_sig)
    checkout["ap2"] = {"merchant_authorization": detached}

    order = {
        "ucp": ucp_block(for_order=True, with_ap2=False),
        "id": "ord_example2_synthetic",
        "checkout_id": checkout["id"],
        "permalink_url": "https://example.com/orders/ord_example2_synthetic",
        "currency": "INR",
        "line_items": [order_line(li, "item_controller_unit", title, total_minor)],
        "fulfillment": {"expectations": []},
        "totals": [
            {"type": "subtotal", "amount": total_minor},
            {"type": "total", "amount": total_minor},
        ],
        "invoice_reference": json.loads(json.dumps(reference)),
    }
    dump(EX2 / "checkout.json", checkout)
    dump(EX2 / "order.json", order)

    dump(ev / "payment_event.json", {
        "simulated": True,
        "kind": "provider_capture_confirmation",
        "format": "Simulated provider-confirmed capture, in the documented "
                  "Gate 1 format (specification section 7). A live integration "
                  "supplies the payment provider's own authenticated capture "
                  "confirmation in this place.",
        "provider": "Simulated Payments Provider",
        "payment_id": "pay_SIMULATED_0001",
        "checkout_id": checkout["id"],
        "status": "captured",
        "amount": total_minor,
        "currency": "INR",
        "captured_at": captured_at,
    })

    # Verifier configuration, held independently of the evidence bundle:
    # which keys are trusted for which example, and the payment
    # identifier the verifier expects for Example 2's checkout (from the
    # payment integration, not from the capture evidence itself).
    dump(ROOT / "validation" / "trust_config.json", {
        "example1": {"irp_public_key": "trust_keys/nic_irp_public_key.pem"},
        "example2": {
            "irp_public_key": "trust_keys/simulated_irp_public_key.pem",
            "merchant_public_key": "trust_keys/merchant_public_key.jwk.json",
            "expected_payment_id": "pay_SIMULATED_0001",
        },
    })
    print("example 2 written; IRN", irn)


if __name__ == "__main__":
    build_example1()
    build_example2()
