"""Report fixed-label Top-1 retrieval success separately from validation."""

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import build_ui


def evaluate() -> dict:
    ui = build_ui()
    cases = json.loads((ROOT / "datasets/evaluation_queries.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        with contextlib.redirect_stdout(io.StringIO()):
            found = ui.run_search(case["mode"], case["input"], 1)
        top_id = found[0]["product"]["product_id"] if found else None
        results.append({**case, "top_1_product_id": top_id, "success": top_id in case["relevant_product_ids"]})
    successes = sum(r["success"] for r in results)
    per_mode = {}
    for mode in ("text", "voice", "image"):
        group = [r for r in results if r["mode"] == mode]
        passed = sum(r["success"] for r in group)
        per_mode[mode] = {"queries": len(group), "top_1_relevant": passed, "success_rate": passed / len(group)}
    validation = []
    for label, call in [
        ("empty text", lambda: ui.run_search("text", "  ")),
        ("empty transcript", lambda: ui.run_search("voice", "\t")),
        ("unsupported image", lambda: ui.run_search("image", "unknown.png")),
        ("invalid top-k", lambda: ui.run_search("text", "shoes", 0)),
        ("zero embedding", lambda: ui.query.image_query([0] * 9)),
        ("wrong dimensions", lambda: ui.search.search(ui.query.image_query([1, 2]))),
    ]:
        try:
            call()
        except (ValueError, OSError) as exc:
            validation.append({"case": label, "passed": True, "message": str(exc)})
        else:
            validation.append({"case": label, "passed": False, "message": "Expected rejection did not occur."})
    return {"retrieval_queries": len(results), "top_1_relevant": successes,
            "top_1_success_rate": successes / len(results), "per_mode": per_mode,
            "failed_queries": [r for r in results if not r["success"]],
            "query_results": results, "input_validation": validation,
            "limitation": "Image queries use CLIP ViT-B/32; this small fixed set is not an external benchmark for arbitrary catalog images."}


if __name__ == "__main__":
    report = evaluate()
    output = ROOT / "outputs"
    output.mkdir(exist_ok=True)
    (output / "evaluation_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Retrieval queries: {report['retrieval_queries']}")
    print(f"Top-1 relevant: {report['top_1_relevant']}")
    print(f"Top-1 success rate: {report['top_1_success_rate']:.2%}")
    for mode, counts in report["per_mode"].items():
        print(f"{mode}: {counts['top_1_relevant']}/{counts['queries']} ({counts['success_rate']:.2%})")
    for failure in report["failed_queries"]:
        print(f"FAILED {failure['query_id']} ({failure['input']}): {failure['explanation']} Top-1={failure['top_1_product_id']}")
    checks = report["input_validation"]
    print(f"Separate input validation: {sum(c['passed'] for c in checks)}/{len(checks)} passed")
    print(report["limitation"])
