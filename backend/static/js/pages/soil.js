/* ═══════════════════════════════════════════════════════════════════
   Soil Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("soil", {
  title: "Soil Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#127793; Soil Engine</h1>
          <p>Analyze soil composition, pH classification, nutrient profiles, and health indexes via ISRIC SoilGrids</p>
        </div>

        <div class="card mb-24">
          <div class="card-header">
            <h3>Analysis Parameters</h3>
          </div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Latitude</label>
                <input class="form-input" id="soil-lat" type="number" step="0.001" value="17.385" placeholder="e.g. 17.385">
                <div class="form-hint">WGS-84 coordinate</div>
              </div>
              <div class="form-group">
                <label class="form-label">Longitude</label>
                <input class="form-input" id="soil-lon" type="number" step="0.001" value="78.487" placeholder="e.g. 78.487">
                <div class="form-hint">WGS-84 coordinate</div>
              </div>
            </div>
            <button class="btn btn-primary btn-lg" id="soil-run">
              <span>&#9654;</span> Run Soil Analysis
            </button>
          </div>
        </div>

        <div id="soil-results"></div>
      </div>`;

    $("#soil-run").addEventListener("click", async () => {
      const lat = parseFloat($("#soil-lat").value);
      const lon = parseFloat($("#soil-lon").value);
      const btn = $("#soil-run");
      const results = $("#soil-results");

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing...';
      showLoading(results);

      try {
        const d = await api.soil({ lat, lon });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Run Soil Analysis';

        const np = d.nutrient_profile || {};
        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Soil Analysis Results</h2>
              ${renderBadge(d.ph_classification || "unknown", d.ph_classification === "neutral" ? "green" : "amber")}
            </div>

            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">Soil pH</div>
                <div class="stat-value">${fmt(d.ph)}</div>
                <div class="stat-sub">${d.ph_classification || "N/A"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Clay Content</div>
                <div class="stat-value">${fmt(d.clay_percent, 0)} g/kg</div>
                <div class="stat-sub">${d.texture_class || "N/A"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Organic Carbon</div>
                <div class="stat-value">${fmt(d.organic_carbon, 0)} g/dm&sup3;</div>
                <div class="stat-sub">Carbon density</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Health Index</div>
                <div class="stat-value" style="color:${scoreColor(d.soil_health_index)}">${fmt(d.soil_health_index, 0)}/100</div>
                <div class="stat-sub">Composite score</div>
              </div>
            </div>

            <div class="card mb-24">
              <div class="card-header"><h3>Nutrient Profile</h3></div>
              <div class="card-body">
                <div class="kv-grid">
                  ${renderKV("Nitrogen", np.nitrogen || "N/A", "Soil N level")}
                  ${renderKV("Phosphorus", np.phosphorus || "N/A", "Available P")}
                  ${renderKV("Potassium", np.potassium || "N/A", "Exchangeable K")}
                  ${renderKV("Organic Carbon", np.organic_carbon_rating || "N/A", "OC rating")}
                </div>
              </div>
            </div>

            <div class="card mb-24">
              <div class="card-header">
                <h3>Health Score</h3>
                ${renderScoreRing(d.soil_health_index)}
              </div>
              <div class="card-body">
                ${renderRiskBar(d.soil_health_index, "Overall Soil Health")}
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
        btn.innerHTML = '<span>&#9654;</span> Run Soil Analysis';
        showError(results, err.message);
      }
    });
  },
});
