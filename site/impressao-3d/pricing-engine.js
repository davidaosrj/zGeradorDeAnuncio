/* ADR-002: arithmetic over exact rational BigInts, independent of the DOM. */
(function (root) {
  'use strict';
  const gcd = (a, b) => { a = a < 0n ? -a : a; while (b) [a, b] = [b, a % b]; return a; };
  class Q {
    constructor(n, d = 1n) {
      if (!d) throw Error('Divisão por zero');
      if (d < 0n) { n = -n; d = -d; }
      const g = gcd(n, d); this.n = n / g; this.d = d / g;
    }
    add(b) { return new Q(this.n * b.d + b.n * this.d, this.d * b.d); }
    sub(b) { return this.add(new Q(-b.n, b.d)); }
    mul(b) { return new Q(this.n * b.n, this.d * b.d); }
    div(b) { return new Q(this.n * b.d, this.d * b.n); }
    cmp(b) { const v = this.n * b.d - b.n * this.d; return v < 0n ? -1 : v > 0n ? 1 : 0; }
    fixed(places = 2) {
      const scale = 10n ** BigInt(places), negative = this.n < 0n;
      const n = (negative ? -this.n : this.n) * scale;
      const value = n / this.d + (n % this.d * 2n >= this.d ? 1n : 0n);
      const digits = value.toString().padStart(places + 1, '0');
      return (negative && value ? '-' : '') + (places ? digits.slice(0, -places) + '.' + digits.slice(-places) : digits);
    }
    ceil(step) {
      const r = this.div(step);
      return new Q(r.n / r.d + (r.n % r.d > 0n ? 1n : 0n)).mul(step);
    }
    exact() {
      // Production costs are finite decimals; no intermediate rounding.
      let d = this.d, places = 0;
      while (d % 2n === 0n) { d /= 2n; places++; }
      let fives = 0; while (d % 5n === 0n) { d /= 5n; fives++; }
      return this.fixed(Math.max(places, fives));
    }
  }
  const ZERO = new Q(0n), ONE = new Q(1n), HUNDRED = new Q(100n), CENT = new Q(1n, 100n);
  function amount(value, name) {
    const s = String(value);
    if (!/^\d{1,10}(?:\.\d{1,6})?$/.test(s)) throw Error(`${name}: informe número não negativo com até 6 casas decimais`);
    const [a, b = ''] = s.split('.');
    const result = new Q(BigInt(a + b), 10n ** BigInt(b.length));
    if (result.cmp(new Q(1000000000n)) > 0) throw Error(`${name}: valor acima do limite de 1 bilhão`);
    return result;
  }
  const number = (obj, key, fallback) => amount(Object.hasOwn(obj, key) ? obj[key] : fallback, key);
  function integer(obj, key, fallback = 1) {
    const v = number(obj, key, fallback);
    if (v.d !== 1n || v.n < 1n || v.n > 1000000n) throw Error(`${key}: informe inteiro entre 1 e 1000000`);
    return v;
  }
  function rate(obj, key, fallback = 0) {
    const v = number(obj, key, fallback);
    if (v.cmp(HUNDRED) > 0) throw Error(`${key}: percentual acima de 100%`);
    return v.div(HUNDRED);
  }
  const empty = v => v === undefined || v === null || v === '';
  function day(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw Error('Data inválida; use AAAA-MM-DD');
    const date = new Date(value + 'T00:00:00Z');
    if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) throw Error('Data inválida; use AAAA-MM-DD');
    return value;
  }
  function calculate(data) {
    if ((data.currency || 'BRL') !== 'BRL') throw Error('Moeda suportada: BRL');
    if (!Array.isArray(data.components) || !data.components.length || data.components.length > 100) throw Error('Informe entre 1 e 100 componentes');
    const units = integer(data, 'order_units'), failure = rate(data, 'failure_pct', 10), target = rate(data, 'target_margin_pct', 30);
    let material = ZERO, machine = ZERO, energy = ZERO, extra = ZERO;
    for (const c of data.components) {
      const quantity = integer(c, 'quantity').mul(units), weight = number(c, 'weight_g'), hours = number(c, 'hours');
      material = material.add(weight.div(new Q(1000n)).mul(number(c, 'filament_price_kg')).mul(quantity));
      machine = machine.add(hours.mul(number(c, 'machine_hour')).mul(quantity));
      energy = energy.add(hours.mul(number(c, 'energy_hour')).mul(quantity));
      extra = extra.add(number(c, 'additional_cost', 0).mul(quantity));
    }
    const subtotal = material.add(machine).add(energy).add(extra), reserve = subtotal.mul(failure);
    const packaging = number(data, 'packaging_cost', 4).mul(integer(data, 'packaging_count'));
    const assembly = number(data, 'assembly_cost', 0), production = subtotal.add(reserve).add(packaging).add(assembly);
    if (production.cmp(ZERO) <= 0) throw Error('Custo de produção deve ser maior que zero');
    const rule = data.fee_rule || {};
    if (!['shopee', 'mercado_livre', 'direct'].includes(rule.marketplace)) throw Error('Marketplace inválido');
    if (!String(rule.version || '').trim()) throw Error('Informe a versão da regra comercial');
    const basis = rule.basis || 'order';
    if (!['order', 'unit'].includes(basis)) throw Error('Base de cobrança deve ser order ou unit');
    const variable = rate(rule, 'commission_pct').add(rate(rule, 'tax_pct')).add(rate(rule, 'payment_pct'));
    if (variable.add(target).cmp(ONE) >= 0) throw Error('Taxas e margem devem somar menos de 100%');
    const fixedFee = number(rule, 'fixed_fee', 0).mul(basis === 'unit' ? units : ONE);
    const shipping = number(data, 'shipping', 0), discount = number(data, 'discount', 0), other = number(data, 'order_other_cost', 0);
    const fixed = production.add(fixedFee).add(shipping).add(discount).add(other);
    const raw = fixed.div(ONE.sub(variable).sub(target)), calculated = raw.ceil(CENT);
    const step = number(data, 'commercial_step', '0.01');
    if (step.cmp(CENT) < 0 || step.cmp(step.ceil(CENT)) !== 0) throw Error('Passo comercial deve ser múltiplo de R$ 0,01');
    const commercial = raw.ceil(step), selling = empty(data.selling_price) ? commercial : number(data, 'selling_price');
    if (selling.cmp(ZERO) <= 0) throw Error('Preço de venda deve ser maior que zero');
    const on = day(data.calculation_date || new Date().toISOString().slice(0, 10));
    if (rule.valid_from && on < day(rule.valid_from)) throw Error('Regra comercial ainda não vigente');
    if (rule.valid_until && on > day(rule.valid_until)) throw Error('Regra comercial vencida');
    const minimum = number(rule, 'min_price', 0), maximum = empty(rule.max_price) ? null : number(rule, 'max_price');
    if (maximum && maximum.cmp(minimum) <= 0) throw Error('Faixa de preço inválida');
    const covered = price => price.div(units).cmp(minimum) >= 0 && (!maximum || price.div(units).cmp(maximum) < 0);
    if (!covered(commercial) || !covered(selling)) throw Error('Preço por unidade fora da faixa da regra; selecione outra regra');
    const evaluate = price => {
      const profit = price.mul(ONE.sub(variable)).sub(fixed);
      return {price: price.fixed(), profit: profit.fixed(), margin_pct: profit.div(price).mul(HUNDRED).fixed(), classification: profit.cmp(ZERO) <= 0 ? 'Inviável' : profit.cmp(price.mul(target)) >= 0 ? 'Alta' : 'Moderada'};
    };
    const competitors = data.competitors || [];
    if (!Array.isArray(competitors) || competitors.length > 100) throw Error('Informe no máximo 100 concorrentes');
    const comparisons = competitors.map(c => {
      if (!c || typeof c !== 'object' || Array.isArray(c)) throw Error('Concorrente inválido');
      const observation = JSON.parse(JSON.stringify(c));
      let validDate = false; try { day(String(c.collected_at).slice(0, 10)); validDate = true; } catch (_) { /* incomplete observation */ }
      if (empty(c.price) || !/^https?:\/\//.test(c.url || '') || !validDate) return {observation, classification: 'Indeterminada'};
      const price = number(c, 'price');
      return price.cmp(ZERO) <= 0 || !covered(price) ? {observation, classification: 'Indeterminada'} : {observation, ...evaluate(price)};
    });
    const evaluated = evaluate(selling), snapshot = JSON.parse(JSON.stringify(data)); snapshot.calculation_date = on;
    return {
      engine_version: '1.0', currency: 'BRL', price_basis: 'order', order_units: units.fixed(0),
      material_cost: material.fixed(), machine_cost: machine.fixed(), energy_cost: energy.fixed(), additional_cost: extra.fixed(),
      subtotal: subtotal.fixed(), failure_reserve: reserve.fixed(), packaging: packaging.fixed(), assembly: assembly.fixed(),
      production_cost: production.fixed(), production_cost_exact: production.exact(), production_per_unit: production.div(units).fixed(),
      fixed_fee: fixedFee.fixed(), shipping: shipping.fixed(), discount: discount.fixed(), order_other_cost: other.fixed(),
      break_even_price: fixed.div(ONE.sub(variable)).ceil(CENT).fixed(), calculated_price: calculated.fixed(), commercial_price: commercial.fixed(),
      price_per_unit: commercial.div(units).fixed(), selling_price: selling.fixed(), variable_fees: selling.mul(variable).fixed(),
      profit: evaluated.profit, margin_pct: evaluated.margin_pct, classification: evaluated.classification,
      multiplier: selling.div(production).fixed(4), target_margin_pct: target.mul(HUNDRED).fixed(), comparisons, snapshot,
    };
  }
  root.Pricing3D = {calculate};
  if (typeof module !== 'undefined') module.exports = root.Pricing3D;
})(typeof window !== 'undefined' ? window : globalThis);
