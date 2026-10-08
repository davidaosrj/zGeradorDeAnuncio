"""Histórico e revisões imutáveis dos cadastros de precificação."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from .pricing import PricingError, amount, rate, calculate_pricing

CATALOGS = {'materials', 'printers', 'products', 'fee-rules'}


class PricingRepository:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv('PRICING_DB', 'data/pricing.sqlite3'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, kind, payload):
        record = {'id': str(uuid4()), 'created_at': datetime.now(timezone.utc).isoformat(), 'data': deepcopy(payload)}
        try:
            encoded = json.dumps(record['data'], ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError) as exc:
            raise PricingError('Dados não serializáveis em JSON válido') from exc
        with self.connection() as db:
            db.execute('INSERT INTO records VALUES (?, ?, ?, ?)', (record['id'], kind, record['created_at'], encoded))
        return record

    def list(self, kind, limit=100, offset=0):
        with self.connection() as db:
            rows = db.execute('SELECT id, created_at, payload FROM records WHERE kind = ? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?', (kind, limit, offset)).fetchall()
        return [{'id': row[0], 'created_at': row[1], 'data': json.loads(row[2])} for row in rows]

    def catalog(self, kind, data):
        if kind not in CATALOGS:
            raise PricingError('Cadastro inválido')
        if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not data['name'].strip():
            raise PricingError('Informe o nome do cadastro')
        fields = {'materials': ('price_kg',), 'printers': ('machine_hour', 'energy_hour'), 'products': ('weight_g', 'hours'), 'fee-rules': ('commission_pct', 'fixed_fee')}
        for field in fields[kind]:
            amount(data.get(field), field)
        if kind == 'fee-rules':
            if data.get('marketplace') not in {'shopee', 'mercado_livre', 'direct'} or data.get('basis') not in {'order', 'unit'}:
                raise PricingError('Marketplace ou base de cobrança inválida')
            if not str(data.get('version', '')).strip() or amount(data['commission_pct'], 'commission_pct') >= 100:
                raise PricingError('Informe versão e comissão menor que 100%')
        if kind == 'fee-rules':
            if sum(rate(data, field) for field in ('commission_pct', 'payment_pct', 'tax_pct')) >= 1:
                raise PricingError('Taxas devem somar menos de 100%')
        if kind == 'products' and 'scenario' in data:
            calculate_pricing(data['scenario'])
        return self.save(kind, data)
