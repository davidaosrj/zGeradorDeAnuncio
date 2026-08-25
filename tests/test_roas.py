import unittest

from gerador_anuncios.roas import RoasValidationError, calculate_simulation, evaluate_campaign


def profile():
    return {
        "marketplace": "shopee", "sku": "SKU1", "price": 100,
        "costs": {"product": 30, "packaging": 5, "commission_pct": 10, "tax_pct": 5},
        "stock": {"physical": 100, "reserved": 0, "safety": 10},
        "campaign": {"credit_total": 300, "daily_credit_limit": 30, "desired_daily_budget": 40,
                     "cashflow_daily_limit": 35, "horizon_days": 30, "minimum_net_margin_pct": 10},
    }


class RoasSimulationTest(unittest.TestCase):
    def test_calculates_economics_and_credit_limit(self):
        result = calculate_simulation(profile())
        self.assertEqual(result["economics"]["contribution_margin"], "50.00")
        self.assertEqual(result["economics"]["break_even_roas"], "2.0000")
        self.assertEqual(result["economics"]["minimum_safe_roas"], "2.5000")
        self.assertEqual(result["budget"]["recommended_daily"], "10.00")
        self.assertEqual(result["budget"]["limiting_factor"], "credito_por_dia")

    def test_blocks_non_positive_margin(self):
        data = profile(); data["costs"]["product"] = 100
        result = calculate_simulation(data)
        self.assertFalse(result["safe"])
        self.assertEqual(result["budget"]["recommended_daily"], "0.00")

    def test_rejects_bad_percentage(self):
        data = profile(); data["costs"]["tax_pct"] = 101
        with self.assertRaises(RoasValidationError): calculate_simulation(data)

    def test_waits_for_mature_sample(self):
        data = profile(); data["actual"] = {"ad_spend": 10, "clicks": 5, "attributed_orders": 1}
        self.assertEqual(evaluate_campaign(data)["evaluation"]["state"], "EM_APRENDIZADO")

    def test_detects_loss_and_healthy_campaign(self):
        loss = profile(); loss["actual"] = {"ad_spend": 100, "attributed_revenue": 150, "clicks": 100,
                                              "attributed_orders": 5, "attributed_units": 5, "data_matured": True}
        self.assertEqual(evaluate_campaign(loss)["evaluation"]["state"], "RISCO_DE_PREJUIZO")
        healthy = profile(); healthy["actual"] = {"ad_spend": 100, "attributed_revenue": 500, "clicks": 100,
                                                    "attributed_orders": 5, "attributed_units": 5, "data_matured": True}
        self.assertEqual(evaluate_campaign(healthy)["evaluation"]["state"], "SAUDAVEL")


if __name__ == "__main__": unittest.main()
