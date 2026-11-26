# Gate 2 conformance mapping

**Verifier:** `verifier/invoice_reference_verifier.py` — computes the
three verdicts from inputs; nothing is precomputed or fixed.
**Suite:** `verifier/tests/test_verifier.py` (unittest, 22 tests).
**Results:** all 22 tests pass; full output in
`conformance/test-results.txt` (run 26 November 2026). The Gate 1
harness still passes 36/36 (`validation/validation-results.txt`); its
schema fetches now resolve against a pinned cache of the published
schemas (fetched from ucp.dev 2026-11-26, `validation/schema_cache/`)
because the live fetch path intermittently truncates responses.

Every test asserts the verifier's **actual returned verdicts**,
including `not_established` outcomes when a binding fails — the
closure the lead required after the Gate 1 harness's fixed verdict
output.

## The thirteen cases from the build order

| # | Case | Rule / spec | Test | Expected → actual |
| --- | --- | --- | --- | --- |
| 1 | Genuine | Rules 1–8; §8 all verdicts | `test_genuine`; file tests for Examples 2 and 3 | all established → **established** |
| 2 | Mismatch with the signed artifact | §8.1 | `test_mismatch_with_signed_artifact` | matches **contradicted** |
| 3 | Cancelled before the payment event | §8.2 | `test_cancelled_before_payment` | active **contradicted** |
| 4 | Cancelled exactly at it | §8.2 (interval [registered, cancelled) ) | `test_cancelled_exactly_at_payment` | active **contradicted** |
| 5 | Cancelled after it | §8.2 | `test_cancelled_after_payment` | active **established** |
| 6 | Valid signed artifact with only the business's status claim | §4 (status is a claim), §8.2 | `test_valid_artifact_with_only_business_claim` | matches **established**; active **not established** |
| 7 | Lookup failure | §8.1, §8.2 (a timeout is not evidence) | `test_lookup_failure_is_not_established_never_contradicted` | **not established**, never contradicted |
| 8 | Authoritative absence | §8.1 | `test_authoritative_absence_contradicts_matches` | matches **contradicted**; active not established |
| 9 | Status not established | Rule 6, §8.2 | `test_status_not_established` | active **not established**; matches established |
| 10 | Registration without a status | Rule 6 | `test_registration_without_status_is_invalid` | definition rejects the entry; adding `not_established` status validates |
| 11 | The same registration on two lines | Rule 1 | `test_same_registration_on_two_lines` | input **invalid** (rule 1 violation reported) |
| 12 | Allocation that does not add up | Rule 4 | `test_allocation_does_not_add_up` | input **invalid** (rule 4 violation reported) |
| 13 | Signed checkout whose reference changed while the price stayed the same | Rule 7, §8.3 | `test_reference_changed_same_price_signature_verdict_falls` | signed **not established** (signature does not verify) |

## Carried into Gate 2 from the lead's review

| Case | Spec | Test | Expected → actual |
| --- | --- | --- | --- |
| Capture currency mutated (Example 2 files) | §7 binding, §8.2 | `test_capture_currency_mutation_active_not_established` | active **not established**; other verdicts unchanged |
| Capture payment ID mutated | §7 binding, §8.2 | `test_capture_payment_id_mutation_active_not_established` | active **not established** |
| Order `checkout_id` mutated | §8.3 | `test_order_checkout_id_mutation_signed_not_established` | signed **not established**; other verdicts unchanged |
| Validly signed status response for a **different IRN** (same scheme key — signature validity is not the failure) | §7 binding | `test_validly_signed_status_for_different_irn_binds_separately` | active **not established**, reason names the identifier binding; matches stays established |
| Readable `claims` copy tampered, JWS untouched | §7 ("evaluate only the verified claims") | `test_unverified_status_claims_copy_is_never_evaluated` | active stays **established** |
| Production-shaped IRP fixture, AckDt nested and offset-free, **with** configured Asia/Kolkata timezone | §8.4, §9 | `test_example3_production_shaped_with_timezone` | all three **established** |
| Same fixture **without** a configured timezone | §8.4 | `test_example3_without_configured_timezone` | active **not established** (reason: no documented scheme timezone); matches and signed stay established |
| NIC operator sample (Example 1) through the verifier | §8, §9 scope | `test_example1_operator_sample` | matches **established** (documentation vector); active and signed **not established** |

## Notes

- Cases 11 and 12 are input-validity cases: the verifier reports the
  rule violation and returns all three verdicts as not established
  with the violation as the reason, rather than computing verdicts
  over a malformed reference.
- Case 10 is decided by the capability definition itself (the
  `allOf` if/then of rule 6), tested against the definition's entry
  schema directly.
- Deterministic conformance results only. No model-review
  measurements are used or restated here (see
  `validation/VALIDATION.md`, evidence separation).
