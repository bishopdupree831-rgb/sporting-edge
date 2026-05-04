(function () {
  const navItems = [
    ["dashboard", "DB", "Dashboard"],
    ["nba", "NBA", "NBA"],
    ["nfl", "NFL", "NFL"],
    ["mlb", "MLB", "MLB"],
    ["nhl", "NHL", "NHL"],
    ["mma", "MMA", "MMA"],
    ["live-simulator", "SIM", "Live Simulator"],
    ["markets", "MK", "Markets"],
    ["betslip", "SLIP", "Betslip"],
    ["ev-feed", "+EV", "+EV Feed"],
    ["arbitrage", "ARB", "Arbitrage"],
    ["line-movement", "LM", "Line Movement"],
    ["community", "CP", "Community Picks"],
    ["bet-tracker", "BT", "Bet Tracker"],
    ["bankroll", "BR", "Bankroll"],
    ["alerts", "AL", "Alerts"]
  ];

  const sportNames = {
    nba: "NBA Edge Board",
    nfl: "NFL Matchup Edge Board",
    mlb: "MLB Diamond Edge",
    nhl: "NHL Ice Edge",
    mma: "MMA Fight Edge"
  };

  const sportCopy = {
    nba: "Pace, usage, rotations, injury impact, 1Q/1H angles, player props, and same-game parlay structure.",
    nfl: "Weather, snap share, game script, red-zone role, QB profile, defensive matchup, and touchdown markets.",
    mlb: "Pitcher form, batting order, park factor, weather, first five innings, strikeout props, and HR watch.",
    nhl: "Goalie confirmation, shot pace, line combinations, power-play role, SOG props, and first-period markets.",
    mma: "Fighter style, cardio, method probabilities, round projection, takedown paths, and distance markets."
  };

  const providerMessage = "Live provider not connected.";

  function qs(selector) {
    return document.querySelector(selector);
  }

  function html(strings, ...values) {
    return strings.reduce((out, part, index) => out + part + (values[index] ?? ""), "");
  }

  function createNav() {
    const nav = qs(".nav");
    if (!nav) return;
    navItems.slice().reverse().forEach(([view, icon, label]) => {
      if (qs(`.nav-item[data-view="${view}"]`)) return;
      const button = document.createElement("button");
      button.className = "nav-item";
      button.type = "button";
      button.dataset.view = view;
      button.title = label;
      button.innerHTML = `<span>${icon}</span> ${label}`;
      nav.insertBefore(button, nav.firstChild);
    });
  }

  function chartBars(values) {
    return values.map((value, index) => `<span style="left:${index * 9 + 4}%;height:${value}%"></span>`).join("");
  }

  function lineChart() {
    return `
      <svg viewBox="0 0 420 150" role="img" aria-label="Line movement chart">
        <polyline points="8,110 70,96 132,104 194,70 256,78 318,42 410,55" fill="none" stroke="#00E676" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
        <polyline points="8,124 70,118 132,112 194,96 256,86 318,84 410,78" fill="none" stroke="#FFD166" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.75" />
      </svg>
    `;
  }

  function emptyCard(title, body) {
    return `
      <article class="dashboard-card span-4">
        <p class="markets-kicker">${title}</p>
        <div class="provider-empty">${body || providerMessage}</div>
      </article>
    `;
  }

  function dashboardSection() {
    return html`
      <section id="dashboard" class="view active premium-view">
        <div class="dashboard-grid">
          <div class="sport-hero">
            <p class="eyebrow">Sportsbook trading terminal</p>
            <h2>Find the Best Betting Edge Tonight</h2>
            <p class="hero-copy">A production-safe command center for live odds, simulations, market movement, betslips, bankroll, and community picks. No fake live betting data is displayed when provider keys are missing.</p>
          </div>
          ${emptyCard("Top Edge of the Day", providerMessage)}
          ${emptyCard("Hottest Prop", providerMessage)}
          ${emptyCard("Best Value Parlay", providerMessage)}
          ${emptyCard("Sharp Line Move", providerMessage)}
          <article class="dashboard-card span-8">
            <div class="terminal-row"><strong>Live Market Movers</strong><span class="provider-status offline">${providerMessage}</span></div>
            <div class="line-chart">${lineChart()}</div>
          </article>
          <article class="dashboard-card span-4">
            <strong>Data Status</strong>
            <div class="metric-row"><span>Odds</span><span class="warning-pill">Not connected</span></div>
            <div class="metric-row"><span>Stats</span><span class="warning-pill">Not connected</span></div>
            <div class="metric-row"><span>Injuries</span><span class="warning-pill">Not connected</span></div>
            <div class="metric-row"><span>News</span><span class="warning-pill">Not connected</span></div>
          </article>
          <article class="hot-card span-6">
            <p class="markets-kicker">Hot Spots / Cold Spots</p>
            <div class="heatmap"></div>
            <p class="muted">Connect provider keys to populate sport-specific hot and cold trend cells.</p>
          </article>
          <article class="dashboard-card span-6">
            <p class="markets-kicker">Community Trending Picks</p>
            <div class="provider-empty">Community feed loads when users post picks. No sportsbook credentials are required.</div>
          </article>
        </div>
      </section>
    `;
  }

  function sportSection(id) {
    const isOutdoor = id === "nfl" || id === "mlb";
    const sport = id.toUpperCase();
    return html`
      <section id="${id}" class="view premium-view">
        <div class="sport-grid">
          <div class="sport-hero">
            <p class="eyebrow">${sport} trading board</p>
            <h2>${sportNames[id]}</h2>
            <p class="hero-copy">${sportCopy[id]}</p>
            <div class="sport-toolbar">
              <span class="source-badge">${providerMessage}</span>
              ${isOutdoor ? `<span class="weather-badge">Weather awaiting provider</span>` : ""}
              <span class="injury-badge">Lineups awaiting provider</span>
            </div>
          </div>
          <article class="game-card span-6">
            <div class="team-row">
              <strong>Game Cards</strong>
              <span class="warning-pill">Empty live state</span>
            </div>
            <div class="provider-empty">Connect odds and stats providers to load matchups, start times, locations, team logos, and live markets.</div>
          </article>
          <article class="sport-panel span-6">
            <strong>${id === "mma" ? "Fighter Faceoff" : id === "mlb" ? "Probable Pitchers / Lineups" : id === "nhl" ? "Goalie Matchup" : "Starting Lineup Strip"}</strong>
            <div class="lineup-strip">
              ${["PG", "SG", "SF", "PF", "C"].map((slot) => `<span class="lineup-chip"><span class="player-avatar">${slot}</span>${providerMessage}</span>`).join("")}
            </div>
          </article>
          <article class="sport-panel span-4">
            <strong>Top Player Props</strong>
            <div class="bar-chart">${chartBars([30, 46, 62, 38, 72, 54, 44])}</div>
            <p class="muted">Live prop feed required.</p>
          </article>
          <article class="sport-panel span-4">
            <strong>${id === "nfl" ? "TD Scorer Board" : id === "mlb" ? "First 5 Innings Board" : id === "nhl" ? "1P Markets" : id === "mma" ? "Method Probabilities" : "1Q / 1H Filters"}</strong>
            <div class="provider-empty">${providerMessage}</div>
          </article>
          <article class="sport-panel span-4">
            <strong>Player Trend Card</strong>
            <div class="trend-dots">${[40, 62, 48, 70, 56, 38, 68].map((height, index) => `<span class="${index === 5 ? "cold" : ""}" style="height:${height}%"></span>`).join("")}</div>
          </article>
        </div>
      </section>
    `;
  }

  function simulatorSection() {
    return html`
      <section id="live-simulator" class="view premium-view">
        <div class="terminal-grid">
          <div class="sport-hero">
            <p class="eyebrow">Universal simulator</p>
            <h2>Run 10,000 Sims</h2>
            <p class="hero-copy">Use the existing simulator route with manual input, or provider-enriched context when API keys are connected.</p>
          </div>
          <article class="premium-panel span-4">
            <strong>Market Selector</strong>
            <div class="provider-empty">Use the Research tab simulator panel until providers are connected. Live provider not connected.</div>
          </article>
          <article class="premium-panel span-4">
            <strong>Result Sentence</strong>
            <div class="provider-empty">This result hit 0 out of 10,000 simulations, or 0.0%. Run a manual simulation to populate real input-based output.</div>
          </article>
          <article class="premium-panel span-4">
            <strong>Distribution</strong>
            <div class="distribution-chart">${chartBars([18, 32, 45, 70, 84, 65, 41, 22])}</div>
          </article>
        </div>
      </section>
    `;
  }

  function genericTerminalSection(id, title, subtitle) {
    return html`
      <section id="${id}" class="view premium-view">
        <div class="terminal-grid">
          <div class="sport-hero">
            <p class="eyebrow">Sharp terminal</p>
            <h2>${title}</h2>
            <p class="hero-copy">${subtitle}</p>
          </div>
          <article class="premium-panel span-6">
            <strong>Live Feed</strong>
            <div class="provider-empty">${providerMessage}</div>
          </article>
          <article class="premium-panel span-6">
            <strong>Analysis</strong>
            <div class="provider-empty">Connect provider keys to calculate odds, probability, EV, edge score, grade, verdict, and freshness.</div>
          </article>
        </div>
      </section>
    `;
  }

  function betslipSection() {
    return html`
      <section id="betslip" class="view premium-view">
        <div class="terminal-grid">
          <div class="sport-hero">
            <p class="eyebrow">Manual placement only</p>
            <h2>Betslip Builder</h2>
            <p class="hero-copy">Add legs from Markets, calculate combined odds and EV, then copy or export. Direct sportsbook connection not available. Copy betslip.</p>
          </div>
          <article class="premium-panel span-8">
            <div class="betslip-panel-root"></div>
          </article>
          <article class="premium-panel span-4">
            <strong>Safety</strong>
            <div class="provider-empty">Sporting Edge will not store sportsbook usernames or passwords and will not auto-place bets.</div>
          </article>
        </div>
      </section>
    `;
  }

  function insertSections() {
    const main = qs(".main");
    if (!main) return;
    const research = qs("#research");
    if (!qs("#dashboard")) research?.insertAdjacentHTML("beforebegin", dashboardSection());
    ["nba", "nfl", "mlb", "nhl", "mma"].forEach((sport) => {
      if (!qs(`#${sport}`)) research?.insertAdjacentHTML("beforebegin", sportSection(sport));
    });
    if (!qs("#live-simulator")) research?.insertAdjacentHTML("beforebegin", simulatorSection());
    if (!qs("#betslip")) qs("#markets")?.insertAdjacentHTML("afterend", betslipSection());
    if (!qs("#ev-feed")) qs("#sharp")?.insertAdjacentHTML("beforebegin", genericTerminalSection("ev-feed", "+EV Feed", "Compare model probability vs sportsbook implied probability, no-vig probability, fair odds, and expected value."));
    if (!qs("#arbitrage")) qs("#sharp")?.insertAdjacentHTML("beforebegin", genericTerminalSection("arbitrage", "Arbitrage", "Find active arbs, middles, guaranteed profit percentage, and stake splits when multi-book odds are connected."));
    if (!qs("#line-movement")) qs("#sharp")?.insertAdjacentHTML("beforebegin", genericTerminalSection("line-movement", "Line Movement", "Track open to current, steam moves, reverse line movement, public versus money, and sharp signals."));
    if (!qs("#bet-tracker")) qs("#community")?.insertAdjacentHTML("afterend", genericTerminalSection("bet-tracker", "Bet Tracker", "Track record, units, ROI, CLV, bankroll curve, sport splits, and market splits."));
    if (!qs("#bankroll")) qs("#bet-tracker")?.insertAdjacentHTML("afterend", genericTerminalSection("bankroll", "Bankroll", "Calculate flat unit, half Kelly, full Kelly, recommended units, and exposure warnings."));
    if (!qs("#alerts")) qs("#bankroll")?.insertAdjacentHTML("afterend", genericTerminalSection("alerts", "Alerts", "Monitor value bets, line moves, injuries, lineup confirmations, arbitrage, and bet grading."));
  }

  function addTerminalChrome() {
    const topbar = qs(".topbar");
    if (topbar && !qs(".terminal-bar")) {
      topbar.insertAdjacentHTML("afterbegin", `
        <div class="terminal-bar">
          <div class="terminal-logo"><span class="terminal-logo-mark">SE</span><span>Sporting Edge</span></div>
          <input class="global-search" type="search" placeholder="Search player, team, prop, matchup..." aria-label="Global search" />
          <span class="freshness-badge">Freshness: waiting</span>
          <span class="provider-status offline">${providerMessage}</span>
          <span class="profile-dot" title="Profile">B</span>
        </div>
      `);
    }
    if (!qs(".global-betslip-rail")) {
      document.body.insertAdjacentHTML("beforeend", `<aside class="global-betslip-rail"><div class="betslip-panel-root"></div></aside>`);
      document.body.classList.add("has-slip-rail");
    }
    if (!qs(".mobile-bottom-nav")) {
      document.body.insertAdjacentHTML("beforeend", `
        <nav class="mobile-bottom-nav" aria-label="Mobile navigation">
          ${[["dashboard", "Home"], ["markets", "Markets"], ["betslip", "Slip"], ["sharp", "Sharp"], ["community", "Picks"]].map(([view, label]) => `<button type="button" data-view="${view}">${label}</button>`).join("")}
        </nav>
      `);
    }
  }

  function setInitialView() {
    qs("#research")?.classList.remove("active");
    qs('.nav-item[data-view="research"]')?.classList.remove("active");
    qs("#dashboard")?.classList.add("active");
    qs('.nav-item[data-view="dashboard"]')?.classList.add("active");
    const title = qs("#view-title");
    if (title) title.textContent = "Find the Best Betting Edge Tonight";
  }

  function bindMobileNav() {
    document.addEventListener("click", (event) => {
      const button = event.target.closest(".mobile-bottom-nav button");
      if (!button) return;
      const nav = qs(`.nav-item[data-view="${button.dataset.view}"]`);
      nav?.click();
      document.querySelectorAll(".mobile-bottom-nav button").forEach((item) => {
        item.classList.toggle("active", item.dataset.view === button.dataset.view);
      });
    });
  }

  function init() {
    createNav();
    insertSections();
    addTerminalChrome();
    setInitialView();
    bindMobileNav();
    window.SEBetSlip?.render?.();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
