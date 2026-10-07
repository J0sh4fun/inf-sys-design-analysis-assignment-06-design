"""Composition root and CLI entry point (Python 3.10+)."""

import argparse
import sys
from application.ranking_service import RankingService
from bootstrap import ROOT, build_services
from presentation.search_ui import SearchUI
from presentation.search_result_view import SearchResultView

def build_ui() -> SearchUI:
    services = build_services()
    return SearchUI(services.query, services.speech, services.image,
                    services.search, SearchResultView())


def main() -> int:
    parser = argparse.ArgumentParser(description="Fictional product search with simulated voice and pretrained image retrieval.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    try:
        RankingService.validate_top_k(args.top_k)
        ui = build_ui()
        if args.demo:
            ui.demo(args.top_k)
        else:
            ui.interactive(args.top_k)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
