/* ═══════════════════════════════════════════════════════════════════
   Crop Recommendation Engine Page
   ═══════════════════════════════════════════════════════════════════ */

registerPage("crop", {
  title: "Crop Recommendation",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#127806; Crop Recommendation Engine</h1>
          <p>ML-powered crop recommendation based on soil conditions, weather data, and regional suitability</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>&#129717; Soil Data</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Nitrogen (kg/ha)</label>
                <input class="form-input" id="crop-n" type="number" step="1" min="0" max="500" value="45">
              </div>
              <div class="form-group">
                <label class="form-label">Phosphorus (kg/ha)</label>
                <input class="form-input" id="crop-p" type="number" step="1" min="0" max="200" value="30">
              </div>
              <div class="form-group">
                <label class="form-label">Potassium (kg/ha)</label>
                <input class="form-input" id="crop-k" type="number" step="1" min="0" max="500" value="40">
              </div>
              <div class="form-group">
                <label class="form-label">Soil pH</label>
                <input class="form-input" id="crop-ph" type="number" step="0.1" min="0" max="14" value="6.5">
              </div>
            </div>
          </div>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>&#9748; Weather Data</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Temperature (&deg;C)</label>
                <input class="form-input" id="crop-temp" type="number" step="0.1" min="-10" max="60" value="32">
              </div>
              <div class="form-group">
                <label class="form-label">Humidity (%)</label>
                <input class="form-input" id="crop-hum" type="number" step="1" min="0" max="100" value="75">
              </div>
              <div class="form-group">
                <label class="form-label">Rainfall (mm)</label>
                <input class="form-input" id="crop-rain" type="number" step="1" min="0" max="5000" value="120">
              </div>
            </div>
          </div>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>&#128205; Location &amp; Season</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group" style="flex:2">
                <label class="form-label">Location</label>
                <input class="form-input" id="crop-loc" type="text" value="Guntur, Andhra Pradesh" placeholder="District, State">
                <div class="form-hint">e.g. Guntur, Andhra Pradesh / Punjab / Indore</div>
              </div>
              <div class="form-group">
                <label class="form-label">Season</label>
                <select class="form-select" id="crop-season">
                  <option value="">Auto-detect</option>
                  <option value="Kharif" selected>Kharif</option>
                  <option value="Rabi">Rabi</option>
                  <option value="Zaid">Zaid</option>
                </select>
              </div>
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="crop-run">
              <span>&#9654;</span> Get Crop Recommendation
            </button>
          </div>
        </div>

        <div id="crop-results"></div>
      </div>`;

    const parseNum = (id) => {
      const v = parseFloat($(id).value);
      return isNaN(v) ? 0 : v;
    };

    $("#crop-run").addEventListener("click", async () => {
      const btn = $("#crop-run");
      const results = $("#crop-results");

      // Build payload
      const payload = {
        soil_data: {
          nitrogen: parseNum("#crop-n"),
          phosphorus: parseNum("#crop-p"),
          potassium: parseNum("#crop-k"),
          ph: parseNum("#crop-ph"),
        },
        weather_data: {
          temperature: parseNum("#crop-temp"),
          humidity: parseNum("#crop-hum"),
          rainfall: parseNum("#crop-rain"),
        },
        location: $("#crop-loc").value.trim() || "India",
        season: $("#crop-season").value || null,
      };

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing...';
      showLoading(results);

      try {
        const d = await api.crop(payload);
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Get Crop Recommendation';

        const confColor = d.confidence >= 85 ? "green" :
                          d.confidence >= 70 ? "green" :
                          d.confidence >= 50 ? "amber" : "red";

        const altsHtml = (d.top_alternatives || []).map((a, i) => `
          <tr>
            <td style="font-weight:600">${i + 2}</td>
            <td><strong>${a.crop}</strong></td>
            <td><span style="color:${scoreColor(a.confidence)};font-weight:700">${fmt(a.confidence, 1)}%</span></td>
            <td>${a.suitability}</td>
          </tr>`).join("");

        const reasonHtml = (d.reasoning || []).map(r =>
          `<li style="padding:6px 0;border-bottom:1px solid var(--border)">${r}</li>`
        ).join("");

        const fvLabels = ["N", "P", "K", "pH", "Temp", "Humidity", "Rainfall"];
        const fvHtml = (d.feature_vector || []).map((v, i) =>
          `<span class="badge" style="margin:4px;padding:6px 10px;font-size:0.85rem">${fvLabels[i] || i}: <strong>${typeof v === 'number' ? v.toFixed(1) : v}</strong></span>`
        ).join("");

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Crop Recommendation</h2>
              ${renderBadge(d.confidence_level || "Unknown", confColor)}
            </div>

            <!-- Hero Card: Top Recommendation -->
            <div class="card mb-24" style="border-left:4px solid var(--success);background:var(--bg-secondary)">
              <div class="card-body" style="text-align:center;padding:32px">
                <div style="font-size:3rem;margin-bottom:8px">&#127793;</div>
                <div style="font-size:1.6rem;font-weight:800;color:var(--text-primary)">${d.recommended_crop}</div>
                <div style="font-size:2rem;font-weight:700;color:${scoreColor(d.confidence)};margin:8px 0">${fmt(d.confidence, 1)}%</div>
                <div style="font-size:0.95rem;color:var(--text-secondary)">Confidence: <strong>${d.confidence_level}</strong> &middot; ${d.season} Season &middot; ${d.location}</div>
              </div>
            </div>

            <!-- Stats Row -->
            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">Recommended Crop</div>
                <div class="stat-value" style="font-size:1.1rem">${d.recommended_crop}</div>
                <div class="stat-sub">${d.confidence_level} confidence</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Confidence</div>
                <div class="stat-value" style="color:${scoreColor(d.confidence)}">${fmt(d.confidence, 1)}%</div>
                <div class="stat-sub">${d.confidence_level}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Season</div>
                <div class="stat-value text-sm">${d.season}</div>
                <div class="stat-sub">${d.location}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Health Score</div>
                <div class="stat-value" style="color:${scoreColor(d.crop_health_score)}">${fmt(d.crop_health_score, 0)}/100</div>
                <div class="stat-sub">Advisory index</div>
              </div>
            </div>

            <!-- Alternatives Table -->
            ${altsHtml ? `
            <div class="card mb-24">
              <div class="card-header"><h3>&#128202; Top Alternatives</h3></div>
              <div class="card-body" style="padding:0">
                <table style="width:100%;border-collapse:collapse">
                  <thead>
                    <tr style="background:var(--bg-secondary);text-align:left">
                      <th style="padding:12px 16px;width:50px">Rank</th>
                      <th style="padding:12px 16px">Crop</th>
                      <th style="padding:12px 16px">Confidence</th>
                      <th style="padding:12px 16px">Suitability</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style="background:var(--success-bg,rgba(34,197,94,0.08))">
                      <td style="padding:10px 16px;font-weight:600">1 &#9733;</td>
                      <td><strong>${d.recommended_crop}</strong></td>
                      <td><span style="color:${scoreColor(d.confidence)};font-weight:700">${fmt(d.confidence, 1)}%</span></td>
                      <td>Best match</td>
                    </tr>
                    ${altsHtml}
                  </tbody>
                </table>
              </div>
            </div>` : ""}

            <!-- Reasoning -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128161; Why This Crop?</h3></div>
              <div class="card-body">
                <ul style="list-style:none;padding:0;margin:0">${reasonHtml}</ul>
              </div>
            </div>

            <!-- Feature Vector -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128200; Feature Vector</h3></div>
              <div class="card-body" style="display:flex;flex-wrap:wrap;gap:4px">
                ${fvHtml}
              </div>
            </div>

            <!-- Confidence Gauge -->
            <div class="card">
              <div class="card-header">
                <h3>Recommendation Confidence</h3>
                ${renderScoreRing(d.confidence)}
              </div>
              <div class="card-body">
                ${renderRiskBar(d.confidence, "Prediction Confidence")}
              </div>
            </div>
          </div>`;
      } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Get Crop Recommendation';
        showError(results, err.message);
      }
    });
  },
});
