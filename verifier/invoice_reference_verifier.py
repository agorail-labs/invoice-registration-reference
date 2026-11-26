#!/usr/bin/env python3
"""Gate 2 verifier for the Invoice Registration Reference v0.1.

Computes the specification's three verdicts (section 8) from actual
inputs -- nothing is fixed or precomputed:

  verify(checkout, order, bundle, config) -> {
      "valid": bool,                      # structural rules 1, 2, 4, 6
      "violations": [str, ...],
      "verdicts": {
          "registration_matches_invoice":   {"verdict": ..., "reason": ...},
          "registration_active_at_payment": {"verdict": ..., "reason": ...},
          "signed_by_checkout_business":    {"verdict": ..., "reason": ...},
      },
  }

Inputs
------
checkout, order : the final checkout as accepted for completion, and
    the order carrying the snapshot (parsed JSON dicts).
bundle : {
    "artifact": compact JWS string of the scheme's signed artifact, or
        None,
    "status_evidence": the documented simulated status format (a dict
        with a "jws" compact JWS) or None,
    "payment_event": the documented simulated capture format or None,
    "lookup_outcome": optional str -- "timeout" / "unavailable" /
        "refused" records a failed lookup; it is never evidence.
}
config : VerifierConfig -- trust held independently of the bundle:
    scheme_public_key (RSA), merchant_public_key (EC) or None,
    expected_payment_id or None, scheme_timezone (IANA name) or None,
    no_reinstatement_rule (documented for in_gst_einvoice_irp, spec
    section 9; a verified status response's scheme_rule may also
    supply it).

Verdicts follow specification section 8 exactly, including: digest
over the compact JWS ASCII bytes; only verified status claims are
evaluated; capture binding (checkout id, expected payment id, amount,
currency) gates the active-at-payment verdict; order.checkout_id is
checked alongside snapshot equality for the signature verdict;
offset-free scheme timestamps (IRP AckDt) order only under the
configured documented timezone; conflicting authenticated evidence is
not established; a timeout/refusal/"not available" is never
contradicted.

Scope is v0.1: scheme in_gst_einvoice_irp, simulated status/payment
formats. This module is the reference verifier, not a production
service.

Capture authentication: the field matching in this module (checkout
id, expected payment id, amount, currency) BINDS capture evidence to
the transaction; it does not AUTHENTICATE it. A live verdict requires
capture evidence authenticated by the caller's payment integration.
The simulated capture format is unauthenticated by construction.
"""
import base64
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

ESTABLISHED = "established"
NOT_ESTABLISHED = "not_established"
CONTRADICTED = "contradicted"


@dataclass
class VerifierConfig:
    scheme_public_key: object = None          # RSA public key
    merchant_public_key: object = None        # EC public key or None
    expected_payment_id: str = None
    scheme_timezone: str = None               # e.g. "Asia/Kolkata"
    no_reinstatement_rule: bool = True        # spec section 9 (GSTN FAQ v1.4 Q91)


def b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parse_time(value):
    """Parse a timestamp. Returns (datetime, had_offset) or (None, False).

    Accepted forms: RFC 3339 (the reference's own timestamps and the
    simulated formats); the IRP's documented AckDt format
    "yyyy-MM-dd HH:mm:ss" (e.g. "2026-11-20 10:15:23" -- NIC's
    Generate IRN specification; ClearTax's published IRP response
    example shows "2023-10-26 14:28:00"), which carries no offset; and
    the IRP's dd/MM/yyyy date forms. A dd/MM/yyyy hh:mm:ss AM/PM
    rendering is also tolerated by the strptime fallbacks below, but
    it is NOT a documented IRP format and no claim in this repository
    rests on it.
    """
    if not value or not isinstance(value, str):
        return None, False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt, dt.tzinfo is not None
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt), False
        except ValueError:
            continue
    return None, False


def aware_time(value, config: VerifierConfig):
    """A timestamp usable for ordering: aware, applying the configured
    documented scheme timezone to offset-free scheme times. Returns
    None when the time cannot be ordered (spec section 8.4)."""
    dt, had_offset = parse_time(value)
    if dt is None:
        return None
    if had_offset:
        return dt
    if config.scheme_timezone:
        return dt.replace(tzinfo=ZoneInfo(config.scheme_timezone))
    return None


def verify_rs256(token: str, key) -> dict:
    h, p, s = token.split(".")
    key.verify(b64u_decode(s), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return json.loads(b64u_decode(p))


def artifact_fields(payload: dict) -> dict:
    """Flatten a signed artifact payload: fields may sit at the top
    level (Example 2's simulation), inside a nested `data` object
    (production IRP shape, Example 3), or inside a `data` JSON string
    (the published signed QR code, Example 1).

    The signed invoice's own structure nests the compared fields one
    level deeper -- DocDtls (No/Typ/Dt), SellerDtls (Gstin), ValDtls
    (TotInvVal); those are mapped onto the flat names the comparison
    uses. (RC3 blocker 4: a DocDtls.No that differed from the
    reference previously went unseen and matches was established.)"""
    fields = dict(payload)
    data = payload.get("data")
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (ValueError, TypeError):
            data = None
    if isinstance(data, dict):
        merged = dict(data)
        merged.update({k: v for k, v in payload.items() if k != "data" and v is not None})
        fields = merged
    doc_dtls = fields.get("DocDtls")
    if isinstance(doc_dtls, dict):
        fields.setdefault("DocNo", doc_dtls.get("No"))
        fields.setdefault("DocTyp", doc_dtls.get("Typ"))
        fields.setdefault("DocDt", doc_dtls.get("Dt"))
    seller_dtls = fields.get("SellerDtls")
    if isinstance(seller_dtls, dict):
        fields.setdefault("SellerGstin", seller_dtls.get("Gstin"))
    val_dtls = fields.get("ValDtls")
    if isinstance(val_dtls, dict):
        fields.setdefault("TotInvVal", val_dtls.get("TotInvVal"))
    return fields


def structural_violations(checkout: dict, order: dict) -> list:
    """Rules 1, 2, 4, 6 (spec section 6), decidable from the payloads."""
    v = []
    refs = checkout.get("invoice_reference") or []
    li = {x["id"]: x for x in checkout.get("line_items", [])}
    seen_lines, seen_irns, seen_docs = set(), set(), set()
    for r in refs:
        if r.get("line_item_id") in seen_lines or r.get("line_item_id") not in li:
            v.append(f"rule 1: line item {r.get('line_item_id')!r} referred twice or unknown")
        seen_lines.add(r.get("line_item_id"))
        reg = r.get("registration")
        if reg:
            if reg["identifier"] in seen_irns:
                v.append("rule 1: same registration identifier on two lines")
            seen_irns.add(reg["identifier"])
            if "status" not in r:
                v.append("rule 6: registration present without a status")
        doc_key = (r["document"]["number"], r["document"]["issuer_tax_identity"])
        if doc_key in seen_docs:
            v.append("rule 1: same document on two lines")
        seen_docs.add(doc_key)
        alloc = r.get("allocation")
        if alloc and alloc["balance_after"] != alloc["balance_before"] - alloc["amount_applied"]:
            v.append("rule 4: declared balance arithmetic does not hold")
    def total_of(payload):
        return [t["amount"] for t in payload.get("totals", []) if t["type"] == "total"][0]
    li_total = {x["id"]: [t["amount"] for t in x["totals"] if t["type"] == "total"][0]
                for x in checkout.get("line_items", [])}
    applied = [(r.get("allocation", {}).get("amount_applied", li_total.get(r["line_item_id"])))
               for r in refs]
    if any(li_total.get(r["line_item_id"]) != a for r, a in zip(refs, applied)):
        v.append("rule 2: an invoice line total does not equal the amount applied to it")
    if refs and sum(applied) != total_of(checkout):
        v.append("rule 2: invoice lines do not sum to the checkout total")
    return v


def _verdict(verdict: str, reason: str) -> dict:
    return {"verdict": verdict, "reason": reason}


def verify(checkout: dict, order: dict, bundle: dict, config: VerifierConfig) -> dict:
    violations = structural_violations(checkout, order)
    refs = checkout.get("invoice_reference") or []
    if violations or not refs:
        reason = "; ".join(violations) or "no invoice_reference present"
        return {
            "valid": False,
            "violations": violations,
            "verdicts": {
                "registration_matches_invoice": _verdict(NOT_ESTABLISHED, f"input invalid: {reason}"),
                "registration_active_at_payment": _verdict(NOT_ESTABLISHED, f"input invalid: {reason}"),
                "signed_by_checkout_business": _verdict(NOT_ESTABLISHED, f"input invalid: {reason}"),
            },
        }

    # ---- verified status claims (only the verified claims are read)
    status_claims = None
    status_note = None
    sev = bundle.get("status_evidence")
    if sev and sev.get("jws"):
        try:
            status_claims = verify_rs256(sev["jws"], config.scheme_public_key)
        except (InvalidSignature, ValueError, KeyError):
            status_note = "status evidence signature does not verify under the configured scheme key"
    elif bundle.get("lookup_outcome"):
        status_note = f"status lookup outcome: {bundle['lookup_outcome']} (not evidence)"
    else:
        status_note = "no authenticated status evidence supplied"

    # ---- per-entry verdicts for matches and active-at-payment
    matches_results, active_results = [], []
    for ref in refs:
        matches_results.append(_matches(ref, bundle, status_claims, config))
        active_results.append(_active(ref, checkout, bundle, status_claims, status_note, config))

    signed = _signed_by_business(checkout, order, config)
    return {
        "valid": True,
        "violations": [],
        "verdicts": {
            "registration_matches_invoice": _aggregate(matches_results),
            "registration_active_at_payment": _aggregate(active_results),
            "signed_by_checkout_business": signed,
        },
    }


def _aggregate(results: list) -> dict:
    for wanted in (CONTRADICTED, NOT_ESTABLISHED):
        for r in results:
            if r["verdict"] == wanted:
                return r
    return results[0]


def rupees_to_minor(value):
    """Convert a rupee amount to minor units EXACTLY (RC4 check 1).

    int() truncation dropped paise: Rs 118,000.25 became 11,800,000
    instead of 11,800,025, contradicting the exact amount and
    establishing the truncated one. Decimal over the value's string
    form is exact; a value with sub-paise precision converts to None
    (it cannot equal any minor-unit total)."""
    try:
        minor = Decimal(str(value)) * 100
    except (InvalidOperation, ValueError):
        return None
    if minor != minor.to_integral_value():
        return None
    return int(minor)


_DATE_ONLY = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})$")


def is_date_only(value) -> bool:
    """True when a timestamp string states only a date (day precision)."""
    return isinstance(value, str) and bool(_DATE_ONLY.match(value.strip()))


def _matches(ref: dict, bundle: dict, status_claims, config: VerifierConfig) -> dict:
    reg = ref.get("registration")
    if not reg:
        return _verdict(NOT_ESTABLISHED, "no registration in this reference entry")
    # Authoritative absence, evaluated WITH the artifact evidence
    # rather than before it (RC4 check 4): absence alone contradicts,
    # but absence alongside a verified matching invoice is a conflict
    # of authenticated evidence -> not established, conflict reported.
    absence = bool(status_claims) and status_claims.get("status") == "not_found" \
        and status_claims.get("registration_identifier") == reg["identifier"]
    artifact = bundle.get("artifact")
    if not artifact:
        if absence:
            return _verdict(CONTRADICTED,
                            "authoritative negative response of known scope: the scheme "
                            "reports no such registration")
        outcome = bundle.get("lookup_outcome")
        if outcome:
            return _verdict(NOT_ESTABLISHED,
                            f"lookup outcome '{outcome}' is not evidence; no artifact supplied")
        return _verdict(NOT_ESTABLISHED, "no scheme artifact supplied")
    digest = "sha256:" + hashlib.sha256(artifact.strip().encode()).hexdigest()
    if digest != reg["artifact_digest"]:
        return _verdict(NOT_ESTABLISHED,
                        "supplied artifact does not match the reference's artifact_digest")
    try:
        payload = verify_rs256(artifact.strip(), config.scheme_public_key)
    except (InvalidSignature, ValueError, KeyError):
        return _verdict(NOT_ESTABLISHED,
                        "artifact signature does not verify under the configured scheme key")
    f = artifact_fields(payload)
    # RC4 check 3: a match can only be established by an artifact that
    # carries recognizable invoice or QR claims. A validly signed
    # status response supplied in the artifact slot binds none of
    # them, and previously established a match by default.
    if not any(f.get(k) is not None
               for k in ("DocNo", "DocTyp", "SellerGstin", "TotInvVal", "Irn")):
        return _verdict(NOT_ESTABLISHED,
                        "supplied artifact carries no recognizable invoice or "
                        "QR claims; a match cannot be established from it")
    doc = ref["document"]
    mismatches = []
    def cmp_field(name, artifact_value, ref_value):
        if artifact_value is not None and str(artifact_value) != str(ref_value):
            mismatches.append(f"{name}: artifact {artifact_value!r} != reference {ref_value!r}")
    cmp_field("document number", f.get("DocNo"), doc["number"])
    cmp_field("document type", f.get("DocTyp"), doc["type"])
    cmp_field("issuer tax identity", f.get("SellerGstin"), doc["issuer_tax_identity"])
    doc_dt, _ = parse_time(f.get("DocDt")) if f.get("DocDt") else (None, False)
    if doc_dt is not None and doc_dt.date().isoformat() != doc["issue_date"]:
        mismatches.append(f"issue date: artifact {f.get('DocDt')!r} != reference {doc['issue_date']!r}")
    if f.get("TotInvVal") is not None and rupees_to_minor(f["TotInvVal"]) != doc["total"]:
        mismatches.append(f"total: artifact {f['TotInvVal']!r} (rupees) != reference {doc['total']!r} (minor units)")
    cmp_field("registration identifier", f.get("Irn"), reg["identifier"])
    if mismatches:
        return _verdict(CONTRADICTED, "verified mismatch -- " + "; ".join(mismatches))
    if absence:
        return _verdict(NOT_ESTABLISHED,
                        "conflicting authenticated evidence: the verified artifact "
                        "establishes this registration and an authoritative response "
                        "reports no such registration for the same identifier; the "
                        "conflict is reported and neither side is preferred")
    return _verdict(ESTABLISHED,
                    "artifact signature verifies and every field the artifact binds matches")


def _active(ref: dict, checkout: dict, bundle: dict, status_claims, status_note,
            config: VerifierConfig) -> dict:
    reg = ref.get("registration")
    if not reg:
        return _verdict(NOT_ESTABLISHED, "no registration in this reference entry")
    pay = bundle.get("payment_event")
    if not pay:
        return _verdict(NOT_ESTABLISHED, "no payment-event evidence supplied")
    total = [t["amount"] for t in checkout["totals"] if t["type"] == "total"][0]
    binding_failures = []
    if pay.get("status") != "captured":
        binding_failures.append("payment event is not a confirmed capture")
    if pay.get("checkout_id") != checkout["id"]:
        binding_failures.append("capture checkout_id does not equal the accepted checkout id")
    if config.expected_payment_id is None:
        # RC3 blocker 3: without an independently configured expected
        # payment identifier the capture cannot be bound at all.
        binding_failures.append("no expected payment identifier is configured; "
                                "the capture cannot be bound to the checkout's payment")
    elif pay.get("payment_id") != config.expected_payment_id:
        binding_failures.append("capture payment_id is not the expected payment identifier")
    if pay.get("amount") != total:
        binding_failures.append("capture amount does not equal the checkout total")
    if pay.get("currency") != checkout["currency"]:
        binding_failures.append("capture currency does not equal the checkout currency")
    if binding_failures:
        return _verdict(NOT_ESTABLISHED,
                        "payment event not bound to the accepted checkout -- "
                        + "; ".join(binding_failures))
    pay_time = aware_time(pay.get("captured_at"), config)
    if pay_time is None:
        return _verdict(NOT_ESTABLISHED, "no trusted payment time supplied")

    # Authenticated registration time: ONLY from an artifact that is
    # bound to this reference (its digest is the reference's
    # artifact_digest and its IRN is the reference's identifier) and
    # whose signature verifies -- and only from that artifact's AckDt.
    # RC3 blocker 1: the reference's own registered_at is the
    # business's statement, never evidence; it supplied the time here
    # before and established this verdict on a claim.
    # RC3 blocker 2: an artifact failing digest or IRN binding
    # previously supplied its AckDt on signature validity alone.
    reg_time = None
    artifact = bundle.get("artifact")
    if artifact:
        digest = "sha256:" + hashlib.sha256(artifact.strip().encode()).hexdigest()
        if digest != reg["artifact_digest"]:
            return _verdict(NOT_ESTABLISHED,
                            "supplied artifact does not match the reference's "
                            "artifact_digest; its timestamps are not evidence "
                            "for this reference")
        try:
            fields = artifact_fields(verify_rs256(artifact.strip(), config.scheme_public_key))
        except (InvalidSignature, ValueError, KeyError):
            return _verdict(NOT_ESTABLISHED, "artifact does not verify; no authenticated registration time")
        if fields.get("Irn") != reg["identifier"]:
            return _verdict(NOT_ESTABLISHED,
                            "supplied artifact binds a different registration "
                            "identifier; its timestamps are not evidence for "
                            "this reference")
        if fields.get("AckDt"):
            if is_date_only(fields["AckDt"]):
                # RC4 check 2 / spec 8.4: a date-only registration
                # time cannot be ordered against a payment event on
                # that date; reading it as midnight invents precision
                # the evidence does not state.
                return _verdict(NOT_ESTABLISHED,
                                "registration time (AckDt) is stated only at day "
                                "precision, so its ordering against the payment "
                                "event is unresolved (spec section 8.4)")
            reg_time = aware_time(fields["AckDt"], config)
            if reg_time is None:
                return _verdict(NOT_ESTABLISHED,
                                "registration time (AckDt) carries no offset and no "
                                "documented scheme timezone is configured, so it "
                                "cannot be ordered against the payment event")
    if reg_time is None:
        return _verdict(NOT_ESTABLISHED,
                        "no authenticated registration time at usable precision "
                        "(the reference's registered_at is a business claim, "
                        "not evidence)")

    if status_claims is None:
        return _verdict(NOT_ESTABLISHED, status_note or "no authenticated status evidence")
    if status_claims.get("registration_identifier") != reg["identifier"]:
        return _verdict(NOT_ESTABLISHED,
                        "status evidence binds a different registration identifier "
                        "than the reference (signature validity is separate)")
    if status_claims.get("status") == "not_found":
        return _verdict(NOT_ESTABLISHED,
                        "the scheme reports no such registration; activity cannot be established")

    cancelled_at = aware_time(status_claims.get("cancelled_at"), config) \
        if status_claims.get("cancelled_at") else None
    observed_at = aware_time(status_claims.get("observed_at"), config) \
        if status_claims.get("observed_at") else None
    no_reinstatement = config.no_reinstatement_rule or \
        "not reinstated" in (status_claims.get("scheme_rule") or "")

    if cancelled_at is not None and cancelled_at <= pay_time \
            and status_claims.get("status") == "active" \
            and observed_at is not None and observed_at >= pay_time:
        return _verdict(NOT_ESTABLISHED,
                        "conflicting authenticated evidence: a cancellation at or "
                        "before the payment event and an active observation at or "
                        "after it are both present")
    if cancelled_at is not None and cancelled_at <= pay_time:
        return _verdict(CONTRADICTED,
                        "authenticated cancellation took effect at or before the payment event")
    if reg_time <= pay_time and cancelled_at is not None and cancelled_at > pay_time:
        return _verdict(ESTABLISHED,
                        "registration time is at or before the payment event and the "
                        "authenticated cancellation falls after it")
    if reg_time <= pay_time and status_claims.get("status") == "active" \
            and observed_at is not None and observed_at >= pay_time and no_reinstatement:
        return _verdict(ESTABLISHED,
                        "registration time is at or before the payment event, an "
                        "authenticated active observation at or after it is present, "
                        "and the scheme's documented rule is that a cancelled "
                        "registration cannot be reinstated")
    return _verdict(NOT_ESTABLISHED,
                    "the authenticated evidence does not establish activity at the payment event")


def _signed_by_business(checkout: dict, order: dict, config: VerifierConfig) -> dict:
    auth = (checkout.get("ap2") or {}).get("merchant_authorization")
    if not auth:
        return _verdict(NOT_ESTABLISHED, "the checkout carries no AP2 merchant authorization")
    if config.merchant_public_key is None:
        return _verdict(NOT_ESTABLISHED, "no merchant key is configured")
    head_b64, _, sig_b64 = auth.partition("..")
    if not sig_b64:
        return _verdict(NOT_ESTABLISHED, "merchant authorization is not a detached JWS")
    signed_checkout = {k: v for k, v in checkout.items() if k != "ap2"}
    canonical = rfc8785.dumps(signed_checkout)
    signing_input = (head_b64 + "." +
                     base64.urlsafe_b64encode(canonical).rstrip(b"=").decode()).encode()
    raw = b64u_decode(sig_b64)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    try:
        config.merchant_public_key.verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return _verdict(NOT_ESTABLISHED,
                        "merchant signature does not verify over the final checkout")
    if order.get("invoice_reference") != checkout.get("invoice_reference"):
        return _verdict(NOT_ESTABLISHED, "the order's snapshot differs from the signed checkout's reference")
    if order.get("checkout_id") != checkout.get("id"):
        return _verdict(NOT_ESTABLISHED, "the order's checkout_id is not the signed checkout's id")
    return _verdict(ESTABLISHED,
                    "merchant signature verifies over the final checkout, the order's "
                    "snapshot equals its reference, and the order names that checkout")


# ------------------------------------------------------------------ config
def load_config(root: pathlib.Path, entry: str) -> VerifierConfig:
    """Build a VerifierConfig from validation/trust_config.json + the
    independently configured key files it names."""
    cfg = json.loads((root / "validation" / "trust_config.json").read_text())[entry]
    scheme_key = serialization.load_pem_public_key(
        (root / "validation" / cfg["irp_public_key"]).read_bytes())
    merchant_key = None
    if cfg.get("merchant_public_key"):
        jwk = json.loads((root / "validation" / cfg["merchant_public_key"]).read_text())
        nums = ec.EllipticCurvePublicNumbers(
            int.from_bytes(b64u_decode(jwk["x"]), "big"),
            int.from_bytes(b64u_decode(jwk["y"]), "big"), ec.SECP256R1())
        merchant_key = nums.public_key()
    return VerifierConfig(
        scheme_public_key=scheme_key,
        merchant_public_key=merchant_key,
        expected_payment_id=cfg.get("expected_payment_id"),
        scheme_timezone=cfg.get("scheme_timezone"),
    )


def load_bundle(example_dir: pathlib.Path) -> dict:
    ev = example_dir / "evidence"
    artifact = None
    for name in ("signed_qr_code.jwt.txt", "scheme_artifact.jwt.txt"):
        if (ev / name).exists():
            artifact = (ev / name).read_text().strip()
    status = json.loads((ev / "status_evidence.json").read_text()) \
        if (ev / "status_evidence.json").exists() else None
    pay = json.loads((ev / "payment_event.json").read_text()) \
        if (ev / "payment_event.json").exists() else None
    return {"artifact": artifact, "status_evidence": status, "payment_event": pay}


def verify_example(root: pathlib.Path, example: str, config_entry: str) -> dict:
    d = root / "examples" / example
    checkout = json.loads((d / "checkout.json").read_text())
    order = json.loads((d / "order.json").read_text())
    return verify(checkout, order, load_bundle(d), load_config(root, config_entry))


if __name__ == "__main__":
    import sys
    root = pathlib.Path(__file__).resolve().parent.parent
    for example, entry in (("example-1-operator-sample", "example1"),
                           ("example-2-synthetic-full", "example2"),
                           ("example-3-production-shaped-irp", "example3")):
        result = verify_example(root, example, entry)
        print(example, json.dumps(result["verdicts"], indent=2))
