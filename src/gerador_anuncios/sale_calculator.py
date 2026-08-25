"""Calculadora determinística de lucro e preço ideal por venda."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .roas import RoasValidationError, _decimal, _non_negative, _percentage

ZERO = Decimal("0")
MONEY = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def _percent(value: Decimal) -> str:
    return str((value * Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP))


def _inputs(data: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, str, Decimal]:
    product = _non_negative(data.get("product_cost"), "product_cost")
    packaging = _non_negative(data.get("packaging"), "packaging")
    fixed_fee = _non_negative(data.get("fixed_fee"), "fixed_fee")
    shipping = _non_negative(data.get("seller_shipping"), "seller_shipping")
    commission = _percentage(data.get("commission_pct"), "commission_pct")
    tax = _percentage(data.get("tax_pct"), "tax_pct")
    ads_mode = str(data.get("ads_mode", "none"))
    if ads_mode not in {"none", "fixed", "roas"}:
        raise RoasValidationError("ads_mode deve ser none, fixed ou roas")
    ads_value = _non_negative(data.get("ads_value"), "ads_value")
    if ads_mode == "roas" and ads_value <= ZERO:
        raise RoasValidationError("ROAS deve ser maior que zero")
    return product, packaging, fixed_fee, shipping, commission, tax, ads_mode, ads_value


def calculate_sale_profit(data: dict[str, Any]) -> dict[str, Any]:
    price = _decimal(data.get("selling_price"), "selling_price")
    if price <= ZERO:
        raise RoasValidationError("selling_price deve ser maior que zero")
    product, packaging, fixed_fee, shipping, commission, tax, ads_mode, ads_value = _inputs(data)
    commission_value = price * commission
    tax_value = price * tax
    ads_cost = ZERO if ads_mode == "none" else ads_value if ads_mode == "fixed" else price / ads_value
    total_cost = product + packaging + fixed_fee + shipping + commission_value + tax_value + ads_cost
    profit = price - total_cost
    margin = profit / price
    markup = price / (product + packaging) if product + packaging > ZERO else ZERO
    return {
        "selling_price": _money(price), "product_cost": _money(product), "packaging": _money(packaging),
        "commission": _money(commission_value), "commission_pct": _percent(commission),
        "fixed_fee": _money(fixed_fee), "tax": _money(tax_value), "tax_pct": _percent(tax),
        "seller_shipping": _money(shipping), "ads_cost": _money(ads_cost), "total_cost": _money(total_cost),
        "net_receipt": _money(price - commission_value - fixed_fee), "profit": _money(profit),
        "margin_pct": _percent(margin), "markup": str(markup.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
        "status": "LUCRO" if profit > ZERO else "EMPATE" if profit == ZERO else "PREJUIZO",
    }


def calculate_ideal_price(data: dict[str, Any]) -> dict[str, Any]:
    product, packaging, fixed_fee, shipping, commission, tax, ads_mode, ads_value = _inputs(data)
    target_margin = _percentage(data.get("target_margin_pct"), "target_margin_pct")
    variable_rate = commission + tax + target_margin
    if ads_mode == "roas":
        variable_rate += Decimal("1") / ads_value
    if variable_rate >= Decimal("1"):
        raise RoasValidationError("Taxas, Ads e margem desejada consomem 100% ou mais do preço")
    fixed_ads = ads_value if ads_mode == "fixed" else ZERO
    price = (product + packaging + fixed_fee + shipping + fixed_ads) / (Decimal("1") - variable_rate)
    result = calculate_sale_profit({**data, "selling_price": price})
    return {**result, "ideal_price": _money(price), "target_margin_pct": _percent(target_margin)}

