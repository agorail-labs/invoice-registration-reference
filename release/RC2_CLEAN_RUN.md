# RC2 clean run — record

**Archive:** `invoice-registration-reference-rc2.zip`
**SHA-256:** `59cd1be238c0da3e870b85d96979516c62938c29f3d71c77561f4e07cb0890d5`
**Commit:** `4996bcb` ("RC2: Option A recorded (Python approved);
file-based end-to-end regressions for the four verdict cases"), on
top of the RC1 clean-run record `ff628f6`.
**Run:** 26 November 2026, from the exact archive above — fresh
extraction into an empty directory, fresh Python virtual environment,
no repository state carried over.

## What RC2 changes against RC1

- **Option A recorded.** Arjun approved Python as the reference
  implementation for the first release (26 November 2026). The
  approval covers tooling only; repository publication, Pages and
  package publication remain separate decisions. The repository
  stays private.
- **The four verdict cases as file-based end-to-end regressions.**
  A dedicated fixture on disk (`validation/regressions/fixture/`)
  with one variant file per broken binding, loaded by the suite and
  run through the shipped verifier: capture currency → active not
  established; capture payment id → active not established; order
  `checkout_id` → signed not established; validly signed status for
  a different IRN → active not established; base → all established.

## Commands and results

```sh
unzip invoice-registration-reference-rc2.zip
python3 -m venv venv
pip install -r verifier/requirements.txt

python3 -m unittest discover -s verifier/tests
#   Ran 27 tests — OK

python3 validation/validate_gate1.py
#   36 PASS, 0 FAIL (pinned schema cache; no network needed)

python3 verifier/invoice_reference_verifier.py
#   Example 1: established / not_established / not_established
#   Example 2: established / established / established
#   Example 3: established / established / established
```

**Result: the exact RC2 archive passes a clean run.** This record is
committed after the RC2 commit it describes, so the archive does not
contain it; the archive is identified by the SHA-256 above. RC2
supersedes RC1 as the release candidate for Gate 3 review.
