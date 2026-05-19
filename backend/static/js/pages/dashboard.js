/* ═══════════════════════════════════════════════════════════════════
   Dashboard — Main landing page with engine overview
   ═══════════════════════════════════════════════════════════════════ */

registerPage("dashboard", {
  title: "Dashboard",
  render(container) {
    container.innerHTML = `
      <div class="page">
        <div class="page-header">
          <h1>Crop Intelligence Dashboard</h1>
          <p>Enterprise agricultural intelligence platform — 9 domain engines working together</p>
        </div>

        <!-- Quick Stats -->
        <div class="stats-row" id="dash-stats">
          <div class="card stat-card">
            <div class="stat-label">Engines Online</div>
            <div class="stat-value" style="color:var(--ci-green-600)">9 / 9</div>
            <div class="stat-sub">All systems operational</div>
          </div>
          <div class="card stat-card">
            <div class="stat-label">API Version</div>
            <div class="stat-value">v1</div>
            <div class="stat-sub">/api/v1 prefix</div>
          </div>
          <div class="card stat-card">
            <div class="stat-label">Architecture</div>
            <div class="stat-value">DDD</div>
            <div class="stat-sub">Domain-driven engines</div>
          </div>
          <div class="card stat-card">
            <div class="stat-label">Status</div>
            <div class="stat-value" id="dash-health-val" style="color:var(--ci-green-600)">OK</div>
            <div class="stat-sub" id="dash-health-sub">Version 0.1.0</div>
          </div>
        </div>

        <!-- Engine Cards Grid -->
        <h2 class="mb-16">Intelligence Engines</h2>
        <div class="engine-grid">

          <!-- Soil -->
          <div class="card card-clickable engine-card engine-soil" data-nav="soil">
            <div class="engine-icon">&#127793;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Soil Engine</h3>
            <p>Analyze soil composition, pH levels, nutrient profiles, and generate health indexes for any location worldwide.</p>
            <div class="engine-features">
              <span class="feature-tag">pH Classification</span>
              <span class="feature-tag">Nutrient Profile</span>
              <span class="feature-tag">Health Index</span>
              <span class="feature-tag">ISRIC SoilGrids</span>
            </div>
          </div>

          <!-- Weather -->
          <div class="card card-clickable engine-card engine-weather" data-nav="weather">
            <div class="engine-icon">&#9925;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Weather Engine</h3>
            <p>Climate analysis, 5-day forecasts, ET0 water modeling, and comprehensive risk assessment.</p>
            <div class="engine-features">
              <span class="feature-tag">NASA POWER</span>
              <span class="feature-tag">OpenWeather</span>
              <span class="feature-tag">ET0 Model</span>
              <span class="feature-tag">Risk Scoring</span>
            </div>
          </div>

          <!-- Crop -->
          <div class="card card-clickable engine-card engine-crop" data-nav="crop">
            <div class="engine-icon">&#127806;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Crop Engine</h3>
            <p>Satellite-based vegetation health, NDVI analysis, growth stage tracking, and yield forecasting.</p>
            <div class="engine-features">
              <span class="feature-tag">Sentinel-2 NDVI</span>
              <span class="feature-tag">Growth Stage</span>
              <span class="feature-tag">Yield Forecast</span>
              <span class="feature-tag">Health Score</span>
            </div>
          </div>

          <!-- Fertilizer -->
          <div class="card card-clickable engine-card engine-fertilizer" data-nav="fertilizer">
            <div class="engine-icon">&#129716;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Fertilizer Engine</h3>
            <p>Precision NPK recommendations, product selection, application scheduling, and cost optimization.</p>
            <div class="engine-features">
              <span class="feature-tag">NPK Calculation</span>
              <span class="feature-tag">Product Guide</span>
              <span class="feature-tag">Schedule</span>
              <span class="feature-tag">Cost Analysis</span>
            </div>
          </div>

          <!-- Disease -->
          <div class="card card-clickable engine-card engine-disease" data-nav="disease">
            <div class="engine-icon">&#128030;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Disease Engine</h3>
            <p>Crop-specific disease risk assessment with 12 disease profiles, prevention plans, and treatment protocols.</p>
            <div class="engine-features">
              <span class="feature-tag">12 Diseases</span>
              <span class="feature-tag">Risk Scoring</span>
              <span class="feature-tag">Prevention Plan</span>
              <span class="feature-tag">4 Crops</span>
            </div>
          </div>

          <!-- Market -->
          <div class="card card-clickable engine-card engine-market" data-nav="market">
            <div class="engine-icon">&#128200;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Market Engine</h3>
            <p>Price tracking, seasonal patterns, profitability analysis, and sell/hold recommendations.</p>
            <div class="engine-features">
              <span class="feature-tag">Price Tracking</span>
              <span class="feature-tag">Seasonal Analysis</span>
              <span class="feature-tag">Profitability</span>
              <span class="feature-tag">Sell Advice</span>
            </div>
          </div>

          <!-- Farmer Profile -->
          <div class="card card-clickable engine-card engine-farmer" data-nav="profile">
            <div class="engine-icon">&#128100;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Farmer Engine</h3>
            <p>Farmer profile management, registration, query history tracking, and personalized recommendations.</p>
            <div class="engine-features">
              <span class="feature-tag">Profile CRUD</span>
              <span class="feature-tag">Query History</span>
              <span class="feature-tag">Personalization</span>
              <span class="feature-tag">Phone Lookup</span>
            </div>
          </div>

          <!-- Geo Intelligence -->
          <div class="card card-clickable engine-card engine-geo" data-nav="geo">
            <div class="engine-icon">&#127758;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Geo Intelligence</h3>
            <p>Satellite NDVI vegetation health, SoilGrids analysis, and climate zone classification for any location.</p>
            <div class="engine-features">
              <span class="feature-tag">NDVI</span>
              <span class="feature-tag">SoilGrids</span>
              <span class="feature-tag">Climate Zone</span>
              <span class="feature-tag">GPS / Village</span>
            </div>
          </div>

          <!-- Notification -->
          <div class="card card-clickable engine-card engine-notification" data-nav="notifications">
            <div class="engine-icon">&#128276;</div>
            <span class="engine-arrow">&#8594;</span>
            <h3>Notification Engine</h3>
            <p>Proactive agricultural alerts — weather warnings, disease risks, market opportunities, and growth reminders.</p>
            <div class="engine-features">
              <span class="feature-tag">Weather Alerts</span>
              <span class="feature-tag">Disease Risks</span>
              <span class="feature-tag">Market Tips</span>
              <span class="feature-tag">Stage Reminders</span>
            </div>
          </div>

        </div>

        <!-- Full Advisory Card -->
        <div class="mt-24">
          <div class="card card-clickable" data-nav="advisory" style="border:2px solid var(--ci-green-200);background:linear-gradient(135deg,var(--ci-green-50) 0%,#fff 100%)">
            <div class="card-body" style="padding:28px">
              <div class="flex items-center gap-16">
                <div style="width:56px;height:56px;background:var(--ci-green-600);border-radius:var(--radius-lg);display:flex;align-items:center;justify-content:center;font-size:1.8rem;color:#fff;flex-shrink:0">&#9881;</div>
                <div style="flex:1">
                  <h2>Full Advisory Report</h2>
                  <p class="text-muted" style="margin-top:4px">Run all 6 engines simultaneously and get a unified farm health score, cross-pollinated insights, and prioritized action items.</p>
                </div>
                <span style="font-size:1.5rem;color:var(--ci-green-600)">&#8594;</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Architecture Diagram -->
        <div class="mt-24">
          <div class="card">
            <div class="card-header"><h3>Platform Architecture</h3></div>
            <div class="card-body" style="font-family:monospace;font-size:0.8rem;line-height:1.8;white-space:pre;overflow-x:auto;color:var(--ci-gray-600)">
Farmer Dashboard
      |
      v
API Gateway (/api/v1)
      |
      +--- /soil/analyze -------- Soil Engine (ISRIC SoilGrids)
      +--- /weather/analyze ----- Weather Engine (NASA POWER + OpenWeather)
      +--- /crop/analyze -------- Crop Engine (Sentinel-2 NDVI)
      +--- /fertilizer/recommend  Fertilizer Engine (NPK + Products)
      +--- /disease/assess ------ Disease Engine (12 diseases x 4 crops)
      +--- /market/analyze ------ Market Engine (Price + Profitability)
      +--- /farmer/register ------ Farmer Engine (Profile + History)
      +--- /notifications/generate  Notification Engine (Alerts)
      +--- /geo/intelligence ---- Geo Intelligence (NDVI + Soil + Climate)
      |
      +--- /advisory/full ------- Advisory Aggregator
            |                       (runs all 6 engines)
            +-- farm_health_score   (cross-pollinated insights)
            +-- priority_actions    (ranked by urgency)
            +-- unified_summary     (executive report)
            </div>
          </div>
        </div>
      </div>`;

    /* Wire navigation on engine cards */
    container.querySelectorAll("[data-nav]").forEach((el) => {
      el.addEventListener("click", () => navigate(el.dataset.nav));
    });

    /* Ping health */
    api.health().then((d) => {
      $("#dash-health-val").textContent = "OK";
      $("#dash-health-sub").textContent = d.version ? `Version ${d.version}` : "All systems go";
    }).catch(() => {
      const v = $("#dash-health-val");
      v.textContent = "ERR";
      v.style.color = "var(--ci-red-500)";
      $("#dash-health-sub").textContent = "Backend unreachable";
    });
  },
});
