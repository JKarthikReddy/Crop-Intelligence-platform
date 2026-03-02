/* ═══════════════════════════════════════════════════════════════════
   Fertilizer Optimization Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("fertilizer", {
  title: "Fertilizer Engine",
  render(container) {
    const deficiencyOptions = ["Nitrogen", "Phosphorus", "Potassium",
      "pH (too acidic)", "pH (too alkaline)"];
    const healthOptions = ["Poor", "Low", "Medium", "Good", "Excellent"];
    const phOptions = ["Strongly Acidic", "Moderately Acidic", "Slightly Acidic",
      "Neutral", "Slightly Alkaline", "Moderately Alkaline", "Strongly Alkaline"];

    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#129716; Fertilizer Optimization Engine</h1>
          <p>Deficiency-driven fertilizer recommendations — type, quantity, schedule &amp; advisory notes</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Soil Report &amp; Crop Selection</h3></div>
          <div class="card-body">
            <!-- Deficiencies -->
            <div class="form-group mb-16">
              <label class="form-label">Nutrient Deficiencies (select all that apply)</label>
              <div id="fert-def-checks" style="display:flex;flex-wrap:wrap;gap:12px;margin-top:4px">
                ${deficiencyOptions.map(d => `
                  <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
                    <input type="checkbox" class="fert-def-cb" value="${d}"> ${d}
                  </label>
                `).join("")}
              </div>
              <div class="form-hint">From Soil Engine output</div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Soil Health</label>
                <select class="form-select" id="fert-health">
                  ${healthOptions.map(h => `<option value="${h}" ${h === "Medium" ? "selected" : ""}>${h}</option>`).join("")}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">pH Status</label>
                <select class="form-select" id="fert-ph-status">
                  ${phOptions.map(p => `<option value="${p}" ${p === "Neutral" ? "selected" : ""}>${p}</option>`).join("")}
                </select>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Selected Crop</label>
                <input class="form-input" id="fert-crop" type="text" value="Rice"
                  placeholder="e.g. Red Chilli, Cotton, Wheat">
                <div class="form-hint">From Crop Engine or enter manually</div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Land Area</label>
                <input class="form-input" id="fert-area" type="number" step="0.5" value="1.0" min="0.1">
              </div>
              <div class="form-group">
                <label class="form-label">Unit</label>
                <select class="form-select" id="fert-unit">
                  <option value="acre" selected>Acre</option>
                  <option value="hectare">Hectare</option>
                </select>
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

      // Collect selected deficiencies
      const deficiencies = Array.from(document.querySelectorAll(".fert-def-cb:checked"))
        .map(cb => cb.value);

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Calculating...';
      showLoading(results);

      try {
        const d = await api.fertilizer({
          soil_report: {
            deficiencies,
            soil_health: $("#fert-health").value,
            ph_status: $("#fert-ph-status").value,
          },
          selected_crop: $("#fert-crop").value,
          land_area: parseFloat($("#fert-area").value),
          unit: $("#fert-unit").value,
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Get Recommendation';

        const fertList = d.fertilizers || [];
        const qtyAcre = d.quantity_per_acre || {};
        const qtyTotal = d.total_required || {};
        const schedule = d.schedule || d.application_schedule || [];
        const notes = d.notes || [];

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Fertilizer Recommendation</h2>
            </div>

            <!-- Recommended Fertilizers -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128230; Recommended Fertilizers</h3></div>
              <div class="card-body">
                <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px">
                  ${fertList.map(f => `<span class="badge badge-green" style="font-size:0.95rem;padding:6px 14px">${f}</span>`).join("")}
                </div>

                <div class="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Qty / Acre</th>
                        <th>Total Required</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${fertList.map(f => `
                        <tr>
                          <td class="text-bold">${f}</td>
                          <td>${qtyAcre[f] || "—"}</td>
                          <td>${qtyTotal[f] || "—"}</td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Application Schedule -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128197; Application Schedule</h3></div>
              <div class="card-body">
                ${schedule.map((s, i) => `
                  <div style="padding:12px 0;${i > 0 ? "border-top:1px solid var(--ci-border);" : ""}">
                    <div class="flex items-center gap-12 mb-8">
                      <span class="badge badge-blue">${s.stage}</span>
                      <span class="text-sm text-muted">${s.timing}</span>
                    </div>
                    <div class="text-sm">${(s.products || []).join(", ") || "<em>No application</em>"}</div>
                    ${s.notes ? `<div class="text-sm text-muted mt-8">${s.notes}</div>` : ""}
                  </div>
                `).join("")}
              </div>
            </div>

            <!-- Advisory Notes -->
            <div class="card">
              <div class="card-header"><h3>&#128161; Advisory Notes</h3></div>
              <div class="card-body">
                ${notes.length ? `<ul class="rec-list">${notes.map(n => `<li>${n}</li>`).join("")}</ul>` : '<p class="text-muted">No specific notes</p>'}
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
