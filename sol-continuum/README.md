# SOL Continuum (`c:\sol-systems\sol-continuum`)

**Autonomous Agentic Research, Curriculum Evolution & Scientific Discovery Network Integrated with the SOL Change Observatory (`sol-change`)**

`sol-continuum` is the dedicated workspace in `c:\sol-systems` where specialized SOL agents collaborate as an autonomous research guild to formulate new mathematical/topological conjectures, prove them formally via `conJecture` (`WGSLProofEngine` / `AutomatedProofEngine`), evolve their own competency curricula, and submit frozen baseline-vs-candidate workflow experiments to the **SOL Change Observatory** (`c:\sol-systems\sol-change`).

---

## Core Architecture

1. **Multi-Agent Discovery Guild & Curriculum Memory (`ContinuumAgentGuild`, `ContinuumAgentNode`)**
   - Coordinates five specialized research agents across the SOL Continuum:
     - `Conjecture_Architect` (`conJecture` + `sol-decide`)
     - `Sheaf_Topologist` (`Frontier_OS` + `sol`)
     - `Counterfactual_Skeptic` (`sol-edge` + `sol-decide`)
     - `Substrate_Synthesizer` (`conJecture` WGSL + `Frontier_OS`)
     - `Observatory_Archivist` (`sol-change` + `sol-lens`)
   - Tracks episodic agent competency vectors, theorem proof mastery, falsification survival rates, and **Epistemic Information Gain ($\Delta I_{\text{epistemic}}$)** consolidated into `HippocampalMemorySink`.

2. **Zero-Trust Discovery & Curriculum Gate (`SolEdgeContinuumDiscoveryGate`)**
   - **Cycle 0 (`PolicyStatus.QUARANTINE`, `UNPROVED_CONJECTURE_OR_CURRICULUM_DRIFT`):** Quarantines unverified baseline agentic self-modifications or unproved conjectures where sheaf coboundary defect $\|\delta\psi\|_2 > 0$ or formal theorem status is not `PROVED_THEOREM`.
   - **Cycle 1 (`PolicyStatus.ELIGIBLE`, `CONTINUUM_DISCOVERY_PROVED_AND_VERIFIED`, `COHOMOLOGICAL_QUARANTINE_CLEARED`):** Clears quarantine only when the candidate discovery proposal is formally proved (`PROVED_THEOREM`), epistemic information gain $\Delta I_{\text{epistemic}} > 0$, sheaf coboundary defect $\|\delta\psi\|_2 = 0$, and SOL Change Observatory comparability is `"compatible"`.

3. **Zero-Warning SOL Change Observatory Bridge (`ChangeObservatoryBridge`)**
   - Embeds complete schema-1.0 `observatory_context` (`schema_version: "1.0"`, `input`, `conditions`, `evaluator_version`, `workflow_version`, `executed_at`, `data_type`) directly into `techman.sol-lens.proof-packet/v0.2` packets.
   - Invokes `sol-change`'s `observatory.continuum` (`packet_to_run`, `build_comparison`) and `observatory.domain` (`validate_run`, `validate_archive`, `compare`, `markdown_report`) to produce:
     - Portable experiment bundles under `c:\sol-systems\sol-continuum\experiments\<experiment_id>\` (`baseline.json`, `candidate.json`, `experiment.json`, `comparison.md`, `candidate_proof_packet.json`).
     - Optional registration into `c:\sol-systems\sol-change\data\observatory.sqlite3` via `observatory.store.Store`, strictly preserving `review_status == "awaiting_review"` and `decisions == []` (honoring `sol-change`'s scientific review boundary).
