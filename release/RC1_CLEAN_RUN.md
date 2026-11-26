# RC1 clean run — record

**Archive:** `invoice-registration-reference-rc1.zip`
**SHA-256:** `6379813264631011e76cae00093d27152d49e44bceafdc5e9e6494caf22f7275`
**Commit:** `3bfd9b2` ("RC1: documented AckDt format, capture-authentication
wording, release decision and notices"), on top of Gate 2 `11b4ea4`.
**Run:** 26 November 2026, from the exact archive above — fresh
extraction into an empty directory, fresh Python virtual environment,
no repository state carried over.

## Commands and results

```sh
unzip invoice-registration-reference-rc1.zip
python3 -m venv venv
pip install -r verifier/requirements.txt
#   cryptography 50.0.2, jsonschema 4.26.0, rfc8785 0.1.4

python3 -m unittest discover -s verifier/tests
#   Ran 22 tests — OK

python3 validation/validate_gate1.py
#   36 PASS, 0 FAIL (published schemas resolved from the pinned
#   cache in validation/schema_cache; no network needed)

python3 verifier/invoice_reference_verifier.py
#   Example 1: established / not_established / not_established
#   Example 2: established / established / established
#   Example 3: established / established / established
```

**Result: the exact RC1 archive passes a clean run.** This record is
committed after the RC1 commit it describes, so the archive does not
contain it; the archive is identified by the SHA-256 above.
