"""Pré-geração determinística de anúncios, sem rede ou modelo de linguagem."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LIST_FIELDS = (
    "medidas",
    "cores_fixas",
    "cores_variaveis",
    "compatibilidade",
    "itens_inclusos",
    "itens_nao_inclusos",
    "beneficios_confirmados",
    "observacoes",
)
SCALAR_FIELDS = ("sku", "nome", "quantidade", "material", "processo_fabricacao")


class OfflineGenerationError(ValueError):
    """Entrada insuficiente ou inválida para geração offline."""


def _load_product(path: Path) -> tuple[Path, dict[str, Any]]:
    json_path = path if path.is_file() else path / "produto.json"
    if not json_path.is_file():
        raise OfflineGenerationError(f"produto.json não encontrado em {json_path}")
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OfflineGenerationError(f"produto.json inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise OfflineGenerationError("produto.json deve conter um objeto JSON")
    if not isinstance(data.get("nome"), str) or not data["nome"].strip():
        raise OfflineGenerationError("O campo 'nome' é obrigatório para pré-geração offline")
    for field in LIST_FIELDS:
        value = data.get(field, [])
        if value is not None and (
            not isinstance(value, list) or any(not isinstance(item, str) for item in value)
        ):
            raise OfflineGenerationError(f"O campo '{field}' deve ser uma lista de textos")
    return json_path, data


def _values(data: dict[str, Any], field: str) -> list[str]:
    return data.get(field) or []


def _section(title: str, values: list[str]) -> list[str]:
    return [title, *values, ""] if values else []


def _build_title(data: dict[str, Any]) -> str:
    quantity = data.get("quantidade")
    name = data["nome"].strip()
    return name if quantity is None or str(quantity) in name else f"{name} — Kit com {quantity} unidades"


def _build_full_description(data: dict[str, Any]) -> str:
    lines = [data["nome"].strip(), ""]
    benefits = _values(data, "beneficios_confirmados")
    if benefits:
        lines.extend([benefits[0], ""])
    lines += _section("O KIT CONTÉM", _values(data, "itens_inclusos"))
    if data.get("material"):
        lines += ["MATERIAL", str(data["material"]), ""]
    if data.get("processo_fabricacao"):
        lines += ["FABRICAÇÃO", str(data["processo_fabricacao"]), ""]
    lines += _section("MEDIDAS", _values(data, "medidas"))
    colors = _values(data, "cores_fixas") + _values(data, "cores_variaveis")
    lines += _section("CORES", colors)
    lines += _section("COMPATIBILIDADE", _values(data, "compatibilidade"))
    lines += _section("BENEFÍCIOS", benefits)
    important = [f"Não acompanha: {item}" for item in _values(data, "itens_nao_inclusos")]
    important += _values(data, "observacoes")
    lines += _section("IMPORTANTE", important)
    return "\n".join(lines).rstrip() + "\n"


def _build_summary(data: dict[str, Any]) -> str:
    custom = data.get("descricao_resumida_personalizada")
    if isinstance(custom, str) and custom.strip():
        return custom.strip() + "\n"
    parts = [data["nome"].strip()]
    benefits = _values(data, "beneficios_confirmados")
    if benefits:
        parts.append(benefits[0])
    included = _values(data, "itens_inclusos")
    if included:
        parts.append("Inclui: " + "; ".join(included))
    return ". ".join(part.rstrip(".") for part in parts) + ".\n"


def _manifest(data: dict[str, Any]) -> dict[str, Any]:
    tracked: dict[str, Any] = {}
    for field in SCALAR_FIELDS:
        value = data.get(field)
        tracked[field] = {
            "valor": value,
            "origem": "produto.json" if value is not None else None,
            "confirmado": value is not None,
        }
    for field in LIST_FIELDS:
        value = _values(data, field)
        tracked[field] = {
            "valor": value,
            "origem": "produto.json" if value else None,
            "confirmado": bool(value),
        }
    return {
        "modo": "offline",
        "produto": tracked,
        "visual": {
            "analisado": False,
            "imagem_principal": None,
            "imagens_secundarias": [],
        },
        "pendencias": ["analise_visual_nao_realizada", "artes_nao_geradas"],
    }


def generate_offline(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    data_override: dict[str, Any] | None = None,
) -> Path:
    source, loaded = _load_product(Path(input_path))
    data = data_override if data_override is not None else loaded
    output = Path(output_path) if output_path else source.parent / "saida"
    output.mkdir(parents=True, exist_ok=True)

    title = _build_title(data)
    full = _build_full_description(data)
    summary = _build_summary(data)
    announcement = f"# {title}\n\n## Descrição completa\n\n{full}\n## Descrição resumida\n\n{summary}"
    files = {
        "titulo.txt": title + "\n",
        "descricao_completa.txt": full,
        "descricao_resumida.txt": summary,
        "anuncio.md": announcement,
        "produto_analisado.json": json.dumps(_manifest(data), ensure_ascii=False, indent=2) + "\n",
        "processamento.log": (
            "[OK] produto.json encontrado\n"
            "[OK] Pré-geração textual offline concluída\n"
            "[INFO] Análise visual não realizada\n"
            "[INFO] Artes e ZIP pendentes\n"
        ),
    }
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8")
    return output
