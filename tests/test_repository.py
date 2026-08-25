import tempfile
import unittest
from pathlib import Path

from gerador_anuncios.repository import ProductRepository, ProductRepositoryError, normalize_sku


class ProductRepositoryTest(unittest.TestCase):
    def test_saves_and_reports_product(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = ProductRepository(Path(temporary))
            target = repo.save_product({"sku": "SKU 001", "nome": "Produto", "quantidade": 2})
            (target / "IMG_ORIGINAL" / "foto.jpg").write_bytes(b"image")
            status = repo.status("SKU_001")
            self.assertTrue(status["exists"])
            self.assertEqual(status["input_images"], 1)

    def test_rejects_invalid_sku(self):
        with self.assertRaises(ProductRepositoryError):
            normalize_sku("../")


if __name__ == "__main__":
    unittest.main()
