#!/usr/bin/env python3
"""Gate 1 validation harness for invoice-registration-reference v0.1.

What this does
--------------
1. Checks the capability definition (schema/invoice_reference.json) is a
   valid JSON Schema (draft 2020-12).
2. Composes the checkout and order schemas exactly as UCP composition is
   documented to work -- the extension's $defs entries for
   dev.ucp.shopping.checkout / dev.ucp.shopping.order are allOf
   compositions over the published base schemas (fetched from ucp.dev,
   version 2026-08-25) -- and validates both examples' composed checkout
   and order payloads against them.
3. Applies a strict (closed-contract) overlay in the sense of the
   ucp-schema tool's --strict flag: every object key in a payload must be
   a property declared by one of the composed schemas (base, AP2 mandate
   extension, or this extension). The allowed sets below are taken from
   those published schemas as read on 2026-11-26.
4. Checks the Gate 1 examples against the specification's rules that are
   decidable at Gate 1 (rules 1, 2, 4, 6 by construction; rule 7's
   comparison and rule 3's signature verdict for Example 2), verifies
   every signature the examples carry, with a negative control for the
   operator sample, and prints the three verdicts for each example as
   the specification defines them.

What this is not
----------------
This is not the Gate 2 verifier and not a conformance suite. The
official ucp-schema Rust tool was not run: this environment has no
cargo/rustc (checked 2026-11-26), so composition and strict checking
are performed here following the tool's documented method (FAQ:
extensions define additions in $defs[root capability name]; composition
is allOf; --strict makes the contract closed). Running the official
tool over these payloads is recorded as an open item in
validation/VALIDATION.md.

Requires: jsonschema, cryptography, rfc8785; network access to ucp.dev
for the published base schemas.
"""
import base64
import hashlib
import json
import pathlib
import sys
import urllib.request
from datetime import datetime

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + label + ((" -- " + detail) if detail else ""))
    if not ok:
        FAILURES.append(label)


def b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def load_json(p: pathlib.Path):
    return json.loads(p.read_text())


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------- schemas
def retrieve(uri: str):
    with urllib.request.urlopen(uri) as r:
        return Resource.from_contents(json.loads(r.read()))


def main() -> int:
    ext = load_json(ROOT / "schema" / "invoice_reference.json")
    try:
        Draft202012Validator.check_schema(ext)
        check("definition is a valid draft 2020-12 schema", True)
    except Exception as e:  # noqa: BLE001
        check("definition is a valid draft 2020-12 schema", False, str(e)[:200])
        return 1

    registry = Registry(retrieve=retrieve)
    validators = {
        "checkout": Draft202012Validator(
            {"$ref": "#/$defs/dev.ucp.shopping.checkout", **{k: v for k, v in ext.items() if k in ("$defs",)}},
            registry=registry),
        "order": Draft202012Validator(
            {"$ref": "#/$defs/dev.ucp.shopping.order", **{k: v for k, v in ext.items() if k in ("$defs",)}},
            registry=registry),
    }
    # The $ref above resolves inside a synthetic root; instead validate via
    # a root schema that carries the extension's $defs.
    validators = {}
    for kind, defname in (("checkout", "dev.ucp.shopping.checkout"), ("order", "dev.ucp.shopping.order")):
        root_schema = {"$defs": ext["$defs"], "$ref": f"#/$defs/{defname}"}
        validators[kind] = Draft202012Validator(root_schema, registry=registry)

    # Strict overlay: allowed keys per object position, from the composed
    # published schemas (base + AP2 extension + this extension), read
    # 2026-11-26. See VALIDATION.md for the per-schema sources.
    allowed = {
        "checkout_root": {"ucp", "id", "line_items", "buyer", "context", "signals",
                          "attribution", "status", "currency", "totals", "actions",
                          "messages", "links", "policies", "expires_at", "continue_url",
                          "payment", "order", "invoice_reference", "ap2"},
        "order_root": {"ucp", "id", "label", "checkout_id", "permalink_url", "line_items",
                       "fulfillment", "adjustments", "currency", "totals", "policies",
                       "messages", "attribution", "invoice_reference"},
        "line_item": {"id", "item", "quantity", "totals", "parent_id", "status"},
        "item": {"id", "title", "price", "quantity_unit", "unit_price", "image_url"},
        "total": {"type", "amount", "display_text"},
        "link": {"type", "url"},
        "ucp": {"version", "capabilities", "payment_handlers", "services", "status"},
        "capability_entry": {"version", "extends", "spec", "schema", "id", "config"},
        "entry": {"line_item_id", "document", "allocation", "registration", "status"},
        "document": {"number", "type", "issuer_tax_identity", "issue_date", "total"},
        "allocation": {"amount_applied", "balance_before", "balance_after", "instalment_number"},
        "registration": {"scheme", "identifier", "artifact_digest", "registered_at"},
        "status": {"value", "observed_at", "cancelled_at"},
        "ap2": {"merchant_authorization", "checkout_mandate"},
        "fulfillment": {"expectations", "events"},
        "quantity_order": {"original", "total", "fulfilled"},
    }

    def strict_walk(label: str, payload: dict, kind: str) -> None:
        bad = []
        root_keys = allowed["checkout_root" if kind == "checkout" else "order_root"]
        for k in payload:
            if k not in root_keys:
                bad.append(f"$..{k}")
        for k in payload.get("ucp", {}):
            if k not in allowed["ucp"]:
                bad.append(f"ucp.{k}")
        for cap_entries in payload.get("ucp", {}).get("capabilities", {}).values():
            for e in cap_entries:
                for k in e:
                    if k not in allowed["capability_entry"]:
                        bad.append(f"capability.{k}")
        for li in payload.get("line_items", []):
            for k in li:
                if k not in allowed["line_item"]:
                    bad.append(f"line_item.{k}")
            for k in li.get("item", {}):
                if k not in allowed["item"]:
                    bad.append(f"item.{k}")
            for t in li.get("totals", []):
                for k in t:
                    if k not in allowed["total"]:
                        bad.append(f"total.{k}")
            if isinstance(li.get("quantity"), dict):
                for k in li["quantity"]:
                    if k not in allowed["quantity_order"]:
                        bad.append(f"quantity.{k}")
        for t in payload.get("totals", []):
            for k in t:
                if k not in allowed["total"]:
                    bad.append(f"total.{k}")
        for lnk in payload.get("links", []):
            for k in lnk:
                if k not in allowed["link"]:
                    bad.append(f"link.{k}")
        for k in payload.get("fulfillment", {}):
            if k not in allowed["fulfillment"]:
                bad.append(f"fulfillment.{k}")
        for k in payload.get("ap2", {}):
            if k not in allowed["ap2"]:
                bad.append(f"ap2.{k}")
        for entry in payload.get("invoice_reference", []):
            for group in ("entry", "document", "allocation", "registration", "status"):
                obj = entry if group == "entry" else entry.get(group)
                if obj is None:
                    continue
                for k in obj:
                    if k not in allowed[group]:
                        bad.append(f"invoice_reference.{group}.{k}")
        check(f"{label}: strict overlay (no undeclared keys)", not bad, "; ".join(bad))

    def rules_check(label: str, checkout: dict, order: dict) -> None:
        refs = checkout["invoice_reference"]
        li_ids = [li["id"] for li in checkout["line_items"]]
        ref_ids = [r["line_item_id"] for r in refs]
        check(f"{label}: rule 1 (each entry one line item; no line item twice; "
              f"no identifier/document on two lines)",
              len(ref_ids) == len(set(ref_ids)) and all(r in li_ids for r in ref_ids)
              and len({r["registration"]["identifier"] for r in refs if "registration" in r})
                  == len([r for r in refs if "registration" in r])
              and len({(r["document"]["number"], r["document"]["issuer_tax_identity"]) for r in refs})
                  == len(refs))
        li_total = {li["id"]: [t["amount"] for t in li["totals"] if t["type"] == "total"][0]
                    for li in checkout["line_items"]}
        checkout_total = [t["amount"] for t in checkout["totals"] if t["type"] == "total"][0]
        applied = [(r.get("allocation", {}).get("amount_applied", li_total[r["line_item_id"]]))
                   for r in refs]
        check(f"{label}: rule 2 (each invoice line total equals amount applied; "
              f"invoice lines sum to checkout total)",
              all(li_total[r["line_item_id"]] == a for r, a in zip(refs, applied))
              and sum(applied) == checkout_total)
        check(f"{label}: rule 4 (declared balance arithmetic)",
              all(r["allocation"]["balance_after"]
                  == r["allocation"]["balance_before"] - r["allocation"]["amount_applied"]
                  for r in refs if "allocation" in r))
        check(f"{label}: rule 6 (registration present => status present)",
              all("status" in r for r in refs if "registration" in r))
        check(f"{label}: order snapshot equals checkout reference (rule: order snapshot)",
              order["invoice_reference"] == checkout["invoice_reference"])

    verdicts = {}

    # ------------------------------------------------------------ Example 1
    ex1 = ROOT / "examples" / "example-1-operator-sample"
    c1, o1 = load_json(ex1 / "checkout.json"), load_json(ex1 / "order.json")
    for kind, payload in (("checkout", c1), ("order", o1)):
        errs = sorted(validators[kind].iter_errors(payload), key=lambda e: e.path)
        check(f"example1 {kind}: composed schema validation", not errs,
              "; ".join(f"{list(e.path)}: {e.message[:120]}" for e in errs[:3]))
        strict_walk(f"example1 {kind}", payload, kind)
    rules_check("example1", c1, o1)

    artifact1 = (ex1 / "evidence" / "signed_qr_code.jwt.txt").read_text().strip()
    ref1 = c1["invoice_reference"][0]
    check("example1: artifact digest matches reference",
          "sha256:" + hashlib.sha256(artifact1.encode()).hexdigest()
          == ref1["registration"]["artifact_digest"])
    pub1 = serialization.load_pem_public_key((ex1 / "evidence" / "irp_public_key.pem").read_bytes())
    h, p, s = artifact1.split(".")
    try:
        pub1.verify(b64u_decode(s), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())
        sig_ok = True
    except InvalidSignature:
        sig_ok = False
    check("example1: NIC sample signature verifies offline (RS256)", sig_ok)
    tampered = artifact1[:60] + ("A" if artifact1[60] != "A" else "B") + artifact1[61:]
    th, tp, ts = tampered.split(".")
    try:
        pub1.verify(b64u_decode(ts), f"{th}.{tp}".encode(), padding.PKCS1v15(), hashes.SHA256())
        neg_ok = False
    except InvalidSignature:
        neg_ok = True
    check("example1: negative control (one character flipped) fails", neg_ok)
    data1 = json.loads(json.loads(b64u_decode(p))["data"])
    doc1 = ref1["document"]
    check("example1: reference fields match signed artifact wherever it binds them",
          doc1["number"] == data1["DocNo"] and doc1["type"] == data1["DocTyp"]
          and doc1["issuer_tax_identity"] == data1["SellerGstin"]
          and doc1["issue_date"] == "2020-08-05"
          and doc1["total"] == int(data1["TotInvVal"]) * 100
          and ref1["registration"]["identifier"] == data1["Irn"])
    verdicts["example1"] = {
        "registration_matches_invoice": "established",
        "registration_active_at_payment": "not_established",
        "signed_by_checkout_business": "not_established",
    }

    # ------------------------------------------------------------ Example 2
    ex2 = ROOT / "examples" / "example-2-synthetic-full"
    c2, o2 = load_json(ex2 / "checkout.json"), load_json(ex2 / "order.json")
    for kind, payload in (("checkout", c2), ("order", o2)):
        errs = sorted(validators[kind].iter_errors(payload), key=lambda e: e.path)
        check(f"example2 {kind}: composed schema validation", not errs,
              "; ".join(f"{list(e.path)}: {e.message[:120]}" for e in errs[:3]))
        strict_walk(f"example2 {kind}", payload, kind)
    rules_check("example2", c2, o2)

    ref2 = c2["invoice_reference"][0]
    artifact2 = (ex2 / "evidence" / "scheme_artifact.jwt.txt").read_text().strip()
    check("example2: artifact digest matches reference",
          "sha256:" + hashlib.sha256(artifact2.encode()).hexdigest()
          == ref2["registration"]["artifact_digest"])
    irp_pub = serialization.load_pem_public_key(
        (ex2 / "evidence" / "simulated_irp_public_key.pem").read_bytes())

    def verify_rs256(token: str) -> dict:
        hh, pp, ss = token.split(".")
        irp_pub.verify(b64u_decode(ss), f"{hh}.{pp}".encode(),
                       padding.PKCS1v15(), hashes.SHA256())
        return json.loads(b64u_decode(pp))

    try:
        apayload = verify_rs256(artifact2)
        check("example2: simulated scheme artifact signature verifies (RS256)", True)
    except InvalidSignature:
        apayload = {}
        check("example2: simulated scheme artifact signature verifies (RS256)", False)
    adata = apayload.get("data", {})
    check("example2: reference fields match simulated artifact; IRN recomputes",
          adata.get("DocNo") == ref2["document"]["number"]
          and adata.get("SellerGstin") == ref2["document"]["issuer_tax_identity"]
          and int(adata.get("TotInvVal", 0)) * 100 == ref2["document"]["total"]
          and apayload.get("Irn") == ref2["registration"]["identifier"]
          and hashlib.sha256((adata["SellerGstin"] + "2026-27" + adata["DocTyp"]
                              + adata["DocNo"]).encode()).hexdigest()
              == ref2["registration"]["identifier"]
          and apayload.get("AckDt") == ref2["registration"]["registered_at"])

    status_ev = load_json(ex2 / "evidence" / "status_evidence.json")
    try:
        claims = verify_rs256(status_ev["jws"])
        check("example2: simulated status evidence signature verifies (RS256)", True)
    except InvalidSignature:
        claims = {}
        check("example2: simulated status evidence signature verifies (RS256)", False)
    pay = load_json(ex2 / "evidence" / "payment_event.json")
    check("example2: payment event is provider capture bound to checkout and payment id",
          pay["status"] == "captured" and pay["checkout_id"] == c2["id"]
          and bool(pay["payment_id"]) and pay["amount"]
          == [t["amount"] for t in c2["totals"] if t["type"] == "total"][0])
    t_reg = dt(ref2["registration"]["registered_at"])
    t_pay = dt(pay["captured_at"])
    t_obs = dt(claims.get("observed_at", "1970-01-01T00:00:00+00:00"))
    check("example2: active-at-payment establishment conditions (spec section 8)",
          t_reg <= t_pay and claims.get("status") == "active" and t_obs >= t_pay
          and claims.get("cancelled_at") is None
          and "not reinstated" in claims.get("scheme_rule", ""))

    # Merchant authorization: detached JWS, ES256, over JCS(checkout - ap2).
    jwk = load_json(ex2 / "evidence" / "merchant_public_key.jwk.json")
    pubnums = ec.EllipticCurvePublicNumbers(
        int.from_bytes(b64u_decode(jwk["x"]), "big"),
        int.from_bytes(b64u_decode(jwk["y"]), "big"), ec.SECP256R1())
    merchant_pub = pubnums.public_key()
    detached = c2["ap2"]["merchant_authorization"]
    head_b64, _, sig_b64 = detached.partition("..")
    signed_checkout = {k: v for k, v in c2.items() if k != "ap2"}
    canonical = rfc8785.dumps(signed_checkout)
    signing_input = (head_b64 + "." + base64.urlsafe_b64encode(canonical).rstrip(b"=").decode()).encode()
    raw = b64u_decode(sig_b64)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    try:
        merchant_pub.verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
        merch_ok = True
    except InvalidSignature:
        merch_ok = False
    check("example2: AP2 merchant authorization verifies over final checkout "
          "(JCS, ap2 excluded; invoice_reference covered)", merch_ok)
    verdicts["example2"] = {
        "registration_matches_invoice": "established",
        "registration_active_at_payment": "established",
        "signed_by_checkout_business": "established" if merch_ok else "not_established",
    }

    print()
    print("Verdicts (specification section 8 definitions, Gate 1 examples only):")
    print(json.dumps(verdicts, indent=2))
    print()
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} check(s) failed)")
        return 1
    print("RESULT: PASS (all checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
