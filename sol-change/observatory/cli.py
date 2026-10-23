"""CLI entry point for SOL Change Observatory continuum & repeat-trial workflows."""

from __future__ import annotations

from .continuum import (
    evaluate_repeat_trial_group,
    format_repeat_trial_evaluation_text,
    main,
    validate_repeat_trial_group,
)

__all__ = [
    "evaluate_repeat_trial_group",
    "format_repeat_trial_evaluation_text",
    "main",
    "validate_repeat_trial_group",
]


if __name__ == "__main__":
    raise SystemExit(main())
