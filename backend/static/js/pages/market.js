/* ═══════════════════════════════════════════════════════════════════
   Market Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("market", {
  title: "Market Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#128200; Market Engine</h1>
          <p>Price tracking, seasonal analysis, profitability estimation, and sell/hold recommendations</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Market Parameters</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop Type</label>
                <select class="form-select" id="mkt-crop">
                  <option value="rice" selected>Rice</option>
                  <option value="wheat">Wheat</option>
                  <option value="maize">Maize</option>
                  <option value="soybean">Soybean</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Region</label>
                <select class="form-select" id="mkt-region">
                  <option value="south_asia" selected>South Asia</option>
                  <option value="southeast_asia">Southeast Asia</option>
                  <option value="east_asia">East Asia</option>
                  <option value="sub_saharan_africa">Sub-Saharan Africa</option>
                  <option value="latin_america">Latin America</option>
                  <option value="global">Global</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Estimated Yield (tons, optional)</label>
                <input class="form-input" id="mkt-yield" type="number" step="0.5" placeholder="e.g. 5">
              </div>
              <div class="form-group">
                <label class="form-label">Area (hectares)</label>
                <input class="form-input" id="mkt-area" type="number" step="0.5" value="1.0">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Production Cost (USD, optional)</label>
              <input class="form-input" id="mkt-cost" type="number" step="10" placeholder="e.g. 500">
              <div class="form-hint">Total cost — enables profitability analysis</div>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="mkt-run">
              <span>&#9654;</span> Analyze Market
            </button>
          </div>
        </div>

        <div id="mkt-results"></div>
      </div>`;

    $("#mkt-run").addEventListener("click", async () => {
      const btn = $("#mkt-run");
      const results = $("#mkt-results");
      const optFloat = (id) => { const v = parseFloat($(id).value); return isNaN(v) ? null : v; };

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing...';
      showLoading(results);

      try {
        const d = await api.market({
          crop_type: $("#mkt-crop").value,
          region: $("#mkt-region").value,
          estimated_yield_tons: optFloat("#mkt-yield"),
          area_hectares: parseFloat($("#mkt-area").value) || 1,
          production_cost_usd: optFloat("#mkt-cost"),
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Analyze Market';

        const ps = d.price_snapshot || {};
        const sp = d.seasonal_pattern || {};
        const pr = d.profitability || {};

        const sellColor = d.sell_recommendation?.toLowerCase().includes("sell") ? "green"
                        : d.sell_recommendation?.toLowerCase().includes("hold") ? "amber" : "blue";

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Market Analysis Results</h2>
              ${renderBadge(d.sell_recommendation || "N/A", sellColor)}
            </div>

            <!-- Price Snapshot -->
            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">Current Price</div>
                <div class="stat-value">${fmtUSD(ps.current_price_usd_per_ton)}</div>
                <div class="stat-sub">per ton</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">30d Change</div>
                <div class="stat-value" style="color:${(ps.price_change_30d_pct || 0) >= 0 ? 'var(--ci-green-600)' : 'var(--ci-red-500)'}">
                  ${(ps.price_change_30d_pct || 0) >= 0 ? '&#9650;' : '&#9660;'} ${fmt(Math.abs(ps.price_change_30d_pct), 1)}%
                </div>
                <div class="stat-sub">vs 30 days ago</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Trend</div>
                <div class="stat-value text-sm">${ps.price_trend || "N/A"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Confidence</div>
                <div class="stat-value">${fmtPct(d.confidence)}</div>
              </div>
            </div>

            <!-- Price History -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128202; Price Timeline</h3></div>
              <div class="card-body">
                <div class="kv-grid">
                  ${renderKV("Current", fmtUSD(ps.current_price_usd_per_ton), "Today")}
                  ${renderKV("30 Days Ago", fmtUSD(ps.price_30d_ago))}
                  ${renderKV("90 Days Ago", fmtUSD(ps.price_90d_ago))}
                  ${renderKV("1 Year Ago", fmtUSD(ps.price_365d_ago))}
                </div>
              </div>
            </div>

            <!-- Seasonal -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128197; Seasonal Pattern</h3></div>
              <div class="card-body">
                <div class="kv-grid">
                  ${renderKV("Best Months to Sell", (sp.best_sell_months || []).join(", ") || "N/A", "Peak price periods")}
                  ${renderKV("Worst Months", (sp.worst_sell_months || []).join(", ") || "N/A", "Low price periods")}
                  ${renderKV("Current Outlook", sp.current_season_outlook || "N/A")}
                  ${renderKV("Seasonality", sp.seasonality_strength || "N/A")}
                </div>
              </div>
            </div>

            <!-- Profitability -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128176; Profitability Estimate</h3></div>
              <div class="card-body">
                <div class="stats-row">
                  <div class="card stat-card" style="border:none;box-shadow:none;background:var(--ci-green-50)">
                    <div class="stat-label">Gross Revenue</div>
                    <div class="stat-value" style="color:var(--ci-green-700)">${fmtUSD(pr.gross_revenue_usd)}</div>
                  </div>
                  <div class="card stat-card" style="border:none;box-shadow:none;background:var(--ci-red-50)">
                    <div class="stat-label">Production Cost</div>
                    <div class="stat-value" style="color:var(--ci-red-600)">${fmtUSD(pr.production_cost_usd)}</div>
                  </div>
                  <div class="card stat-card" style="border:none;box-shadow:none;background:${(pr.net_profit_usd || 0) >= 0 ? 'var(--ci-green-50)' : 'var(--ci-red-50)'}">
                    <div class="stat-label">Net Profit</div>
                    <div class="stat-value">${fmtUSD(pr.net_profit_usd)}</div>
                    <div class="stat-sub">Margin: ${fmtPct((pr.profit_margin_pct || 0) / 100)}</div>
                  </div>
                  <div class="card stat-card" style="border:none;box-shadow:none">
                    <div class="stat-label">Break-Even</div>
                    <div class="stat-value">${fmtUSD(pr.break_even_price_usd)}</div>
                    <div class="stat-sub">per ton</div>
                  </div>
                </div>
              </div>
            </div>

            <div class="card">
              <div class="card-header"><h3>&#128161; Recommendations</h3></div>
              <div class="card-body">
                ${renderRecs(d.recommendations)}
              </div>
            </div>
          </div>`;
      } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Analyze Market';
        showError(results, err.message);
      }
    });
  },
});
