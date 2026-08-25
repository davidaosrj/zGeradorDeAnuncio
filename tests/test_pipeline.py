import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from gerador_anuncios.pipeline import generate_advertisement


class PipelineTest(unittest.TestCase):
    def test_offline_creates_variants_images_and_zips(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "IMG_ORIGINAL").mkdir()
            Image.new("RGB", (320, 240), "red").save(root / "IMG_ORIGINAL" / "foto.jpg")
            (root / "produto.json").write_text(json.dumps({
                "sku": "SKU1", "nome": "Kit de tampas", "quantidade": 2,
                "cores_variaveis": ["vermelho", "laranja"], "medidas": ["3,9 cm"],
                "itens_inclusos": ["2 tampas"], "itens_nao_inclusos": ["cartucho"],
            }), encoding="utf-8")
            output = generate_advertisement(root, mode="offline")
            for color in ("vermelho", "laranja"):
                files = sorted((output / "imagens" / color).glob("*.png"))
                self.assertEqual(len(files), 6)
                for path in files:
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (1000, 1000))
                archive = output / f"SKU1_{color}_Imagens_Anuncio.zip"
                with zipfile.ZipFile(archive) as zf: self.assertEqual(len(zf.namelist()), 6)
