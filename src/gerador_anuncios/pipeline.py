"""Pipeline completo: copy, artes determinísticas, validação e ZIP."""

from __future__ import annotations

import colorsys
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFont, ImageOps, ImageStat, ImageDraw

from .offline import OfflineGenerationError, generate_offline
from .ollama import OllamaClient, OllamaError

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
ARTS = ("capa", "conteudo", "medidas", "funcionamento", "detalhes", "importante")
COLOR_RGB = {
    "vermelho": (220, 35, 35), "vermelha": (220, 35, 35),
    "laranja": (245, 115, 20), "verde": (35, 170, 85),
    "azul": (35, 105, 210), "preto": (25, 25, 25), "branco": (235, 235, 235),
    "rosa": (225, 110, 145),
}
# Matiz alvo (graus, 0-360) para cores cromáticas. Comparar por matiz, e não pela
# média RGB da foto inteira, evita confundir cores próximas (ex.: vermelho x laranja)
# quando o fundo claro e as sombras da foto diluem a cor média do produto.
COLOR_HUE = {
    "vermelho": 358, "vermelha": 358, "laranja": 28, "amarelo": 50,
    "verde": 130, "azul": 215, "roxo": 275, "rosa": 340,
}
# Cores acromáticas (preto/branco) não têm matiz: comparar por luminosidade média.
COLOR_LIGHTNESS = {"preto": 25, "branco": 235}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{name}", size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= width:
            current = trial
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines


def _images(root: Path) -> list[Path]:
    candidates = []
    for base in (root / "IMG_ORIGINAL", root / "entrada", root):
        if base.is_dir():
            candidates.extend(p for p in base.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    return sorted(set(candidates))


def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _dominant_hue(pixels: list[tuple[int, int, int]]) -> float | None:
    vivid = [p for p in pixels if (max(p) - min(p)) >= 40 and max(p) >= 90]
    if not vivid:
        return None
    hues = sorted(colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)[0] * 360 for p in vivid)
    return hues[len(hues) // 2]


def _color_score(path: Path, color: str) -> float:
    try:
        im = Image.open(path).convert("RGB").resize((160, 160))
        pixels = list(im.getdata())
    except OSError:
        return -1_000
    name = color.lower()
    if name in COLOR_LIGHTNESS:
        avg = sum(sum(p) / 3 for p in pixels) / len(pixels)
        return -abs(avg - COLOR_LIGHTNESS[name])
    hue = COLOR_HUE.get(name)
    if hue is None:
        return 0.0
    dominant = _dominant_hue(pixels)
    return -_hue_distance(dominant, hue) if dominant is not None else -1_000


def _select_image(paths: list[Path], color: str) -> Path:
    name = color.lower()
    if name not in COLOR_HUE and name not in COLOR_LIGHTNESS:
        return paths[0]
    return max(paths, key=lambda p: _color_score(p, color))


def _photo_panel(source: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(source).convert("RGB")
    im = ImageOps.exif_transpose(im)
    im = ImageEnhance.Contrast(im).enhance(1.05)
    return ImageOps.contain(im, size, Image.Resampling.LANCZOS)


def _lines_for(art: str, data: dict[str, Any], color: str) -> tuple[str, list[str]]:
    quantity = data.get("quantidade") or 1
    measures = data.get("medidas") or []
    included = data.get("itens_inclusos") or [f"{quantity} unidade(s)"]
    benefits = data.get("beneficios_confirmados") or []
    excluded = data.get("itens_nao_inclusos") or []
    selected = f"COR SELECIONADA: {color.upper()}" if color != "padrao" else ""
    mapping = {
        "capa": (data["nome"], [f"KIT COM {quantity} UNIDADES", selected]),
        "conteudo": ("CONTEÚDO DO KIT", included + ([selected] if selected else [])),
        "medidas": ("MEDIDAS CONFIRMADAS", measures or ["Consulte a descrição"]),
        "funcionamento": ("COMO UTILIZAR", (data.get("como_usar") or ["Consulte as fotos de demonstração"]) + ["ITENS DE DEMONSTRAÇÃO NÃO INCLUSOS"]),
        "detalhes": ("DETALHES E BENEFÍCIOS", benefits[:4] or ["Características conforme descrição"]),
        "importante": ("IMPORTANTE — NÃO ACOMPANHA", excluded[:5] or ["Somente os itens descritos no kit"]),
    }
    return mapping[art]


def _render(source: Path, output: Path, title: str, lines: list[str], accent: tuple[int, int, int]) -> None:
    canvas = Image.new("RGB", (1000, 1000), "white")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1000, 18), fill=accent)
    title_font, body_font, brand_font = _font(48, True), _font(28), _font(24, True)
    y = 48
    for line in _wrap(draw, title.upper(), title_font, 900)[:3]:
        box = draw.textbbox((0, 0), line, font=title_font)
        draw.text(((1000 - (box[2] - box[0])) / 2, y), line, fill=(25, 25, 25), font=title_font)
        y += 58
    panel = _photo_panel(source, (820, 520))
    canvas.paste(panel, ((1000 - panel.width) // 2, 220 + (520 - panel.height) // 2))
    y = 765
    for item in lines:
        for line in _wrap(draw, str(item), body_font, 860):
            draw.text((70, y), f"• {line}", fill=(40, 40, 40), font=body_font)
            y += 36
            if y > 930: break
        if y > 930: break
    draw.text((30, 960), "zonegeeklab3D", fill=accent, font=brand_font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG")


def _try_ollama_copy(data: dict[str, Any], mode: str, log: list[str]) -> None:
    if mode == "offline": return
    try:
        client = OllamaClient()
        if not client.config.model:
            raise OllamaError("OLLAMA_MODEL não configurado")
        prompt = "Reescreva somente o nome e benefícios abaixo, sem criar fatos. Responda JSON com titulo e resumo.\n" + json.dumps(data, ensure_ascii=False)
        raw = client.chat([{"role": "user", "content": prompt}], format="json")
        candidate = json.loads(raw)
        summary = candidate.get("resumo")
        facts = json.dumps(data, ensure_ascii=False)
        if not isinstance(summary, str):
            raise OllamaError("Resposta não contém resumo")
        invented_numbers = set(re.findall(r"\d+(?:[,.]\d+)?", summary)) - set(re.findall(r"\d+(?:[,.]\d+)?", facts))
        if invented_numbers:
            raise OllamaError(f"Resumo contém números não confirmados: {sorted(invented_numbers)}")
        data["descricao_resumida_personalizada"] = summary
        log.append("[OK] Copy enriquecida pelo Ollama")
    except (OllamaError, json.JSONDecodeError, KeyError) as exc:
        log.append(f"[INFO] Ollama indisponível; fallback offline: {exc}")
        if mode == "online": raise OfflineGenerationError(str(exc)) from exc


def generate_advertisement(input_path: str | Path, *, mode: str = "auto", output_path: str | Path | None = None) -> Path:
    root = Path(input_path)
    json_path = root if root.is_file() else root / "produto.json"
    if root.is_file(): root = root.parent
    try: data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise OfflineGenerationError(f"produto.json inválido: {exc}") from exc
    paths = _images(root)
    if not paths: raise OfflineGenerationError("Nenhuma imagem encontrada em IMG_ORIGINAL, entrada ou diretório do produto")
    log = [f"[OK] {len(paths)} imagens encontradas"]
    _try_ollama_copy(data, mode, log)
    output = Path(output_path) if output_path else root / "saida"
    generate_offline(json_path, output, data_override=data)
    colors = data.get("cores_variaveis") or data.get("cores_fixas") or ["padrao"]
    sku = data.get("sku") or "produto"
    for color in colors:
        variant = re.sub(r"[^a-z0-9_-]+", "_", str(color).lower())
        image_dir = output / "imagens" / variant if len(colors) > 1 else output / "imagens"
        source = _select_image(paths, str(color))
        accent = COLOR_RGB.get(str(color).lower(), (230, 90, 30))
        generated = []
        for index, art in enumerate(ARTS, 1):
            title, lines = _lines_for(art, data, str(color))
            target = image_dir / f"{sku}_{variant}_{index:02d}_{art}.png"
            _render(source, target, title, lines, accent)
            generated.append(target)
            log.append(f"[OK] {target.name}")
        archive = output / f"{sku}_{variant}_Imagens_Anuncio.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in generated: zf.write(path, path.name)
        log.append(f"[OK] {archive.name}")
    manifest_path = output / "produto_analisado.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modo"] = f"pipeline_{mode}"
    manifest["visual"] = {
        "fontes": [str(path.relative_to(root)) for path in paths],
        "artes_geradas": True,
        "validacao_estrutural": True,
        "validacao_visual_semantica": False,
    }
    manifest["pendencias"] = ["validacao_visual_humana_recomendada"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.append("[OK] Validação estrutural concluída: PNG 1000x1000 e ZIP por variante")
    log.append("[INFO] Validação visual humana recomendada")
    (output / "processamento.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    return output
