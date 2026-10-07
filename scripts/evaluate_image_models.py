"""Compare image encoders with leave-one-out nearest-neighbour retrieval."""

import json
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def encode(model: Path, products: list[dict], mean: list[float], std: list[float], method: int) -> np.ndarray:
    session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    batch = []
    for product in products:
        with Image.open(ROOT / product["image"]) as source:
            image = ImageOps.fit(source.convert("RGB"), (224, 224), method=method)
            pixels = np.asarray(image, dtype=np.float32) / 255.0
            batch.append(((pixels - np.asarray(mean, dtype=np.float32)) /
                          np.asarray(std, dtype=np.float32)).transpose(2, 0, 1))
    vectors = np.concatenate([
        session.run(None, {session.get_inputs()[0].name: np.expand_dims(item, axis=0)})[0]
        for item in batch
    ]).astype(np.float32)
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def evaluate(name: str, model: str, products: list[dict], mean: list[float],
             std: list[float], method: int) -> dict:
    started = perf_counter()
    vectors = encode(ROOT / model, products, mean, std, method)
    category_hits = color_hits = combined_hits = 0
    cases = []
    for index, product in enumerate(products):
        scores = vectors @ vectors[index]
        scores[index] = -np.inf
        nearest_index = int(np.argmax(scores))
        nearest = products[nearest_index]
        category_ok = nearest["category"] == product["category"]
        color_ok = nearest["color"] == product["color"]
        category_hits += category_ok
        color_hits += color_ok
        combined_hits += category_ok and color_ok
        cases.append({"query_product_id": product["product_id"],
                      "nearest_product_id": nearest["product_id"],
                      "score": float(scores[nearest_index]),
                      "category_match": category_ok, "color_match": color_ok})
    total = len(products)
    return {"model": name, "embedding_dimension": int(vectors.shape[1]), "queries": total,
            "category_top_1": category_hits, "category_accuracy": category_hits / total,
            "color_top_1": color_hits, "color_accuracy": color_hits / total,
            "category_and_color_top_1": combined_hits,
            "category_and_color_accuracy": combined_hits / total,
            "elapsed_ms": (perf_counter() - started) * 1000, "cases": cases}


def main() -> None:
    products = json.loads((ROOT / "datasets/products.json").read_text(encoding="utf-8"))
    common = [
        ("MobileNetV2 ImageNet logits (previous)", "models/mobilenetv2-12.onnx",
         [0.485, 0.456, 0.406], [0.229, 0.224, 0.225], Image.Resampling.BILINEAR),
        ("CLIP ViT-B/32 semantic embedding (current)", "models/clip-vit-base-patch32-vision-int8.onnx",
         [0.48145466, 0.4578275, 0.40821073], [0.26862954, 0.26130258, 0.27577711],
         Image.Resampling.BICUBIC),
    ]
    results = [evaluate(name, model, products, mean, std, method)
               for name, model, mean, std, method in common]
    report = {"method": "Leave-one-out nearest neighbour over 40 catalog photos; exact self-match excluded.",
              "purpose": "Internal regression proxy for visual category retrieval, not an external benchmark.",
              "results": results,
              "category_accuracy_gain": results[1]["category_accuracy"] - results[0]["category_accuracy"]}
    output = ROOT / "outputs/image_similarity_evaluation.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['model']}: category {result['category_top_1']}/{result['queries']} "
              f"({result['category_accuracy']:.1%}); category+color "
              f"{result['category_and_color_top_1']}/{result['queries']} "
              f"({result['category_and_color_accuracy']:.1%})")
    print(f"Category accuracy gain: {report['category_accuracy_gain']:+.1%}")


if __name__ == "__main__":
    main()
