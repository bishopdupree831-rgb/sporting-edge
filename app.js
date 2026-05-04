const CUSTOM_PLAYERS_KEY = "edgelab.customPlayers";
const WATCHLIST_KEY = "edgelab.watchlist";
const AUTH_TOKEN_KEY = "edgelab.authToken";
const THEME_KEY = "edgelab.theme";

const basePlayers = [];

let customPlayers = loadCustomPlayers();
let players = [...basePlayers, ...customPlayers];

const insights = [];

const quickPrompts = [
  { tag: "Prop edge", text: "Research a player prop from the live market board." },
  { tag: "Alt line", text: "Find a safer alternate line for a selected prop." },
  { tag: "Parlay", text: "Build a 3 leg balanced card with low correlation risk." },
  { tag: "Sharp money", text: "Show me line movement and market edge signals." },
  { tag: "Injuries", text: "What late injury or roster news changes projections?" },
  { tag: "Matchup", text: "Compare two selected players for safest prop." },
  { tag: "MLB", text: "What MLB market has the strongest live edge?" },
  { tag: "MMA", text: "Which MMA prop has the best live model score?" }
];

const titles = {
  dashboard: "Find the Best Betting Edge Tonight",
  nba: "NBA Edge Board",
  nfl: "NFL Matchup Edge Board",
  mlb: "MLB Diamond Edge",
  nhl: "NHL Ice Edge",
  mma: "MMA Fight Edge",
  "live-simulator": "Live Simulator",
  research: "Ask a sports research question",
  insights: "Curated daily edges",
  players: "Player profiles",
  profile: "Your profile and tracked research",
  parlay: "Parlay builder",
  markets: "Sportsbook markets",
  betslip: "Betslip Builder",
  "ev-feed": "+EV Feed",
  arbitrage: "Arbitrage",
  "line-movement": "Line Movement",
  sharp: "Sharp terminal",
  community: "Community picks",
  "bet-tracker": "Bet Tracker",
  bankroll: "Bankroll",
  alerts: "Alerts",
  rankings: "Prop-centric rankings",
  engine: "Live betting engine",
  analytics: "Analytics dashboard"
};

let activeMode = "quick";
let engineSnapshot = null;
let manualParlayLegs = [];
let livePlayerResults = [];
let liveInsights = [];
let liveRankings = [];
let analyticsSnapshot = null;
let watchlist = loadJson(WATCHLIST_KEY, []);
let marketSources = null;
let dataFreshness = null;
let authToken = localStorage.getItem(AUTH_TOKEN_KEY) || "";
let currentUser = null;
let savedCards = [];
let serverAlerts = [];
let serverWatchlist = [];
let responsibleUse = null;
let lastParlayLegs = [];
let activeTheme = localStorage.getItem(THEME_KEY) || "day";
let catalog = {
  teams: {},
  markets: {},
  sample_players: []
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function loadJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}

function loadCustomPlayers() {
  try {
    return JSON.parse(localStorage.getItem(CUSTOM_PLAYERS_KEY)) || [];
  } catch {
    return [];
  }
}

function saveCustomPlayers() {
  localStorage.setItem(CUSTOM_PLAYERS_KEY, JSON.stringify(customPlayers));
  players = [...basePlayers, ...customPlayers];
}

function activeSport() {
  return $("#sport-filter").value;
}

function compactTeamName(team) {
  if (!team) return "";
  const map = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
    "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "New York Knicks": "NYK", "Philadelphia 76ers": "PHI",
    "Toronto Raptors": "TOR", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Detroit Pistons": "DET",
    "Indiana Pacers": "IND", "Milwaukee Bucks": "MIL", "Atlanta Hawks": "ATL", "Charlotte Hornets": "CHA",
    "Miami Heat": "MIA", "Orlando Magic": "ORL", "Washington Wizards": "WAS", "Dallas Mavericks": "DAL",
    "Houston Rockets": "HOU", "Memphis Grizzlies": "MEM", "New Orleans Pelicans": "NO", "San Antonio Spurs": "SA",
    "Denver Nuggets": "DEN", "Minnesota Timberwolves": "MIN", "Oklahoma City Thunder": "OKC", "Portland Trail Blazers": "POR",
    "Utah Jazz": "UTA", "Golden State Warriors": "GSW", "LA Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "Phoenix Suns": "PHX", "Sacramento Kings": "SAC"
  };
  return map[team] || team;
}

function initials(value) {
  return (value || "EL").replace(/[^a-z0-9 ]/gi, " ").split(/\s+/).filter(Boolean).slice(0, 3).map((part) => part[0]).join("").toUpperCase() || "EL";
}

function teamLogo(team, sport = "") {
  const label = compactTeamName(team);
  return `<span class="team-logo ${sport.toLowerCase()}">${initials(label || team)}</span>`;
}

function trendFor(values = [], line = 0) {
  if (!values.length) return { label: "trend pending", value: 50, tone: "watch" };
  const first = avg(values.slice(0, Math.ceil(values.length / 2)));
  const second = avg(values.slice(Math.floor(values.length / 2)));
  const hit = values.filter((item) => item > line).length / values.length;
  if (second > first * 1.08 && hit >= 0.55) return { label: "hot streak", value: Math.round(hit * 100), tone: "play" };
  if (second < first * 0.92 && hit < 0.5) return { label: "cold streak", value: Math.round(hit * 100), tone: "fade" };
  return { label: "steady form", value: Math.round(hit * 100), tone: "watch" };
}

function sparkline(values = [], line = 0) {
  const safe = values.length ? values : [line || 1, line || 1];
  const max = Math.max(...safe, line || 1);
  const min = Math.min(...safe, line || 0);
  const span = max - min || 1;
  const points = safe.map((value, index) => {
    const x = safe.length === 1 ? 50 : (index / (safe.length - 1)) * 100;
    const y = 86 - ((value - min) / span) * 72;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const lineY = 86 - (((line || min) - min) / span) * 72;
  return `<svg class="sparkline" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><line x1="0" y1="${lineY}" x2="100" y2="${lineY}" class="sparkline-line"></line><polyline points="${points}"></polyline></svg>`;
}

function makeRecent(line, confidence) {
  const center = line * (0.9 + confidence / 180);
  return Array.from({ length: 10 }, (_, index) => {
    const wave = Math.sin(index * 1.7) * line * 0.14;
    const drift = (index % 3 - 1) * line * 0.07;
    return Number(Math.max(0, center + wave + drift).toFixed(1));
  });
}

function estimateConfidence(line, sport) {
  const sportBase = { NFL: 70, MLB: 66, NBA: 69, NHL: 67, MMA: 63 }[sport] || 66;
  const lineDrag = line > 50 ? 4 : line > 10 ? 2 : 0;
  return Math.max(58, Math.min(82, sportBase - lineDrag));
}

function hitRate(player) {
  const hits = player.recent.filter((value) => value > player.line).length;
  return Math.round((hits / player.recent.length) * 100);
}

function avg(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function filteredPlayers() {
  const sport = $("#sport-filter").value;
  const team = $("#team-filter").value;
  return players.filter((player) => {
    const matchesSport = sport === "All" || player.sport === sport;
    const matchesTeam = team === "All" || player.team === team || player.opponent === team;
    return matchesSport && matchesTeam;
  });
}

function renderTeamFilter() {
  const current = $("#team-filter").value;
  const sport = $("#sport-filter").value;
  const catalogTeams = sport === "All"
    ? Object.values(catalog.teams || {}).flat()
    : (catalog.teams?.[sport] || []);
  const playerTeams = players
    .filter((player) => sport === "All" || player.sport === sport)
    .flatMap((player) => [player.team, player.opponent])
    .filter(Boolean);
  const liveTeams = liveRankings
    .filter((row) => sport === "All" || row.sport === sport)
    .flatMap((row) => [row.team, row.opponent, row.matchup])
    .filter(Boolean);
  const teams = [...new Set([...catalogTeams, ...playerTeams, ...liveTeams].map(compactTeamName).filter(Boolean))].sort();

  $("#team-filter").innerHTML = `<option value="All">All teams</option>${teams.map((team) => `<option value="${team}">${team}</option>`).join("")}`;
  $("#team-filter").value = teams.includes(current) ? current : "All";
}

async function loadCatalog() {
  try {
    const response = await fetch("/api/catalog", { cache: "no-store" });
    if (!response.ok) throw new Error("Catalog unavailable");
    catalog = await response.json();
  } catch {
    catalog = {
      teams: {
        NFL: ["Kansas City Chiefs", "Buffalo Bills", "Dallas Cowboys", "Philadelphia Eagles"],
        MLB: ["New York Yankees", "Los Angeles Dodgers", "Atlanta Braves", "Houston Astros"],
        NBA: ["Los Angeles Lakers", "Boston Celtics", "New York Knicks", "Dallas Mavericks"],
        NHL: ["Boston Bruins", "Colorado Avalanche", "Edmonton Oilers", "New York Rangers", "Toronto Maple Leafs"],
        MMA: ["UFC", "Bellator", "PFL", "ONE Championship"]
      },
      markets: {
        NFL: ["Passing Yards", "Rushing Yards", "Receiving Yards", "Receptions", "Anytime Touchdown"],
        MLB: ["Hits", "Total Bases", "Home Runs", "Pitcher Strikeouts"],
        NBA: ["Points", "Rebounds", "Assists", "Threes"],
        NHL: ["Shots On Goal", "Points", "Goals", "Assists", "Saves", "Puck Line"],
        MMA: ["Moneyline", "Significant Strikes", "Takedowns", "Fight Goes Distance"]
      },
      sample_players: basePlayers
    };
  }
  renderPredictionSuggestions();
  renderTeamFilter();
}

function renderPredictionSuggestions() {
  const sport = $("#predict-sport").value;
  const teams = catalog.teams?.[sport] || [];
  const markets = catalog.markets?.[sport] || [];
  const names = [...new Set([
    ...basePlayers.filter((player) => player.sport === sport).map((player) => player.name),
    ...customPlayers.filter((player) => player.sport === sport).map((player) => player.name),
    ...livePlayerResults.filter((player) => player.sport === sport).map((player) => player.name)
  ])].sort();

  $("#team-suggestions").innerHTML = teams.map((team) => `<option value="${team}"></option>`).join("");
  $("#market-suggestions").innerHTML = markets.map((market) => `<option value="${market}"></option>`).join("");
  $("#player-suggestions").innerHTML = names.map((name) => `<option value="${name}"></option>`).join("");
}

function localPrediction(payload) {
  const implied = oddsToProbability(payload.odds || -110);
  const edge = 0 - implied;
  const recommendation = "Manual review";

  return {
    ...payload,
    subject: payload.player || payload.team || "Unknown",
    projection: Number(payload.line || 0),
    hit_rate: 0,
    implied_probability: Number(implied.toFixed(3)),
    edge: Number(edge.toFixed(3)),
    confidence: 0,
    recommendation,
    source: "manual-mode",
    sample_size: 0,
    validation: ["Live provider not connected. Using manual mode."],
    explanation: "No live provider result was available for this browser session. Enter manual context or connect provider keys before treating this as a live prediction."
  };
}

function oddsToProbability(odds) {
  return odds > 0 ? 100 / (odds + 100) : Math.abs(odds) / (Math.abs(odds) + 100);
}

function formatEventTime(value) {
  if (!value) return "time pending";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function applyTheme(theme) {
  activeTheme = theme === "night" ? "night" : "day";
  document.documentElement.dataset.theme = activeTheme;
  localStorage.setItem(THEME_KEY, activeTheme);
  const button = $("#theme-toggle");
  if (button) {
    button.textContent = activeTheme === "night" ? "Day" : "Night";
    button.title = activeTheme === "night" ? "Switch to day mode" : "Switch to night mode";
  }
}

function toggleTheme() {
  applyTheme(activeTheme === "night" ? "day" : "night");
}

async function postJson(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) throw new Error(data.error || "Request failed");
  return data;
}

async function apiPost(path, body = {}) {
  return postJson(path, body);
}

function renderSimulatorResult(result) {
  const target = $("#simulator-result");
  if (!target) return;
  if (!result) {
    target.innerHTML = "";
    return;
  }
  target.innerHTML = `
    <div class="result-card">
      <strong>${result.player || "Selected prop"} ${result.market || ""}</strong>
      <span>${result.sport || ""} line ${result.line ?? ""} odds ${result.odds ?? ""}</span>
      <div class="metric-row"><span>Projection</span><strong>${result.projection ?? "-"}</strong></div>
      <div class="metric-row"><span>True probability</span><strong>${Math.round((result.true_probability || 0) * 100)}%</strong></div>
      <div class="metric-row"><span>Edge</span><strong>${Math.round((result.edge || 0) * 1000) / 10}%</strong></div>
      <div class="metric-row"><span>Confidence</span><strong>${Math.round((result.confidence || 0) * 100)}%</strong></div>
      <p>${result.recommendation || result.confidence_tier || "Research output ready."}</p>
    </div>
  `;
}

async function runFullPropSimulator() {
  const enteredName = $("#sim-player")?.value || "Selected player";
  const existing = players.find((item) => item.name.toLowerCase() === enteredName.toLowerCase());
  const body = {
    player: enteredName,
    sport: $("#sim-sport")?.value || activeSport || "NBA",
    market: $("#sim-market")?.value || "Points",
    line: Number($("#sim-line")?.value || 0),
    odds: Number($("#sim-odds")?.value || -110),
    recent: existing?.recent || null
  };
  try {
    const result = await apiPost("/api/projection", body);
    renderSimulatorResult(result);
  } catch (error) {
    $("#simulator-result").innerHTML = `<div class="result-card"><strong>Simulator error</strong><p>${error.message}</p></div>`;
  }
}

window.runFullPropSimulator = runFullPropSimulator;

function renderLiveSimulation(result) {
  const target = $("#live-sim-output");
  if (!target) return;
  const provider = result.provider_message ? `<p class="warning">${result.provider_message}</p>` : "";
  target.innerHTML = `
    <article class="result-card live-sim-result">
      <div class="card-top">
        <div>
          <strong>${result.result_sentence}</strong>
          <span>${result.sport} - ${result.market_type} - ${result.sportsbook || "sportsbook not entered"}</span>
        </div>
        <span class="pill">${result.confidence_grade} grade</span>
      </div>
      ${provider}
      <div class="sim-result-grid">
        <div><span>Hit</span><strong>${Math.round(result.hit_percentage * 1000) / 10}%</strong></div>
        <div><span>Miss</span><strong>${Math.round(result.miss_percentage * 1000) / 10}%</strong></div>
        <div><span>Avg result</span><strong>${result.average_result}</strong></div>
        <div><span>Median</span><strong>${result.median_result}</strong></div>
        <div><span>25th / 75th</span><strong>${result.percentile_25} / ${result.percentile_75}</strong></div>
        <div><span>Implied</span><strong>${Math.round(result.implied_probability * 1000) / 10}%</strong></div>
        <div><span>Model edge</span><strong>${Math.round(result.model_edge * 1000) / 10}%</strong></div>
        <div><span>EV</span><strong>${result.expected_value}</strong></div>
      </div>
      <div class="trend-card">
        <strong>${result.betting_verdict}</strong>
        <p>${result.trend_explanation}</p>
        <small>Freshness: ${new Date(result.data_freshness).toLocaleString()} - Sources: ${result.provider_sources.map((source) => source.name).join(", ")}</small>
      </div>
    </article>
  `;
}

async function runLiveSimulator() {
  const sport = $("#live-sim-sport")?.value || "NBA";
  const marketType = $("#live-sim-market-type")?.value || "player_prop";
  const subject = $("#live-sim-subject")?.value.trim() || "";
  const body = {
    sport,
    matchup: $("#live-sim-matchup")?.value.trim() || null,
    market_type: marketType,
    player_name: marketType.includes("player") || marketType.includes("fighter") || marketType.startsWith("first") ? subject : null,
    team_name: marketType.includes("team") || ["moneyline", "spread", "total"].includes(marketType) ? subject : null,
    stat_type: $("#live-sim-stat")?.value.trim() || marketType,
    line: Number($("#live-sim-line")?.value || 0),
    odds: Number($("#live-sim-odds")?.value || -110),
    sportsbook: $("#live-sim-book")?.value.trim() || null,
    simulations: 10000,
    live_context: {
      season_average: Number($("#live-sim-season")?.value || $("#live-sim-line")?.value || 0),
      last_5_average: Number($("#live-sim-l5")?.value || $("#live-sim-line")?.value || 0),
      last_10_average: Number($("#live-sim-l10")?.value || $("#live-sim-line")?.value || 0),
      opponent_average_allowed: Number($("#live-sim-opp")?.value || $("#live-sim-line")?.value || 0),
      usage_rate: 0,
      injury_adjustment: 0,
      lineup_adjustment: 0,
      pace_adjustment: 0,
      weather_adjustment: 0,
      pitcher_adjustment: 0,
      goalie_adjustment: 0,
      fight_style_adjustment: 0,
      odds_movement: 0,
      public_betting_percentage: 50,
      sharp_money_signal: ""
    }
  };
  const output = $("#live-sim-output");
  if (output) output.innerHTML = '<article class="result-card"><strong>Running 10,000 simulations...</strong></article>';
  try {
    const result = await apiPost("/api/live-simulate", body);
    renderLiveSimulation(result);
  } catch (error) {
    if (output) output.innerHTML = `<article class="result-card"><strong>Simulation error</strong><p>${error.message}</p></article>`;
  }
}

window.runLiveSimulator = runLiveSimulator;

async function loadCurrentUser() {
  if (!authToken) {
    currentUser = null;
    return;
  }
  try {
    const data = await fetch(`/api/me?token=${encodeURIComponent(authToken)}`, { cache: "no-store" }).then((response) => response.json());
    currentUser = data.ok ? data.user : null;
    if (!currentUser) {
      authToken = "";
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch {
    currentUser = null;
  }
}

async function submitPrediction(event) {
  event.preventDefault();
  const payload = {
    sport: $("#predict-sport").value,
    player: $("#predict-player").value.trim(),
    team: $("#predict-team").value.trim(),
    market: $("#predict-market").value.trim(),
    line: Number($("#predict-line").value),
    odds: Number($("#predict-odds").value || -110)
  };

  let result;
  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error("Prediction API unavailable");
    result = await response.json();
  } catch {
    result = localPrediction(payload);
  }

  renderPrediction(result);
}

async function getPrediction(payload) {
  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error("Prediction API unavailable");
    return await response.json();
  } catch {
    return localPrediction(payload);
  }
}

function renderPrediction(result) {
  const statusClass = result.recommendation === "Play" ? "play" : result.recommendation === "Fade" ? "fade" : "";
  const resultSourceLabel = {
    "sportsdataio-stats": "Live stats model",
    "model-fallback": "Model fallback",
    "manual-model": "Manual model",
    "browser-fallback": "Browser fallback",
    "manual-mode": "Manual mode"
  }[result.source] || result.source || "Model";
  const validation = Array.isArray(result.validation) && result.validation.length
    ? `<div class="prediction-warnings">${result.validation.map((item) => `<div>${item}</div>`).join("")}</div>`
    : "";
  const factors = Array.isArray(result.factors) ? result.factors : [];
  const marketIntel = result.market_intelligence || {};
  const power = result.power_rating || {};
  const risk = result.risk || {};
  const environment = result.environment || {};
  const matchup = result.matchup_intelligence || {};
  const proLayers = result.pro_layers || {};
  const edgeSystem = proLayers.edge_system || {};
  const simulation = proLayers.simulation || {};
  const lineMovement = proLayers.line_movement || {};
  const altLines = Array.isArray(result.alternate_lines) ? result.alternate_lines : [];
  const bestLines = Array.isArray(result.best_lines) && result.best_lines.length
    ? `<div class="engine-list">${result.best_lines.slice(0, 3).map((event) => `
        <div class="engine-item">
          <strong>${event.away_team || ""} ${event.home_team ? `at ${event.home_team}` : ""}</strong>
          <span class="muted">${formatEventTime(event.commence_time)}${event.venue ? ` - ${event.venue}` : ""}</span>
          ${(event.best_lines || []).slice(0, 3).map((line) => `<span>${line.outcome} ${line.market}: ${line.best_price ?? ""} ${line.best_price_book ? `at ${line.best_price_book}` : ""}${line.best_line !== null && line.best_line !== undefined ? ` · line ${line.best_line}` : ""}</span>`).join("")}
        </div>
      `).join("")}</div>`
    : "";
  $("#prediction-output").classList.add("active");
  $("#prediction-output").innerHTML = `
    <div class="prediction-result">
      <div class="prediction-head">
        <div>
          <h2>${result.subject} ${result.market}</h2>
          <p class="muted">${result.sport}${result.team ? ` · ${result.team}` : ""} · line ${result.line} · odds ${result.odds}</p>
        </div>
        <span class="recommendation ${statusClass}">${result.recommendation}</span>
      </div>
      <div class="metric-row">
        <span class="pill">${resultSourceLabel}</span>
        <span class="pill">${result.sample_size || 0} stat samples</span>
        <span class="pill">${risk.tier || "Watch"}${risk.label ? ` - ${risk.label}` : ""}</span>
        <span class="pill">power ${power.rating ?? "n/a"}</span>
      </div>
      <div class="confidence">
        <strong>${Math.round(result.confidence * 100)}% confidence</strong>
        <div class="bar"><span style="width:${Math.round(result.confidence * 100)}%"></span></div>
      </div>
      <p>${result.explanation}</p>
      <div class="market-grid">
        <div class="market-box"><strong>Projected stat</strong><span>${result.projection}</span></div>
        <div class="market-box"><strong>Fair odds</strong><span>${marketIntel.fair_odds ?? "n/a"}</span></div>
        <div class="market-box"><strong>True probability</strong><span>${marketIntel.true_probability ? `${Math.round(marketIntel.true_probability * 100)}%` : "n/a"}</span></div>
        <div class="market-box"><strong>Sharp signal</strong><span>${marketIntel.sharp_signal || "Waiting for market data"}</span></div>
        <div class="market-box"><strong>EV</strong><span>${marketIntel.expected_value ?? edgeSystem.ev ?? "n/a"}</span></div>
        <div class="market-box"><strong>Simulation</strong><span>${simulation.runs || 0} runs</span></div>
        <div class="market-box"><strong>Environment</strong><span>${[environment.roof, environment.surface, environment.weather_risk].filter(Boolean).join(" / ") || "n/a"}</span></div>
        <div class="market-box"><strong>Venue</strong><span>${environment.venue || "n/a"}</span></div>
        <div class="market-box"><strong>Matchup</strong><span>${matchup.lean || "neutral"} (${matchup.score ?? "n/a"})</span></div>
        <div class="market-box"><strong>CLV watch</strong><span>${marketIntel.clv_watch || "Track close vs entry"}</span></div>
        <div class="market-box"><strong>Line movement</strong><span>${lineMovement.steam_move || "pending"} / ${lineMovement.reverse_line_movement || "pending"}</span></div>
      </div>
      ${proLayers.model_stack ? `<div class="factor-list"><div><strong>Model stack</strong><span>${proLayers.model_stack.join(" -> ")}</span></div><div><strong>Sport-specific edges</strong><span>${(proLayers.sport_specific || []).join(", ")}</span></div></div>` : ""}
      ${(environment.notes || []).length ? `<div class="factor-list">${environment.notes.map((note) => `<div><strong>Playing environment</strong><span>${note}</span></div>`).join("")}</div>` : ""}
      ${matchup.score ? `<div class="factor-list"><div><strong>Opponent and coaching layer</strong><span>${matchup.history_note} ${matchup.coaching_note} ${matchup.opponent_note}</span></div></div>` : ""}
      ${altLines.length ? `<div class="alt-lines"><h3>Alternate lines</h3>${altLines.map((alt) => `<div><strong>${alt.line}</strong><span>${Math.round(alt.hit_rate * 100)}% hit</span><span>fair ${alt.fair_odds}</span><span>${alt.risk?.tier || "Watch"}</span></div>`).join("")}</div>` : ""}
      ${factors.length ? `<div class="factor-list">${factors.map((factor) => `<div><strong>${factor.name}</strong><span>${factor.note}</span></div>`).join("")}</div>` : ""}
      ${validation}
      ${bestLines}
      <div class="metric-row">
        <span class="pill">projection ${result.projection}</span>
        <span class="pill">hit ${Math.round(result.hit_rate * 100)}%</span>
        <span class="pill">implied ${Math.round(result.implied_probability * 100)}%</span>
        <span class="pill">edge ${result.edge}</span>
        <button class="mini-btn" type="button" id="watch-current">Watch this prop</button>
        <button class="mini-btn" type="button" id="alert-current">Create alert</button>
      </div>
    </div>
  `;
  $("#watch-current")?.addEventListener("click", () => addWatch(result));
  $("#alert-current")?.addEventListener("click", () => createAlertFromResult(result));
}

function addWatch(result) {
  const item = {
    id: `${result.sport}-${result.subject}-${result.market}`.toLowerCase(),
    subject: result.subject,
    sport: result.sport,
    market: result.market,
    line: result.line,
    odds: result.odds,
    confidence: result.confidence,
    createdAt: new Date().toISOString()
  };
  watchlist = [item, ...watchlist.filter((watch) => watch.id !== item.id)].slice(0, 20);
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(watchlist));
  fetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: authToken || null, ...item, threshold: Number(result.confidence || 0) })
  }).catch(() => {});
  renderAnalytics();
}

async function createAlertFromResult(result) {
  try {
    await postJson("/api/alerts", {
      token: authToken || null,
      subject: result.subject,
      sport: result.sport,
      market: result.market,
      threshold: Math.max(0.55, Number(result.confidence || 0.6))
    });
    await loadAnalytics();
  } catch (error) {
    alert(error.message || "Could not create that alert.");
  }
}

async function submitStatsAsk(event) {
  event.preventDefault();
  const question = $("#ask-input").value.trim();
  if (!question) return;
  const output = $("#ask-output");
  output.classList.add("active");
  output.innerHTML = `<p class="muted">Checking live stats, odds, and context feeds...</p>`;
  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, sport: $("#sport-filter").value })
    });
    if (!response.ok) throw new Error("stats ask failed");
    const data = await response.json();
    output.innerHTML = `
      <div class="prediction-result">
        <div class="prediction-head">
          <div>
            <h2>${data.subject || "Stats answer"}</h2>
            <p class="muted">${data.sport || "All sports"} - ${data.source || "engine"}</p>
          </div>
          <span class="recommendation">${data.recommendation || "Research"}</span>
        </div>
        <p>${data.answer || data.explanation || "No answer was returned."}</p>
        <div class="metric-row">
          ${data.confidence ? `<span class="pill">${Math.round(data.confidence * 100)}% confidence</span>` : ""}
          ${data.projection ? `<span class="pill">projection ${data.projection}</span>` : ""}
          ${data.sample_size ? `<span class="pill">${data.sample_size} stat samples</span>` : ""}
        </div>
      </div>
    `;
  } catch {
    output.innerHTML = `<div class="prediction-warnings"><div>The stats question engine is unavailable right now. Try the Prediction lab while the feed recovers.</div></div>`;
  }
}

function renderChatIntro() {
  addMessage(
    "bot",
    "Ask me about a prop, player, matchup, injury note, line movement, alternate line, or parlay. I will use live providers first and label fallback logic."
  );
}

function addMessage(role, html) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.innerHTML = html;
  $("#chat-log").appendChild(node);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
}

function analyzeQuestion(question) {
  const lower = question.toLowerCase();
  const requested = players.find((player) => lower.includes(player.name.toLowerCase().split(" ")[0]) || lower.includes(player.name.toLowerCase().split(" ").at(-1)));

  if (lower.includes("parlay")) {
    const card = buildParlay(3, "balanced", $("#sport-filter").value);
    return formatParlayAnswer(card);
  }

  if (lower.includes("compare")) {
    const sorted = [...filteredPlayers()].sort((a, b) => b.confidence - a.confidence).slice(0, 2);
    return `<strong>Comparison</strong>${sorted.map((player) => `${player.name}: ${player.confidence}% confidence, ${hitRate(player)}% recent hit rate, ${player.matchup}/10 matchup`).join("<br>")}<div class="metric-row"><span class="pill">Best floor: ${sorted[0].name}</span><span class="pill">${activeMode === "full" ? "Full mode includes volatility notes" : "Quick mode"}</span></div>`;
  }

  if (lower.includes("mlb") || lower.includes("nba") || lower.includes("nfl") || lower.includes("nhl") || lower.includes("mma") || lower.includes("insight")) {
    const sport = lower.includes("mlb") ? "MLB" : lower.includes("nfl") ? "NFL" : lower.includes("nba") ? "NBA" : lower.includes("nhl") ? "NHL" : lower.includes("mma") ? "MMA" : $("#sport-filter").value;
    const item = insights.filter((insight) => sport === "All" || insight.sport === sport).sort((a, b) => b.score - a.score)[0];
    return `<strong>${item.title}</strong>${item.body}<div class="metric-row"><span class="pill">${item.sport}</span><span class="pill">${item.type}</span><span class="pill">${item.score}/100 edge score</span></div>`;
  }

  const player = requested || filteredPlayers().sort((a, b) => b.confidence - a.confidence)[0];
  const lean = hitRate(player) >= 60 && player.confidence >= 70 ? "Positive lean" : "Researchable, but not automatic";
  const detail = activeMode === "full"
    ? ` Average recent result is ${avg(player.recent).toFixed(1)} against a ${player.line} line. The main risk is variance around role, game script, or late injury news.`
    : "";

  return `<strong>${lean}: ${player.name} ${player.market} ${player.line}</strong>${player.note}${detail}<div class="metric-row"><span class="pill">${hitRate(player)}% last-ten hit rate</span><span class="pill">${player.usage}% usage</span><span class="pill">${player.matchup}/10 matchup</span><span class="pill">${player.confidence}% confidence</span></div>`;
}

function renderQuickPrompts() {
  const sport = activeSport();
  const top = liveRankings.find((row) => sport === "All" || row.sport === sport);
  const dynamicPrompts = top ? [
    { tag: "Live board", text: `Research ${top.name || top.matchup} ${top.market || "market"} at ${top.odds || "current odds"}` },
    { tag: "Best line", text: `Where is the best ${top.sport} line for ${top.matchup || top.name}?` },
    { tag: "Parlay", text: `Build a 3 leg ${top.sport} card from the live board.` }
  ] : [];
  $("#quick-prompts").innerHTML = [...dynamicPrompts, ...quickPrompts].slice(0, 7)
    .map((prompt) => `
      <button class="prompt" type="button" data-prompt="${prompt.text}">
        <span>${prompt.tag}</span>
        <strong>${prompt.text}</strong>
      </button>
    `)
    .join("");

  $$(".prompt").forEach((button) => {
    button.addEventListener("click", () => {
      $("#chat-input").value = button.dataset.prompt;
      $("#chat-form").requestSubmit();
    });
  });
}

function renderInsights() {
  const search = $("#insight-search").value.toLowerCase();
  const sport = $("#sport-filter").value;
  const edge = $("#edge-filter").value;
  const customInsights = customPlayers.map((player) => ({
    type: "Market",
    sport: player.sport,
    title: `${player.name} added to tracked props`,
    body: `${player.market} ${player.line} is now available in chat, rankings, profiles, and parlay generation.`,
    player: player.name,
    score: player.confidence
  }));
  const allInsights = [...liveInsights, ...insights, ...customInsights];
  const rows = allInsights.filter((insight) => {
    const matchesSport = sport === "All" || insight.sport === sport;
    const matchesEdge = edge === "All" || insight.type === edge;
    const matchesSearch = `${insight.title} ${insight.body} ${insight.player}`.toLowerCase().includes(search);
    return matchesSport && matchesEdge && matchesSearch;
  });

  $("#insight-list").innerHTML = rows.map((insight) => `
    <article class="insight-card">
      <div class="card-top">
        <span class="tag ${insight.type}">${insight.type}</span>
        <span class="score">${insight.score}</span>
      </div>
      <h3>${insight.title}</h3>
      <p>${insight.body}</p>
      <div class="metric-row">
        <span class="pill">${insight.sport}</span>
        <span class="pill">${insight.player}</span>
        ${insight.source ? `<span class="pill">${insight.source}</span>` : ""}
      </div>
    </article>
  `).join("") || `<p class="muted">No insights match those filters.</p>`;
}

async function loadLiveInsights() {
  const sport = $("#sport-filter").value;
  const query = $("#insight-search").value.trim();
  try {
    const response = await fetch(`/api/insights?sport=${encodeURIComponent(sport)}&q=${encodeURIComponent(query)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("insights unavailable");
    const data = await response.json();
    liveInsights = data.insights || [];
  } catch {
    liveInsights = [];
  }
  renderInsights();
}

function renderPlayers() {
  const localCards = filteredPlayers();
  const liveCards = livePlayerResults.map((player) => ({
    name: player.name,
    sport: $("#custom-sport").value,
    team: player.team || "FA",
    opponent: "Live profile",
    market: player.position || "Profile",
    line: 0,
    recent: [0],
    usage: 0,
    matchup: 0,
    confidence: player.status ? 72 : 66,
    note: `${player.position || "Player"} · ${player.status || "No current status note"}`,
    hotspots: [[42, 48], [58, 52], [50, 66]],
    source: player.source || "sportsdataio",
    live: true
  }));
  const rankingCards = liveRankings.slice(0, 18).map((row) => {
    const line = Number(row.line ?? 0);
    const confidence = Math.round(row.confidence || 62);
    return {
      name: row.name || row.subject || row.player || row.matchup,
      sport: row.sport,
      team: compactTeamName(row.team),
      opponent: compactTeamName(row.opponent),
      market: row.market || "Market",
      line,
      recent: makeRecent(line || 1, confidence),
      usage: Math.round(confidence * 0.35),
      matchup: Math.max(5, Math.min(9, Math.round(confidence / 10))),
      confidence,
      note: `${row.book || "Best line"} ${row.odds || ""} ${row.commence_time ? `- ${formatEventTime(row.commence_time)}` : ""}`,
      hotspots: [[42, 48], [58, 52], [50, 66]],
      source: row.source || "live-ranking",
      live: true
    };
  });
  const seen = new Set();
  const cards = [...liveCards, ...rankingCards, ...localCards].filter((player) => {
    const key = `${player.sport}-${player.name}-${player.market}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  $("#player-grid").innerHTML = cards.length ? cards.map((player) => `
    <article class="player-card">
      <div class="player-head">
        ${teamLogo(player.team || player.name, player.sport)}
        <div>
          <h3>${player.name}</h3>
          <p class="muted">${player.team || "Team"} vs ${player.opponent || "Opponent"} - ${player.sport}</p>
        </div>
      </div>
      ${sparkline(player.recent, player.line)}
      <div class="bars">
        <span>Confidence ${player.confidence}%</span>
        <div class="bar"><span style="width:${player.confidence}%"></span></div>
        <span>${trendFor(player.recent, player.line).label} - ${player.live ? "provider profile" : `recent hit rate ${hitRate(player)}%`}</span>
        <div class="bar"><span style="width:${player.live ? Math.max(55, player.confidence - 5) : hitRate(player)}%"></span></div>
      </div>
      <div class="metric-row">
        <span class="pill">${player.market} ${player.line || ""}</span>
        <span class="pill">${player.source || "model"}</span>
        <button class="prompt open-player" data-player="${player.name}">Open profile</button>
        ${player.live ? `<span class="pill">Live profile</span>` : ""}
        ${player.custom ? `<button class="remove-player" data-player="${player.name}">Remove</button>` : ""}
      </div>
    </article>
  `).join("") : `<div class="empty-market-state"><strong>No live player profiles loaded.</strong><p>Connect a working stats/roster provider or add a manual profile. No sample player cards are shown.</p></div>`;

  $$(".open-player").forEach((button) => button.addEventListener("click", () => openPlayer(button.dataset.player)));
  $$(".remove-player").forEach((button) => button.addEventListener("click", () => removeCustomPlayer(button.dataset.player)));
}

async function openPlayer(name) {
  const player = players.find((item) => item.name === name) || livePlayerResults.find((item) => item.name === name);
  const sport = player.sport || $("#custom-sport").value;
  let context = null;
  try {
    const response = await fetch(`/api/context/${sport}?q=${encodeURIComponent(name)}`);
    if (response.ok) context = await response.json();
  } catch {
    context = null;
  }
  const contextHtml = context ? `
    <h2>News and injury wire</h2>
    <div class="engine-list">
      ${(context.injuries || []).slice(0, 4).map((item) => `<div class="engine-item"><strong>${item.player || name}</strong>${[item.team, item.status, item.body_part].filter(Boolean).join(" · ")}</div>`).join("")}
      ${(context.news || []).slice(0, 4).map((item) => `<div class="engine-item"><strong>${item.title || "News"}</strong><span class="muted">${item.summary || ""}</span></div>`).join("")}
    </div>
  ` : "";
  $("#dialog-content").innerHTML = `
    <div class="profile">
      <div>
        <div class="avatar">${player.name.split(" ").map((part) => part[0]).join("")}</div>
        <h2>${player.name}</h2>
        <p class="muted">${player.team} vs ${player.opponent}</p>
        <p>${player.note || "Live player profile."}</p>
        <div class="metric-row">
          <span class="pill">${player.market} ${player.line}</span>
          ${player.live ? `<span class="pill">SportsDataIO profile</span>` : `<span class="pill">${hitRate(player)}% hit rate</span>`}
          <span class="pill">${player.confidence}% confidence</span>
        </div>
      </div>
      <div>
        <h2>Usage map</h2>
        <div class="shot-map">
          ${(player.hotspots || [[42, 48], [58, 52], [50, 66]]).map(([x, y]) => `<span class="hotspot" style="left:${x}%; top:${y}%"></span>`).join("")}
        </div>
        ${contextHtml}
      </div>
    </div>
  `;
  $("#player-dialog").showModal();
}

function buildParlay(legs, risk, sport) {
  const pool = players
    .filter((player) => sport === "All" || player.sport === sport)
    .map((player) => ({
      ...player,
      modelScore: player.confidence + hitRate(player) * 0.22 + player.matchup * 1.6
    }))
    .sort((a, b) => {
      if (risk === "upside") return (b.line + b.modelScore) - (a.line + a.modelScore);
      if (risk === "safer") return b.confidence - a.confidence;
      return b.modelScore - a.modelScore;
    })
    .slice(0, legs);

  const combined = Math.round(pool.reduce((score, player) => score + player.confidence, 0) / pool.length);
  return { pool, combined };
}

function sourceLabel(source) {
  return {
    "sportsdataio-stats": "Live stats",
    "model-fallback": "Model fallback",
    "manual-model": "Manual model",
    "browser-fallback": "Browser fallback",
    "manual-mode": "Manual mode",
    "live-best-line": "Live best line",
    "live-ranking": "Live ranking"
  }[source] || source || "Fallback";
}

function renderManualParlayLegs() {
  $("#manual-parlay-legs").innerHTML = manualParlayLegs.map((leg, index) => `
    <div class="manual-leg">
      <strong>${index + 1}. ${leg.player || leg.team} ${leg.market} ${leg.line}</strong>
      <div class="metric-row">
        <span class="pill">${leg.sport}</span>
        <span class="pill">odds ${leg.odds}</span>
        <button class="remove-player remove-parlay-leg" data-index="${index}" type="button">Remove</button>
      </div>
    </div>
  `).join("");

  $$(".remove-parlay-leg").forEach((button) => {
    button.addEventListener("click", () => {
      manualParlayLegs.splice(Number(button.dataset.index), 1);
      renderManualParlayLegs();
    });
  });
}

function addManualParlayLeg() {
  const sport = $("#focus-input").value === "All" ? $("#sport-filter").value : $("#focus-input").value;
  const subject = $("#parlay-subject").value.trim();
  const market = $("#parlay-market").value.trim();
  const line = Number($("#parlay-line").value);
  const odds = Number($("#parlay-odds").value || -110);
  if (!subject || !market || !Number.isFinite(line)) return;

  manualParlayLegs.push({
    sport: sport === "All" ? "NFL" : sport,
    player: subject,
    team: "",
    market,
    line,
    odds
  });

  $("#parlay-subject").value = "";
  $("#parlay-market").value = "";
  $("#parlay-line").value = "";
  $("#parlay-odds").value = "";
  renderManualParlayLegs();
}

function formatParlayAnswer(card) {
  return `<strong>Generated ${card.pool.length}-leg research card</strong>${card.pool.map((player) => `${player.name} ${player.market} over ${player.line}: ${player.confidence}% confidence`).join("<br>")}<div class="metric-row"><span class="pill">Combined confidence ${card.combined}%</span><span class="pill">Check live lines before acting</span></div>`;
}

function rankingToPrediction(row) {
  const line = Number(row.line ?? 0);
  const odds = Number(row.odds || -110);
  const confidence = Math.max(0.48, Math.min(0.9, Number(row.confidence || 62) / 100));
  return {
    subject: row.name || row.subject || row.player || row.matchup,
    sport: row.sport,
    team: compactTeamName(row.team),
    market: row.market || "Market",
    line,
    odds,
    confidence,
    hit_rate: Math.max(0.48, Math.min(0.86, confidence + 0.03)),
    edge: Number((confidence - oddsToProbability(odds)).toFixed(3)),
    recommendation: confidence > 0.62 ? "Play" : "Watch",
    source: row.source || "live-ranking",
    sample_size: row.books_checked || 0,
    explanation: `${row.matchup || "Live board"}${row.book ? ` - best price at ${row.book}` : ""}${row.commence_time ? ` - ${formatEventTime(row.commence_time)}` : ""}`,
    validation: row.source?.includes("live") ? ["Live provider board. Confirm final injury/lineup news before using."] : ["Provider fallback. Add live odds/stats keys for stronger coverage."]
  };
}

async function renderParlay() {
  const legs = Number($("#legs-input").value);
  const risk = $("#risk-input").value;
  const focus = $("#focus-input").value;
  const manualPredictions = [];
  for (const leg of manualParlayLegs) {
    manualPredictions.push(await getPrediction(leg));
  }

  if (!liveRankings.length) await loadRankingsData(false);
  const remaining = Math.max(0, legs - manualPredictions.length);
  const livePool = liveRankings
    .filter((row) => focus === "All" || row.sport === focus)
    .filter((row) => !manualPredictions.some((leg) => String(leg.subject).toLowerCase() === String(row.name || row.subject).toLowerCase()))
    .sort((a, b) => {
      if (risk === "safer") return (b.confidence || 0) - (a.confidence || 0);
      if (risk === "upside") return Math.abs(Number(b.odds || -110)) - Math.abs(Number(a.odds || -110));
      return ((b.confidence || 0) + Math.max(0, Number(b.edge || 0) * 100)) - ((a.confidence || 0) + Math.max(0, Number(a.edge || 0) * 100));
    })
    .slice(0, remaining)
    .map(rankingToPrediction);
  const allLegs = [...manualPredictions, ...livePool].slice(0, legs);
  lastParlayLegs = allLegs;
  const combined = allLegs.length
    ? Math.round((allLegs.reduce((sum, leg) => sum + Number(leg.confidence || 0), 0) / allLegs.length) * 100)
    : 0;

  $("#parlay-output").innerHTML = `
    <h2>Generated card</h2>
    <div class="confidence">
      <strong>${combined}%</strong>
      <div class="bar"><span style="width:${combined}%"></span></div>
    </div>
    ${allLegs.length ? allLegs.map((leg, index) => `
      <div class="leg">
        <strong>${index + 1}. ${leg.subject} over ${leg.line} ${leg.market}</strong>
        <span class="muted">${leg.explanation}</span>
        <div class="metric-row">
          <span class="pill">${leg.sport}</span>
          <span class="pill">${sourceLabel(leg.source)}</span>
          <span class="pill">${Math.round(Number(leg.hit_rate || 0) * 100)}% hit</span>
          <span class="pill">edge ${leg.edge}</span>
        </div>
        ${Array.isArray(leg.validation) && leg.validation.length ? `<div class="prediction-warnings">${leg.validation.map((item) => `<div>${item}</div>`).join("")}</div>` : ""}
      </div>
    `).join("") : `<div class="empty-market-state"><strong>No parlay legs available.</strong><p>Add typed legs or connect live market providers. No sample slate legs are generated.</p></div>`}
    <button class="mini-btn full-width" type="button" id="save-parlay-card">Save card</button>
  `;
  $("#save-parlay-card")?.addEventListener("click", saveParlayCard);
}

async function saveParlayCard() {
  if (!lastParlayLegs.length) return;
  try {
    await postJson("/api/cards", {
      token: authToken || null,
      name: `${lastParlayLegs.length}-leg card ${new Date().toLocaleDateString()}`,
      legs: lastParlayLegs
    });
    await loadAnalytics();
  } catch (error) {
    alert(error.message || "Could not save this card.");
  }
}

async function renderRankings() {
  await loadRankingsData(true);
}

async function loadRankingsData(render = true) {
  const sport = $("#sport-filter").value;
  const team = $("#team-filter").value;
  let rows = [];
  let source = "live-provider-unavailable";
  try {
    const response = await fetch(`/api/rankings?sport=${encodeURIComponent(sport)}&team=${encodeURIComponent(team)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("rankings unavailable");
    const data = await response.json();
    rows = data.rankings || [];
    source = data.source || "live rankings";
  } catch {
    rows = [];
    source = "Live provider not connected. Using manual mode.";
  }
  liveRankings = rows;
  renderTeamFilter();
  renderPredictionSuggestions();
  renderQuickPrompts();
  if (!render) return rows;
  $("#ranking-table").innerHTML = `
    <div class="rank-row header">
      <span>Rank</span><span>Player</span><span>Sport</span><span>Market</span><span>Confidence</span>
    </div>
    ${rows.map((row, index) => `
      <div class="rank-row">
        <span>#${index + 1}</span>
        <span><strong>${row.player || row.subject || row.name}</strong><br><span class="muted">${row.team || row.matchup || row.event || source}</span></span>
        <span>${row.sport}</span>
        <span>${row.market}${row.line !== null && row.line !== undefined ? ` ${row.line}` : ""}${row.book || row.best_book ? `<br><span class="muted">${row.book || row.best_book}</span>` : ""}${row.commence_time ? `<br><span class="muted">${formatEventTime(row.commence_time)}</span>` : ""}${row.venue ? `<br><span class="muted">${row.venue}</span>` : ""}</span>
        <span>${Math.round(row.confidence || 0)}%</span>
      </div>
    `).join("") || `<div class="rank-row"><span></span><span>No live rankings yet. Live provider not connected or returned no matching markets.</span><span></span><span></span><span></span></div>`}
  `;
  return rows;
}

function localEngineSnapshot() {
  const allBets = players.map((player) => {
    const rate = hitRate(player) / 100;
    const implied = 110 / 210;
    const edge = rate - implied;
    return {
      name: player.name,
      market: player.market,
      line: player.line,
      edge: Number(edge.toFixed(3)),
      hit_rate: Number(rate.toFixed(3)),
      confidence: Number((rate * (1 - Math.abs(edge))).toFixed(3)),
      bet: edge > 0.05
    };
  }).sort((a, b) => b.edge - a.edge);

  const firstShotPool = players.filter((player) => ["NBA", "MMA"].includes(player.sport)).slice(0, 6);
  const usageTotal = firstShotPool.reduce((sum, player) => sum + player.usage, 0) || 1;

  return {
    mode: "local baseline",
    top_bets: allBets.filter((bet) => bet.confidence > 0.55 && bet.edge > 0.05).slice(0, 10),
    all_bets: allBets,
    parlay: allBets.filter((bet) => bet.edge > 0.06).slice(0, 3),
    insights: players
      .filter((player) => player.usage > 28 || avg(player.recent) > player.line)
      .map((player) => `${player.name}: ${player.usage > 28 ? "usage spike" : "recent average above line"}`),
    first_shot: Object.fromEntries(firstShotPool.map((player) => [player.name, Number((player.usage / usageTotal).toFixed(3))]))
  };
}

async function loadEngineSnapshot() {
  try {
    const response = await fetch("/api", { cache: "no-store" });
    if (!response.ok) throw new Error("API unavailable");
    engineSnapshot = await response.json();
    $("#engine-status").textContent = engineSnapshot.mode || "API live";
  } catch {
    engineSnapshot = {
      mode: "manual mode",
      message: "Live provider not connected. Using manual mode.",
      providers: {},
      top_bets: [],
      all_bets: [],
      parlay: [],
      insights: [],
      first_shot: {}
    };
    $("#engine-status").textContent = "Manual mode";
  }
  renderEngine();
}

function renderEngine() {
  const snapshot = engineSnapshot || {
    mode: "manual mode",
    message: "Live provider not connected. Using manual mode.",
    providers: {},
    top_bets: [],
    all_bets: [],
    events: [],
    insights: [],
    first_shot: {}
  };
  const topBets = snapshot.top_bets?.length ? snapshot.top_bets : snapshot.all_bets?.slice(0, 5) || [];
  const events = snapshot.events || [];
  const providers = snapshot.providers || {};
  const liveSports = providers.live_odds_sports || [];
  const providerSummary = [
    providers.odds_api_connected ? "Odds key connected" : "Odds key missing",
    providers.sportsdata_api_connected ? "Stats key connected" : "Stats key missing",
    liveSports.length ? `Live odds: ${liveSports.join(", ")}` : "No live odds feed in this view"
  ];
  $("#engine-status").textContent = snapshot.mode || "Model engine";

  $("#top-bets").innerHTML = topBets.map((bet) => `
    <div class="engine-item">
      <strong>${bet.name}${bet.market ? ` · ${bet.market}` : ""}${bet.line ? ` ${bet.line}` : ""}</strong>
      <div class="confidence">
        <span>${Math.round((bet.confidence || 0) * 100)}%</span>
        <div class="bar"><span style="width:${Math.round((bet.confidence || 0) * 100)}%"></span></div>
      </div>
      <div class="metric-row">
        <span class="pill">edge ${bet.edge}</span>
        <span class="pill">hit ${Math.round((bet.hit_rate || 0) * 100)}%</span>
        <span class="pill">${bet.bet ? "sharp" : "watch"}</span>
      </div>
    </div>
  `).join("") || `<p class="muted">No sharp bets yet.</p>`;

  $("#first-shot").innerHTML = Object.entries(snapshot.first_shot || {}).map(([name, probability]) => `
    <div class="engine-item">
      <strong>${name}</strong>
      <div class="confidence">
        <span>${Math.round(probability * 100)}%</span>
        <div class="bar"><span style="width:${Math.round(probability * 100)}%"></span></div>
      </div>
    </div>
  `).join("") || `<p class="muted">First-shot history is not loaded.</p>`;

  $("#engine-insights").innerHTML = `
    ${events.length ? `<div class="engine-item"><strong>Upcoming games and locations</strong>${events.slice(0, 8).map((event) => `<span>${event.matchup || `${event.away_team} at ${event.home_team}`} - ${formatEventTime(event.commence_time)} - ${event.venue || "venue pending"}</span>`).join("")}</div>` : ""}
    ${providerSummary.map((item) => `<div class="engine-item"><strong>${item}</strong></div>`).join("")}
    ${(snapshot.insights || []).map((insight) => `
    <div class="engine-item">${insight}</div>
  `).join("")}
  ` || `<p class="muted">No engine insights yet.</p>`;
}

async function loadAnalytics() {
  try {
    const token = encodeURIComponent(authToken || "");
    const [analyticsResponse, statusResponse, cardsResponse, alertsResponse, watchResponse, responsibleResponse] = await Promise.all([
      fetch("/api/analytics", { cache: "no-store" }),
      fetch("/api/admin/status", { cache: "no-store" }),
      fetch(`/api/cards?token=${token}`, { cache: "no-store" }),
      fetch(`/api/alerts?token=${token}`, { cache: "no-store" }),
      fetch(`/api/watchlist?token=${token}`, { cache: "no-store" }),
      fetch("/api/responsible-use", { cache: "no-store" })
    ]);
    analyticsSnapshot = {
      analytics: analyticsResponse.ok ? await analyticsResponse.json() : null,
      status: statusResponse.ok ? await statusResponse.json() : null
    };
    savedCards = cardsResponse.ok ? (await cardsResponse.json()).cards || [] : [];
    serverAlerts = alertsResponse.ok ? (await alertsResponse.json()).alerts || [] : [];
    serverWatchlist = watchResponse.ok ? (await watchResponse.json()).watchlist || [] : [];
    responsibleUse = responsibleResponse.ok ? await responsibleResponse.json() : null;
  } catch {
    analyticsSnapshot = null;
  }
  renderAnalytics();
}

async function loadMarketSources() {
  try {
    const [response, freshnessResponse] = await Promise.all([
      fetch("/api/market-sources", { cache: "no-store" }),
      fetch("/api/data-freshness", { cache: "no-store" })
    ]);
    if (!response.ok) throw new Error("market source framework unavailable");
    marketSources = await response.json();
    dataFreshness = freshnessResponse.ok ? await freshnessResponse.json() : null;
  } catch {
    marketSources = null;
    dataFreshness = null;
  }
  renderAnalytics();
}

function renderObjectList(object) {
  return Object.entries(object || {}).map(([key, value]) => `<div class="engine-item"><strong>${key}</strong>${typeof value === "object" ? Object.entries(value).map(([inner, flag]) => `${inner}: ${Array.isArray(flag) ? flag.join(", ") : flag}`).join(" | ") : value}</div>`).join("");
}

function renderAnalytics() {
  const analytics = analyticsSnapshot?.analytics;
  const status = analyticsSnapshot?.status;
  const database = status?.database || {};
  const clvCount = analytics?.clv_tracked || 0;
  const avgClv = analytics?.average_clv ?? 0;
  const hitPct = Math.round((analytics?.hit_rate || 0) * 100);
  const providerScore = [
    status?.providers?.odds_api_connected || status?.odds_api_connected,
    status?.providers?.sportsdata_api_connected || status?.sportsdata_api_connected,
    status?.weather_api_connected,
    database.ready
  ].filter(Boolean).length;
  $("#analytics-chart").innerHTML = `
    <div><strong>${hitPct}%</strong><span>tracked hit rate</span><div class="bar"><span style="width:${hitPct}%"></span></div></div>
    <div><strong>${analytics?.total_predictions || 0}</strong><span>logged predictions</span><div class="bar"><span style="width:${Math.min(100, (analytics?.total_predictions || 0) * 8)}%"></span></div></div>
  `;
  $("#provider-chart").innerHTML = `
    <div><strong>${providerScore}/4</strong><span>connected systems</span><div class="bar"><span style="width:${providerScore * 25}%"></span></div></div>
    <div><strong>${liveRankings.length}</strong><span>live board rows</span><div class="bar"><span style="width:${Math.min(100, liveRankings.length * 4)}%"></span></div></div>
  `;
  $("#analytics-summary").innerHTML = analytics ? `
    <div class="engine-item"><strong>Total predictions</strong>${analytics.total_predictions}</div>
    <div class="engine-item"><strong>Tracked hit rate</strong>${Math.round((analytics.hit_rate || 0) * 100)}% (${analytics.wins || 0}-${analytics.losses || 0}-${analytics.pushes || 0})</div>
    <div class="engine-item"><strong>CLV tracked</strong>${clvCount} entries | avg ${avgClv}</div>
    ${renderObjectList(analytics.by_source)}
    ${renderObjectList(analytics.by_recommendation)}
  ` : `<p class="muted">Analytics are waiting for predictions.</p>`;

  $("#provider-health").innerHTML = status ? `
    <div class="engine-item"><strong>Engine mode</strong>${status.engine_mode || "warming up"}</div>
    <div class="engine-item"><strong>Cache entries</strong>${status.cache_entries}</div>
    <div class="engine-item"><strong>Database</strong>${database.ready ? "ready" : "not ready"} | ${database.type || "sqlite"}${database.persistent_on_render ? " | persistent" : " | add Render Postgres for persistence"}</div>
    <div class="engine-item"><strong>Weather provider</strong>${status.weather_api_connected ? "connected" : "modeled fallback"}</div>
    ${renderObjectList(status.providers)}
  ` : `<p class="muted">Provider health is unavailable.</p>`;

  $("#prediction-history").innerHTML = (analytics?.recent || []).slice().reverse().map((row) => `
    <div class="engine-item">
      <strong>${row.subject} - ${row.market}</strong>
      <div class="metric-row">
        <span class="pill">${row.sport}</span>
        <span class="pill">${row.recommendation}</span>
        <span class="pill">${row.source}</span>
        <span class="pill">${Math.round((row.confidence || 0) * 100)}%</span>
        <span class="pill">${row.outcome || "pending"}</span>
        ${row.clv !== null && row.clv !== undefined ? `<span class="pill">CLV ${row.clv}</span>` : ""}
        ${row.id ? `<button class="mini-btn grade-btn" type="button" data-id="${row.id}" data-outcome="win">Win</button><button class="mini-btn grade-btn" type="button" data-id="${row.id}" data-outcome="loss">Loss</button><button class="mini-btn grade-btn" type="button" data-id="${row.id}" data-outcome="push">Push</button>` : ""}
      </div>
      ${row.id ? `<div class="metric-row"><input class="mini-input clv-line" data-id="${row.id}" inputmode="decimal" placeholder="Closing line"><input class="mini-input clv-odds" data-id="${row.id}" inputmode="numeric" placeholder="Closing odds"><button class="mini-btn clv-btn" type="button" data-id="${row.id}">Save CLV</button></div>` : ""}
    </div>
  `).join("") || `<p class="muted">No predictions have been logged yet.</p>`;

  $("#accuracy-report").innerHTML = analytics ? `
    <div class="engine-item"><strong>Settled</strong>${analytics.settled_predictions || 0}</div>
    <div class="engine-item"><strong>Confidence tiers</strong>${renderInlineMap(analytics.by_confidence)}</div>
    <div class="engine-item"><strong>By sport</strong>${renderInlineMap(analytics.by_sport)}</div>
  ` : `<p class="muted">Grade predictions to unlock accuracy tracking.</p>`;

  $("#owner-controls").innerHTML = `
    <div class="engine-item">
      <strong>Account</strong>
      ${currentUser ? `<span>Signed in as ${currentUser.username}</span><button class="mini-btn" type="button" id="auth-logout">Log out</button>` : `
        <input class="mini-input" id="auth-username" autocomplete="username" placeholder="Username">
        <input class="mini-input" id="auth-password" autocomplete="current-password" type="password" placeholder="Password">
        <div class="metric-row"><button class="mini-btn" type="button" id="auth-login">Log in</button><button class="mini-btn" type="button" id="auth-register">Register</button></div>
      `}
    </div>
    <div class="engine-item"><strong>Watchlist</strong>${serverWatchlist.length || watchlist.length} server/local watches</div>
    ${[...serverWatchlist, ...watchlist].slice(0, 5).map((item) => `<div class="engine-item"><strong>${item.subject}</strong>${item.sport} - ${item.market} ${item.line || ""}</div>`).join("")}
    <div class="engine-item">
      <strong>Alerts</strong>
      <input class="mini-input" id="alert-subject" placeholder="Player/team">
      <div class="inline-grid">
        <select class="mini-input" id="alert-sport"><option>NFL</option><option>MLB</option><option>NBA</option><option>NHL</option><option>MMA</option></select>
        <input class="mini-input" id="alert-market" placeholder="Market">
        <input class="mini-input" id="alert-threshold" inputmode="decimal" placeholder="0.60">
      </div>
      <div class="metric-row"><button class="mini-btn" type="button" id="create-alert">Create alert</button><button class="mini-btn" type="button" id="check-alerts">Check alerts</button></div>
    </div>
    ${serverAlerts.slice(0, 4).map((item) => `<div class="engine-item"><strong>${item.subject}</strong>${item.sport} - ${item.market}<span class="muted">${item.last_message || "watching"}</span></div>`).join("")}
    <div class="engine-item"><strong>Saved cards</strong>${savedCards.length} saved</div>
    ${savedCards.slice(0, 3).map((card) => `<div class="engine-item"><strong>${card.name}</strong>${(card.legs || []).length} legs</div>`).join("")}
    <div class="engine-item"><strong>24-hour refresh</strong>${dataFreshness?.daily_refresh?.status || "waiting"}${dataFreshness?.daily_refresh?.timestamp ? ` - ${new Date(dataFreshness.daily_refresh.timestamp * 1000).toLocaleString()}` : ""}</div>
    <div class="engine-item"><strong>Manual refresh</strong><button class="mini-btn" type="button" id="force-refresh">Refresh feeds now</button></div>
    <div class="engine-item"><strong>Settlement</strong><button class="mini-btn" type="button" id="run-settlement">Check pending results</button></div>
    <div class="engine-item"><strong>Market framework</strong>${(marketSources?.framework || []).slice(0, 4).join(" | ") || "Loading source stack..."}</div>
    ${(marketSources?.sources || []).slice(0, 4).map((source) => `<div class="engine-item"><strong>${source.name}</strong>${source.role}: ${source.use}</div>`).join("")}
    <div class="engine-item"><strong>Responsible use</strong>${(responsibleUse?.rules || []).slice(0, 2).join(" ") || "Research only. Predictions are not guarantees."}</div>
    <div class="engine-item"><strong>Gambling help</strong>${responsibleUse?.helpline ? `Call ${responsibleUse.helpline.call}, text ${responsibleUse.helpline.text}, or use NCPG chat.` : "If gambling is causing problems, seek free confidential help through the National Council on Problem Gambling."}</div>
  `;
  $("#force-refresh")?.addEventListener("click", forceRefreshFeeds);
  $("#auth-login")?.addEventListener("click", () => submitAuth("login"));
  $("#auth-register")?.addEventListener("click", () => submitAuth("register"));
  $("#auth-logout")?.addEventListener("click", logoutUser);
  $("#create-alert")?.addEventListener("click", createManualAlert);
  $("#check-alerts")?.addEventListener("click", checkAlerts);
  $("#run-settlement")?.addEventListener("click", runSettlement);
  $$(".grade-btn").forEach((button) => button.addEventListener("click", () => gradePrediction(button.dataset.id, button.dataset.outcome)));
  $$(".clv-btn").forEach((button) => button.addEventListener("click", () => updateClosingLine(button.dataset.id)));
  renderProfile();
}

function renderProfile() {
  const account = $("#profile-account");
  const tracking = $("#profile-tracking");
  const saved = $("#profile-saved");
  if (!account || !tracking || !saved) return;
  account.innerHTML = currentUser ? `
    <div class="engine-item"><strong>${currentUser.username}</strong>Profile is active. Saved cards, alerts, and watchlists are stored on the server when the database is ready.</div>
    <button class="mini-btn" type="button" id="profile-logout">Log out</button>
  ` : `
    <div class="engine-item"><strong>Create a free profile</strong>Use this to track predictions, saved cards, watchlists, alerts, CLV, and accuracy.</div>
    <input class="mini-input" id="profile-username" autocomplete="username" placeholder="Username">
    <input class="mini-input" id="profile-password" autocomplete="current-password" type="password" placeholder="Password">
    <div class="metric-row"><button class="mini-btn" type="button" id="profile-login">Log in</button><button class="mini-btn" type="button" id="profile-register">Register</button></div>
  `;
  const localTracked = customPlayers.length + watchlist.length;
  tracking.innerHTML = `
    <div class="engine-item"><strong>Watchlist items</strong>${serverWatchlist.length || watchlist.length} server/local</div>
    <div class="engine-item"><strong>Custom tracked props</strong>${customPlayers.length}</div>
    <div class="engine-item"><strong>Alerts</strong>${serverAlerts.length} active/server alerts</div>
    <div class="engine-item"><strong>Local profile data</strong>${localTracked} items stored in this browser</div>
  `;
  saved.innerHTML = `
    ${(savedCards || []).map((card) => `<div class="engine-item"><strong>${card.name}</strong>${(card.legs || []).length} legs saved</div>`).join("") || `<div class="engine-item"><strong>No saved cards yet</strong>Generate a parlay card and press Save card to track it here.</div>`}
    ${(analyticsSnapshot?.analytics?.recent || []).slice(-5).reverse().map((row) => `<div class="engine-item"><strong>${row.subject} - ${row.market}</strong>${row.recommendation} - ${Math.round((row.confidence || 0) * 100)}% - ${row.outcome || "pending"}</div>`).join("")}
  `;
  $("#profile-login")?.addEventListener("click", () => submitProfileAuth("login"));
  $("#profile-register")?.addEventListener("click", () => submitProfileAuth("register"));
  $("#profile-logout")?.addEventListener("click", logoutUser);
}

async function submitProfileAuth(action) {
  const username = $("#profile-username")?.value.trim();
  const password = $("#profile-password")?.value;
  if (!username || !password) return;
  try {
    const data = await postJson(`/api/auth/${action}`, { username, password });
    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    await loadAnalytics();
  } catch (error) {
    alert(error.message || "Profile request failed.");
  }
}

function renderInlineMap(object) {
  return Object.entries(object || {}).map(([key, value]) => `${key}: ${value}`).join(" | ") || "none";
}

async function gradePrediction(id, outcome) {
  try {
    const response = await fetch(`/api/predictions/${encodeURIComponent(id)}/grade`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome })
    });
    if (!response.ok) throw new Error("grade failed");
    await loadAnalytics();
  } catch {
    alert("Could not grade that prediction. Render may have restarted and cleared in-memory history.");
  }
}

async function updateClosingLine(id) {
  const line = $(`.clv-line[data-id="${id}"]`)?.value;
  const odds = $(`.clv-odds[data-id="${id}"]`)?.value || "-110";
  if (!line) return;
  try {
    const response = await fetch(`/api/predictions/${encodeURIComponent(id)}/closing-line?closing_line=${encodeURIComponent(line)}&closing_odds=${encodeURIComponent(odds)}`, { method: "POST" });
    if (!response.ok) throw new Error("clv failed");
    await loadAnalytics();
  } catch {
    alert("Could not save that closing line.");
  }
}

async function submitAuth(action) {
  const username = $("#auth-username")?.value.trim();
  const password = $("#auth-password")?.value;
  if (!username || !password) return;
  try {
    const data = await postJson(`/api/auth/${action}`, { username, password });
    authToken = data.token;
    currentUser = data.user;
    localStorage.setItem(AUTH_TOKEN_KEY, authToken);
    await loadAnalytics();
  } catch (error) {
    alert(error.message || "Account request failed.");
  }
}

function logoutUser() {
  authToken = "";
  currentUser = null;
  savedCards = [];
  serverAlerts = [];
  serverWatchlist = [];
  localStorage.removeItem(AUTH_TOKEN_KEY);
  renderAnalytics();
}

async function createManualAlert() {
  const subject = $("#alert-subject")?.value.trim();
  const market = $("#alert-market")?.value.trim();
  if (!subject || !market) return;
  try {
    await postJson("/api/alerts", {
      token: authToken || null,
      subject,
      sport: $("#alert-sport").value,
      market,
      threshold: Number($("#alert-threshold").value || 0.6)
    });
    await loadAnalytics();
  } catch (error) {
    alert(error.message || "Could not create alert.");
  }
}

async function checkAlerts() {
  try {
    const data = await postJson("/api/alerts/check");
    await loadAnalytics();
    if (data.triggered?.length) alert(`${data.triggered.length} alert(s) triggered.`);
  } catch {
    alert("Could not check alerts right now.");
  }
}

async function runSettlement() {
  try {
    const data = await postJson("/api/settlement/run");
    await loadAnalytics();
    alert(data.note || `Checked ${data.checked || 0} pending predictions.`);
  } catch {
    alert("Could not run settlement right now.");
  }
}

async function forceRefreshFeeds() {
  try {
    const response = await fetch("/api/admin/refresh", { method: "POST" });
    if (!response.ok) throw new Error("refresh failed");
    await Promise.all([loadEngineSnapshot(), loadLiveInsights(), loadAnalytics(), loadMarketSources()]);
  } catch {
    alert("Could not force-refresh feeds right now.");
  }
}

function switchView(view) {
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  $$(".view").forEach((section) => section.classList.toggle("active", section.id === view));
  $("#view-title").textContent = titles[view] || "Sporting Edge";
  document.body.classList.toggle("show-slip-rail", view === "betslip" || view === "markets");
  document.querySelectorAll(".mobile-bottom-nav button").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  if (view === "profile") renderProfile();
  if (view === "analytics") renderAnalytics();
  if (view === "markets") window.SEMarkets?.init?.();
  if (view === "betslip") window.SEBetSlip?.render?.();
}

function refreshAll() {
  renderTeamFilter();
  renderInsights();
  renderPlayers();
  renderRankings();
  renderEngine();
  renderAnalytics();
}

function addCustomPlayer(event) {
  event.preventDefault();
  const sport = $("#custom-sport").value;
  const line = Number($("#custom-line").value);
  const confidence = estimateConfidence(line, sport);
  const name = $("#custom-name").value.trim();

  const player = {
    name,
    sport,
    team: $("#custom-team").value.trim().toUpperCase(),
    opponent: $("#custom-opponent").value.trim().toUpperCase(),
    market: $("#custom-market").value.trim(),
    line,
    recent: makeRecent(line, confidence),
    usage: Math.round(confidence * 0.4),
    matchup: Math.max(5, Math.min(9, Math.round(confidence / 10))),
    confidence,
    note: "Custom tracked prop. Replace the line or market any time by removing it and adding an updated version.",
    hotspots: [[40, 44], [56, 52], [48, 68]],
    custom: true
  };

  customPlayers = customPlayers.filter((item) => item.name.toLowerCase() !== name.toLowerCase());
  customPlayers.push(player);
  saveCustomPlayers();
  $("#custom-player-form").reset();
  refreshAll();
}

function removeCustomPlayer(name) {
  customPlayers = customPlayers.filter((player) => player.name !== name);
  saveCustomPlayers();
  refreshAll();
}

async function searchLivePlayers() {
  const name = $("#custom-name").value.trim();
  const sport = $("#custom-sport").value;
  if (!name) {
    livePlayerResults = [];
    renderPlayers();
    return;
  }
  try {
    const response = await fetch(`/api/players/${sport}?q=${encodeURIComponent(name)}`, { cache: "no-store" });
    if (!response.ok) throw new Error("player search failed");
    const data = await response.json();
    livePlayerResults = (data.players || []).map((player) => ({ ...player, sport, source: data.source }));
  } catch {
    livePlayerResults = [];
  }
  renderPlayers();
}

$$(".nav-item").forEach((item) => item.addEventListener("click", () => switchView(item.dataset.view)));
$$(".mode").forEach((button) => button.addEventListener("click", () => {
  activeMode = button.dataset.mode;
  $$(".mode").forEach((item) => item.classList.toggle("active", item === button));
}));

$("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("#chat-input").value.trim();
  if (!question) return;
  addMessage("user", question);
  $("#chat-input").value = "";
  setTimeout(() => addMessage("bot", analyzeQuestion(question)), 220);
});

$("#ask-form").addEventListener("submit", submitStatsAsk);
$("#sport-filter").addEventListener("change", refreshAll);
$("#team-filter").addEventListener("change", refreshAll);
$("#predict-sport").addEventListener("change", renderPredictionSuggestions);
$("#edge-filter").addEventListener("change", renderInsights);
$("#insight-search").addEventListener("input", () => {
  clearTimeout(window.__insightSearchTimer);
  window.__insightSearchTimer = setTimeout(loadLiveInsights, 350);
});
$("#build-parlay").addEventListener("click", renderParlay);
$("#add-parlay-leg").addEventListener("click", addManualParlayLeg);
$("#custom-player-form").addEventListener("submit", addCustomPlayer);
$("#custom-name").addEventListener("input", () => {
  clearTimeout(window.__playerSearchTimer);
  window.__playerSearchTimer = setTimeout(searchLivePlayers, 350);
});
$("#custom-sport").addEventListener("change", searchLivePlayers);
$("#prediction-form").addEventListener("submit", submitPrediction);
$("#theme-toggle")?.addEventListener("click", toggleTheme);
$("#run-full-simulator")?.addEventListener("click", runFullPropSimulator);
$("#run-live-simulator")?.addEventListener("click", runLiveSimulator);
$("#refresh-btn").addEventListener("click", () => {
  Promise.all([loadRankingsData(false), loadLiveInsights(), loadEngineSnapshot(), loadAnalytics(), loadMarketSources()])
    .finally(refreshAll);
});
$("#close-dialog").addEventListener("click", () => $("#player-dialog").close());

applyTheme(activeTheme);
renderQuickPrompts();
renderChatIntro();
refreshAll();
loadCurrentUser().finally(() => {
  loadCatalog();
  loadRankingsData(false).then(() => {
    renderTeamFilter();
    renderPlayers();
    renderRankings();
    renderParlay();
  });
  loadLiveInsights();
  loadEngineSnapshot();
  loadAnalytics();
  loadMarketSources();
});
setInterval(loadEngineSnapshot, 60000);
setInterval(loadLiveInsights, 60000);
setInterval(() => loadRankingsData(false).then(() => {
  renderTeamFilter();
  renderPlayers();
  renderRankings();
}), 60000);
setInterval(loadAnalytics, 60000);
setInterval(loadMarketSources, 300000);
