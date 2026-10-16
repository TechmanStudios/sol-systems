# Gemini handoff: SOL Change and the SOL continuum

Prepared for the owner on October 15, 2026. This file is a local handoff; no message was sent to Gemini and no future task was scheduled.

## Start here

Read `C:\sol-systems\docs\SOL_NEXT_SESSION_PRIMER.md` for the current Gemini-led continuum work, then this file and `C:\sol-systems\sol-change\docs\CONTINUUM_INTEGRATION.md`.

The owner uses **SOL continuum** to mean the entire `C:\sol-systems` workspace. SOL Change’s application root is **`C:\sol-systems\sol-change`**. Existing work in sibling projects is in progress; this integration does not reset or rewrite it.

## What SOL Change does

SOL Change Observatory v0.2.0 is a local Python-standard-library/SQLite application for comparing versions of workflows and recording a human decision. Its four main screens are experiment list, setup, comparison workspace, and decision record. It preserves imported run source text, criteria revisions, selected run bindings, decision snapshots, and JSON/Markdown exports.

Launch: `C:\sol-systems\sol-change\launch.cmd`. URL: **http://127.0.0.1:8770**. The live SOL server keeps **8765**; this port separation was made specifically for coexistence. No paid calls, external accounts, provider SDKs, or sibling imports are required.

## Working integration already present

- App action **SOL packets** imports two saved `techman.sol-lens.proof-packet/v0.2` primary observations into one experiment.
- `observatory/continuum.py` supplies offline `inventory`, `convert`, and `compare` commands.
- Full original packet text and digest are retained. Each score has an evidence pointer to its original JSON location; source packets can be downloaded from run provenance.
- Raw `/metrics` and normalized `/evaluation/metrics` are supported. Normalized values take precedence when present; conflicts are visible.
- `baseline_evaluation` is preserved as source material and never manufactured into a separately executed baseline.
- Imported scores stay **automated assessments, score/1**. Time, cost, and independent human review remain unknown when not captured.
- An optional context sidecar records exact input, conditions, evaluator/workflow versions, execution timestamp, and declared data origin. Contract: `schemas/continuum-context.schema.json`.
- Upstream `PROMOTE` / `ELIGIBLE` statuses never create a human decision, approval token, or authority to actuate anything.

No producer algorithm, execution gate, ledger, Lens source, or Studio source was changed by this integration. A cross-agent discovery note is saved in `C:\sol-systems\codexWork\SOL_CHANGE_INTEGRATION_2026-10-15.md`.

## Concrete observed result

The local app contains **SOL continuum: packet interoperability check**, importing the saved wormhole and Ricci-surgery packets from `sol-lens/samples/`. It is deliberately an interoperability test. Their different scenarios produce an incompatible-comparison warning; no improvement or adoption verdict is asserted. Original input/evaluation context is missing in those saved files and remains visible. There are no human decisions in that prepared experiment.

Prepared files: `sol-change/data/continuum/packet-intake-2026-10-15/`. Dated inventory: `sol-change/data/continuum/inventory-2026-10-15.json`. These owner trace artifacts remain local and are ignored by Git.

Verification details and the exact test total are in `sol-change/docs/CONTINUUM_VERIFICATION.md`. The bridge and app were tested locally; upstream model calls, mathematical claims, hardware performance, and the whole continuum’s test suite were not independently revalidated by this intake work.

## Proposed next collaboration

Please assess how SOL Change should fit into the continuum and, if the owner asks you to implement the next step:

1. Identify the canonical producer location that can capture two independent runs on the same task. Record exact input, dataset/source identity, controlled conditions, model/workflow version, and evaluator version before comparing results.
2. Prefer a context sidecar or direct run-1.0 exporter initially. The current Lens TypeScript packet type does not declare `observatory_context`; do not assume a new packet field will survive its normalizer.
3. Export observed timings/costs only when genuinely captured, with units and acquisition methods. Preserve source evidence and distinguish simulations, automated ratings, and physical measurements.
4. Consider a small Lens/Studio “Review in SOL Change” saved-artifact handoff. Keep execution, evidence review, software adoption, and physical release authority distinct.
5. Propose a repeat-trial/group contract before adding significance, confidence intervals, or automated “test next” recommendations.

These are open proposals for the owner and Gemini to review. Keep code changes and recommendations grounded in fresh inspection of the active workspace.

## Integration API

`POST http://127.0.0.1:8770/api/continuum/experiments` with JSON:

```json
{
  "title": "Comparison title",
  "proposed_change": "The proposed workflow change",
  "baseline_source_text": "Original first packet JSON as a string",
  "candidate_source_text": "Original second packet JSON as a string",
  "baseline_label": "before-packet.json",
  "candidate_label": "after-packet.json"
}
```

Optional `baseline_context` / `candidate_context` objects use the sidecar schema. Successful intake returns HTTP 201 with the complete experiment, awaiting review and with no human decision. A duplicate comparison returns 409 and preserves existing history. This is a local artifact API; it has no remote fetching or live-agent action endpoint.

From the project root:

```text
python -m unittest discover -s tests -v
node --check static/app.js
python -m observatory.continuum --help
```

On this host, if `python` is unavailable on PATH, the build was checked with `C:\Users\Frankie\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`. The Windows launcher already finds that bundled runtime as a fallback.
