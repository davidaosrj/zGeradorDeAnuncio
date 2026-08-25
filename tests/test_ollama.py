import json
import unittest

from gerador_anuncios.ollama import OllamaClient, OllamaConfig, OllamaError


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


class OllamaClientTest(unittest.TestCase):
    def test_list_models(self):
        client = OllamaClient(opener=lambda *_args, **_kwargs: FakeResponse({"models": [{"name": "modelo:1b"}]}))
        self.assertEqual(client.list_models(), ["modelo:1b"])

    def test_chat(self):
        client = OllamaClient(
            OllamaConfig(model="modelo:1b"),
            opener=lambda *_args, **_kwargs: FakeResponse({"message": {"content": "OK"}}),
        )
        self.assertEqual(client.chat([{"role": "user", "content": "teste"}]), "OK")

    def test_chat_requires_model(self):
        client = OllamaClient(OllamaConfig(model=None))
        with self.assertRaisesRegex(OllamaError, "Informe o modelo"):
            client.chat([{"role": "user", "content": "teste"}])

    def test_invalid_json(self):
        class InvalidResponse(FakeResponse):
            def read(self):
                return b"invalid"

        client = OllamaClient(opener=lambda *_args, **_kwargs: InvalidResponse({}))
        with self.assertRaisesRegex(OllamaError, "JSON inválido"):
            client.list_models()


if __name__ == "__main__":
    unittest.main()
