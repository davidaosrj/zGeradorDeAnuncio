"""Frontend e API HTTP para cadastro e geração de anúncios."""

from __future__ import annotations

from pathlib import Path
from typing import List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse

from .offline import OfflineGenerationError
from .pipeline import IMAGE_SUFFIXES, generate_advertisement
from .repository import ProductRepository, ProductRepositoryError

app = FastAPI(title="Gerador de Anúncios", version="0.2.0")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/api/products")
async def create_product(
    sku: str = Form(...), nome: str = Form(...), quantidade: int = Form(..., ge=1),
    medidas: str = Form(""), cores: str = Form(""), compatibilidade: str = Form(""),
    itens_inclusos: str = Form(""), itens_nao_inclusos: str = Form(""),
    beneficios: str = Form(""), observacoes: str = Form(""),
    processo_fabricacao: str = Form(""), images: List[UploadFile] = File(...),
) -> dict:
    repo = ProductRepository()
    data = {
        "sku": sku, "nome": nome, "quantidade": quantidade, "material": None,
        "processo_fabricacao": processo_fabricacao or None,
        "medidas": _csv(medidas), "cores_fixas": [], "cores_variaveis": _csv(cores),
        "compatibilidade": _csv(compatibilidade), "itens_inclusos": _csv(itens_inclusos),
        "itens_nao_inclusos": _csv(itens_nao_inclusos),
        "beneficios_confirmados": _csv(beneficios), "observacoes": _csv(observacoes),
    }
    try:
        target = repo.save_product(data)
        image_dir = target / "IMG_ORIGINAL"
        saved = 0
        for upload in images:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in IMAGE_SUFFIXES:
                raise ProductRepositoryError(f"Formato não permitido: {suffix}")
            name = f"foto_{saved + 1:02d}{suffix}"
            content = await upload.read()
            if not content or len(content) > 20 * 1024 * 1024:
                raise ProductRepositoryError("Imagem vazia ou maior que 20 MB")
            (image_dir / name).write_bytes(content); saved += 1
        return {"ok": True, "sku": data["sku"], "images": saved, "path": str(target)}
    except (ProductRepositoryError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/products/{sku}/generate")
async def generate(sku: str, mode: str = "auto") -> dict:
    if mode not in {"auto", "offline", "online"}:
        raise HTTPException(400, "Modo inválido")
    repo = ProductRepository()
    try:
        target = repo.product_dir(sku)
        output = await run_in_threadpool(generate_advertisement, target, mode=mode)
        return {"ok": True, "output": str(output), "status": repo.status(sku)}
    except (ProductRepositoryError, OfflineGenerationError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/products/{sku}")
def product_status(sku: str) -> dict:
    try: return ProductRepository().status(sku)
    except ProductRepositoryError as exc: raise HTTPException(400, str(exc)) from exc


def main() -> None:
    uvicorn.run("gerador_anuncios.web:app", host="0.0.0.0", port=8000)
