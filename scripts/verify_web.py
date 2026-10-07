"""Save new evidence without modifying earlier outputs or dataset files."""

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate import evaluate


def preserved_hashes() -> dict:
    files = list((ROOT / "datasets").rglob("*")) + list((ROOT / "outputs").glob("*"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files if path.is_file()}


def main() -> None:
    output = ROOT / "outputs/web" / datetime.now().strftime("run-%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    before = preserved_hashes()
    for name, args in [("tests.txt", ["-m", "unittest", "discover", "-s", "tests", "-v"]),
                       ("demo.txt", ["main.py", "--demo"]),
                       ("dependencies.txt", ["-m", "pip", "freeze"])]:
        result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
        (output / name).write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"{name}: exit {result.returncode}")
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
    # Call the original evaluator without its output-overwriting __main__ wrapper.
    report = evaluate()
    (output / "evaluation_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    previous = json.loads((ROOT / "outputs/evaluation_results.json").read_text(encoding="utf-8"))
    if report != previous:
        raise AssertionError("Evaluation report changed; inspect the new report.")
    after = preserved_hashes()
    if before != after:
        raise AssertionError("A preserved dataset or previous output was modified.")
    summary = {"evaluation_identical": True, "top_1_relevant": report["top_1_relevant"],
               "queries": report["retrieval_queries"], "preserved_sha256": after}
    (output / "verification.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Evaluation unchanged: {report['top_1_relevant']}/{report['retrieval_queries']}; datasets and prior outputs unchanged.")
    print(f"Evidence: {output}")


if __name__ == "__main__":
    main()
