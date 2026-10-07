"""Check an already-running local server and save new HTTP evidence."""

import json
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10, trust_env=False) as client:
        for path in ("/", "/static/app.js", "/static/styles.css", "/api/health", "/api/image-samples", "/images/query_a.png", "/api/products/1"):
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            checks.append({"method": "GET", "path": path, "status": response.status_code})
        for mode, payload, first_id in [("text", {"text": "black shoes"}, 1),
                                         ("voice", {"transcript": "find running shoes"}, 2),
                                         ("image", {"sample_id": "sample-2"}, 5)]:
            response = client.post(f"/api/search/{mode}", json=payload)
            assert response.status_code == 200
            body = response.json()
            assert body["results"][0]["product"]["product_id"] == first_id
            checks.append({"method": "POST", "path": f"/api/search/{mode}", "status": 200, "response": body})
    destination = ROOT / "outputs/web" / f"http-smoke-{datetime.now():%Y%m%d-%H%M%S}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(checks)} real HTTP checks. Evidence: {destination}")


if __name__ == "__main__":
    main()
