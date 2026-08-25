/* Versão estática para GitHub Pages. O backend Python continua sendo a fonte principal. */
(function () {
  const money = value => Number(value).toFixed(2);
  const ratio = value => value == null || !Number.isFinite(value) ? null : value.toFixed(4);
  const pct = value => value == null || !Number.isFinite(value) ? null : (value * 100).toFixed(2);
  const value = (input, fallback = 0) => input == null || input === "" ? fallback : Number(input);
  const positive = (input, name) => {
    const result = value(input);
    if (!Number.isFinite(result) || result < 0) throw Error(`${name} não pode ser negativo`);
    return result;
  };
  const percentage = (input, name) => {
    const result = positive(input, name);
    if (result > 100) throw Error(`${name} deve estar entre 0 e 100`);
    return result / 100;
  };

  function simulate(profile) {
    const price = Number(profile.price);
    if (!Number.isFinite(price) || price <= 0) throw Error("Preço deve ser maior que zero");
    const c = profile.costs || {}, s = profile.stock || {}, a = profile.campaign || {};
    const fixed = ["product", "packaging", "fixed_fee", "seller_shipping", "seller_discount", "other"]
      .reduce((total, key) => total + positive(c[key], key), 0);
    const rate = ["commission_pct", "tax_pct", "payment_pct", "returns_reserve_pct"]
      .reduce((total, key) => total + percentage(c[key], key), 0);
    if (rate > 1) throw Error("A soma das taxas não pode superar 100%");
    const contribution = price - fixed - price * rate;
    const desiredMargin = percentage(a.minimum_net_margin_pct, "margem mínima");
    const safeCpa = contribution - price * desiredMargin;
    const physical = positive(s.physical, "estoque físico");
    const sellable = Math.max(0, physical - positive(s.reserved, "estoque reservado") - positive(s.safety, "estoque de segurança"));
    const horizon = Number(a.horizon_days);
    if (!Number.isFinite(horizon) || horizon <= 0) throw Error("Horizonte deve ser maior que zero");
    const credit = positive(a.credit_total, "crédito total");
    const desired = positive(a.desired_daily_budget, "orçamento desejado");
    const planned = desired > 0 ? Math.min(credit, desired * horizon) : credit;
    const minBreakEven = planned > 0 && contribution > 0 ? Math.ceil(planned / contribution) : null;
    const minSafe = planned > 0 && safeCpa > 0 ? Math.ceil(planned / safeCpa) : null;
    const maxSafeCredit = Math.max(0, sellable * safeCpa);
    let compatibility = planned <= 0 ? "SEM_CREDITO" : contribution <= 0 || safeCpa <= 0 ? "INCOMPATIVEL_MARGEM" : sellable < minSafe ? "INCOMPATIVEL_ESTOQUE" : "COMPATIVEL";
    const limits = {orcamento_desejado: desired, credito_por_dia: credit / horizon};
    if (a.daily_credit_limit != null) limits.limite_diario_credito = positive(a.daily_credit_limit, "limite diário");
    if (a.cashflow_daily_limit != null) limits.fluxo_caixa = positive(a.cashflow_daily_limit, "limite de caixa");
    if (safeCpa > 0) limits.estoque = sellable / horizon * safeCpa;
    let limitingFactor = Object.keys(limits).reduce((x, y) => limits[x] <= limits[y] ? x : y);
    let recommended = limits[limitingFactor], alerts = [];
    const safe = contribution > 0 && safeCpa > 0 && sellable > 0;
    if (contribution <= 0) alerts.push("A margem antes dos anúncios não é positiva; revise preço e custos.");
    else if (safeCpa <= 0) alerts.push("A margem desejada consome toda a verba disponível para aquisição.");
    if (sellable <= 0) alerts.push("Não há estoque vendável para anunciar.");
    if (compatibility === "INCOMPATIVEL_MARGEM") alerts.push("Produto incompatível com crédito de Ads: a margem não suporta publicidade.");
    if (compatibility === "INCOMPATIVEL_ESTOQUE") alerts.push(`Produto incompatível com o crédito: faltam ${Math.max(0, minSafe - Math.floor(sellable))} unidades vendáveis.`);
    if (!safe) { recommended = 0; limitingFactor = "bloqueio_seguranca"; }
    const projectedProfit = minSafe != null && compatibility === "COMPATIVEL" ? minSafe * contribution - planned : null;
    return {
      safe, economics: {price: money(price), contribution_margin: money(contribution), contribution_margin_pct: pct(contribution / price),
        maximum_safe_cpa: money(Math.max(0, safeCpa)), break_even_roas: contribution > 0 ? ratio(price / contribution) : null,
        minimum_safe_roas: safeCpa > 0 ? ratio(price / safeCpa) : null},
      inventory: {sellable_units: money(sellable), minimum_units_break_even: minBreakEven, minimum_units_safe_profit: minSafe,
        additional_units_needed: minSafe == null ? null : Math.max(0, minSafe - Math.floor(sellable))},
      profit: {protected_per_unit: money(price * desiredMargin), projected_units_for_credit: minSafe,
        projected_after_ads: projectedProfit == null ? null : money(projectedProfit),
        result_if_all_sellable_stock_is_sold: money(sellable * contribution - planned),
        projection_notice: "Cenário matemático; não garante vendas nem desempenho da campanha."},
      budget: {recommended_daily: money(recommended), limiting_factor: limitingFactor, planned_credit: money(planned),
        maximum_safe_credit_for_stock: money(maxSafeCredit), incompatible_credit_amount: money(Math.max(0, planned - maxSafeCredit)),
        credit_compatibility: compatibility}, alerts
    };
  }

  window.calculateRoas = function (profile, evaluate) {
    const result = simulate(profile);
    if (!evaluate) return result;
    const a = profile.actual || {}, spend = positive(a.ad_spend, "gasto Ads"), revenue = positive(a.attributed_revenue, "receita atribuída"),
      clicks = positive(a.clicks, "cliques"), orders = positive(a.attributed_orders, "pedidos"), units = positive(a.attributed_units, "unidades"),
      sessions = positive(a.sessions, "sessões"), totalOrders = positive(a.total_orders, "pedidos totais");
    const roas = spend > 0 ? revenue / spend : null, cpa = orders > 0 ? spend / orders : null;
    const unitCost = Number(result.economics.price) - Number(result.economics.contribution_margin);
    const attributedResult = revenue - unitCost * units - spend;
    let state = "SEM_DADOS", recommendation = "Informe os resultados da campanha.";
    if (spend > 0 || clicks > 0) {
      if (!a.data_matured || clicks < value(a.minimum_clicks, 30) || orders < value(a.minimum_orders, 3)) {
        state = "EM_APRENDIZADO"; recommendation = "Aguarde a maturação e a amostra mínima antes de alterar o orçamento.";
      } else if (roas == null || result.economics.break_even_roas == null || roas < Number(result.economics.break_even_roas) || attributedResult < 0) {
        state = "RISCO_DE_PREJUIZO"; recommendation = "Reduza ou pause o orçamento e revise preço, custos e conversão.";
      } else if (result.economics.minimum_safe_roas == null || roas < Number(result.economics.minimum_safe_roas)) {
        state = "ATENCAO"; recommendation = "O resultado ainda não preserva a margem de segurança desejada.";
      } else { state = "SAUDAVEL"; recommendation = "Mantenha ou aumente gradualmente, respeitando crédito e estoque."; }
    }
    return {...result, evaluation: {state, recommendation, roas: ratio(roas), acos_pct: pct(revenue > 0 ? spend / revenue : null),
      cpa: cpa == null ? null : money(cpa), attributed_result: money(attributedResult), click_conversion_pct: pct(clicks > 0 ? orders / clicks : null),
      session_conversion_pct: pct(sessions > 0 ? totalOrders / sessions : null)}};
  };
}());
