"""Demo driver for the IRR video: real verifier runs, printed plainly.
Uses only the shipped verifier (src/verifier) and the shipped test
Factory for the cancelled-before-payment construction."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(ROOT))

from verifier.invoice_reference_verifier import verify_example, verify  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "test_verifier", ROOT / "verifier" / "tests" / "test_verifier.py")
tv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv)

NAMES = {
    "registration_matches_invoice": "registration matches invoice",
    "registration_active_at_payment": "registration active at payment",
    "signed_by_checkout_business": "signed by checkout business",
}

def show(title, result):
    print(f"== {title}")
    print(f"   structurally valid: {result['valid']}")
    for key, label in NAMES.items():
        v = result["verdicts"][key]
        print(f"   {label:<34} {v['verdict']}")
        print(f"   {'':<34} ({v['reason']})")

show("Example 2 - synthetic full evidence (examples/example-2-synthetic-full)",
     verify_example(ROOT, "example-2-synthetic-full", "example2"))
print()
show("Example 1 - NIC's published signed sample (examples/example-1-operator-sample)",
     verify_example(ROOT, "example-1-operator-sample", "example1"))
print()
f = tv.Factory()
checkout, order, bundle = f.genuine()
bundle["status_evidence"] = f.status(
    status="cancelled", observed_at="2026-11-20T12:00:00+05:30",
    cancelled_at="2026-11-20T12:00:00+05:30")
show("Same case, signed status: cancelled before the payment event",
     verify(checkout, order, bundle, f.config))
