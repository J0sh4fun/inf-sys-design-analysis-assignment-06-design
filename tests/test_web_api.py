"""Integration checks against the real Python services and fixed datasets."""

import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from bootstrap import ROOT, build_services
from web.app import create_app


class WebAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = TestClient(cls.app)
        cls.client.__enter__()
        cls.direct = build_services()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def assert_candidates_equal(self, actual, expected):
        self.assertEqual([r["product"] for r in actual], [r["product"] for r in expected])
        for left, right in zip(actual, expected):
            self.assertAlmostEqual(left["score"], right["score"], places=12)

    def test_text_matches_direct_and_diagnostics(self):
        response = self.client.post("/api/search/text", json={"text": "black shoes"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assert_candidates_equal(body["results"], self.direct.search.search(self.direct.query.text_query("black shoes")))
        self.assertEqual(body["mode"], "text")
        self.assertEqual(body["input"], "black shoes")
        self.assertEqual(body["top_k"], 5)
        self.assertEqual(body["diagnostics"]["returned_results"], len(body["results"]))
        self.assertGreaterEqual(body["diagnostics"]["backend_processing_ms"], 0)
        self.assertIn(3, [r["product"]["product_id"] for r in body["results"]])

    def test_voice_matches_direct_pipeline_and_sequence(self):
        services = self.app.state.services
        calls = Mock()
        with patch.object(services.speech, "transcribe", wraps=services.speech.transcribe) as transcribe, \
             patch.object(services.query, "voice_query", wraps=services.query.voice_query) as query, \
             patch.object(services.search, "search", wraps=services.search.search) as search:
            for name, method in [("transcribe", transcribe), ("query", query), ("search", search)]:
                calls.attach_mock(method, name)
            response = self.client.post("/api/search/voice", json={"transcript": "find running shoes"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([call[0] for call in calls.mock_calls], ["transcribe", "query", "search"])
        transcript = self.direct.speech.transcribe("find running shoes")
        expected = self.direct.search.search(self.direct.query.voice_query(transcript))
        self.assert_candidates_equal(response.json()["results"], expected)

    def test_text_and_voice_equivalence(self):
        text = self.client.post("/api/search/text", json={"text": " RUNNING  shoes "}).json()
        voice = self.client.post("/api/search/voice", json={"transcript": " RUNNING  shoes "}).json()
        self.assert_candidates_equal(text["results"], voice["results"])
        self.assertEqual(voice["query"]["text"], "running shoes")

    def test_all_registered_images_match_pipeline(self):
        samples = self.client.get("/api/image-samples").json()["samples"]
        self.assertEqual(len(samples), 3)
        for sample, path in zip(samples, self.direct.image.supported_images()):
            with self.subTest(sample=sample["sample_id"]):
                response = self.client.post("/api/search/image", json={"sample_id": sample["sample_id"]})
                self.assertEqual(response.status_code, 200)
                embedding = self.direct.image.encode(path)
                expected = self.direct.search.search(self.direct.query.image_query(embedding))
                self.assert_candidates_equal(response.json()["results"], expected)
                self.assertEqual(response.json()["query"]["embedding_dimension"], 512)
                self.assertIn("CLIP ViT-B/32", response.json()["query"]["model"])
                image = self.client.get(sample["image_url"])
                self.assertEqual(image.status_code, 200)
                self.assertTrue(image.content.startswith(b"\x89PNG"))

    def test_arbitrary_image_upload_runs_pretrained_inference(self):
        content = (ROOT / "datasets/images/product_02.png").read_bytes()
        response = self.client.post("/api/search/image", data={"top_k": "3"},
                                    files={"image": ("my-photo.png", content, "image/png")})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["input"], "my-photo.png")
        self.assertEqual(body["query"]["embedding_dimension"], 512)
        self.assertEqual(body["results"][0]["product"]["product_id"], 2)
        self.assertAlmostEqual(body["results"][0]["score"], 1.0, places=5)

    def test_image_upload_validation(self):
        invalid = self.client.post("/api/search/image", data={"top_k": "5"},
                                   files={"image": ("fake.png", b"not an image", "image/png")})
        self.assertEqual(invalid.status_code, 422)
        media = self.client.post("/api/search/image", data={"top_k": "5"},
                                 files={"image": ("photo.gif", b"GIF89a", "image/gif")})
        self.assertEqual(media.status_code, 415)
        missing = self.client.post("/api/search/image", data={"top_k": "5"})
        self.assertEqual(missing.status_code, 415)

    def test_top_k_limit(self):
        for k in (1, 3):
            body = self.client.post("/api/search/text", json={"text": "shoes", "top_k": k}).json()
            self.assertEqual(len(body["results"]), k)

    def test_invalid_top_k_all_modes(self):
        for mode, payload in [("text", {"text": "shoes"}), ("voice", {"transcript": "shoes"}), ("image", {"sample_id": "sample-1"})]:
            for value in (0, -1, 1.5, 2.0, True, False, "2", "bad", None, [], {}):
                with self.subTest(mode=mode, value=value):
                    response = self.client.post(f"/api/search/{mode}", json={**payload, "top_k": value})
                    self.assertEqual(response.status_code, 422)
                    self.assertIn("top_k", response.json()["detail"])

    def test_empty_input_rejected_before_search(self):
        services = self.app.state.services
        with patch.object(services.search, "search") as search, \
             patch.object(services.speech, "transcribe", wraps=services.speech.transcribe) as transcribe, \
             patch.object(services.query, "voice_query") as query:
            for value in ("", " \t\n "):
                self.assertEqual(self.client.post("/api/search/text", json={"text": value}).status_code, 422)
                self.assertEqual(self.client.post("/api/search/voice", json={"transcript": value}).status_code, 422)
            self.assertEqual(transcribe.call_count, 2)
            search.assert_not_called()
            query.assert_not_called()

    def test_unknown_sample_and_paths_rejected(self):
        for sample_id in ("unknown", "datasets/images/query_a.png", "../products.json", "C:\\Windows\\win.ini"):
            response = self.client.post("/api/search/image", json={"sample_id": sample_id})
            self.assertEqual(response.status_code, 404)

    def test_product_details_and_missing_product(self):
        self.assertEqual(self.client.get("/api/products/1").json()["product"], self.direct.search.get_product(1))
        self.assertEqual(self.client.get("/api/products/999").status_code, 404)
        self.assertEqual(self.client.get("/api/products/0").status_code, 422)
        self.assertEqual(self.client.get("/api/products/abc").status_code, 422)

    def test_no_match_success(self):
        response = self.client.post("/api/search/text", json={"text": "unobtainium"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_bilingual_search_and_original_input(self):
        for vi, en, expected_id in [("giày đen", "shoes black", 1),
                                     ("balo xanh lá", "backpack green", 5),
                                     ("bình nước đỏ", "water bottle red", 9),
                                     ("ao thun trang", "shirt white", 6),
                                     ("giày blue", "shoes blue", 2)]:
            with self.subTest(query=vi):
                actual = self.client.post("/api/search/text", json={"text": vi}).json()
                expected = self.client.post("/api/search/text", json={"text": en}).json()
                self.assert_candidates_equal(actual["results"], expected["results"])
                self.assertEqual(actual["input"], vi)
                self.assertEqual(actual["results"][0]["product"]["product_id"], expected_id)

    def test_vietnamese_voice_unicode_and_no_accents(self):
        import unicodedata
        expected = self.client.post("/api/search/text", json={"text": "running shoes"}).json()
        for transcript in ("tìm cho tôi giày chạy bộ", "tim cho toi giay chay bo",
                           unicodedata.normalize("NFD", "TÌM CHO TÔI GIÀY CHẠY BỘ")):
            body = self.client.post("/api/search/voice", json={"transcript": transcript}).json()
            self.assertEqual(body["mode"], "voice")
            self.assert_candidates_equal(body["results"], expected["results"])

    def test_query_with_only_vietnamese_filler(self):
        for mode, key in [("text", "text"), ("voice", "transcript")]:
            response = self.client.post(f"/api/search/{mode}", json={key: "tìm cho tôi"})
            self.assertEqual(response.status_code, 422)

    def test_catalog_images_and_no_ranking_before_query(self):
        body = self.client.get("/api/catalog").json()
        self.assertEqual(len(body["products"]), 40)
        for item in body["products"]:
            self.assertNotIn("score", item)
            response = self.client.get(item["image_url"])
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.content.startswith(b"\x89PNG"))

    def test_ten_products_per_category_and_new_products_searchable(self):
        from collections import Counter
        products = self.client.get("/api/catalog").json()["products"]
        self.assertEqual(Counter(item["product"]["category"] for item in products),
                         {"shoes": 10, "bags": 10, "clothing": 10, "drinkware": 10})
        for item in products:
            product = item["product"]
            self.assertTrue(product["name_vi"].strip())
            self.assertEqual(self.client.get(f'/api/products/{product["product_id"]}').status_code, 200)
            response = self.client.post("/api/search/text", json={"text": product["name"], "top_k": 1})
            self.assertEqual(response.json()["results"][0]["product"]["product_id"], product["product_id"])
        for query, category in [("giày", "shoes"), ("túi", "bags"), ("áo", "clothing"), ("bình", "drinkware")]:
            results = self.client.post("/api/search/text", json={"text": query, "top_k": 40}).json()["results"]
            self.assertEqual(len(results), 10)
            self.assertTrue(all(item["product"]["category"] == category for item in results))

    def test_product_photos_are_unique_and_credited(self):
        import hashlib
        import json
        from bootstrap import ROOT
        products = self.direct.search.list_products()
        paths = [product["image"] for product in products]
        self.assertEqual(len(set(paths)), len(products))
        hashes = [hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths]
        self.assertEqual(len(set(hashes)), len(products))
        sources = json.loads((ROOT / "datasets/photo_sources.json").read_text(encoding="utf-8"))
        self.assertEqual({s["product_id"] for s in sources}, {p["product_id"] for p in products})
        self.assertEqual(len({s["source"] for s in sources}), len(products))
        by_id = {s["product_id"]: s for s in sources}
        for product in products:
            self.assertEqual(by_id[product["product_id"]]["file"], product["image"])

    def test_image_and_static_boundaries(self):
        for path in ("/images/../products.json", "/images/%2e%2e%2fproducts.json", "/images/..%5cproducts.json",
                     "/images/%2fetc%2fpasswd", "/images/C:%5cWindows%5cwin.ini", "/images/products.json",
                     "/datasets/products.json", "/main.py", "/static/../main.py", "/images/missing.png"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/images/product_01.png").headers["content-type"], "image/png")
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/api/health").json()["status"], "ok")

    def test_request_structure(self):
        for payload in ({}, {"text": 12}, {"text": "shoes", "filters": {}}, {"text": None}):
            self.assertEqual(self.client.post("/api/search/text", json=payload).status_code, 422)
        self.assertEqual(self.client.post("/api/search/text", content="{bad", headers={"Content-Type": "application/json"}).status_code, 422)

    def test_missing_sample_file_clear_error(self):
        with patch.object(self.app.state.services.image, "encode", side_effect=FileNotFoundError("private path")), self.assertLogs("web.app", level="ERROR"):
            response = self.client.post("/api/search/image", json={"sample_id": "sample-1"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private path", response.text)

    def test_unexpected_failure_logged_not_leaked(self):
        with TestClient(self.app, raise_server_exceptions=False) as client:
            with patch.object(self.app.state.services.search, "search", side_effect=RuntimeError("private traceback")), self.assertLogs("web.app", level="ERROR"):
                response = client.post("/api/search/text", json={"text": "shoes"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private traceback", response.text)


if __name__ == "__main__":
    unittest.main()
