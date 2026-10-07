"""Collect inputs and coordinate application services."""

from application.query_service import QueryService
from application.speech_service import SpeechService
from application.image_service import ImageService
from application.search_service import SearchService
from presentation.search_result_view import SearchResultView


def voice_input() -> str:
    return input("Simulated voice transcript: ")


def image_upload() -> str:
    return input("Image path (or 'list' for demo images): ")


class SearchUI:
    def __init__(self, query: QueryService, speech: SpeechService, image: ImageService,
                 search: SearchService, view: SearchResultView):
        self.query, self.speech, self.image = query, speech, image
        self.search, self.view = search, view

    def run_search(self, mode: str, value: str, top_k: int = 5) -> list[dict]:
        if mode == "voice":
            transcript = self.speech.transcribe(value)
            if not transcript.strip():
                raise ValueError("Simulated voice transcript must not be empty.")
            query = self.query.voice_query(transcript)
        elif mode == "image":
            embedding = self.image.encode(value)
            query = self.query.image_query(embedding)
        elif mode == "text":
            query = self.query.text_query(value)
        else:
            raise ValueError("Unknown search mode.")
        results = self.search.search(query, top_k)
        self.view.results(mode, value, query, results)
        return results

    def demo(self, top_k: int = 5) -> None:
        self.run_search("text", "black shoes", top_k)
        self.run_search("voice", "find running shoes", top_k)
        self.run_search("image", self.image.supported_images()[0], top_k)

    def interactive(self, default_top_k: int = 5) -> None:
        while True:
            self.view.feedback("\n1. Text search\n2. Simulated voice search\n3. Pretrained-model image search\n4. View product details\n0. Exit")
            try:
                choice = input("Choice: ").strip()
                if choice == "0":
                    return
                if choice == "4":
                    try:
                        product_id = int(input("Product ID: "))
                    except ValueError:
                        raise ValueError("Product ID must be a positive integer.") from None
                    self.view.product(self.search.get_product(product_id))
                    continue
                if choice not in {"1", "2", "3"}:
                    self.view.feedback("Invalid menu choice. Enter 0 through 4.")
                    continue
                mode = {"1": "text", "2": "voice", "3": "image"}[choice]
                value = input("Search text: ") if mode == "text" else voice_input() if mode == "voice" else image_upload()
                if mode == "image" and value.strip().lower() == "list":
                    self.view.feedback("Demo query images:\n" + "\n".join(self.image.supported_images()))
                    continue
                raw = input(f"top_k [{default_top_k}]: ").strip()
                try:
                    top_k = int(raw) if raw else default_top_k
                except ValueError:
                    raise ValueError("top_k must be a positive integer.") from None
                self.run_search(mode, value, top_k)
            except (ValueError, OSError) as exc:
                self.view.feedback(f"Error: {exc}")
            except (EOFError, KeyboardInterrupt):
                self.view.feedback("\nGoodbye.")
                return
