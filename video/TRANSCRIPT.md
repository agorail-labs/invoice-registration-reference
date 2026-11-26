# Narration transcript — "Agorail: When an AI Agent Pays an Invoice, What Proves It Was Real?"

Full video: `dist/irr-demo.mp4` (82.87 s, 1920×1080, narrated).
Voice: synthesized (Helio), English. Captions: `dist/captions.vtt`
(19 cues, timed from the actual segment durations).

## S1 — The problem

An AI agent is told: pay this invoice. In a UCP checkout, paying is
easy. Proving what was paid is not. Was the invoice really registered
with the tax authority? Was that registration still active when the
money moved? And did the business sign this checkout?

## S2 — The reference, on complete evidence

The Invoice Registration Reference adds one capability to checkout
and order: a reference to the invoice and its registration, checkable
against the scheme's own signed evidence. Run the verifier on a
complete synthetic case, and all three questions come back
established, each with its reason.

## S3 — The honest gap, on a real signed sample

Now the real thing: the tax authority's own published, signed sample.
The verifier confirms the registration matches the invoice. But the
sample carries no payment evidence, so was it active at payment? Not
established. The verifier says what the evidence proves, and no more.

## S4 — When the evidence turns

And when the evidence turns, so does the verdict. In a separate
synthetic test, the signed status says the registration was cancelled
before the payment event. Active at payment: contradicted, with the cancellation named
as the reason. Three verdicts, three values: established, not
established, contradicted.

## S5 — Call to action

Read the specification, and run the verifier yourself. The repository
is public, and the schema is live on GitHub Pages. The demo uses simulated registration
status and payment capture evidence. Live integrations supply
authenticated evidence.
