"""Read fictional product records from products.json."""

import json
from pathlib import Path


class ProductRepository:
    def __init__(self, path: Path):
        records = json.loads(path.read_text(encoding="utf-8"))
        required = {"product_id", "name", "category", "color", "price", "stock", "description", "image"}
        if not isinstance(records, list) or not records:
            raise ValueError("Product dataset must be a nonempty list.")
        self._products: dict[int, dict] = {}
        for record in records:
            if not isinstance(record, dict) or not required <= record.keys():
                raise ValueError("Product record is missing required fields.")
            product_id = record["product_id"]
            if type(product_id) is not int or product_id <= 0 or product_id in self._products:
                raise ValueError("Product IDs must be unique positive integers.")
            self._products[product_id] = record

    def all_products(self) -> list[dict]:
        return [record.copy() for record in self._products.values()]

    def get_by_id(self, product_id: int) -> dict | None:
        if type(product_id) is not int or product_id <= 0:
            raise ValueError("Product ID must be a positive integer.")
        record = self._products.get(product_id)
        return record.copy() if record else None
