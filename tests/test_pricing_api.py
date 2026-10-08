import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from gerador_anuncios.web import app
from test_pricing import sample


class PricingApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'PRICING_DB': self.temp.name + '/pricing.sqlite3'})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def test_calculate_persists_snapshot(self):
        data = sample()
        response = self.client.post('/api/pricing/calculate', json=data)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result['commercial_price'], '46.37')
        self.assertTrue(result['history_id'])
        history = self.client.get('/api/pricing/history').json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['data']['snapshot'], data)
        self.assertEqual(history[0]['data']['profit'], '13.91')

    def test_invalid_calculation_not_saved(self):
        for value in [{'components': []}, {**sample(), 'target_margin_pct': '80'}, {'components': [None]}]:
            self.assertEqual(self.client.post('/api/pricing/calculate', json=value).status_code, 422)
        self.assertEqual(self.client.get('/api/pricing/history').json(), [])
        self.assertEqual(self.client.get('/api/pricing/history?limit=501').status_code, 422)
        self.assertEqual(self.client.get('/api/pricing/history?offset=-1').status_code, 422)

    def test_catalog_revision_and_asset_routes(self):
        for price in ['120', '150']:
            response = self.client.post('/api/pricing/catalogs/materials', json={'name': 'PLA', 'price_kg': price})
            self.assertEqual(response.status_code, 200)
        revisions = self.client.get('/api/pricing/catalogs/materials').json()
        self.assertEqual([r['data']['price_kg'] for r in revisions], ['150', '120'])
        self.assertNotEqual(revisions[0]['id'], revisions[1]['id'])
        self.assertEqual(self.client.get('/api/pricing/catalogs/unknown').status_code, 404)
        self.assertEqual(self.client.post('/api/pricing/catalogs/printers', json={'name': 'Bad', 'machine_hour': -1}).status_code, 422)
        self.assertEqual(self.client.get('/impressao-3d').status_code, 200)
        for path in ['/pricing-ui.js', '/pricing-engine.js']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('application/javascript', response.headers['content-type'])


if __name__ == '__main__': unittest.main()
