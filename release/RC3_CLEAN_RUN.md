# RC3 clean run — record

**Archive:** `invoice-registration-reference-rc3.zip`
**SHA-256:** `d5fb626892f899e7046902b2a672a734e1ab85a82d6a158704a6292e78a9d5a4`
**Commit:** `03efb7d` ("RC3: fix the four publication blockers in the
verifier"), on top of the RC2 clean-run record `b0c4fd5`.
**Run:** 26 November 2026, from the exact archive above — fresh
extraction into an empty directory, fresh Python virtual environment,
no repository state carried over.

## What RC3 changes against RC2

The lead reproduced four verdict defects against RC2 (commit
4996bcb) — the verifier itself changed in RC3 (it was byte-for-byte
identical between RC1 and RC2). The four cases, RC2's returns, and
the required results:

| Case | RC2 returned | Required / RC3 |
| --- | --- | --- |
| Only the checkout supplies `registered_at` | active established | **not established** |
| Timestamp from an artifact failing digest and IRN binding | active established | **not established** |
| No configured expected payment ID | active established | **not established** |
| Nested `DocDtls.No` differs from the reference | matches established | **contradicted** |

Acceptance evidence: the five `RC3Blockers` tests (the four cases
plus the blocker-4 positive control) were run against the RC2
verifier first — **the four blocker tests failed, exactly as
required** — and pass on RC3. The existing 27 tests are unchanged
and still pass. Fixes and mapping: `conformance/CONFORMANCE.md`,
RC3 section; rules stated in specification §8.4.

## Commands and results

```sh
unzip invoice-registration-reference-rc3.zip
python3 -m venv venv
pip install -r verifier/requirements.txt

python3 -m unittest discover -s verifier/tests
#   Ran 32 tests — OK
python3 -m unittest verifier.tests.test_verifier.RC3Blockers
#   Ran 5 tests — OK

python3 validation/validate_gate1.py
#   36 PASS, 0 FAIL (pinned schema cache; no network needed)

python3 verifier/invoice_reference_verifier.py
#   Example 1: established / not_established / not_established
#   Example 2: established / established / established
#   Example 3: established / established / established
```

**Result: the exact RC3 archive passes a clean run.** This record is
committed after the RC3 commit it describes, so the archive does not
contain it; the archive is identified by the SHA-256 above. RC3
supersedes RC2 as the release candidate. Repository publication,
Pages, and package publication remain separate decisions; the
repository stays private.
