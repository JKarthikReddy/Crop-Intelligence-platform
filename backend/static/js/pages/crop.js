/* ═══════════════════════════════════════════════════════════════════
   Crop Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("crop", {
  title: "Crop Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#127806; Crop Engine</h1>
          <p>Satellite-based vegetation health analysis, NDVI classification, growth staging, and yield forecasting</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Analysis Parameters</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Latitude</label>
                <input class="form-input" id="crop-lat" type="number" step="0.001" value="17.385">
              </div>
              <div class="form-group">
                <label class="form-label">Longitude</label>
                <input class="form-input" id="crop-lon" type="number" step="0.001" value="78.487">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop Type</label>
                <select class="form-select" id="crop-type">
                  <option value="rice" selected>Rice</option>
                  <option value="wheat">Wheat</option>
                  <option value="maize">Maize</option>
                  <option value="soybean">Soybean</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Planting Date</label>
                <input class="form-input" id="crop-planting" type="date">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Bounding Box (West, South, East, North)</label>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px">
                  <input class="form-input" id="crop-w" type="number" step="0.01" value="78.40" placeholder="West">
                  <input class="form-input" id="crop-s" type="number" step="0.01" value="17.35" placeholder="South">
                  <input class="form-input" id="crop-e" type="number" step="0.01" value="78.55" placeholder="East">
                  <input class="form-input" id="crop-n" type="number" step="0.01" value="17.42" placeholder="North">
                </div>
                <div class="form-hint">WGS-84 bounding box for satellite analysis</div>
              </div>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="crop-run">
              <span>&#9654;</span> Run Crop Analysis
            </button>
          </div>
        </div>

        <div id="crop-results"></div>
      </div>`;

    $("#crop-run").addEventListener("click", async () => {
      const btn = $("#crop-run");
      const results = $("#crop-results");
      const planting = $("#crop-planting").value || null;

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing...';
      showLoading(results);

      try {
        const d = await api.crop({
          lat: parseFloat($("#crop-lat").value),
          lon: parseFloat($("#crop-lon").value),
          crop_type: $("#crop-type").value,
          planting_date: planting,
          bounds: [
            parseFloat($("#crop-w").value),
            parseFloat($("#crop-s").value),
            parseFloat($("#crop-e").value),
            parseFloat($("#crop-n").value),
          ],
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Run Crop Analysis';

        const veg = d.vegetation || {};
        const yf = d.yield_forecast || {};

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Crop Analysis Results</h2>
              ${renderBadge(veg.ndvi_classification || "unknown",
                veg.ndvi_classification === "excellent" ? "green" :
                veg.ndvi_classification === "good" ? "green" :
                veg.ndvi_classification === "fair" ? "amber" : "red"
              )}
            </div>

            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">NDVI Mean</div>
                <div class="stat-value">${fmt(veg.ndvi_mean, 3)}</div>
                <div class="stat-sub">${veg.ndvi_classification || "N/A"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Moisture</div>
                <div class="stat-value">${veg.moisture_status || "N/A"}</div>
                <div class="stat-sub">Soil moisture status</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Growth Stage</div>
                <div class="stat-value text-sm">${veg.growth_stage || "N/A"}</div>
                <div class="stat-sub">Current stage</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Health Score</div>
                <div class="stat-value" style="color:${scoreColor(d.crop_health_score)}">${fmt(d.crop_health_score, 0)}/100</div>
                <div class="stat-sub">Crop health index</div>
              </div>
            </div>

            <!-- Yield Forecast -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#127807; Yield Forecast</h3></div>
              <div class="card-body">
                <div class="kv-grid">
                  ${renderKV("Predicted Yield", fmt(yf.predicted_yield) + " t/ha", yf.model_version || "")}
                  ${renderKV("Confidence", fmtPct(yf.confidence))}
                  ${renderKV("Yield Trend", yf.yield_trend || "N/A")}
                  ${renderKV("Harvest Window", d.optimal_harvest_window || "N/A")}
                </div>
              </div>
            </div>

            <!-- Health -->
            <div class="card mb-24">
              <div class="card-header">
                <h3>Crop Health</h3>
                ${renderScoreRing(d.crop_health_score)}
              </div>
              <div class="card-body">
                ${renderRiskBar(d.crop_health_score, "Overall Crop Health")}
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
        btn.innerHTML = '<span>&#9654;</span> Run Crop Analysis';
        showError(results, err.message);
      }
    });
  },
});
