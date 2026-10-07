"""Asset QA: decode photos, check unique content and produce contact sheets (Pillow)."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
products = json.loads((ROOT / "datasets/products.json").read_text(encoding="utf-8"))
sources = json.loads((ROOT / "datasets/photo_sources.json").read_text(encoding="utf-8"))
output = ROOT / "outputs/web/unique-photos"
output.mkdir(parents=True, exist_ok=True)
hashes = []
for category in ("shoes", "bags", "clothing", "drinkware"):
    group = [p for p in products if p["category"] == category]
    sheet = Image.new("RGB", (1200, 600), "white")
    draw = ImageDraw.Draw(sheet)
    for index, product in enumerate(group):
        with Image.open(ROOT / product["image"]) as image:
            photo = image.convert("RGB")
            assert min(photo.size) >= 250
            digest = hashlib.sha256(photo.tobytes()).hexdigest()
            hashes.append({"id": product["product_id"], "path": product["image"], "pixel_sha256": digest})
            thumbnail = ImageOps.contain(photo, (224, 248))
        x, y = (index % 5) * 240, (index // 5) * 300
        sheet.paste(thumbnail, (x + (224-thumbnail.width)//2, y))
        draw.text((x+5, y+252), f'{product["product_id"]}: {product["name"]}', fill="black")
        draw.text((x+5, y+269), product["color"], fill="black")
    sheet.save(output / f"{category}.jpg", quality=90)
assert len({h["path"] for h in hashes}) == len(products)
assert len({h["pixel_sha256"] for h in hashes}) == len(products)
assert len({s["source"] for s in sources}) == len(products)
(output / "verification.json").write_text(json.dumps({"products": len(products), "unique_sources": len(sources),
    "unique_decoded_images": len(hashes), "images": hashes}, indent=2), encoding="utf-8")
print(f"Verified {len(products)} unique paths, source photos and decoded pixel contents.")
