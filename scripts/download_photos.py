"""Download isolated catalog cutouts from PNGimg and normalize their color/layout."""
import hashlib
import io
import json
import shutil
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"

# Every product uses a different source image. The values are
# (PNGimg collection slug, PNGimg numeric image id).
PHOTO_PLAN = {
    1: ("running_shoes", 5786), 2: ("running_shoes", 5805),
    3: ("running_shoes", 5808), 4: ("backpack", 6334),
    5: ("backpack", 6346), 6: ("tshirt", 5426),
    7: ("tshirt", 5427), 8: ("water_bottle", 10144),
    9: ("water_bottle", 98942), 10: ("running_shoes", 5781),
    11: ("women_bag", 6420), 12: ("tshirt", 5454),
    13: ("running_shoes", 5819), 14: ("running_shoes", 5787),
    15: ("running_shoes", 5806), 16: ("running_shoes", 5790),
    17: ("running_shoes", 5782), 18: ("running_shoes", 5813),
    19: ("backpack", 6335), 20: ("backpack", 6353),
    21: ("women_bag", 6400), 22: ("backpack", 6343),
    23: ("backpack", 6354), 24: ("women_bag", 6406),
    25: ("backpack", 6313), 26: ("tshirt", 5429),
    27: ("tshirt", 5451), 28: ("tshirt", 5450),
    29: ("tshirt", 5434), 30: ("tshirt", 5446),
    31: ("tshirt", 5437), 32: ("tshirt", 5447),
    33: ("water_bottle", 98935), 34: ("water_bottle", 10166),
    35: ("water_bottle", 98945), 36: ("water_bottle", 98949),
    37: ("water_bottle", 98947), 38: ("water_bottle", 98954),
    39: ("water_bottle", 98950), 40: ("water_bottle", 98939),
}

PALETTES = {
    "black": ((5, 6, 8), (82, 86, 92)),
    "blue": ((5, 25, 62), (76, 163, 236)),
    "red": ((65, 5, 8), (235, 78, 78)),
    "green": ((5, 48, 18), (91, 180, 100)),
    "white": ((72, 75, 78), (252, 252, 250)),
}


def source_details(collection: str, image_id: int) -> tuple[str, str]:
    filename = f"{collection}_PNG{image_id}.png"
    return (
        f"https://pngimg.com/image/{image_id}",
        f"https://pngimg.com/uploads/{collection}/{filename}",
    )


def normalize(content: bytes, color: str) -> Image.Image:
    """Recolor the isolated cutout, center it, and use a neutral RGB backdrop."""
    source = Image.open(io.BytesIO(content)).convert("RGBA")
    alpha = source.getchannel("A")
    if alpha.getextrema() == (255, 255):
        corners = [source.getpixel(point)[:3] for point in (
            (0, 0), (source.width - 1, 0),
            (0, source.height - 1), (source.width - 1, source.height - 1),
        )]
        backdrop = tuple(sum(channel) // 4 for channel in zip(*corners))
        difference = ImageChops.difference(
            source.convert("RGB"), Image.new("RGB", source.size, backdrop)
        ).convert("L")
        alpha = difference.point(lambda value: 255 if value > 14 else 0)
        alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
        source.putalpha(alpha)
    visible = alpha.point(lambda value: 255 if value > 24 else 0)
    bounds = visible.getbbox()
    if bounds is None:
        raise ValueError("Source image has no visible pixels.")
    source = source.crop(bounds)
    alpha = source.getchannel("A")
    grayscale = ImageOps.grayscale(source)
    dark, light = PALETTES[color]
    recolored = ImageOps.colorize(grayscale, black=dark, white=light).convert("RGBA")
    recolored.putalpha(alpha)
    recolored = ImageOps.contain(
        recolored, (760, 760), method=Image.Resampling.LANCZOS
    )
    canvas = Image.new("RGB", (900, 900), (247, 247, 244))
    x = (canvas.width - recolored.width) // 2
    y = (canvas.height - recolored.height) // 2
    canvas.paste(recolored.convert("RGB"), (x, y), recolored)
    return canvas


def main() -> None:
    products = json.loads((ROOT / "datasets/products.json").read_text(encoding="utf-8"))
    assert {p["product_id"] for p in products} == set(PHOTO_PLAN)
    by_id = {p["product_id"]: p for p in products}
    records = []
    for product_id, (collection, image_id) in PHOTO_PLAN.items():
        source, download_url = source_details(collection, image_id)
        request = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Assignment06-Educational-Demo/2.0"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            photo = normalize(response.read(), by_id[product_id]["color"])
        filename = f"datasets/images/product_{product_id:02}.png"
        temporary = (ROOT / filename).with_suffix(".download.png")
        photo.save(temporary, optimize=True)
        temporary.replace(ROOT / filename)
        records.append({
            "product_id": product_id,
            "file": filename,
            "source": source,
            "author": "PNGimg.com",
            "license": LICENSE_URL,
            "download_url": download_url,
            "modifications": "Isolated cutout recolored to the catalog color and centered on a neutral background.",
        })
        print(f"Ready product {product_id}", flush=True)

    fingerprints = []
    for record in records:
        with Image.open(ROOT / record["file"]) as photo:
            fingerprints.append(hashlib.sha256(photo.convert("RGB").tobytes()).hexdigest())
    assert len(set(fingerprints)) == len(records), "Duplicate photo pixels found."
    assert len({r["source"] for r in records}) == len(records), "Duplicate source found."
    for suffix, product_id in [("a", 1), ("b", 5), ("c", 9)]:
        shutil.copyfile(
            ROOT / f"datasets/images/product_{product_id:02}.png",
            ROOT / f"datasets/images/query_{suffix}.png",
        )
    (ROOT / "datasets/photo_sources.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
