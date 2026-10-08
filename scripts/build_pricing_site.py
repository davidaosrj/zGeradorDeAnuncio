"""Sincroniza a calculadora Pages a partir dos arquivos mantidos em static/."""
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]


def build(check=False):
    source = ROOT / 'src/gerador_anuncios/static'
    target = ROOT / 'site/impressao-3d'
    page = (source / 'pricing.html').read_text(encoding='utf-8')
    page = page.replace('data-api="true"', 'data-api="false"')
    for old, new in [('/logo-zonegeeklab3d.png', '../logo-zonegeeklab3d.png'), ('/calculadora-marketplaces', '../'), ('/pricing-engine.js', './pricing-engine.js'), ('/pricing-ui.js', './pricing-ui.js')]:
        page = page.replace('"' + old + '"', '"' + new + '"')
    files = {'index.html': page, **{name: (source / name).read_text(encoding='utf-8') for name in ['pricing-engine.js', 'pricing-ui.js']}}
    for name, content in files.items():
        path = target / name
        if check:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                raise SystemExit(f'{path.relative_to(ROOT)} desatualizado; execute python scripts/build_pricing_site.py')
        else:
            target.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
