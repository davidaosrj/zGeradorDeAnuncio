import json
import tempfile
import unittest
from pathlib import Path

from gerador_anuncios.offline import OfflineGenerationError, generate_offline


class OfflineGenerationTest(unittest.TestCase):
    def test_generates_expected_files_without_inventing_missing_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            product_dir = Path(temporary)
            (product_dir / "produto.json").write_text(
                json.dumps(
                    {
                        "nome": "Tampa de teste",
                        "material": None,
                        "medidas": ["3,9 cm"],
                        "itens_inclusos": ["1 tampa"],
                        "beneficios_confirmados": ["Ajuda a preservar o conteúdo"],
                    }
                ),
                encoding="utf-8",
            )

            output = generate_offline(product_dir)

            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "titulo.txt",
                    "descricao_completa.txt",
                    "descricao_resumida.txt",
                    "anuncio.md",
                    "produto_analisado.json",
                    "processamento.log",
                },
            )
            description = (output / "descricao_completa.txt").read_text(encoding="utf-8")
            self.assertIn("3,9 cm", description)
            self.assertNotIn("MATERIAL", description)
            manifest = json.loads((output / "produto_analisado.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["modo"], "offline")
            self.assertFalse(manifest["visual"]["analisado"])

    def test_requires_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            product_dir = Path(temporary)
            (product_dir / "produto.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(OfflineGenerationError, "nome"):
                generate_offline(product_dir)

    def test_rejects_invalid_list_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            product_dir = Path(temporary)
            (product_dir / "produto.json").write_text(
                json.dumps({"nome": "Produto", "medidas": "3 cm"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(OfflineGenerationError, "medidas"):
                generate_offline(product_dir)


if __name__ == "__main__":
    unittest.main()
