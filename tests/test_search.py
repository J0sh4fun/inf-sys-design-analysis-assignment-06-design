"""Focused baseline correctness and sequence tests."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from main import ROOT, build_ui
from application.search_service import SearchService, cosine_similarity
from application.ranking_service import RankingService
from data.image_storage import ImageStorage
from data.product_repository import ProductRepository
from data.vector_index import VectorIndex


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.ui = build_ui()

    def test_normalization_and_schema(self):
        self.assertEqual(self.ui.query.text_query("  BLACK\t Shoes\n"),
                         {"type": "text", "text": "black shoes", "embedding": None, "filters": {}})
        self.assertEqual(self.ui.query.image_query([1, 2])["text"], "")

    def test_whole_tokens_and_unique_tokens(self):
        self.assertEqual(self.ui.search.search(self.ui.query.text_query("shoe")), [])
        query = self.ui.query.text_query("shoes shoes")
        self.assertTrue(all(c["score"] == 1.0 for c in self.ui.search.search(query)))

    def test_equivalent_voice_text(self):
        transcript = self.ui.speech.transcribe(" Running SHOES ")
        self.assertEqual(self.ui.search.search(self.ui.query.text_query(transcript)),
                         self.ui.search.search(self.ui.query.voice_query(transcript)))

    def test_ties_and_top_k(self):
        candidates = [{"product": {"product_id": i}, "score": s} for i, s in [(10, 1.), (2, 1.), (3, 2.)]]
        self.assertEqual([c["product"]["product_id"] for c in RankingService().rank(candidates, 2)], [3, 2])
        self.assertEqual(len(RankingService().rank(candidates, 100)), 3)

    def test_empty_results(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(self.ui.run_search("text", "unobtainium"), [])
        self.assertIn("No results found", output.getvalue())

    def test_cosine_known_vectors(self):
        self.assertAlmostEqual(cosine_similarity([1, 0], [1, 1]), 2 ** -0.5)
        self.assertEqual(cosine_similarity([1, 0], [0, 1]), 0)
        self.assertEqual(cosine_similarity([1, 0], [-1, 0]), -1)
        self.assertAlmostEqual(cosine_similarity([1e308, 1e308], [1, 1]), 1)

    def test_invalid_embeddings(self):
        for vector in ([], [0, 0], [float("nan"), 1], [float("inf"), 1], ["1", 0], [True, 1], None):
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                self.ui.query.image_query(vector)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            self.ui.search.retrieve_image_candidates([1, 2])

    def test_invalid_top_k(self):
        for k in (0, -1, 1.5, "2", True, None):
            with self.subTest(k=k), self.assertRaises(ValueError):
                self.ui.search.search(self.ui.query.text_query("shoes"), k)

    def test_product_vector_consistency(self):
        self.assertEqual({p["product_id"] for p in self.ui.search.products.all_products()},
                         set(self.ui.search.vectors.all_embeddings()))
        self.assertEqual(self.ui.search.vectors.dimension, 512)
        vectors = Mock()
        vectors.all_embeddings.return_value = {999: [1.]}
        with self.assertRaisesRegex(ValueError, "IDs"):
            SearchService(self.ui.search.products, vectors, RankingService())

    def test_clip_leave_one_out_category_quality(self):
        products = self.ui.search.list_products()
        vectors = self.ui.search.vectors.all_embeddings()
        correct = 0
        for product in products:
            query_id = product["product_id"]
            nearest = max(
                (candidate for candidate in products if candidate["product_id"] != query_id),
                key=lambda candidate: cosine_similarity(
                    vectors[query_id], vectors[candidate["product_id"]]
                ),
            )
            correct += nearest["category"] == product["category"]
        self.assertGreaterEqual(correct, 36)

    def test_retrieval_preserves_order_and_all_images(self):
        records = [self.ui.search.get_product(i) for i in (10, 3, 2, 1)]
        found = self.ui.search.retrieve_text_candidates(self.ui.query.text_query("shoes"), records)
        self.assertEqual([c["product"]["product_id"] for c in found], [10, 3, 2, 1])
        image = self.ui.image.encode(self.ui.image.supported_images()[0])
        self.assertEqual(len(self.ui.search.retrieve_image_candidates(image)), 40)
        self.assertIn(3, [c["product"]["product_id"] for c in self.ui.search.search(self.ui.query.text_query("red running shoes"))])

    def test_voice_sequence_and_empty_rejection(self):
        events = Mock()
        for obj, method in [(self.ui.speech, "transcribe"), (self.ui.query, "voice_query"),
                            (self.ui.search, "search"), (self.ui.search.products, "all_products"),
                            (self.ui.search, "retrieve_text_candidates"), (self.ui.search.ranking, "rank"),
                            (self.ui.view, "results")]:
            wrapped = Mock(wraps=getattr(obj, method))
            setattr(obj, method, wrapped)
            events.attach_mock(wrapped, method)
        with contextlib.redirect_stdout(io.StringIO()):
            self.ui.run_search("voice", "running shoes")
        self.assertEqual([c[0] for c in events.mock_calls],
                         ["transcribe", "voice_query", "search", "all_products", "retrieve_text_candidates", "rank", "results"])
        events.reset_mock()
        with self.assertRaises(ValueError):
            self.ui.run_search("voice", "  ")
        self.assertEqual([c[0] for c in events.mock_calls], ["transcribe"])

    def test_storage_paths_and_missing_files(self):
        path = self.ui.image.supported_images()[0]
        self.assertEqual(self.ui.image.encode(path), self.ui.image.encode(str(ROOT / path)))
        with self.assertRaises(FileNotFoundError):
            self.ui.image.encode("not-supported.png")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                ProductRepository(root / "missing.json")
            (root / "mapping.json").write_text(json.dumps({"missing.png": [1, 0]}))
            with self.assertRaises(FileNotFoundError):
                ImageStorage(root, root / "mapping.json", 2)
            (root / "vectors.json").write_text(json.dumps({"1": [1, 0], "2": [1]}))
            with self.assertRaises(ValueError):
                VectorIndex(root / "vectors.json")

    def test_product_details_and_menu_errors(self):
        self.assertIsNone(self.ui.search.get_product(999))
        with self.assertRaises(ValueError):
            self.ui.search.get_product(-1)
        with patch("builtins.input", side_effect=["9", "4", "bad", "1", "shoes", "no", "0"]), contextlib.redirect_stdout(io.StringIO()) as output:
            self.ui.interactive()
        self.assertIn("Invalid menu choice", output.getvalue())
        self.assertIn("top_k must be a positive integer", output.getvalue())


if __name__ == "__main__":
    unittest.main()
