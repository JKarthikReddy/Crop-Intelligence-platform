/* ═══════════════════════════════════════════════════════════════════
   Fertilizer Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("fertilizer", {
  title: "Fertilizer Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#129716; Fertilizer Engine</h1>
          <p>Precision NPK recommendations, product selection, application scheduling, and cost optimization</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Recommendation Parameters</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop Type</label>
                <select class="form-select" id="fert-crop">
                  <option value="rice" selected>Rice</option>
                  <option value="wheat">Wheat</option>
                  <option value="maize">Maize</option>
                  <option value="soybean">Soybean</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Target Yield (t/ha)</label>
                <input class="form-input" id="fert-yield" type="number" step="0.5" value="5.0">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Soil pH (optional)</label>
                <input class="form-input" id="fert-ph" type="number" step="0.1" placeholder="e.g. 6.5">
                <div class="form-hint">From Soil Engine — affects N efficiency</div>
              </div>
              <div class="form-group">
                <label class="form-label">Area (hectares)</label>
                <input class="form-input" id="fert-area" type="number" step="0.5" value="1.0">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Organic Carbon (g/dm&sup3;, optional)</label>
                <input class="form-input" id="fert-oc" type="number" placeholder="e.g. 25">
              </div>
              <div class="form-group">
                <label class="form-label">Clay Percent (g/kg, optional)</label>
                <input class="form-input" id="fert-clay" type="number" placeholder="e.g. 300">
              </div>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="fert-run">
              <span>&#9654;</span> Get Recommendation
            </button>
          </div>
        </div>

        <div id="fert-results"></div>
      </div>`;

    $("#fert-run").addEventListener("click", async () => {
      const btn = $("#fert-run");
      const results = $("#fert-results");
      const ph = parseFloat($("#fert-ph").value);
      const oc = parseInt($("#fert-oc").value, 10);
      const clay = parseInt($("#fert-clay").value, 10);

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Calculating...';
      showLoading(results);

      try {
        const d = await api.fertilizer({
          crop_type: $("#fert-crop").value,
          target_yield: parseFloat($("#fert-yield").value),
          soil_ph: isNaN(ph) ? null : ph,
          organic_carbon: isNaN(oc) ? null : oc,
          clay_percent: isNaN(clay) ? null : clay,
          area_hectares: parseFloat($("#fert-area").value),
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Get Recommendation';

        const npk = d.npk_recommendation || {};
        const cost = d.cost_summary || {};

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Fertilizer Recommendation</h2>
            </div>

            <!-- NPK Summary -->
            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">Nitrogen (N)</div>
                <div class="stat-value" style="color:var(--ci-blue-600)">${fmt(npk.nitrogen_kg_per_ha, 1)}</div>
                <div class="stat-sub">kg/ha &middot; Total: ${fmt(npk.total_nitrogen_kg, 1)} kg</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Phosphorus (P&#8322;O&#8325;)</div>
                <div class="stat-value" style="color:var(--ci-purple-600)">${fmt(npk.phosphorus_kg_per_ha, 1)}</div>
                <div class="stat-sub">kg/ha &middot; Total: ${fmt(npk.total_phosphorus_kg, 1)} kg</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Potassium (K&#8322;O)</div>
                <div class="stat-value" style="color:var(--ci-orange-600)">${fmt(npk.potassium_kg_per_ha, 1)}</div>
                <div class="stat-sub">kg/ha &middot; Total: ${fmt(npk.total_potassium_kg, 1)} kg</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Total Cost</div>
                <div class="stat-value">${fmtUSD(cost.total_cost_usd)}</div>
                <div class="stat-sub">${fmtUSD(cost.cost_per_hectare_usd)} per ha</div>
              </div>
            </div>

            <!-- Products -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128230; Recommended Products</h3></div>
              <div class="card-body">
                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Composition</th>
                        <th>Qty/ha</th>
                        <th>Total Qty</th>
                        <th>Est. Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${(d.products || []).map(p => `
                        <tr>
                          <td class="text-bold">${p.name}</td>
                          <td class="text-muted">${p.composition}</td>
                          <td>${fmt(p.quantity_kg_per_ha, 1)} kg</td>
                          <td>${fmt(p.total_quantity_kg, 1)} kg</td>
                          <td>${fmtUSD(p.estimated_cost_usd)}</td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Schedule -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128197; Application Schedule</h3></div>
              <div class="card-body">
                ${(d.application_schedule || []).map((s, i) => `
                  <div style="padding:12px 0;${i > 0 ? "border-top:1px solid var(--ci-border);" : ""}">
                    <div class="flex items-center gap-12 mb-8">
                      <span class="badge badge-blue">${s.stage}</span>
                      <span class="text-sm text-muted">${s.timing}</span>
                    </div>
                    <div class="text-sm">${(s.products || []).join(", ")}</div>
                    ${s.notes ? `<div class="text-sm text-muted mt-8">${s.notes}</div>` : ""}
                  </div>
                `).join("")}
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
        btn.innerHTML = '<span>&#9654;</span> Get Recommendation';
        showError(results, err.message);
      }
    });
  },
});
