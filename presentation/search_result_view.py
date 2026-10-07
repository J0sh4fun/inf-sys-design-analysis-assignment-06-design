"""Format application results without accessing data or ranking."""


class SearchResultView:
    def feedback(self, message: str) -> None:
        print(message)

    def results(self, mode: str, original: str, query: dict, results: list[dict]) -> None:
        label = f"{mode} (simulated)" if mode == "voice" else mode
        print(f"\nSearch mode: {label}\nInput: {original}")
        if mode == "image":
            print(f"Query embedding: CLIP ViT-B/32 semantic vector ({len(query['embedding'])} dimensions)")
            print("Retrieval: pretrained inference from pixels; cosine similarity against all catalog images.")
        else:
            print(f"Normalized text: {query['text']}")
            print("Retrieval: whole-token set intersection across name, category, color, description.")
        print("Ranking: score descending, product ID ascending; top-k selection.")
        if not results:
            print("No results found.")
        for item in results:
            p = item["product"]
            print(f"{p['product_id']:>2} | {p['name']} | ${p['price']:.2f} | stock={p['stock']} | score={item['score']:.4f}")

    def product(self, product: dict | None) -> None:
        if product is None:
            print("Product not found.")
            return
        for key, value in product.items():
            print(f"{key}: {value}")
