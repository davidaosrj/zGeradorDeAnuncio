from decimal import Decimal
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from gerador_anuncios.pricing import PricingError, calculate_pricing
from gerador_anuncios.pricing_repository import PricingRepository

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return {
        'name': 'Dinossauro', 'currency': 'BRL', 'calculation_date': '2026-10-08',
        'components': [{'name': 'Peça', 'quantity': '1', 'weight_g': '55', 'hours': '3', 'filament_price_kg': '120', 'machine_hour': '2', 'energy_hour': '0.25'}],
        'order_units': '1', 'packaging_cost': '4', 'packaging_count': '1',
        'failure_pct': '10', 'target_margin_pct': '30',
        'fee_rule': {'marketplace': 'shopee', 'version': 'exemplo-1', 'commission_pct': '20', 'fixed_fee': '4.50', 'basis': 'order'},
    }


class PricingTest(unittest.TestCase):
    def test_adr_example(self):
        result = calculate_pricing(sample())
        self.assertEqual(Decimal(result['production_cost_exact']), Decimal('18.685'))
        self.assertEqual(result['calculated_price'], '46.37')
        self.assertEqual(result['break_even_price'], '28.99')
        self.assertEqual(result['profit'], '13.91')
        self.assertEqual(result['margin_pct'], '30.00')
        self.assertEqual(result['classification'], 'Alta')

    def test_kit_order_and_unit_fee_and_single_packaging(self):
        data = sample()
        data['order_units'] = '2'
        data['components'][0]['quantity'] = '3'
        data['components'].append({**data['components'][0], 'quantity': '1'})
        result = calculate_pricing(data)
        self.assertEqual(Decimal(result['production_cost_exact']), Decimal('121.48'))
        self.assertEqual(result['packaging'], '4.00')
        self.assertEqual(result['fixed_fee'], '4.50')
        data['fee_rule']['basis'] = 'unit'
        self.assertEqual(calculate_pricing(data)['fixed_fee'], '9.00')

    def test_commercial_price_never_reduces_margin(self):
        data = sample()
        data['commercial_step'] = '0.10'
        result = calculate_pricing(data)
        self.assertEqual(result['commercial_price'], '46.40')
        self.assertGreaterEqual(Decimal(result['margin_pct']), Decimal('30'))
        data['selling_price'] = '20'
        self.assertEqual(calculate_pricing(data)['classification'], 'Inviável')

    def test_tax_shipping_assembly_direct_sale_and_discounts(self):
        data = sample()
        data.update(assembly_cost='5', shipping='7', discount='2', order_other_cost='3', target_margin_pct='0')
        data['fee_rule'].update(marketplace='direct', commission_pct='0', fixed_fee='0', tax_pct='5', payment_pct='2')
        result = calculate_pricing(data)
        self.assertEqual(result['production_cost'], '23.69')
        self.assertEqual(result['commercial_price'], '38.38')
        self.assertEqual(result['fixed_fee'], '0.00')

    def test_competitor_classification_and_missing_data(self):
        data = sample()
        observation = {'url': 'https://example.com/product', 'collected_at': '2026-10-08', 'displayed_sales': '500'}
        data['competitors'] = [{**observation, 'price': p} for p in ['50', '40', '20']] + [{'price': '50'}]
        result = calculate_pricing(data)
        self.assertEqual([x['classification'] for x in result['comparisons']], ['Alta', 'Moderada', 'Inviável', 'Indeterminada'])
        self.assertEqual(result['comparisons'][0]['observation']['displayed_sales'], '500')

    def test_rejects_invalid_inputs(self):
        changes = [
            {'target_margin_pct': '80'}, {'target_margin_pct': '101'}, {'order_units': '1.2'},
            {'order_units': '0'}, {'packaging_count': '0'}, {'commercial_step': '0'},
            {'commercial_step': '0.001'}, {'selling_price': '0'}, {'shipping': '-1'},
            {'shipping': 'NaN'}, {'shipping': 'Infinity'}, {'shipping': True}, {'shipping': '1e3'},
            {'shipping': '0.0000001'}, {'shipping': '1000000001'}, {'currency': 'USD'},
            {'components': []}, {'components': [None]}, {'competitors': 'invalid'}, {'competitors': [None]},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(PricingError):
                calculate_pricing({**sample(), **change})

    def test_rule_dates_and_price_range(self):
        for field, value in [('valid_from','2026-10-09'), ('valid_until','2026-10-07'), ('valid_from','bad'), ('min_price','50'), ('max_price','46.37')]:
            data = sample(); data['fee_rule'][field] = value
            with self.subTest(field=field), self.assertRaises(PricingError):
                calculate_pricing(data)
        data = sample(); data['fee_rule'].update(valid_from='2026-10-08', valid_until='2026-10-08', min_price='46.37', max_price='46.38')
        self.assertEqual(calculate_pricing(data)['commercial_price'], '46.37')

    def test_snapshot_independence_and_repository(self):
        data = sample(); result = calculate_pricing(data)
        data['fee_rule']['commission_pct'] = '99'
        self.assertEqual(result['snapshot']['fee_rule']['commission_pct'], '20')
        with tempfile.TemporaryDirectory() as temp:
            repo = PricingRepository(Path(temp) / 'pricing.db')
            record = repo.save('history', result)
            repo.catalog('materials', {'name':'PLA', 'price_kg':'120'})
            repo.catalog('materials', {'name':'PLA', 'price_kg':'150'})
            result['profit'] = '0'
            self.assertEqual(repo.list('history')[0], record)
            self.assertEqual(len(repo.list('materials')), 2)
            self.assertEqual(len(repo.list('materials', 1, 1)), 1)
            with self.assertRaises(PricingError): repo.catalog('materials', {'name':'PLA', 'price_kg':'-1'})

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser parity')
    def test_python_browser_parity(self):
        cases = [sample()]
        rng = random.Random(2002)
        for _ in range(80):
            data = sample()
            data['components'] = [dict(name='Peça', quantity=str(rng.randint(1, 9)), weight_g=f'{rng.randint(1,900)}.123456', hours=f'{rng.randint(0,20)}.012345', filament_price_kg=f'{rng.randint(1,300)}.99', machine_hour='2.123456', energy_hour='0.256789', additional_cost='0.002345') for _ in range(rng.randint(1,4))]
            data.update(order_units=str(rng.randint(1,5)), packaging_count=str(rng.randint(1,4)), commercial_step=rng.choice(['0.01','0.10','0.50','1']), shipping='2.15', discount='1.05', assembly_cost='3.33', target_margin_pct=str(rng.randint(0, 65)))
            data['fee_rule'].update(commission_pct='20', payment_pct='2', tax_pct='5', basis=rng.choice(['order','unit']))
            cases.append(data)
        edge = sample(); edge['target_margin_pct'] = '79.999999'; cases.append(edge)
        script = "const fs=require('fs'), engine=require('./src/gerador_anuncios/static/pricing-engine.js');process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(x=>engine.calculate(x))));"
        process = subprocess.run(['node','-e',script], cwd=ROOT, input=json.dumps(cases), text=True, capture_output=True, check=True)
        results = json.loads(process.stdout)
        for data, browser in zip(cases, results):
            python = calculate_pricing(data)
            self.assertEqual(Decimal(python.pop('production_cost_exact')), Decimal(browser.pop('production_cost_exact')))
            self.assertEqual(python, browser)

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser parity')
    def test_browser_rejects_financially_invalid_data(self):
        changes = [{'target_margin_pct': '80'}, {'shipping': '-1'}, {'shipping': 'NaN'}, {'order_units': '0'}, {'commercial_step': '0.001'}, {'components': []}, {'selling_price': '0'}]
        cases = [{**sample(), **change} for change in changes]
        script = "const fs=require('fs'),e=require('./src/gerador_anuncios/static/pricing-engine.js');process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(x=>{try{e.calculate(x);return false}catch(err){return true}})));"
        result = subprocess.run(['node', '-e', script], cwd=ROOT, input=json.dumps(cases), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), [True] * len(cases))

    def test_static_site_matches_source(self):
        import runpy
        runpy.run_path(str(ROOT / 'scripts/build_pricing_site.py'))['build'](check=True)


if __name__ == '__main__': unittest.main()
