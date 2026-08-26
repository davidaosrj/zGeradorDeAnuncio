"""Frontend e API HTTP para cadastro e geração de anúncios."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse

from .offline import OfflineGenerationError
from .pipeline import IMAGE_SUFFIXES, generate_advertisement
from .repository import ProductRepository, ProductRepositoryError
from .roas import RoasValidationError, calculate_simulation, evaluate_campaign
from .sale_calculator import calculate_ideal_price, calculate_sale_profit

app = FastAPI(title="Gerador de Anúncios", version="0.2.0")
STATIC_DIR = Path(__file__).parent / "static"


def _absolute_outputs_enabled() -> bool:
    return os.getenv("ALLOW_ABSOLUTE_OUTPUT_PATHS", "").lower() in {"1", "true", "yes"}


def _output_browser_roots() -> list[Path]:
    configured = os.getenv("OUTPUT_BROWSER_ROOTS", "")
    candidates = [Path(item) for item in configured.split(os.pathsep) if item] if configured else [Path("/mnt/c"), ProductRepository().root]
    return [path.expanduser().resolve() for path in candidates if path.expanduser().is_dir()]


def _inside(path: Path, roots: list[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def _listable_directory(path: Path, roots: list[Path]) -> bool:
    """Confirma que a pasta pode ser aberta e não escapa por link simbólico."""
    try:
        resolved = path.resolve()
        if not _inside(resolved, roots) or not resolved.is_dir():
            return False
        with os.scandir(resolved):
            return True
    except OSError:
        return False


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/roas", response_class=HTMLResponse)
def roas_page() -> str:
    return (STATIC_DIR / "roas.html").read_text(encoding="utf-8")


@app.get("/calculadora-shopee", response_class=HTMLResponse)
def shopee_calculator_page() -> str:
    return (STATIC_DIR / "sale-calculator.html").read_text(encoding="utf-8")


@app.get("/calculadora-mercado-livre", response_class=HTMLResponse)
def mercado_livre_calculator_page() -> str:
    return (STATIC_DIR / "mercado-livre-calculator.html").read_text(encoding="utf-8")


@app.get("/calculadora-marketplaces", response_class=HTMLResponse)
def marketplace_calculator_page() -> str:
    return (STATIC_DIR / "marketplace-calculator.html").read_text(encoding="utf-8")


@app.get("/marketplace-admin.js", response_class=FileResponse)
def marketplace_admin_script() -> FileResponse:
    return FileResponse(STATIC_DIR / "marketplace-admin.js", media_type="application/javascript")


@app.get("/mercado-livre-calculator.js", response_class=FileResponse)
def mercado_livre_calculator_script() -> FileResponse:
    return FileResponse(STATIC_DIR / "mercado-livre-calculator.js", media_type="application/javascript")


@app.get("/logo-zonegeeklab3d.png", response_class=FileResponse)
def brand_logo() -> Path:
    return STATIC_DIR / "logo-zonegeeklab3d.png"


@app.get("/favicon.ico", response_class=FileResponse)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "logo-zonegeeklab3d.png", media_type="image/png")


@app.get("/api/output-directories")
def output_directories(path: Optional[str] = None) -> dict:
    if not _absolute_outputs_enabled():
        raise HTTPException(403, "Seletor desabilitado. Configure ALLOW_ABSOLUTE_OUTPUT_PATHS=true")
    roots = _output_browser_roots()
    if not roots:
        raise HTTPException(503, "Nenhuma raiz de saída está disponível")
    current = Path(path).expanduser().resolve() if path else roots[0]
    if not _inside(current, roots) or not current.is_dir():
        raise HTTPException(400, "Diretório fora das raízes autorizadas ou inexistente")
    try:
        directories = sorted(
            (
                item
                for item in current.iterdir()
                if not item.name.startswith(".") and _listable_directory(item, roots)
            ),
            key=lambda item: item.name.lower(),
        )
    except OSError as exc:
        raise HTTPException(403, "Sem permissão para listar este diretório") from exc
    parent = current.parent if current.parent != current and _inside(current.parent, roots) else None
    return {"current": str(current), "parent": str(parent) if parent else None, "directories": [{"name": item.name, "path": str(item.resolve())} for item in directories], "roots": [str(root) for root in roots]}


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
async def generate(sku: str, mode: str = "auto", output_path: Optional[str] = None) -> dict:
    if mode not in {"auto", "offline", "online"}:
        raise HTTPException(400, "Modo inválido")
    repo = ProductRepository()
    try:
        target = repo.product_dir(sku)
        custom_output = None
        if output_path and output_path.strip():
            requested = Path(output_path.strip()).expanduser()
            if requested.is_absolute():
                if not _absolute_outputs_enabled():
                    raise ProductRepositoryError(
                        "Caminho absoluto bloqueado. Inicie com ALLOW_ABSOLUTE_OUTPUT_PATHS=true ou use uma subpasta relativa."
                    )
                custom_output = requested.resolve()
                if not _inside(custom_output, _output_browser_roots()):
                    raise ProductRepositoryError("Diretório de saída fora das raízes autorizadas")
            else:
                custom_output = (target / requested).resolve()
                product_root = target.resolve()
                if custom_output != product_root and product_root not in custom_output.parents:
                    raise ProductRepositoryError("A subpasta de saída não pode sair do diretório do produto")
        output = await run_in_threadpool(generate_advertisement, target, mode=mode, output_path=custom_output)
        return {"ok": True, "output": str(output), "status": repo.status(sku)}
    except (ProductRepositoryError, OfflineGenerationError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/products/{sku}")
def product_status(sku: str) -> dict:
    try: return ProductRepository().status(sku)
    except ProductRepositoryError as exc: raise HTTPException(400, str(exc)) from exc


@app.post("/api/roas/simulate")
def simulate_roas(profile: dict) -> dict:
    try: return calculate_simulation(profile)
    except RoasValidationError as exc: raise HTTPException(422, str(exc)) from exc


@app.post("/api/roas/evaluate")
def evaluate_roas(profile: dict) -> dict:
    try: return evaluate_campaign(profile)
    except RoasValidationError as exc: raise HTTPException(422, str(exc)) from exc


@app.post("/api/calculator/sale-profit")
def sale_profit(data: dict) -> dict:
    try: return calculate_sale_profit(data)
    except RoasValidationError as exc: raise HTTPException(422, str(exc)) from exc


@app.post("/api/calculator/ideal-price")
def ideal_price(data: dict) -> dict:
    try: return calculate_ideal_price(data)
    except RoasValidationError as exc: raise HTTPException(422, str(exc)) from exc


def main() -> None:
    uvicorn.run("gerador_anuncios.web:app", host="0.0.0.0", port=8000)
