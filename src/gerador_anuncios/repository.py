"""Persistência local segura para produtos cadastrados pelo frontend e MCP."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


class ProductRepositoryError(ValueError):
    pass


def products_root() -> Path:
    return Path(os.getenv("PRODUCTS_ROOT", "data/products")).resolve()


def normalize_sku(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    if not slug or len(slug) > 80:
        raise ProductRepositoryError("SKU inválido; use letras, números, hífen ou sublinhado")
    return slug


class ProductRepository:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or products_root()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def product_dir(self, sku: str) -> Path:
        target = (self.root / normalize_sku(sku)).resolve()
        if target.parent != self.root:
            raise ProductRepositoryError("Produto fora do diretório autorizado")
        return target

    def save_product(self, data: dict[str, Any]) -> Path:
        sku = normalize_sku(str(data.get("sku", "")))
        if not isinstance(data.get("nome"), str) or not data["nome"].strip():
            raise ProductRepositoryError("Nome do produto é obrigatório")
        target = self.product_dir(sku)
        (target / "IMG_ORIGINAL").mkdir(parents=True, exist_ok=True)
        (target / "produto.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return target

    def load_product(self, sku: str) -> dict[str, Any]:
        path = self.product_dir(sku) / "produto.json"
        if not path.is_file():
            raise ProductRepositoryError(f"Produto {sku} não encontrado")
        return json.loads(path.read_text(encoding="utf-8"))

    def status(self, sku: str) -> dict[str, Any]:
        target = self.product_dir(sku)
        images = sorted((target / "IMG_ORIGINAL").glob("*")) if target.exists() else []
        outputs = sorted((target / "saida").rglob("*")) if (target / "saida").exists() else []
        return {
            "sku": normalize_sku(sku),
            "exists": (target / "produto.json").is_file(),
            "input_images": len([p for p in images if p.is_file()]),
            "output_files": len([p for p in outputs if p.is_file()]),
            "path": str(target),
        }
