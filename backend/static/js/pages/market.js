/* ═══════════════════════════════════════════════════════════════════
   Market Engine Page — Indian Mandi Price Intelligence
   ═══════════════════════════════════════════════════════════════════ */

registerPage("market", {
  title: "Market Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#128200; Market Engine</h1>
          <p>Mandi price tracking, 7-day trend analysis, price prediction &amp; sell/hold advisory</p>
        </div>

        <div class="card mb-24">
          <div class="card-header"><h3>Market Query</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Crop</label>
                <input class="form-input" id="mkt-crop" type="text" value="Red Chilli" placeholder="e.g. Red Chilli, Rice, Cotton">
                <div class="form-hint">Crop name — matches Crop Engine output</div>
              </div>
              <div class="form-group">
                <label class="form-label">Location / Mandi</label>
                <input class="form-input" id="mkt-location" type="text" value="Guntur" placeholder="e.g. Guntur, Warangal, Nashik">
                <div class="form-hint">District or mandi name</div>
              </div>
            </div>
            <div class="form-group" style="max-width:300px">
              <label class="form-label">Quantity (quintals, optional)</label>
              <input class="form-input" id="mkt-qty" type="number" step="1" placeholder="e.g. 50">
            </div>
            <button class="btn btn-primary btn-lg mt-8" id="mkt-run">
              <span>&#9654;</span> Check Prices
            </button>
          </div>
        </div>

        <div id="mkt-results"></div>
      </div>`;

    $("#mkt-run").addEventListener("click", async () => {
      const btn  = $("#mkt-run");
      const out  = $("#mkt-results");
      const optF = (id) => { const v = parseFloat($(id).value); return isNaN(v) ? null : v; };

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Fetching prices\u2026';
      showLoading(out);

      try {
        const d = await api.market({
          crop:     $("#mkt-crop").value.trim(),
          location: $("#mkt-location").value.trim(),
          quantity: optF("#mkt-qty"),
        });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Check Prices';

        /* helpers */
        const rupee = (v) => v != null ? "\u20b9" + Number(v).toLocaleString("en-IN", {maximumFractionDigits:0}) : "\u2014";
        const trendIcon = d.trend === "Increasing" ? "\u25b2" : d.trend === "Decreasing" ? "\u25bc" : "\u25cf";
        const trendColor = d.trend === "Increasing" ? "var(--ci-green-600)"
                         : d.trend === "Decreasing" ? "var(--ci-red-500)" : "var(--ci-blue-600)";
        const recColor = d.recommendation?.toLowerCase().includes("hold") ? "amber"
                       : d.recommendation?.toLowerCase().includes("immediately") ? "red"
                       : d.recommendation?.toLowerCase().includes("sell") ? "green" : "blue";

        /* Nearby mandis table rows */
        const mandiRows = (d.nearby_mandis || []).map(m => `
          <tr>
            <td>${m.mandi}</td>
            <td style="text-align:right;font-weight:600">${rupee(m.price)}</td>
            <td style="text-align:right">${m.distance_km != null ? m.distance_km + " km" : "Local"}</td>
          </tr>`).join("");

        /* Price history rows */
        const histRows = (d.price_history || []).map(h => `
          <tr>
            <td>${h.label}</td>
            <td style="text-align:right;font-weight:600">${rupee(h.price)}</td>
          </tr>`).join("");

        out.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Market Intelligence</h2>
              ${renderBadge(d.recommendation || "N/A", recColor)}
            </div>

            <!-- Price Stats -->
            <div class="stats-row">
              <div class="card stat-card">
                <div class="stat-label">Current Price</div>
                <div class="stat-value">${rupee(d.current_price)}</div>
                <div class="stat-sub">${d.unit || "\u20b9/quintal"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">7-Day Average</div>
                <div class="stat-value">${rupee(d.seven_day_avg)}</div>
                <div class="stat-sub">${d.unit || "\u20b9/quintal"}</div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Trend</div>
                <div class="stat-value" style="color:${trendColor}">
                  ${trendIcon} ${d.trend || "N/A"}
                </div>
              </div>
              <div class="card stat-card">
                <div class="stat-label">Expected Next Week</div>
                <div class="stat-value">${rupee(d.expected_price_next_week)}</div>
                <div class="stat-sub">predicted</div>
              </div>
            </div>

            <!-- Nearby Mandis -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#127981; Nearby Mandi Prices</h3></div>
              <div class="card-body">
                <table class="data-table" style="width:100%">
                  <thead><tr><th>Mandi</th><th style="text-align:right">Price (${d.unit || "\u20b9/quintal"})</th><th style="text-align:right">Distance</th></tr></thead>
                  <tbody>${mandiRows || '<tr><td colspan="3">No nearby mandis found</td></tr>'}</tbody>
                </table>
              </div>
            </div>

            <!-- Price History -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128202; 7-Day Price History</h3></div>
              <div class="card-body">
                <table class="data-table" style="width:100%;max-width:400px">
                  <thead><tr><th>Day</th><th style="text-align:right">Price</th></tr></thead>
                  <tbody>${histRows}</tbody>
                </table>
              </div>
            </div>

            <!-- Advisory Notes -->
            <div class="card">
              <div class="card-header"><h3>&#128161; Advisory Notes</h3></div>
              <div class="card-body">
                ${renderRecs(d.notes)}
              </div>
            </div>
          </div>`;
      } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Check Prices';
        showError(out, err.message);
      }
    });
  },
});
