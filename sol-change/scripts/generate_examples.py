"""Regenerate the documented, synthetic JSON examples. Run from the project root."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from observatory.fixtures import make_demo

if __name__ == "__main__":
    folder = ROOT / "examples"
    folder.mkdir(exist_ok=True)
    demo = make_demo()
    examples = {"baseline.json": demo["baseline"], "candidate.json": demo["candidate"],
                "incompatible-candidate.json": make_demo(True)["candidate"], "experiment-setup.json": demo["setup"]}
    for name, document in examples.items():
        (folder / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Generated four synthetic example files.")
