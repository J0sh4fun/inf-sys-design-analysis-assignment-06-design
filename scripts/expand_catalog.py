"""Expand the demo to ten products per category without replacing existing IDs.

New records use their own category/color photograph as an illustration.
Names, descriptions, prices and stock are fictional, not claims about the photo.
"""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"

# English name, Vietnamese name, reference photo/product, price, stock, description.
ADDITIONS = [
    ("Urban Black Walking Shoes", "Giày đi bộ đen Urban", 1, 62, 18, "Walking shoes with a padded collar for city commutes."),
    ("Aero Blue Running Shoes", "Giày chạy bộ xanh Aero", 2, 95, 11, "Running shoes with breathable mesh for warm weather training."),
    ("Velocity Red Running Shoes", "Giày chạy bộ đỏ Velocity", 3, 85, 9, "Running shoes with a supportive heel for regular workouts."),
    ("Weekend White Canvas Shoes", "Giày vải trắng Weekend", 10, 42, 24, "Canvas shoes with simple laces for relaxed weekend outfits."),
    ("Stride Black Walking Shoes", "Giày đi bộ đen Stride", 1, 72, 13, "Walking shoes with cushioned insoles for long days on foot."),
    ("Coast Blue Casual Shoes", "Giày thường ngày xanh Coast", 2, 68, 16, "Casual shoes with flexible soles for everyday outings."),
    ("Campus Black Backpack", "Balo đen Campus", 4, 39, 28, "Backpack with book compartments for school and study."),
    ("Summit Green Backpack", "Balo xanh lá Summit", 5, 78, 8, "Backpack with adjustable straps and extra space for hiking."),
    ("Daily Red Tote", "Túi tote đỏ Daily", 11, 21, 32, "Reusable tote bag for groceries and daily errands."),
    ("Transit Black Backpack", "Balo đen Transit", 4, 58, 14, "Backpack with a laptop sleeve and organizer for work travel."),
    ("Explorer Green Backpack", "Balo xanh lá Explorer", 5, 89, 5, "Backpack with roomy compartments for outdoor day trips."),
    ("Picnic Red Tote", "Túi tote đỏ Picnic", 11, 26, 19, "Reusable tote bag with long handles for weekend picnics."),
    ("Compact Black Backpack", "Balo đen Compact", 4, 35, 22, "Compact backpack for a tablet and everyday essentials."),
    ("Essential White Cotton Shirt", "Áo cotton trắng Essential", 6, 23, 36, "Cotton shirt with a classic cut for everyday wear."),
    ("Midnight Black Cotton Shirt", "Áo cotton đen Midnight", 7, 31, 21, "Cotton shirt with a soft finish for casual evenings."),
    ("Meadow Green Cotton Shirt", "Áo cotton xanh lá Meadow", 12, 28, 17, "Cotton shirt with a relaxed fit for outdoor weekends."),
    ("Breeze White Summer Shirt", "Áo mùa hè trắng Breeze", 6, 27, 25, "Lightweight shirt for comfortable summer days."),
    ("Studio Black Casual Shirt", "Áo thường ngày đen Studio", 7, 34, 12, "Casual shirt with a clean neckline for simple outfits."),
    ("Garden Green Casual Shirt", "Áo thường ngày xanh lá Garden", 12, 30, 20, "Casual shirt with a comfortable cut for daily activities."),
    ("Serene White Shirt", "Áo trắng Serene", 6, 29, 15, "Shirt with a neat collar and easy fit for casual occasions."),
    ("Active Blue Water Bottle", "Bình nước xanh Active", 8, 18, 35, "Reusable water bottle with a carry handle for daily hydration."),
    ("Sport Red Water Bottle", "Bình nước đỏ Sport", 9, 24, 26, "Water bottle with an easy grip for gym sessions."),
    ("Hydro Blue Water Bottle", "Bình nước xanh Hydro", 8, 21, 30, "Reusable water bottle for the office and school."),
    ("Nomad Red Insulated Bottle", "Bình giữ nhiệt đỏ Nomad", 9, 32, 16, "Insulated water bottle with a secure lid for travel."),
    ("Fresh Blue Water Bottle", "Bình nước xanh Fresh", 8, 16, 42, "Water bottle with a simple lid for everyday use."),
    ("Peak Red Water Bottle", "Bình nước đỏ Peak", 9, 27, 11, "Water bottle with a sturdy grip for outdoor adventures."),
    ("Wave Blue Water Bottle", "Bình nước xanh Wave", 8, 23, 23, "Reusable water bottle with a carry loop for walking trips."),
    ("Trail Red Insulated Bottle", "Bình giữ nhiệt đỏ Trail", 9, 35, 7, "Insulated water bottle for hiking and day trips."),
]
ORIGINAL_NAMES_VI = ["Giày đen Metro", "Giày chạy bộ xanh Sprint", "Giày chạy bộ đỏ Pace",
                     "Balo đen Commuter", "Balo xanh lá Trail", "Áo trắng Cloud", "Áo đen Night",
                     "Bình nước xanh Ocean", "Bình nước đỏ Ruby", "Giày trắng Canvas",
                     "Túi tote đỏ Market", "Áo xanh lá Forest"]


def main():
    products = json.loads((DATA / "products.json").read_text(encoding="utf-8"))
    vectors = json.loads((DATA / "product_embeddings.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "photo_sources.json").read_text(encoding="utf-8"))
    by_id = {p["product_id"]: p for p in products}
    source_by_id = {s["product_id"]: s for s in sources}
    for product_id, name in enumerate(ORIGINAL_NAMES_VI, 1):
        by_id[product_id]["name_vi"] = name
    for product_id, (name, name_vi, reference, price, stock, description) in enumerate(ADDITIONS, 13):
        if product_id in by_id:
            if by_id[product_id]["name"] != name:
                raise ValueError(f"Product ID {product_id} already belongs to another record.")
            continue
        template = by_id[reference]
        record = dict(product_id=product_id, name=name, name_vi=name_vi,
                      category=template["category"], color=template["color"], price=float(price),
                      stock=stock, description=description, image=f"datasets/images/product_{product_id:02}.png")
        by_id[product_id] = record
        products.append(record)
        vectors[str(product_id)] = vectors[str(reference)].copy()
        if product_id not in source_by_id:
            raise ValueError(f"Prepare a unique credited photo for product {product_id} before expanding the catalog.")
    counts = Counter(p["category"] for p in products)
    assert set(counts) == {"shoes", "bags", "clothing", "drinkware"}
    assert all(count >= 10 for count in counts.values()), counts
    assert set(vectors) == {str(p["product_id"]) for p in products}
    assert all((ROOT / p["image"]).is_file() for p in products)
    for filename, value in [("products.json", products), ("product_embeddings.json", vectors),
                            ("photo_sources.json", sources)]:
        (DATA / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(counts), ensure_ascii=False))


if __name__ == "__main__":
    main()
