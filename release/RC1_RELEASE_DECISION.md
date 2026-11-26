# Release decision — RC1 (for Gate 3 approval)

**Status: tooling decided; publication NOT approved.** On 26 November
2026 Arjun approved **Option A** (below): Python is the reference
implementation for the first release. That approval covers the
tooling only. Repository publication, GitHub Pages, and package
publication each remain separate decisions, none of them taken; the
repository stays private and local. (This document was drafted for
RC1; RC2 supersedes RC1 as the candidate — see
`release/RC2_CLEAN_RUN.md`.)

## What RC1 is

The repository at the RC1 commit (see `release/RC1_CLEAN_RUN.md` for
the commit and the archive's SHA-256), packaged as
`invoice-registration-reference-rc1.zip`: specification, capability
definition, reference verifier, conformance suite, three examples,
research reports, validation harness with its pinned schema cache,
licence and third-party notices.

## Recommended first release (lead's recommendation, adopted here)

1. **The public repository** — the full RC1 tree, under the
   agorail-labs organisation, Apache-2.0.
2. **GitHub Pages** serving the schema and specification documents,
   so the capability name `io.github.agorail-labs.shopping.
   invoice_reference` gains the authority binding it currently lacks
   (specification section 10).
3. Positioned as an **offline reference**: a specification, a
   definition that passes the official UCP tooling, and a reference
   verifier with a conformance suite. No live scheme or provider
   integration is claimed; status and payment evidence are the
   documented simulated formats.

## Explicitly NOT in the first release

- **No package publication** (npm or PyPI). Package publication is a
  separate decision, taken after the repository and Pages release,
  and is not approved by approving this document.
- No UCP proposal, issue or PR upstream; no announcement. Those are
  separate acts with their own approvals.

## The tooling deviation — decision required

The approved build (build order v2, "the organisation's layout,
licence and tooling") inherits the agorail-labs convention from SCQ
and MSE: **TypeScript and npm**. The delivered verifier, example
builders and validation harness are **Python**. That deviation was
not flagged at Gate 1 or Gate 2 and is flagged now, before any
approval:

- **Option A — approve the Python reference implementation as the
  released tooling** for the first release. Rationale: the release is
  an offline reference; the verifier is a single readable module with
  three common dependencies; the conformance suite runs anywhere
  Python 3.11+ runs. The npm package decision stays separate and can
  still choose a TypeScript port later.
- **Option B — port the verifier to TypeScript/npm before any
  release.** The repository and Pages release can still proceed on
  the specification and definition, with the verifier marked
  Python-reference-only until the port lands.

**Recommendation: Option A**, with the package decision kept
separate either way. **Decided 26 November 2026: Arjun approved
Option A** — Python is the reference implementation for the first
release. The approval is for the Python implementation only;
repository publication, Pages, and package publication remain
separate decisions.

## Release claims settled before RC1

- **AckDt format named and proven.** Example 3 uses the IRP's
  documented format `yyyy-MM-dd HH:mm:ss` (NIC Generate IRN
  specification; ClearTax's published IRP response example,
  `"AckDt": "2023-10-26 14:28:00"`). The earlier AM/PM rendering was
  not a documented IRP format and has been removed from the fixture
  and from every claim. The parser's behaviour on the documented
  offset-free form is tested with and without the configured
  timezone (established / not established).
- **Capture authentication is explicit** in the specification
  (section 7), the README, the verifier's own documentation and the
  evidence register: field matching binds, it does not authenticate;
  a live verdict requires capture evidence authenticated by the
  caller's payment integration; the simulated format is
  unauthenticated by construction.
- **Upstream licensing retained.** `THIRD_PARTY_NOTICES.md` covers
  the vendored UCP schemas (Apache-2.0, pinned cache) and the NIC
  published sample and key, with provenance.

## Clean-run requirement

Gate 3 approval is contingent on the exact candidate archive passing
a clean run: fresh extraction, fresh virtual environment,
dependencies from `verifier/requirements.txt`, the verifier suite
(22 tests at RC1; 27 at RC2, which adds file-based end-to-end
regressions for the four binding verdict cases) and the 36-check
Gate 1 harness, all passing with no network access required. The
runs and their results are recorded in `release/RC1_CLEAN_RUN.md`
and `release/RC2_CLEAN_RUN.md`.
