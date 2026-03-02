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

        const cw = d.current || {};
        const cl = d.climate || {};
        const fc = d.forecast || {};
        const wm = d.water_model || {};
        const ra = d.risk_assessment || {};

        /* helper — convert unix timestamp to locale time string */
        const ts = (unix) => unix ? new Date(unix * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A';
        /* helper — weather icon URL */
        const iconUrl = (code) => code ? `https://openweathermap.org/img/wn/${code}@2x.png` : '';

        results.innerHTML = `
          <div class="results-panel">
            <div class="results-header">
              <h2>Weather Analysis Results</h2>
              ${renderBadge(
                ra.overall_risk_score != null ? (ra.overall_risk_score > 60 ? "High Risk" : ra.overall_risk_score > 30 ? "Moderate" : "Low Risk") : "N/A",
                ra.overall_risk_score > 60 ? "red" : ra.overall_risk_score > 30 ? "amber" : "green"
              )}
            </div>

            <!-- Current Weather -->
            ${cw.temperature != null ? `
            <div class="result-section">
              <h3 class="mb-8">&#127774; Current Weather — ${cw.city_name || 'Unknown'}${cw.country ? ', ' + cw.country : ''}</h3>
              <div class="card mb-24" style="background:linear-gradient(135deg,var(--ci-green-50),var(--ci-blue-50));border:1px solid var(--ci-green-200);">
                <div class="card-body" style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
                  <div style="text-align:center;min-width:100px;">
                    ${cw.weather_icon ? '<img src="' + iconUrl(cw.weather_icon) + '" alt="' + cw.weather_main + '" width="80" height="80" style="filter:drop-shadow(0 2px 4px rgba(0,0,0,0.15));">' : ''}
                    <div style="font-weight:600;text-transform:capitalize;color:var(--ci-gray-700);">${cw.weather_description || cw.weather_main || ''}</div>
                  </div>
                  <div style="flex:1;min-width:200px;">
                    <div style="font-size:2.5rem;font-weight:700;color:var(--ci-gray-900);line-height:1;">${cw.temperature.toFixed(1)}&deg;C</div>
                    <div style="color:var(--ci-gray-500);margin-top:4px;">Feels like ${cw.feels_like.toFixed(1)}&deg;C &nbsp;|&nbsp; ${cw.temp_min.toFixed(1)}&deg; ~ ${cw.temp_max.toFixed(1)}&deg;</div>
                  </div>
                </div>
                <div class="card-body" style="border-top:1px solid var(--ci-border);padding-top:12px;">
                  <div class="stats-row">
                    <div class="card stat-card">
                      <div class="stat-label">Humidity</div>
                      <div class="stat-value">${cw.humidity}%</div>
                    </div>
                    <div class="card stat-card">
                      <div class="stat-label">Pressure</div>
                      <div class="stat-value">${cw.pressure} hPa</div>
                    </div>
                    <div class="card stat-card">
                      <div class="stat-label">Wind</div>
                      <div class="stat-value">${cw.wind_speed} m/s</div>
                      <div class="stat-sub">${cw.wind_deg}&deg;${cw.wind_gust ? ' · gust ' + cw.wind_gust + ' m/s' : ''}</div>
                    </div>
                    <div class="card stat-card">
                      <div class="stat-label">Visibility</div>
                      <div class="stat-value">${(cw.visibility / 1000).toFixed(1)} km</div>
                    </div>
                    <div class="card stat-card">
                      <div class="stat-label">Clouds</div>
                      <div class="stat-value">${cw.clouds}%</div>
                    </div>
                    <div class="card stat-card">
                      <div class="stat-label">Sunrise / Sunset</div>
                      <div class="stat-value">${ts(cw.sunrise)} / ${ts(cw.sunset)}</div>
                    </div>
                  </div>
                  ${cw.rain_1h != null ? '<div style="margin-top:8px;color:var(--ci-blue-600);font-weight:500;">&#127783; Rain: ' + cw.rain_1h + ' mm/h</div>' : ''}
                  ${cw.snow_1h != null ? '<div style="margin-top:8px;color:var(--ci-blue-400);font-weight:500;">&#10052; Snow: ' + cw.snow_1h + ' mm/h</div>' : ''}
                </div>
              </div>
            </div>
            ` : ''}

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
