/* ═══════════════════════════════════════════════════════════════════
   Disease Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("disease", {
  title: "Disease Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#128030; Disease Engine</h1>
          <p>Crop-specific disease risk assessment — 12 disease profiles across 4 crops with prevention plans</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Assessment Parameters</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop Type</label>
                <select class="form-select" id="dis-crop">
                  <option value="rice" selected>Rice</option>
                  <option value="wheat">Wheat</option>
                  <option value="maize">Maize</option>
                  <option value="soybean">Soybean</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Growth Stage (optional)</label>
                <select class="form-select" id="dis-stage">
                  <option value="">Auto-detect</option>
                  <option value="seedling">Seedling</option>
                  <option value="vegetative">Vegetative</option>
                  <option value="reproductive">Reproductive</option>
                  <option value="maturity">Maturity</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Avg Temperature (&deg;C, optional)</label>
                <input class="form-input" id="dis-temp" type="number" step="0.1" placeholder="e.g. 28.5">
                <div class="form-hint">From Weather Engine</div>
              </div>
              <div class="form-group">
                <label class="form-label">Avg Humidity (%, optional)</label>
                <input class="form-input" id="dis-hum" type="number" step="1" placeholder="e.g. 75">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Recent Rainfall (mm, optional)</label>
                <input class="form-input" id="dis-rain" type="number" step="1" placeholder="e.g. 50">
              </div>
              <div class="form-group">
                <label class="form-label">NDVI Mean (optional)</label>
                <input class="form-input" id="dis-ndvi" type="number" step="0.01" placeholder="e.g. 0.65">
                <div class="form-hint">From Crop Engine</div>
              </div>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="dis-run">
              <span>&#9654;</span> Assess Disease Risk
            </button>
          </div>
        </div>

        <div id="dis-results"></div>
      </div>`;

    $("#dis-run").addEventListener("click", async () => {
      const btn = $("#dis-run");
      const results = $("#dis-results");

      const optFloat = (id) => { const v = parseFloat($(id).value); return isNaN(v) ? null : v; };
      const stage = $("#dis-stage").value || null;

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Assessing...';
      showLoading(results);

      try {
        const d = await api.disease({
          crop_type: $("#dis-crop").value,
          growth_stage: stage,
          avg_temperature: optFloat("#dis-temp"),
          avg_humidity: optFloat("#dis-hum"),
          recent_rainfall_mm: optFloat("#dis-rain"),
          ndvi_mean: optFloat("#dis-ndvi"),
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Assess Disease Risk';

        const riskBadgeColor = d.risk_level === "low" ? "green" : d.risk_level === "moderate" ? "amber" : "red";

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Disease Risk Assessment</h2>
              ${renderBadge(d.risk_level || "unknown", riskBadgeColor)}
            </div>

            <!-- Overall -->
            <div class="card mb-24">
              <div class="card-header">
                <h3>Overall Disease Risk</h3>
                ${renderScoreRing(100 - (d.overall_risk_score || 0))}
              </div>
              <div class="card-body">
                ${renderRiskBar(d.overall_risk_score, "Disease Risk Score")}
              </div>
            </div>

            <!-- Individual Diseases -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128270; Disease Profiles</h3></div>
              <div class="card-body">
                ${(d.disease_risks || []).map((dr) => {
                  const col = dr.risk_level === "low" ? "green" : dr.risk_level === "moderate" ? "amber" : "red";
                  return `
                    <div style="padding:16px 0;border-bottom:1px solid var(--ci-border)">
                      <div class="flex items-center gap-12 mb-8">
                        <span class="text-bold">${dr.disease_name}</span>
                        ${renderBadge(dr.risk_level, col)}
                        <span class="text-sm text-muted" style="margin-left:auto">${fmt(dr.risk_score, 0)}/100</span>
                      </div>
                      ${renderRiskBar(dr.risk_score, "")}
                      <div class="text-sm text-muted mt-8">
                        <strong>Type:</strong> ${dr.pathogen_type || "N/A"}
                      </div>
                      ${dr.favorable_conditions ? `<div class="text-sm text-muted mt-8"><strong>Favored by:</strong> ${dr.favorable_conditions}</div>` : ""}
                      ${dr.symptoms ? `<div class="text-sm text-muted mt-8"><strong>Symptoms:</strong> ${dr.symptoms}</div>` : ""}
                    </div>`;
                }).join("")}
              </div>
            </div>

            <!-- Prevention Plan -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128737; Prevention Plan</h3></div>
              <div class="card-body">
                ${(d.prevention_plan || []).map((pp) => `
                  <div style="padding:12px 0;border-bottom:1px solid var(--ci-border)">
                    <div class="flex items-center gap-8 mb-8">
                      ${renderBadge(pp.priority,
                        pp.priority === "Immediate" ? "red" :
                        pp.priority === "Short-term" ? "amber" : "blue"
                      )}
                      ${renderBadge(pp.method, "gray")}
                    </div>
                    <div class="text-bold text-sm">${pp.action}</div>
                    ${pp.details ? `<div class="text-sm text-muted mt-8">${pp.details}</div>` : ""}
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
        btn.innerHTML = '<span>&#9654;</span> Assess Disease Risk';
        showError(results, err.message);
      }
    });
  },
});
