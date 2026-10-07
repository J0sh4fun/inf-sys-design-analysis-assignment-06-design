"""Reproduce fixed fictional data and synthetic geometric PNG illustrations."""

import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_json(name: str, value: object) -> None:
    (ROOT / "datasets" / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_png(path: Path, color: tuple[int, int, int], shape: int) -> None:
    """Draw a shoe, bag, shirt, or bottle silhouette in a valid RGB PNG."""
    def inside(x: int, y: int) -> bool:
        if shape == 0:
            return (24 < x < 66 and 44 < y < 83) or (24 < x < 109 and 72 < y < 96)
        if shape == 1:
            return (30 < x < 98 and 44 < y < 106) or (45 < x < 83 and 23 < y < 49 and not (52 < x < 76 and y > 30))
        if shape == 2:
            return (39 < x < 89 and 39 < y < 106) or (22 < x < 106 and 32 < y < 59)
        return (44 < x < 84 and 43 < y < 109) or (53 < x < 75 and 22 < y < 48)

    rows = b"".join(b"\x00" + bytes(channel for x in range(128) for channel in (color if inside(x, y) else (245, 245, 240))) for y in range(128))
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 128, 128, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def main() -> None:
    images = ROOT / "datasets/images"
    images.mkdir(parents=True, exist_ok=True)
    rows = [
        ("Metro Black Shoes", "shoes", "black", 59.0, 12, "Everyday walking shoes with flexible soles.", 0),
        ("Sprint Blue Running Shoes", "shoes", "blue", 89.0, 8, "Lightweight running shoes for road training.", 0),
        ("Pace Red Running Shoes", "shoes", "red", 79.0, 0, "Cushioned running shoes for daily training.", 0),
        ("Commuter Black Backpack", "bags", "black", 45.0, 20, "Backpack with a laptop pocket for commuting.", 1),
        ("Trail Green Backpack", "bags", "green", 65.0, 6, "Backpack for hiking with roomy storage.", 1),
        ("Cloud White Shirt", "clothing", "white", 25.0, 30, "Soft cotton shirt for everyday wear.", 2),
        ("Night Black Shirt", "clothing", "black", 29.0, 15, "Cotton shirt with short sleeves.", 2),
        ("Ocean Blue Bottle", "drinkware", "blue", 19.0, 40, "Reusable water bottle with a secure lid.", 3),
        ("Ruby Red Bottle", "drinkware", "red", 22.0, 14, "Insulated water bottle for travel.", 3),
        ("Canvas White Shoes", "shoes", "white", 49.0, 10, "Casual canvas shoes for everyday walking.", 0),
        ("Market Red Tote", "bags", "red", 18.0, 25, "Reusable tote bag for shopping.", 1),
        ("Forest Green Shirt", "clothing", "green", 32.0, 7, "Breathable cotton shirt for relaxed weekends.", 2),
    ]
    colors = {"black": (35, 35, 40), "blue": (35, 95, 200), "red": (200, 45, 55), "green": (40, 135, 70), "white": (205, 205, 210)}
    products, vectors = [], {}
    for product_id, (name, category, color, price, stock, description, shape) in enumerate(rows, 1):
        image = f"datasets/images/product_{product_id:02}.png"
        products.append(dict(product_id=product_id, name=name, category=category, color=color, price=price, stock=stock, description=description, image=image))
        vector = [0.0] * 9
        vector[shape] = 1.0
        vector[4 + list(colors).index(color)] = 0.5
        vectors[str(product_id)] = vector
        make_png(ROOT / image, colors[color], shape)
    queries = {}
    for suffix, product_id, color, shape in [("a", 1, "black", 0), ("b", 5, "green", 1), ("c", 9, "red", 3)]:
        path = f"datasets/images/query_{suffix}.png"
        queries[path] = vectors[str(product_id)].copy()
        make_png(ROOT / path, colors[color], shape)
    write_json("products.json", products)
    write_json("product_embeddings.json", vectors)
    write_json("query_embeddings.json", queries)
    # Relevance labels are authored here, before any evaluation is run.
    cases = [
        ("t1", "text", "black shoes", [1], "Exact color and category."),
        ("t2", "text", "green backpack", [5], "Exact color and product kind."),
        ("t3", "text", "white shirt", [6], "Exact color and product kind."),
        ("t4", "text", "blue bottle", [8], "Exact color and product kind."),
        ("t5", "text", "sneakers", [1, 2, 3, 10], "Known limitation: no synonym expansion from sneakers to shoes."),
        ("v1", "voice", "find running shoes", [2, 3], "Running shoes; supplied transcript only."),
        ("v2", "voice", "red tote", [11], "Exact color and product kind."),
        ("v3", "voice", "black shirt", [7], "Exact color and product kind."),
        ("v4", "voice", "red running shoes", [3], "Out-of-stock products remain eligible."),
        ("i1", "image", "datasets/images/query_a.png", [1], "Fixed vector for black shoe illustration."),
        ("i2", "image", "datasets/images/query_b.png", [5], "Fixed vector for green bag illustration."),
        ("i3", "image", "datasets/images/query_c.png", [9], "Fixed vector for red bottle illustration."),
    ]
    write_json("evaluation_queries.json", [dict(query_id=i, mode=m, input=v, relevant_product_ids=r, explanation=e) for i, m, v, r, e in cases])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Restore the original synthetic dataset and overwrite photos.")
    parser.add_argument("--overwrite-with-synthetic", action="store_true")
    if not parser.parse_args().overwrite_with_synthetic:
        parser.error("Use --overwrite-with-synthetic to explicitly replace current photos and datasets.")
    main()
