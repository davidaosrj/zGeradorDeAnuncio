"""ADR-002: motor independente, sem I/O e sem tarifas presumidas."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP, localcontext
import re


class PricingError(ValueError):
    pass


def amount(value, name):
    if isinstance(value, bool) or not re.fullmatch(r"\d{1,10}(?:\.\d{1,6})?", str(value)):
        raise PricingError(f"{name}: informe número não negativo com até 6 casas decimais")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise PricingError(f"{name}: número inválido") from exc
    if result > Decimal('1000000000'):
        raise PricingError(f"{name}: valor acima do limite de 1 bilhão")
    return result


def number(obj, key, default=None):
    return amount(obj.get(key, default), key)


def integer(obj, key, default=1):
    result = number(obj, key, default)
    if result < 1 or result > 1000000 or result != result.to_integral_value():
        raise PricingError(f"{key}: informe inteiro entre 1 e 1000000")
    return result


def rate(obj, key, default=0):
    result = number(obj, key, default)
    if result > 100:
        raise PricingError(f"{key}: percentual acima de 100%")
    return result / 100


def money(value):
    return format(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f')


def rounded(value, step=Decimal('.01')):
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def calculate_pricing(data: dict) -> dict:
    with localcontext() as ctx:
        ctx.prec = 80
        try:
            return _calculate(data)
        except (TypeError, AttributeError, KeyError) as exc:
            raise PricingError('Estrutura de dados inválida') from exc


def _calculate(data):
    if data.get('currency', 'BRL') != 'BRL':
        raise PricingError('Moeda suportada: BRL')
    components = data.get('components')
    if not isinstance(components, list) or not 1 <= len(components) <= 100:
        raise PricingError('Informe entre 1 e 100 componentes')
    units = integer(data, 'order_units')
    failure = rate(data, 'failure_pct', 10)
    target = rate(data, 'target_margin_pct', 30)
    material = machine = energy = extra = Decimal(0)
    for component in components:
        quantity = integer(component, 'quantity') * units
        weight = number(component, 'weight_g')
        hours = number(component, 'hours')
        material += weight / 1000 * number(component, 'filament_price_kg') * quantity
        machine += hours * number(component, 'machine_hour') * quantity
        energy += hours * number(component, 'energy_hour') * quantity
        extra += number(component, 'additional_cost', 0) * quantity
    subtotal = material + machine + energy + extra
    reserve = subtotal * failure
    packaging = number(data, 'packaging_cost', 4) * integer(data, 'packaging_count')
    assembly = number(data, 'assembly_cost', 0)
    production = subtotal + reserve + packaging + assembly
    if production <= 0:
        raise PricingError('Custo de produção deve ser maior que zero')
    rule = data.get('fee_rule', {})
    if rule.get('marketplace') not in {'shopee', 'mercado_livre', 'direct'}:
        raise PricingError('Marketplace inválido')
    if not str(rule.get('version', '')).strip():
        raise PricingError('Informe a versão da regra comercial')
    basis = rule.get('basis', 'order')
    if basis not in {'order', 'unit'}:
        raise PricingError('Base de cobrança deve ser order ou unit')
    commission = rate(rule, 'commission_pct')
    tax = rate(rule, 'tax_pct')
    payment = rate(rule, 'payment_pct')
    variable = commission + tax + payment
    if variable + target >= 1:
        raise PricingError('Taxas e margem devem somar menos de 100%')
    fixed_fee = number(rule, 'fixed_fee', 0) * (units if basis == 'unit' else 1)
    shipping = number(data, 'shipping', 0)
    discount = number(data, 'discount', 0)
    other = number(data, 'order_other_cost', 0)
    fixed = production + fixed_fee + shipping + discount + other
    raw = fixed / (1 - variable - target)
    calculated = rounded(raw)
    step = number(data, 'commercial_step', '0.01')
    if step < Decimal('.01') or step != rounded(step):
        raise PricingError('Passo comercial deve ser múltiplo de R$ 0,01')
    commercial = rounded(raw, step)
    selling = number(data, 'selling_price') if data.get('selling_price') not in (None, '') else commercial
    if selling <= 0:
        raise PricingError('Preço de venda deve ser maior que zero')
    try:
        on = date.fromisoformat(str(data.get('calculation_date', date.today().isoformat())))
        if rule.get('valid_from') and on < date.fromisoformat(rule['valid_from']):
            raise PricingError('Regra comercial ainda não vigente')
        if rule.get('valid_until') and on > date.fromisoformat(rule['valid_until']):
            raise PricingError('Regra comercial vencida')
    except ValueError as exc:
        if isinstance(exc, PricingError):
            raise
        raise PricingError('Data inválida; use AAAA-MM-DD') from exc
    minimum = number(rule, 'min_price', 0)
    maximum = number(rule, 'max_price') if rule.get('max_price') not in (None, '') else None
    if maximum is not None and maximum <= minimum:
        raise PricingError('Faixa de preço inválida')

    def covered(price):
        per_unit = price / units
        return per_unit >= minimum and (maximum is None or per_unit < maximum)

    if not covered(commercial) or not covered(selling):
        raise PricingError('Preço por unidade fora da faixa da regra; selecione outra regra')

    def evaluate(price):
        profit = price * (1 - variable) - fixed
        margin = profit / price * 100
        classification = 'Inviável' if profit <= 0 else 'Alta' if profit >= price * target else 'Moderada'
        return {'price': money(price), 'profit': money(profit), 'margin_pct': money(margin), 'classification': classification}

    comparisons = []
    competitors = data.get('competitors', [])
    if not isinstance(competitors, list) or len(competitors) > 100:
        raise PricingError('Informe no máximo 100 concorrentes')
    for competitor in competitors:
        if not isinstance(competitor, dict):
            raise PricingError('Concorrente inválido')
        observation = deepcopy(competitor)
        valid_source = str(competitor.get('url', '')).startswith(('https://', 'http://'))
        collected = competitor.get('collected_at')
        try:
            date.fromisoformat(str(collected)[:10])
        except ValueError:
            collected = None
        if competitor.get('price') in (None, '') or not valid_source or not collected:
            comparisons.append({'observation': observation, 'classification': 'Indeterminada'})
            continue
        price = number(competitor, 'price')
        if price <= 0 or not covered(price):
            comparisons.append({'observation': observation, 'classification': 'Indeterminada'})
        else:
            comparisons.append({'observation': observation, **evaluate(price)})
    evaluated = evaluate(selling)
    snapshot = deepcopy(data)
    snapshot['calculation_date'] = on.isoformat()
    return {
        'engine_version': '1.0', 'currency': 'BRL', 'price_basis': 'order',
        'order_units': str(int(units)), 'material_cost': money(material),
        'machine_cost': money(machine), 'energy_cost': money(energy),
        'additional_cost': money(extra), 'subtotal': money(subtotal),
        'failure_reserve': money(reserve), 'packaging': money(packaging),
        'assembly': money(assembly), 'production_cost': money(production),
        'production_cost_exact': format(production, 'f'),
        'production_per_unit': money(production / units), 'fixed_fee': money(fixed_fee),
        'shipping': money(shipping), 'discount': money(discount), 'order_other_cost': money(other),
        'break_even_price': money(rounded(fixed / (1 - variable))),
        'calculated_price': money(calculated), 'commercial_price': money(commercial),
        'price_per_unit': money(commercial / units),
        'selling_price': money(selling), 'variable_fees': money(selling * variable),
        'profit': evaluated['profit'], 'margin_pct': evaluated['margin_pct'],
        'classification': evaluated['classification'],
        'multiplier': format((selling / production).quantize(Decimal('.0001'), rounding=ROUND_HALF_UP), 'f'),
        'target_margin_pct': money(target * 100), 'comparisons': comparisons, 'snapshot': snapshot,
    }
