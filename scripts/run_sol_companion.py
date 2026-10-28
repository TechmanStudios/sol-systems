"""
SOL Reflective Physics & Topological Companion CLI (`scripts/run_sol_companion.py`)
===================================================================================
Pairs a live LLM (`gemini-4-argon`, `thinking_level="high"`) with the 12-tool
`SubstrateToolSandbox` (`sol-continuum`, `sol-holo`, `sol-decide`, `Frontier_OS/Exciton-MoA`,
`sol/tools/sol-hippocampus`, `sol/tools/sol-rsi`, and `synThesis`).

Zero background CPU burn when idle — executes on-demand stateful `interactions.create`
turns chained via `previous_interaction_id` with live `function_call` -> `function_result`
dispatch into the SOL substrate.

Usage:
  .\\.venv\\Scripts\\python.exe scripts/run_sol_companion.py
  .\\.venv\\Scripts\\python.exe scripts/run_sol_companion.py "Your scientific or architectural challenge..."
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
for sub_pkg in ("", "sol-holo", "sol-continuum", "sol-decide", "sol-edge/src", "sol-change", "Frontier_OS/Exciton-MoA"):
    pkg_dir = str((ROOT_DIR / sub_pkg).resolve()) if sub_pkg else str(ROOT_DIR)
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)

from sol_continuum.reflective_domain import SACRED_DEFAULT_GRAPH_SHA256, verify_sacred_core_graph_sha256
from sol_continuum.substrate_tools import SUBSTRATE_TOOL_DECLARATIONS, SubstrateToolSandbox
from sol_decide.agentic.live_llm_elicitation import _load_env_safely

LEDGER_JSONL_PATH = ROOT_DIR / "sol-holo" / "packets" / "companion_sessions_ledger.jsonl"
SESSIONS_DOCS_DIR = ROOT_DIR / "docs" / "companion_sessions"

DEFAULT_COMPANION_SYSTEM_INSTRUCTION = (
    "You are an AI operating with the SOL Reflective Physics & Topological Companion Substrate. "
    "Unlike a standard LLM that only predicts tokens, you have direct function-calling access to "
    "12 physical, topological, hippocampal, and sheaf-cohomological substrate tools. "
    "Before answering the user's challenge, invoke the relevant SOL substrate tools to empirically "
    "probe the 140-node manifold, query hippocampal memory/compile concepts, run RSI/LogosVM chambers, "
    "or audit for Vector 0 moment collisions and H^1 sheaf cohomological contradictions. "
    "Ground your final synthesis strictly in the numerical telemetry returned by the substrate."
)

DEFAULT_CHALLENGE = (
    "We are designing a multi-agent scientific reasoning and decision system, but standard LLM ensembles "
    "suffer from three fatal flaws: (1) stateless amnesia across sessions, (2) premature collapse onto a single "
    "hypothesis instead of holding counterfactuals in superposition, and (3) Vector 0 contradiction dilution "
    "(where averaging opposing agent vectors hides a topological conflict, or 4-moment summaries collide on "
    "orthogonal Rademacher signals).\n\n"
    "Use your SOL Companion Substrate tools right now to:\n"
    "1. Query the Hippocampus KB & compile concept topology (`sol_query_kb_hippocampus_and_compile_concepts`),\n"
    "2. Fork the 140-node SOLEngine into a 5-basin wave superposition (`sol_fork_and_rollout_superposition`),\n"
    "3. Run the Vector 0 counterexample & 6D Spectral-Wavelet Prism + H^1 Sheaf audit (`sol_audit_synthesis_counterexamples_and_daosoft_bridge`), and\n"
    "4. Run the Exciton-MoA Snowball + Infinity Node (`sol_run_exciton_snowball_and_paper_synthesis`).\n\n"
    "After inspecting the live tool outputs, explain how the SOL substrate companion paradigm solves all three flaws "
    "using the exact numbers returned by your tool calls."
)


def _slugify(text: str, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return cleaned[:max_len].strip("_") or "companion_session"


def record_companion_session(
    *,
    prompt: str,
    model: str,
    thinking_level: str,
    duration_s: float,
    telemetry: dict,
    slug: str | None = None,
    recorded_at_iso: str | None = None,
) -> tuple[Path, Path]:
    """Persistently record a live companion session to JSONL ledger and Markdown docs."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    iso_ts = recorded_at_iso or now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_prefix = iso_ts[:10]
    session_slug = _slugify(slug or prompt[:64])

    LEDGER_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    # Determine sequence number from existing ledger lines
    existing_count = 0
    if LEDGER_JSONL_PATH.exists():
        existing_lines = [ln for ln in LEDGER_JSONL_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
        existing_count = len(existing_lines)
    seq_num = existing_count + 1

    sacred_immutable, _ = verify_sacred_core_graph_sha256(ROOT_DIR)
    tool_executions = telemetry.get("tool_executions", [])
    tool_names = [tex.get("name") or tex.get("tool_name") for tex in tool_executions]

    md_filename = f"{date_prefix}_session_{seq_num:02d}_{session_slug}.md"
    md_path = SESSIONS_DOCS_DIR / md_filename

    record = {
        "session_index": seq_num,
        "recorded_at": iso_ts,
        "slug": session_slug,
        "markdown_report_path": f"docs/companion_sessions/{md_filename}",
        "model": model,
        "thinking_level": thinking_level,
        "duration_s": round(float(duration_s), 2),
        "interaction_chain": telemetry.get("interaction_chain", []),
        "token_telemetry": {
            "input_tokens": telemetry.get("input_tokens", 0),
            "thought_tokens": telemetry.get("thought_tokens", 0),
            "output_tokens": telemetry.get("output_tokens", 0),
            "cached_input_tokens": telemetry.get("cached_input_tokens", 0),
        },
        "thought_step_count": telemetry.get("thought_step_count", 0),
        "thought_summaries": telemetry.get("thought_summaries", []),
        "tools_invoked": tool_names,
        "tool_executions": [
            {
                "name": tex.get("name") or tex.get("tool_name"),
                "arguments": tex.get("arguments", {}),
                "result_summary": {
                    k: (round(v, 6) if isinstance(v, float) else v)
                    for k, v in (tex.get("result") or {}).items()
                    if isinstance(v, (int, float, bool, str)) and len(str(v)) < 120
                },
            }
            for tex in tool_executions
        ],
        "governance": {
            "allow_production_execution": False,
            "authorized_claimed": False,
            "sacred_core_graph_immutable": sacred_immutable,
            "sacred_core_graph_normlf_sha256": SACRED_DEFAULT_GRAPH_SHA256,
        },
        "prompt": prompt,
        "response_sha256": hashlib.sha256((telemetry.get("content") or "").encode("utf-8")).hexdigest(),
    }

    with LEDGER_JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

    # Build human-readable Markdown report
    md_lines = [
        f"# SOL Companion Session #{seq_num:02d}: `{session_slug}`",
        "",
        f"- **Recorded At (UTC):** `{iso_ts}`",
        f"- **Model:** `{model}` (`thinking_level=\"{thinking_level}\"`)",
        f"- **Wall-Clock Duration:** `{duration_s:.2f}s`",
        f"- **Interaction Chain:** `{json.dumps(telemetry.get('interaction_chain', []))}`",
        f"- **Token Telemetry:** `input={telemetry.get('input_tokens', 0)} | thought={telemetry.get('thought_tokens', 0)} | output={telemetry.get('output_tokens', 0)} | cached={telemetry.get('cached_input_tokens', 0)}`",
        f"- **Sacred Core Graph SHA-256 (`default_graph.json`):** `{SACRED_DEFAULT_GRAPH_SHA256}` (`immutable={sacred_immutable}`)",
        f"- **Governance Invariants:** `allow_production_execution=False`, `authorized_claimed=False`",
        "",
        "## 1. Challenge Prompt",
        "",
        "```text",
        prompt.strip(),
        "```",
        "",
        "## 2. Live Model Thought Summaries",
        "",
    ]
    for idx, ts in enumerate(telemetry.get("thought_summaries", []), 1):
        md_lines.append(f"### Thought Step {idx}")
        md_lines.append(ts.strip())
        md_lines.append("")

    md_lines.extend([
        "## 3. Live Substrate Tool Calls Executed",
        "",
        "| # | Substrate Tool | Arguments | Key Telemetry Summary |",
        "| :---: | :--- | :--- | :--- |",
    ])
    for idx, tex in enumerate(tool_executions, 1):
        tname = tex.get("name") or tex.get("tool_name")
        targs = json.dumps(tex.get("arguments", {}))
        compact_res = {
            k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in (tex.get("result") or {}).items()
            if isinstance(v, (int, float, bool, str)) and len(str(v)) < 60
        }
        res_str = json.dumps(dict(list(compact_res.items())[:8]))
        md_lines.append(f"| {idx} | `{tname}` | `{targs}` | `{res_str}` |")

    md_lines.extend([
        "",
        "## 4. Final Substrate-Grounded Synthesis",
        "",
        (telemetry.get("content") or "").strip(),
        "",
    ])
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return LEDGER_JSONL_PATH, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a live Gemini 4 Argon + 12-Tool SOL Companion Substrate agentic session."
    )
    parser.add_argument("prompt", nargs="?", default=DEFAULT_CHALLENGE, help="Challenge prompt for the LLM + SOL Companion")
    parser.add_argument("--model", default="gemini-4-argon", help="Model ID (default: gemini-4-argon)")
    parser.add_argument("--thinking-level", default="high", choices=["minimal", "low", "medium", "high"])
    parser.add_argument("--max-tool-rounds", type=int, default=3, help="Maximum tool-calling rounds (default: 3)")
    parser.add_argument("--slug", default=None, help="Optional descriptive slug for the recorded session")
    parser.add_argument("--no-record", action="store_true", help="Skip appending to the companion session ledger")
    args = parser.parse_args(argv)

    _load_env_safely()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY / GOOGLE_API_KEY not found in environment or .env.", file=sys.stderr)
        return 1

    from google import genai

    spec = importlib.util.spec_from_file_location("sol_llm_client", ROOT_DIR / "sol" / "tools" / "sol-llm" / "client.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load sol/tools/sol-llm/client.py")
    llm_mod = importlib.util.module_from_spec(spec)
    sys.modules["sol_llm_client"] = llm_mod
    spec.loader.exec_module(llm_mod)

    client = genai.Client(api_key=api_key)
    sandbox = SubstrateToolSandbox(repo_root=ROOT_DIR)

    print(f"=== STARTING LIVE {args.model.upper()} + SOL SUBSTRATE COMPANION SESSION ===")
    t0 = time.perf_counter()
    telemetry = llm_mod.run_gemini_interaction_with_tools(
        client,
        model=args.model,
        input_payload=args.prompt,
        system_instruction=DEFAULT_COMPANION_SYSTEM_INSTRUCTION,
        thinking_level=args.thinking_level,
        max_output_tokens=32768,
        tools=SUBSTRATE_TOOL_DECLARATIONS,
        tool_dispatcher=sandbox.execute_tool,
        max_tool_rounds=args.max_tool_rounds,
        background=False,
        poll_interval_s=0.25,
        max_wait_s=120.0,
    )
    dt = time.perf_counter() - t0

    print(f"\n=== LIVE SESSION COMPLETE IN {dt:.2f}s ===")
    print("Interaction Chain:", telemetry.get("interaction_chain"))
    print(
        f"Token Telemetry: input={telemetry.get('input_tokens')} | "
        f"thought={telemetry.get('thought_tokens')} | "
        f"output={telemetry.get('output_tokens')} | "
        f"cached={telemetry.get('cached_input_tokens')}"
    )
    print(f"Thought Steps: {telemetry.get('thought_step_count')} | Thought Signatures: {len(telemetry.get('thought_signature_digests', []))}")

    print("\n--- LIVE MODEL THOUGHT SUMMARIES ---")
    for idx, ts in enumerate(telemetry.get("thought_summaries", []), 1):
        print(f"  [Thought {idx}] {ts[:400]}{'...' if len(ts) > 400 else ''}")

    print("\n--- LIVE SUBSTRATE TOOL CALLS EXECUTED ---")
    for idx, tex in enumerate(telemetry.get("tool_executions", []), 1):
        tname = tex.get("name") or tex.get("tool_name")
        targs = tex.get("arguments")
        tres = tex.get("result", {})
        compact_res = {
            k: (round(v, 4) if isinstance(v, float) else v)
            for k, v in tres.items()
            if isinstance(v, (int, float, bool, str)) and len(str(v)) < 60
        }
        print(f"  [Tool Call {idx}] {tname}({json.dumps(targs)})")
        print(f"     -> Substrate Result: {json.dumps(dict(list(compact_res.items())[:8]))}")

    print("\n--- FINAL SUBSTRATE-GROUNDED RESPONSE ---")
    print(telemetry.get("content", ""))

    if not args.no_record:
        ledger_path, md_path = record_companion_session(
            prompt=args.prompt,
            model=args.model,
            thinking_level=args.thinking_level,
            duration_s=dt,
            telemetry=telemetry,
            slug=args.slug,
        )
        print(f"\n[Recorded] JSONL Ledger -> {ledger_path.relative_to(ROOT_DIR)}")
        print(f"[Recorded] Markdown Doc -> {md_path.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
