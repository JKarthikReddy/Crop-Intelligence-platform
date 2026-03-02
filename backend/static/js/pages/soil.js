/* ═══════════════════════════════════════════════════════════════════
   Soil Engine Page — Enterprise Diagnostic Dashboard
   ═══════════════════════════════════════════════════════════════════ */

registerPage("soil", {
  title: "Soil Engine",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>&#127793; Soil Engine</h1>
          <p>Diagnostic soil health analysis — detect deficiencies, score soil health, and get precision amendment recommendations</p>
        </div>

        <!-- ── Input Form ──────────────────────────────────────── -->
        <div class="card mb-24" style="border-left:4px solid var(--ci-green-500);">
          <div class="card-header"><h3>&#128221; Soil Test Data</h3></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Nitrogen (N) <span style="color:var(--ci-gray-400)">kg/ha</span></label>
                <input class="form-input" id="soil-n" type="number" step="0.1" min="0" max="500" value="45" placeholder="e.g. 45">
                <div class="form-hint">Ideal: 50 – 120 kg/ha</div>
              </div>
              <div class="form-group">
                <label class="form-label">Phosphorus (P) <span style="color:var(--ci-gray-400)">kg/ha</span></label>
                <input class="form-input" id="soil-p" type="number" step="0.1" min="0" max="200" value="30" placeholder="e.g. 30">
                <div class="form-hint">Ideal: 25 – 60 kg/ha</div>
              </div>
              <div class="form-group">
                <label class="form-label">Potassium (K) <span style="color:var(--ci-gray-400)">kg/ha</span></label>
                <input class="form-input" id="soil-k" type="number" step="0.1" min="0" max="500" value="40" placeholder="e.g. 40">
                <div class="form-hint">Ideal: 40 – 110 kg/ha</div>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Soil pH</label>
                <input class="form-input" id="soil-ph" type="number" step="0.01" min="0" max="14" value="6.5" placeholder="e.g. 6.5">
                <div class="form-hint">Optimal: 6.0 – 7.5</div>
              </div>
              <div class="form-group">
                <label class="form-label">Soil Type</label>
                <select class="form-input" id="soil-type">
                  <option value="Alluvial">Alluvial</option>
                  <option value="Black">Black</option>
                  <option value="Red">Red</option>
                  <option value="Laterite">Laterite</option>
                  <option value="Sandy">Sandy</option>
                  <option value="Clayey">Clayey</option>
                  <option value="Loamy" selected>Loamy</option>
                  <option value="Peaty">Peaty</option>
                  <option value="Saline">Saline</option>
                  <option value="Other">Other</option>
                </select>
                <div class="form-hint">Select soil category</div>
              </div>
            </div>
            <button class="btn btn-primary btn-lg" id="soil-run">
              <span>&#9654;</span> Analyze Soil Health
            </button>
          </div>
        </div>

        <div id="soil-results"></div>
      </div>`;

    $("#soil-run").addEventListener("click", async () => {
      const btn = $("#soil-run");
      const results = $("#soil-results");

      const n  = parseFloat($("#soil-n").value);
      const p  = parseFloat($("#soil-p").value);
      const k  = parseFloat($("#soil-k").value);
      const ph = parseFloat($("#soil-ph").value);
      const st = $("#soil-type").value;

      btn.classList.add("loading");
      btn.innerHTML = '<span class="spinner"></span> Analyzing…';
      showLoading(results);

      try {
        const d = await api.soil({ nitrogen: n, phosphorus: p, potassium: k, ph, soil_type: st });
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Analyze Soil Health';

        const np  = d.nutrient_profile || {};
        const pa  = d.ph_analysis || {};
        const sb  = d.score_breakdown || {};
        const si  = d.soil_insight || {};
        const defs = d.deficiencies || [];
        const recs = d.recommendations || [];

        /* color helpers */
        const healthColor = (h) => ({ Excellent:'var(--ci-green-500)', Good:'var(--ci-green-400)', Medium:'var(--ci-amber-500)', Low:'var(--ci-red-400)', Poor:'var(--ci-red-500)' })[h] || 'var(--ci-gray-400)';
        const statusColor = (s) => ({ Adequate:'var(--ci-green-500)', High:'var(--ci-amber-500)', Excess:'var(--ci-red-400)', Low:'var(--ci-amber-500)', Deficient:'var(--ci-red-500)' })[s] || 'var(--ci-gray-400)';
        const prioColor = (p) => ({ Critical:'var(--ci-red-500)', High:'var(--ci-amber-500)', Medium:'var(--ci-blue-500)', Low:'var(--ci-green-500)' })[p] || 'var(--ci-gray-400)';
        const prioIcon = (p) => ({ Critical:'&#9888;', High:'&#9888;', Medium:'&#128161;', Low:'&#9989;' })[p] || '&#8226;';
        const barPct = (val, max) => Math.min(100, Math.max(0, (val / max) * 100));

        /* nutrient bar helper */
        const nutrientBar = (label, detail, maxVal) => {
          const pct = barPct(detail.value, maxVal);
          const col = statusColor(detail.status);
          return '<div style="margin-bottom:16px;">' +
            '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">' +
              '<span style="font-weight:600;color:var(--ci-gray-800);">' + label + '</span>' +
              '<span style="font-size:0.85rem;color:' + col + ';font-weight:600;">' + detail.status + '</span>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:12px;">' +
              '<div style="flex:1;height:10px;background:var(--ci-gray-100);border-radius:5px;overflow:hidden;">' +
                '<div style="height:100%;width:' + pct + '%;background:' + col + ';border-radius:5px;transition:width 0.6s ease;"></div>' +
              '</div>' +
              '<span style="font-weight:700;min-width:80px;text-align:right;">' + detail.value + ' kg/ha</span>' +
            '</div>' +
            '<div style="font-size:0.78rem;color:var(--ci-gray-400);margin-top:2px;">Ideal: ' + detail.ideal_range + ' · Deviation: ' + (detail.deviation_pct > 0 ? '+' : '') + detail.deviation_pct + '%</div>' +
          '</div>';
        };

        /* score bar helper */
        const scoreBar = (label, val, max, color) => {
          const pct = barPct(val, max);
          return '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">' +
            '<span style="min-width:110px;font-size:0.85rem;color:var(--ci-gray-600);">' + label + '</span>' +
            '<div style="flex:1;height:8px;background:var(--ci-gray-100);border-radius:4px;overflow:hidden;">' +
              '<div style="height:100%;width:' + pct + '%;background:' + (color || 'var(--ci-green-500)') + ';border-radius:4px;"></div>' +
            '</div>' +
            '<span style="min-width:50px;text-align:right;font-weight:600;font-size:0.85rem;">' + val + '/' + max + '</span>' +
          '</div>';
        };

        results.innerHTML = `
          <div class="results-panel">

            <!-- ── Header ── -->
            <div class="results-header">
              <h2>Soil Diagnostic Report</h2>
              ${renderBadge(d.soil_health, d.score >= 70 ? 'green' : d.score >= 50 ? 'amber' : 'red')}
            </div>

            <!-- ── Hero Score Card ── -->
            <div class="card mb-24" style="background:linear-gradient(135deg,var(--ci-green-50),var(--ci-blue-50));border:1px solid var(--ci-green-200);">
              <div class="card-body" style="display:flex;align-items:center;gap:32px;flex-wrap:wrap;">
                <div style="text-align:center;min-width:130px;">
                  <div style="position:relative;width:120px;height:120px;margin:0 auto;">
                    <svg viewBox="0 0 36 36" style="width:120px;height:120px;transform:rotate(-90deg);">
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--ci-gray-200)" stroke-width="2.5"/>
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="${healthColor(d.soil_health)}" stroke-width="2.5"
                              stroke-dasharray="${d.score} ${100-d.score}" stroke-linecap="round"/>
                    </svg>
                    <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                      <span style="font-size:1.8rem;font-weight:800;color:${healthColor(d.soil_health)};">${d.score}</span>
                      <span style="font-size:0.7rem;color:var(--ci-gray-500);">/ 100</span>
                    </div>
                  </div>
                  <div style="margin-top:8px;font-weight:700;font-size:1rem;color:${healthColor(d.soil_health)};">${d.soil_health}</div>
                </div>
                <div style="flex:1;min-width:240px;">
                  <h3 style="margin:0 0 8px;">Soil Health Summary</h3>
                  <div style="color:var(--ci-gray-600);line-height:1.6;font-size:0.95rem;">
                    <div><strong>pH Status:</strong> ${d.ph_status} (${pa.value})</div>
                    <div><strong>Deficiencies:</strong> ${defs.length === 0 ? '<span style="color:var(--ci-green-500);">None detected &#10004;</span>' : '<span style="color:var(--ci-red-500);">' + defs.join(', ') + '</span>'}</div>
                    <div><strong>Soil Type:</strong> ${si.soil_type} — Fertility: ${si.fertility}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Score Breakdown ── -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128202; Score Breakdown</h3></div>
              <div class="card-body">
                ${scoreBar('Nitrogen', sb.nitrogen_score, 25, 'var(--ci-green-500)')}
                ${scoreBar('Phosphorus', sb.phosphorus_score, 20, 'var(--ci-blue-500)')}
                ${scoreBar('Potassium', sb.potassium_score, 20, 'var(--ci-amber-500)')}
                ${scoreBar('pH Balance', sb.ph_score, 25, 'var(--ci-purple-500)')}
                ${scoreBar('Soil Type', sb.soil_type_score, 10, 'var(--ci-gray-500)')}
                <div style="border-top:2px solid var(--ci-border);padding-top:10px;margin-top:10px;">
                  ${scoreBar('TOTAL', sb.total, 100, healthColor(d.soil_health))}
                </div>
              </div>
            </div>

            <!-- ── NPK Nutrient Profile ── -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#127811; Nutrient Profile (NPK)</h3></div>
              <div class="card-body">
                ${nutrientBar('Nitrogen (N)', np.nitrogen, 200)}
                ${nutrientBar('Phosphorus (P)', np.phosphorus, 100)}
                ${nutrientBar('Potassium (K)', np.potassium, 180)}
              </div>
            </div>

            <!-- ── pH Analysis ── -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#128167; pH Analysis</h3></div>
              <div class="card-body">
                <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
                  <div style="text-align:center;min-width:100px;">
                    <div style="font-size:2.2rem;font-weight:800;color:${pa.status === 'Neutral' ? 'var(--ci-green-500)' : 'var(--ci-amber-500)'};">${pa.value}</div>
                    <div style="font-size:0.85rem;color:var(--ci-gray-500);">pH Value</div>
                  </div>
                  <div style="flex:1;min-width:200px;">
                    <!-- pH Scale Bar -->
                    <div style="position:relative;height:28px;border-radius:14px;background:linear-gradient(90deg,#ef4444 0%,#f59e0b 25%,#22c55e 42%,#22c55e 58%,#f59e0b 75%,#ef4444 100%);margin-bottom:8px;">
                      <div style="position:absolute;top:-4px;left:${(pa.value / 14) * 100}%;transform:translateX(-50%);">
                        <div style="width:4px;height:36px;background:var(--ci-gray-900);border-radius:2px;"></div>
                      </div>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:var(--ci-gray-400);">
                      <span>0 (Acid)</span><span>7 (Neutral)</span><span>14 (Alkaline)</span>
                    </div>
                  </div>
                  <div style="min-width:160px;">
                    <div class="kv-grid">
                      ${renderKV('Status', pa.status)}
                      ${renderKV('Optimal', pa.optimal_range)}
                      ${renderKV('Deviation', (pa.deviation > 0 ? '+' : '') + pa.deviation)}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Soil Type Insight ── -->
            <div class="card mb-24">
              <div class="card-header"><h3>&#127758; Soil Type: ${si.soil_type}</h3></div>
              <div class="card-body">
                <div class="stats-row">
                  <div class="card stat-card">
                    <div class="stat-label">Water Retention</div>
                    <div class="stat-value" style="font-size:0.95rem;">${si.water_retention}</div>
                  </div>
                  <div class="card stat-card">
                    <div class="stat-label">Drainage</div>
                    <div class="stat-value" style="font-size:0.95rem;">${si.drainage}</div>
                  </div>
                  <div class="card stat-card">
                    <div class="stat-label">Fertility</div>
                    <div class="stat-value" style="font-size:0.95rem;">${si.fertility}</div>
                  </div>
                </div>
                <div style="margin-top:16px;">
                  <div style="font-weight:600;margin-bottom:6px;color:var(--ci-gray-700);">Best Suited Crops</div>
                  <div style="display:flex;flex-wrap:wrap;gap:6px;">
                    ${(si.best_crops || []).map(c => '<span style="display:inline-block;padding:4px 12px;background:var(--ci-green-50);color:var(--ci-green-700);border-radius:12px;font-size:0.82rem;font-weight:500;border:1px solid var(--ci-green-200);">' + c + '</span>').join('')}
                  </div>
                </div>
                <div style="margin-top:12px;padding:10px 14px;background:var(--ci-blue-50);border-radius:8px;font-size:0.88rem;color:var(--ci-blue-700);border:1px solid var(--ci-blue-200);">
                  &#128161; ${si.management_notes}
                </div>
              </div>
            </div>

            <!-- ── Deficiencies ── -->
            <div class="card mb-24">
              <div class="card-header">
                <h3>&#128680; Deficiency Alert</h3>
                ${renderBadge(defs.length === 0 ? 'All Clear' : defs.length + ' Issue' + (defs.length > 1 ? 's' : ''), defs.length === 0 ? 'green' : 'red')}
              </div>
              <div class="card-body">
                ${defs.length === 0
                  ? '<div style="text-align:center;padding:20px;color:var(--ci-green-600);font-size:1.1rem;">&#10004; No nutrient deficiencies detected. Soil is within acceptable ranges.</div>'
                  : '<div style="display:flex;flex-wrap:wrap;gap:10px;">' + defs.map(d =>
                      '<div style="display:flex;align-items:center;gap:8px;padding:10px 16px;background:var(--ci-red-50);border:1px solid var(--ci-red-200);border-radius:8px;">' +
                        '<span style="color:var(--ci-red-500);font-size:1.2rem;">&#9888;</span>' +
                        '<span style="font-weight:600;color:var(--ci-red-700);">' + d + '</span>' +
                      '</div>'
                    ).join('') + '</div>'
                }
              </div>
            </div>

            <!-- ── Recommendations ── -->
            <div class="card">
              <div class="card-header"><h3>&#128736; Amendment Recommendations</h3></div>
              <div class="card-body" style="padding:0;">
                ${recs.map((r, i) =>
                  '<div style="display:flex;gap:14px;padding:16px 20px;' + (i < recs.length - 1 ? 'border-bottom:1px solid var(--ci-border);' : '') + '">' +
                    '<div style="min-width:36px;height:36px;display:flex;align-items:center;justify-content:center;border-radius:8px;background:' + prioColor(r.priority) + '15;color:' + prioColor(r.priority) + ';font-size:1.1rem;">' + prioIcon(r.priority) + '</div>' +
                    '<div style="flex:1;">' +
                      '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">' +
                        '<span style="font-weight:700;color:var(--ci-gray-800);">' + r.action + '</span>' +
                        '<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;background:' + prioColor(r.priority) + '15;color:' + prioColor(r.priority) + ';">' + r.priority + '</span>' +
                        '<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.72rem;background:var(--ci-gray-100);color:var(--ci-gray-600);">' + r.category + '</span>' +
                      '</div>' +
                      (r.product ? '<div style="font-size:0.85rem;color:var(--ci-gray-600);"><strong>Product:</strong> ' + r.product + (r.dosage ? ' &nbsp;|&nbsp; <strong>Dosage:</strong> ' + r.dosage : '') + '</div>' : '') +
                    '</div>' +
                  '</div>'
                ).join('')}
              </div>
            </div>

          </div>`;
      } catch (err) {
        btn.classList.remove("loading");
        btn.innerHTML = '<span>&#9654;</span> Analyze Soil Health';
        showError(results, err.message);
      }
    });
  },
});
