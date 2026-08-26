import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from gerador_anuncios.web import download_generated_advertisement


class WebDownloadTest(unittest.TestCase):
    def test_packages_complete_output_for_browser_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "SKU_WEB" / "saida"
            (output / "imagens").mkdir(parents=True)
            (output / "titulo.txt").write_text("Produto", encoding="utf-8")
            (output / "imagens" / "01_CAPA.png").write_bytes(b"png")
            with patch.dict(os.environ, {"PRODUCTS_ROOT": str(root)}):
                response = download_generated_advertisement("SKU_WEB")
                archive = Path(response.path)
                self.assertEqual(response.filename, "SKU_WEB_Anuncio_Completo.zip")
                with zipfile.ZipFile(archive) as bundle:
                    self.assertEqual(
                        sorted(bundle.namelist()),
                        ["imagens/01_CAPA.png", "titulo.txt"],
                    )


if __name__ == "__main__":
    unittest.main()
