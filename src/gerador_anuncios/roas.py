"""Cálculos determinísticos para o simulador seguro de ROAS."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

ZERO = Decimal("0")
HUNDRED = Decimal("100")
MONEY = Decimal("0.01")
RATIO = Decimal("0.0001")


class RoasValidationError(ValueError):
    """Entrada financeira ausente ou inconsistente."""


def _decimal(value: Any, name: str, *, default: Decimal | None = None) -> Decimal:
    if value in (None, ""):
        if default is not None:
            return default
        raise RoasValidationError(f"Campo obrigatório: {name}")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RoasValidationError(f"Valor inválido em {name}") from exc
    if not result.is_finite():
        raise RoasValidationError(f"Valor inválido em {name}")
    return result


def _non_negative(value: Any, name: str, *, default: Decimal = ZERO) -> Decimal:
    result = _decimal(value, name, default=default)
    if result < ZERO:
        raise RoasValidationError(f"{name} não pode ser negativo")
    return result


def _percentage(value: Any, name: str, *, default: Decimal = ZERO) -> Decimal:
    result = _non_negative(value, name, default=default)
    if result > HUNDRED:
        raise RoasValidationError(f"{name} deve estar entre 0 e 100")
    return result / HUNDRED


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def _ratio(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(RATIO, rounding=ROUND_HALF_UP))


def _pct(value: Decimal | None) -> str | None:
    return None if value is None else str((value * HUNDRED).quantize(MONEY, rounding=ROUND_HALF_UP))


def calculate_simulation(profile: dict[str, Any]) -> dict[str, Any]:
    marketplace = str(profile.get("marketplace", "")).lower()
    if marketplace not in {"shopee", "mercado_livre"}:
        raise RoasValidationError("marketplace deve ser shopee ou mercado_livre")
    price = _decimal(profile.get("price"), "price")
    if price <= ZERO:
        raise RoasValidationError("price deve ser maior que zero")

    costs = profile.get("costs") or {}
    fixed_costs = sum((_non_negative(costs.get(key), f"costs.{key}") for key in (
        "product", "packaging", "fixed_fee", "seller_shipping", "seller_discount", "other",
    )), ZERO)
    rate = sum((_percentage(costs.get(key), f"costs.{key}") for key in (
        "commission_pct", "tax_pct", "payment_pct", "returns_reserve_pct",
    )), ZERO)
    if rate > Decimal("1"):
        raise RoasValidationError("A soma das taxas percentuais não pode superar 100%")
    percentage_costs = price * rate
    contribution = price - fixed_costs - percentage_costs
    contribution_rate = contribution / price

    campaign = profile.get("campaign") or {}
    desired_margin = _percentage(campaign.get("minimum_net_margin_pct"), "campaign.minimum_net_margin_pct")
    reserved_profit = price * desired_margin
    safe_cpa = contribution - reserved_profit
    break_even_roas = price / contribution if contribution > ZERO else None
    break_even_acos = contribution_rate if contribution > ZERO else None
    safe_roas = price / safe_cpa if safe_cpa > ZERO else None

    stock = profile.get("stock") or {}
    physical = _non_negative(stock.get("physical"), "stock.physical")
    reserved = _non_negative(stock.get("reserved"), "stock.reserved")
    safety = _non_negative(stock.get("safety"), "stock.safety")
    sellable = max(ZERO, physical - reserved - safety)

    horizon = _decimal(campaign.get("horizon_days"), "campaign.horizon_days")
    if horizon <= ZERO:
        raise RoasValidationError("campaign.horizon_days deve ser maior que zero")
    credit = _non_negative(campaign.get("credit_total"), "campaign.credit_total")
    desired_budget = _non_negative(campaign.get("desired_daily_budget"), "campaign.desired_daily_budget")
    limits: dict[str, Decimal] = {
        "orcamento_desejado": desired_budget,
        "credito_por_dia": credit / horizon,
    }
    for key, label in (("daily_credit_limit", "limite_diario_credito"), ("cashflow_daily_limit", "fluxo_caixa")):
        value = campaign.get(key)
        if value not in (None, ""):
            limits[label] = _non_negative(value, f"campaign.{key}")
    if safe_cpa > ZERO:
        limits["estoque"] = (sellable / horizon) * safe_cpa
    recommended_name, recommended_budget = min(limits.items(), key=lambda item: item[1])

    alerts: list[str] = []
    safe = contribution > ZERO and safe_cpa > ZERO and sellable > ZERO
    if contribution <= ZERO:
        alerts.append("A margem antes dos anúncios não é positiva; revise preço e custos.")
    elif safe_cpa <= ZERO:
        alerts.append("A margem líquida desejada consome toda a verba disponível para aquisição.")
    if sellable <= ZERO:
        alerts.append("Não há estoque vendável para anunciar.")
    if not safe:
        recommended_budget, recommended_name = ZERO, "bloqueio_seguranca"

    return {
        "marketplace": marketplace, "sku": profile.get("sku"), "safe": safe,
        "economics": {
            "price": _money(price), "fixed_costs": _money(fixed_costs),
            "percentage_costs": _money(percentage_costs), "contribution_margin": _money(contribution),
            "contribution_margin_pct": _pct(contribution_rate), "reserved_profit": _money(reserved_profit),
            "maximum_safe_cpa": _money(max(ZERO, safe_cpa)), "break_even_acos_pct": _pct(break_even_acos),
            "break_even_roas": _ratio(break_even_roas), "minimum_safe_roas": _ratio(safe_roas),
        },
        "inventory": {"sellable_units": _money(sellable)},
        "budget": {
            "recommended_daily": _money(recommended_budget), "limiting_factor": recommended_name,
            "limits": {name: _money(value) for name, value in limits.items()},
            "estimated_credit_days": _ratio(credit / recommended_budget if recommended_budget > ZERO else None),
        },
        "alerts": alerts, "formula_version": "1.0.0",
    }


def evaluate_campaign(profile: dict[str, Any]) -> dict[str, Any]:
    simulation = calculate_simulation(profile)
    actual = profile.get("actual") or {}
    spend = _non_negative(actual.get("ad_spend"), "actual.ad_spend")
    revenue = _non_negative(actual.get("attributed_revenue"), "actual.attributed_revenue")
    clicks = _non_negative(actual.get("clicks"), "actual.clicks")
    orders = _non_negative(actual.get("attributed_orders"), "actual.attributed_orders")
    units = _non_negative(actual.get("attributed_units"), "actual.attributed_units", default=orders)
    sessions = _non_negative(actual.get("sessions"), "actual.sessions")
    total_orders = _non_negative(actual.get("total_orders"), "actual.total_orders")
    minimum_clicks = _non_negative(actual.get("minimum_clicks"), "actual.minimum_clicks", default=Decimal("30"))
    minimum_orders = _non_negative(actual.get("minimum_orders"), "actual.minimum_orders", default=Decimal("3"))
    matured = bool(actual.get("data_matured", False))

    roas = revenue / spend if spend > ZERO else None
    acos = spend / revenue if revenue > ZERO else None
    cpa = spend / orders if orders > ZERO else None
    click_conversion = orders / clicks if clicks > ZERO else None
    session_conversion = total_orders / sessions if sessions > ZERO else None
    unit_variable_cost = Decimal(simulation["economics"]["price"]) - Decimal(simulation["economics"]["contribution_margin"])
    result = revenue - (unit_variable_cost * units) - spend

    state, recommendation = "SEM_DADOS", "Informe gasto e resultados da campanha para iniciar a avaliação."
    if spend > ZERO or clicks > ZERO:
        if not matured or clicks < minimum_clicks or orders < minimum_orders:
            state, recommendation = "EM_APRENDIZADO", "Aguarde a maturação e a amostra mínima antes de alterar o orçamento."
        else:
            break_even, safe_roas = simulation["economics"]["break_even_roas"], simulation["economics"]["minimum_safe_roas"]
            if roas is None or break_even is None or roas < Decimal(break_even) or result < ZERO:
                state, recommendation = "RISCO_DE_PREJUIZO", "Reduza ou pause o orçamento e revise preço, custos e conversão."
            elif safe_roas is None or roas < Decimal(safe_roas):
                state, recommendation = "ATENCAO", "Mantenha sob observação: o resultado não preserva a margem de segurança desejada."
            else:
                state, recommendation = "SAUDAVEL", "Mantenha ou aumente gradualmente, respeitando crédito, caixa e estoque."
    if Decimal(simulation["inventory"]["sellable_units"]) <= units and units > ZERO:
        state, recommendation = "RISCO_DE_ESTOQUE", "Reduza o orçamento e priorize a reposição para evitar ruptura de estoque."
    if Decimal(simulation["budget"]["recommended_daily"]) <= ZERO and state == "SAUDAVEL":
        state, recommendation = "CREDITO_INSUFICIENTE", "Não aumente o investimento: o limite seguro de crédito ou caixa foi atingido."

    return {**simulation, "evaluation": {
        "state": state, "recommendation": recommendation, "roas": _ratio(roas), "acos_pct": _pct(acos),
        "cpa": None if cpa is None else _money(cpa), "click_conversion_pct": _pct(click_conversion),
        "session_conversion_pct": _pct(session_conversion), "attributed_result": _money(result),
        "data_matured": matured,
    }}

