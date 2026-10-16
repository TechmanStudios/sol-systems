"""Entirely invented fixtures. These values are not real agent measurements."""

import copy


TASK = "Research whether a small public library should pilot a lending collection of home energy monitors. Summarize benefits, limitations, and a practical pilot plan with source support."


def make_demo(incompatible=False):
    criteria = [
        {"id": "citation_support", "label": "Citation support", "unit": "%", "direction": "higher", "threshold": 85, "max_regression_percent": 0, "required": True},
        {"id": "duration", "label": "Execution time", "unit": "s", "direction": "lower", "threshold": 120, "max_regression_percent": 60, "required": True},
        {"id": "cost", "label": "Run cost", "unit": "USD", "direction": "lower", "threshold": 0.50, "max_regression_percent": 50, "required": True},
        {"id": "usefulness", "label": "Reader usefulness", "unit": "rating/5", "direction": "higher", "threshold": 4, "max_regression_percent": 0, "required": True},
    ]
    setup = {"title": "A better sourced research agent" if not incompatible else "When the comparison breaks",
             "task": TASK, "proposed_change": "Add a claim-to-source verification pass before the agent writes its final brief.",
             "hypothesis": "A verification pass will improve citation support while keeping execution time and cost within the pilot budget.",
             "intended_improvement": "At least 85% of factual claims have matching source support.",
             "constraints": "Finish within 120 seconds and spend no more than $0.50 per run. Do not reduce reader usefulness.",
             "acceptable_tradeoffs": "Up to 60% longer and 50% more expensive if citation support reaches 85%. Reader usefulness still requires review.",
             "criteria": criteria}
    if incompatible:
        setup["proposed_change"] = "Illustrate why runs from different datasets and evaluation methods cannot support a fair comparison."
    evidence = [
        {"id": "citation-audit", "title": "Claim-to-source audit", "reference": "synthetic://library-pilot/claim-audit", "provenance": "Invented fixture: 50 claims reviewed against an imaginary source packet. No real sources were audited."},
        {"id": "trace", "title": "Execution trace", "reference": "synthetic://library-pilot/execution-trace", "provenance": "Invented timings for demonstrating a latency tradeoff; not a captured execution trace."},
        {"id": "usage", "title": "Token usage ledger", "reference": "synthetic://library-pilot/usage", "provenance": "Invented USD cost; not an invoice or provider billing record."},
        {"id": "reader-rubric", "title": "Reader evaluation rubric", "reference": "synthetic://library-pilot/reader-rubric", "provenance": "Invented baseline rating. Candidate review deliberately missing."},
    ]
    methods = {
        "citation_support": {"kind": "automated_assessment", "description": "Supported factual claims divided by 50 claims, using the same frozen source packet and rubric.", "version": "claim-audit/1"},
        "duration": {"kind": "measured", "description": "Wall-clock elapsed time from task submission to final output.", "version": "timer/1"},
        "cost": {"kind": "measured", "description": "Input and output token charges summed using a frozen price table.", "version": "cost-ledger/1"},
        "usefulness": {"kind": "human_rating", "description": "One reviewer rates clarity and actionability from 1 to 5 using the pilot rubric.", "version": "reader-rubric/1"},
    }
    runs = []
    for role, values in (("baseline", (68, 78, 0.24, 4.0)), ("candidate", (92, 112, 0.38, None))):
        candidate = role == "candidate"
        run = {"schema_version": "1.0", "kind": "sol-change/run", "id": f"synthetic-research-{role}{'-incompatible' if incompatible and candidate else ''}",
               "designation": role, "input": TASK,
               "output": "RESEARCH BRIEF · Library energy monitor pilot\n\nRecommendation: run a six-week lending pilot with ten plug-in monitors.\n\nBenefits: help patrons understand appliance energy use and identify avoidable consumption.\n\n" + (
                   "Evidence: 46 of 50 factual claims are supported in the imaginary source packet [citation-audit]. Four claims remain unsupported.\n\nLimitations: plug-in monitors cannot assess hardwired appliances; findings depend on usage habits. Savings are not guaranteed.\n\nPilot: track loans, returns, device failures, and patron feedback. Review usefulness with a librarian before adoption."
                   if candidate else "Evidence: 34 of 50 factual claims are supported in the imaginary source packet [citation-audit]. Several claims have no matching source.\n\nLimitations: findings depend on usage habits.\n\nPilot: track loans and ask patrons whether the monitors helped."),
               "configuration": {"verification_pass": candidate, "temperature": 0.2, "max_output_tokens": 1800},
               "workflow_version": f"research-agent/{'2.0' if candidate else '1.0'} (synthetic)",
               "executed_at": f"2026-10-15T14:{'05' if candidate else '00'}:00Z",
               "conditions": {"task_id": "library-energy-pilot", "source_packet": "frozen-library-packet/1", "environment": "invented demo", "seed": 7},
               "data_type": "synthetic", "measurements": [], "evidence": copy.deepcopy(evidence)}
        for criterion, value, evidence_id in zip(criteria, values, ("citation-audit", "trace", "usage", "reader-rubric")):
            run["measurements"].append({"criterion_id": criterion["id"], "value": value, "unit": criterion["unit"], "method": copy.deepcopy(methods[criterion["id"]]), "evidence_ids": [evidence_id] if value is not None else []})
        if incompatible and candidate:
            run["conditions"]["source_packet"] = "different-library-packet/2"
            run["input"] = TASK + " Use a different source packet and a 12-week pilot."
            run["measurements"][0]["method"]["version"] = "claim-audit/2"
        runs.append(run)
    return {"setup": setup, "baseline": runs[0], "candidate": runs[1]}
