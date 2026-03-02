/* ═══════════════════════════════════════════════════════════════════
   Advisory Aggregator Page — Full Farm Intelligence Report
   ═══════════════════════════════════════════════════════════════════ */

registerPage("advisory", {
  title: "Full Advisory",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#9881; Full Advisory Report</h1>
          <p>Run all 6 intelligence engines simultaneously — get a unified farm health score and prioritized action plan</p>
        </div>

        <div class="card mb-24" style="border:2px solid var(--ci-green-200)">
          <div class="card-header" style="background:var(--ci-green-50)">
            <h3>Farm Parameters</h3>
          </div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Latitude</label>
                <input class="form-input" id="adv-lat" type="number" step="0.001" value="17.385">
              </div>
              <div class="form-group">
                <label class="form-label">Longitude</label>
                <input class="form-input" id="adv-lon" type="number" step="0.001" value="78.487">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop Type</label>
                <select class="form-select" id="adv-crop">
                  <option value="rice" selected>Rice</option>
                  <option value="wheat">Wheat</option>
                  <option value="maize">Maize</option>
                  <option value="soybean">Soybean</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Planting Date</label>
                <input class="form-input" id="adv-planting" type="date">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Target Yield (t/ha)</label>
                <input class="form-input" id="adv-yield" type="number" step="0.5" value="5.0">
              </div>
              <div class="form-group">
                <label class="form-label">Area (hectares)</label>
                <input class="form-input" id="adv-area" type="number" step="0.5" value="1.0">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Region</label>
              <select class="form-select" id="adv-region">
                <option value="south_asia" selected>South Asia</option>
                <option value="southeast_asia">Southeast Asia</option>
                <option value="east_asia">East Asia</option>
                <option value="sub_saharan_africa">Sub-Saharan Africa</option>
                <option value="latin_america">Latin America</option>
                <option value="global">Global</option>
              </select>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="adv-run" style="width:100%">
              <span>&#9881;</span> Generate Full Advisory Report
            </button>
          </div>
        </div>

        <div id="adv-results"></div>
      </div>`;

    $("#adv-run").addEventListener("click", async () => {
      const btn = $("#adv-run");
      const results = $("#adv-results");

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Running 6 engines...';
      showLoading(results);

      try {
        const d = await api.advisory({
          lat: parseFloat($("#adv-lat").value),
          lon: parseFloat($("#adv-lon").value),
          crop_type: $("#adv-crop").value,
          planting_date: $("#adv-planting").value || null,
          target_yield: parseFloat($("#adv-yield").value),
          area_hectares: parseFloat($("#adv-area").value),
          region: $("#adv-region").value,
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9881;</span> Generate Full Advisory Report';

        const healthColor = scoreColor(d.farm_health_score);

        results.innerHTML = `
          <div class="results-panel">

            <!-- Executive Summary -->
            <div class="card mb-24" style="border:2px solid var(--ci-green-200)">
              <div class="card-body" style="padding:28px">
                <div class="flex items-center gap-16" style="flex-wrap:wrap">
                  ${renderScoreRing(d.farm_health_score, 72)}
                  <div style="flex:1;min-width:200px">
                    <h2>Farm Health Score: <span style="color:${healthColor}">${fmt(d.farm_health_score, 0)}/100</span></h2>
                    <p class="text-muted mt-8">${d.advisory_summary || "No summary available."}</p>
                  </div>
                  <div>
                    <div class="text-sm text-muted">Engines: ${d.engines_succeeded || 0}/${d.engines_total || 6} OK</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Engine Statuses -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128640; Engine Status</h3></div>
              <div class="card-body" style="padding:0">
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr><th>Engine</th><th>Status</th><th>Latency</th><th>Error</th></tr>
                    </thead>
                    <tbody>
                      ${(d.engine_statuses || []).map(es => `
                        <tr>
                          <td class="text-bold">${es.engine}</td>
                          <td>${renderBadge(es.status, es.status === "ok" ? "green" : "red")}</td>
                          <td>${es.latency_ms != null ? fmt(es.latency_ms, 0) + " ms" : "N/A"}</td>
                          <td class="text-sm text-muted">${es.error || "\u2014"}</td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Priority Actions -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128293; Priority Actions</h3></div>
              <div class="card-body">
                ${(d.priority_actions || []).length === 0 ? '<p class="text-muted text-sm">No critical actions needed.</p>' : ""}
                ${(d.priority_actions || []).map((a, i) => `
                  <div style="padding:14px 0;${i > 0 ? "border-top:1px solid var(--ci-border);" : ""}">
                    <div class="flex items-center gap-8 mb-8">
                      <span style="width:24px;height:24px;background:var(--ci-gray-100);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;color:var(--ci-gray-600)">${i + 1}</span>
                      ${renderBadge(a.urgency || "N/A",
                        a.urgency === "Immediate" ? "red" :
                        a.urgency === "This Week" ? "amber" :
                        a.urgency === "This Month" ? "blue" : "gray"
                      )}
                      ${renderBadge(a.category || "General", "purple")}
                    </div>
                    <div class="text-bold">${a.action}</div>
                    <div class="text-sm text-muted">Impact: ${a.impact || "N/A"}</div>
                  </div>
                `).join("")}
              </div>
            </div>

            <!-- Engine Summaries -->
            <h3 class="mb-16">Engine Intelligence Details</h3>
            <div class="engine-grid" style="grid-template-columns:repeat(auto-fill,minmax(280px,1fr))">
              ${renderEngineCard("Soil", "&#127793;", d.soil_intelligence, "engine-soil")}
              ${renderEngineCard("Weather", "&#9925;", d.weather_intelligence, "engine-weather")}
              ${renderEngineCard("Crop", "&#127806;", d.crop_intelligence, "engine-crop")}
              ${renderEngineCard("Fertilizer", "&#129716;", d.fertilizer_intelligence, "engine-fertilizer")}
              ${renderEngineCard("Disease", "&#128030;", d.disease_intelligence, "engine-disease")}
              ${renderEngineCard("Market", "&#128200;", d.market_intelligence, "engine-market")}
            </div>
          </div>`;
      } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9881;</span> Generate Full Advisory Report';
        showError(results, err.message);
      }
    });
  },
});

function renderEngineCard(name, icon, data, cls) {
  if (!data) {
    return `
      <div class="card engine-card ${cls}" style="opacity:0.6">
        <div class="engine-icon">${icon}</div>
        <h3>${name} Engine</h3>
        <p class="text-sm text-muted">Engine did not return data.</p>
      </div>`;
  }

  /* Pull out most interesting KVs per engine type */
  let highlights = "";
  switch (name) {
    case "Soil":
      highlights = `
        <div class="text-sm">pH: <strong>${fmt(data.ph)}</strong> (${data.ph_classification || "N/A"})</div>
        <div class="text-sm">Health: <strong>${fmt(data.soil_health_index, 0)}/100</strong></div>
        <div class="text-sm">Texture: ${data.texture_class || "N/A"}</div>`;
      break;
    case "Weather":
      highlights = `
        <div class="text-sm">Risk: <strong>${fmt(data.risk_assessment?.overall_risk_score, 0)}/100</strong></div>
        <div class="text-sm">Temp: ${fmt(data.climate?.temperature_avg_30d)}&deg;C</div>
        <div class="text-sm">ET0: ${fmt(data.water_model?.et0_estimate)} mm/day</div>`;
      break;
    case "Crop":
      highlights = `
        <div class="text-sm">Health: <strong>${fmt(data.crop_health_score, 0)}/100</strong></div>
        <div class="text-sm">NDVI: ${fmt(data.vegetation?.ndvi_mean, 3)} (${data.vegetation?.ndvi_classification || "N/A"})</div>
        <div class="text-sm">Yield: ${fmt(data.yield_forecast?.predicted_yield)} t/ha</div>`;
      break;
    case "Fertilizer":
      highlights = `
        <div class="text-sm">N: ${fmt(data.npk_recommendation?.nitrogen_kg_per_ha)} kg/ha</div>
        <div class="text-sm">Products: ${(data.products || []).length}</div>
        <div class="text-sm">Cost: ${fmtUSD(data.cost_summary?.total_cost_usd)}</div>`;
      break;
    case "Disease":
      highlights = `
        <div class="text-sm">Risk: <strong>${fmt(data.overall_risk_score, 0)}/100</strong> (${data.risk_level || "N/A"})</div>
        <div class="text-sm">Diseases: ${(data.disease_risks || []).length} profiled</div>
        <div class="text-sm">Actions: ${(data.prevention_plan || []).length} planned</div>`;
      break;
    case "Market":
      highlights = `
        <div class="text-sm">Price: ${fmtUSD(data.price_snapshot?.current_price_usd_per_ton)}/ton</div>
        <div class="text-sm">Advice: <strong>${data.sell_recommendation || "N/A"}</strong></div>
        <div class="text-sm">Profit: ${fmtUSD(data.profitability?.net_profit_usd)}</div>`;
      break;
  }

  return `
    <div class="card engine-card ${cls}">
      <div class="engine-icon">${icon}</div>
      <h3>${name} Engine</h3>
      <div style="margin-top:8px">${highlights}</div>
    </div>`;
}
