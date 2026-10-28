"""Integrity checks require an observed graph, including on partial checkouts."""

from pathlib import Path

import pytest

from sol_continuum.reflective_domain import (
    SACRED_DEFAULT_GRAPH_SHA256,
    verify_sacred_core_graph_sha256,
)


def _graph_path(root: Path) -> Path:
    return root / "sol" / "tools" / "sol-core" / "default_graph.json"


@pytest.mark.parametrize("state", ["missing", "directory", "tampered"])
def test_unavailable_or_tampered_graph_is_unverified(tmp_path: Path, state: str) -> None:
    graph = _graph_path(tmp_path)
    if state == "directory":
        graph.mkdir(parents=True)
    elif state == "tampered":
        graph.parent.mkdir(parents=True)
        graph.write_text("{}\n", encoding="utf-8")

    verified, digest = verify_sacred_core_graph_sha256(tmp_path)

    assert verified is False
    assert digest != SACRED_DEFAULT_GRAPH_SHA256
    if state != "tampered":
        assert digest == ""


def test_unreadable_graph_is_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def deny_read(_path: Path) -> bytes:
        raise PermissionError("graph is unreadable")

    monkeypatch.setattr(Path, "read_bytes", deny_read)
    assert verify_sacred_core_graph_sha256(tmp_path) == (False, "")


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_valid_graph_verifies_with_platform_line_endings(tmp_path: Path, newline: bytes) -> None:
    workspace = Path(__file__).resolve().parents[2]
    canonical = _graph_path(workspace).read_bytes().replace(b"\r\n", b"\n")
    graph = _graph_path(tmp_path)
    graph.parent.mkdir(parents=True)
    graph.write_bytes(canonical.replace(b"\n", newline))

    assert verify_sacred_core_graph_sha256(tmp_path) == (True, SACRED_DEFAULT_GRAPH_SHA256)
