"""Sincroniza o Pages e empacota o leitor; --check garante artefatos reproduzíveis."""
from pathlib import Path
import argparse
import io
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def extension_archive():
    stream = io.BytesIO()
    folder = ROOT / 'extensions/leitor-anuncios'
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            if path.suffix not in {'.js', '.json', '.txt'}:
                continue
            info = zipfile.ZipInfo(path.name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return stream.getvalue()


def build(check=False):
    source = ROOT / 'src/gerador_anuncios/static'
    target = ROOT / 'site/impressao-3d'
    page = (source / 'pricing.html').read_text(encoding='utf-8')
    page = page.replace('data-api="true"', 'data-api="false"')
    for old, new in [('/logo-zonegeeklab3d.png', '../logo-zonegeeklab3d.png'), ('/calculadora-marketplaces', '../'), ('/pricing-engine.js', './pricing-engine.js'), ('/pricing-ui.js', './pricing-ui.js'), ('/listing-reader.js', './listing-reader.js'), ('/leitor-anuncios.zip', './leitor-anuncios.zip')]:
        page = page.replace('"' + old + '"', '"' + new + '"')
    files = {target / 'index.html': page.encode(), **{target / name: (source / name).read_bytes() for name in ['pricing-engine.js', 'pricing-ui.js', 'listing-reader.js']}}
    archive = extension_archive()
    files[target / 'leitor-anuncios.zip'] = archive
    files[source / 'leitor-anuncios.zip'] = archive
    for path, content in files.items():
        if check:
            if not path.exists() or path.read_bytes() != content:
                raise SystemExit(f'{path.relative_to(ROOT)} desatualizado; execute python scripts/build_pricing_site.py')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
