/* ═══════════════════════════════════════════════════════════════════
   Weather Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("weather", {
  title: "Weather Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#9925; Weather Engine</h1>
          <p>Climate analysis, 5-day forecasts, evapotranspiration modeling, and agricultural risk assessment</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Analysis Parameters</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Latitude</label>
                <input class="form-input" id="wx-lat" type="number" step="0.001" value="17.385" placeholder="e.g. 17.385">
              </div>
              <div class="form-group">
                <label class="form-label">Longitude</label>
                <input class="form-input" id="wx-lon" type="number" step="0.001" value="78.487" placeholder="e.g. 78.487">
              </div>
            </div>
            <button class="btn btn-primary btn-lg" id="wx-run">
              <span>&#9654;</span> Run Weather Analysis
            </button>
          </div>
        </div>

        <div id="wx-results"></div>
      </div>`;

    $("#wx-run").addEventListener("click", async () => {
      const lat = parseFloat($("#wx-lat").value);
      const lon = parseFloat($("#wx-lon").value);
      const btn = $("#wx-run");
      const results = $("#wx-results");

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing...';
      showLoading(results);

      try {
        const d = await api.weather({ lat, lon });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Run Weather Analysis';

        const cl = d.climate || {};
        const fc = d.forecast || {};
        const wm = d.water_model || {};
        const ra = d.risk_assessment || {};

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Weather Analysis Results</h2>
              ${renderBadge(
                ra.overall_risk_score != null ? (ra.overall_risk_score > 60 ? "High Risk" : ra.overall_risk_score > 30 ? "Moderate" : "Low Risk") : "N/A",
                ra.overall_risk_score > 60 ? "red" : ra.overall_risk_score > 30 ? "amber" : "green"
              )}
            </div>

            <!-- Climate Snapshot -->
            <div class="result-section">
              <h3 class="mb-8">&#127777; Climate Snapshot (30-day)</h3>
              <div class="stats-row">
                <div class="card stat-card">
                  <div class="stat-label">Avg Temperature</div>
                  <div class="stat-value">${fmt(cl.temperature_avg_30d)}&deg;C</div>
                  <div class="stat-sub">30-day average</div>
                </div>
                <div class="card stat-card">
                  <div class="stat-label">Solar Radiation</div>
                  <div class="stat-value">${fmt(cl.solar_radiation_avg_30d)} MJ/m&sup2;</div>
                  <div class="stat-sub">Daily average</div>
                </div>
                <div class="card stat-card">
                  <div class="stat-label">Wind Speed</div>
                  <div class="stat-value">${fmt(cl.wind_speed_avg_30d)} m/s</div>
                  <div class="stat-sub">Average wind</div>
                </div>
              </div>
            </div>

            <!-- Forecast -->
            <div class="result-section">
              <h3 class="mb-8">&#9748; 5-Day Forecast</h3>
              <div class="stats-row">
                <div class="card stat-card">
                  <div class="stat-label">Avg Temp</div>
                  <div class="stat-value">${fmt(fc.avg_temp_next_5d)}&deg;C</div>
                </div>
                <div class="card stat-card">
                  <div class="stat-label">Max Temp</div>
                  <div class="stat-value">${fmt(fc.max_temp_next_5d)}&deg;C</div>
                  ${fc.heat_risk_flag ? '<div class="stat-sub" style="color:var(--ci-red-500)">&#9888; Heat Risk</div>' : ""}
                </div>
                <div class="card stat-card">
                  <div class="stat-label">Total Rain</div>
                  <div class="stat-value">${fmt(fc.total_rain_next_5d)} mm</div>
                  ${fc.heavy_rain_flag ? '<div class="stat-sub" style="color:var(--ci-amber-500)">&#9888; Heavy Rain</div>' : ""}
                </div>
              </div>
            </div>

            <!-- Water Model -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128167; Water Model (ET0)</h3></div>
              <div class="card-body">
                <div class="kv-grid">
                  ${renderKV("ET0 Estimate", fmt(wm.et0_estimate) + " mm/day", "Reference evapotranspiration")}
                  ${renderKV("Water Stress", wm.water_stress_risk || "N/A")}
                  ${renderKV("Irrigation", wm.irrigation_recommendation || "N/A")}
                </div>
              </div>
            </div>

            <!-- Risks -->
            <div class="card mb-24">
              <div class="card-header">
                <h3>&#9888; Risk Assessment</h3>
                ${renderScoreRing(100 - (ra.overall_risk_score || 0))}
              </div>
              <div class="card-body">
                ${renderRiskBar(ra.drought_risk, "Drought Risk")}
                ${renderRiskBar(ra.flood_risk, "Flood Risk")}
                ${renderRiskBar(ra.frost_risk, "Frost Risk")}
                <div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--ci-border)">
                  ${renderRiskBar(ra.overall_risk_score, "Overall Risk Score")}
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
        btn.innerHTML = '<span>&#9654;</span> Run Weather Analysis';
        showError(results, err.message);
      }
    });
  },
});
