import unittest

from gerador_anuncios.roas import RoasValidationError
from gerador_anuncios.sale_calculator import calculate_ideal_price, calculate_sale_profit


class SaleCalculatorTest(unittest.TestCase):
    def test_calculates_profit_breakdown(self):
        result = calculate_sale_profit({"selling_price": 100, "product_cost": 30, "packaging": 5,
            "commission_pct": 15, "fixed_fee": 4, "tax_pct": 6, "seller_shipping": 0,
            "ads_mode": "fixed", "ads_value": 10})
        self.assertEqual(result["profit"], "30.00")
        self.assertEqual(result["margin_pct"], "30.00")
        self.assertEqual(result["status"], "LUCRO")

    def test_calculates_price_for_target_margin(self):
        result = calculate_ideal_price({"product_cost": 30, "packaging": 5, "commission_pct": 15,
            "fixed_fee": 4, "tax_pct": 5, "seller_shipping": 0, "ads_mode": "none",
            "ads_value": 0, "target_margin_pct": 20})
        self.assertEqual(result["ideal_price"], "65.00")
        self.assertEqual(result["profit"], "13.00")

    def test_supports_roas_cost(self):
        result = calculate_sale_profit({"selling_price": 100, "product_cost": 40,
            "commission_pct": 10, "tax_pct": 0, "ads_mode": "roas", "ads_value": 5})
        self.assertEqual(result["ads_cost"], "20.00")
        self.assertEqual(result["profit"], "30.00")

    def test_rejects_impossible_target(self):
        with self.assertRaises(RoasValidationError):
            calculate_ideal_price({"product_cost": 10, "commission_pct": 50, "tax_pct": 20,
                "ads_mode": "none", "target_margin_pct": 30})


if __name__ == "__main__": unittest.main()
