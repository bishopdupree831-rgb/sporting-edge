const CUSTOM_PLAYERS_KEY = "edgelab.customPlayers";

const basePlayers = [
  {
    name: "Jalen Brunson",
    sport: "NBA",
    team: "NYK",
    opponent: "IND",
    market: "Points",
    line: 27.5,
    recent: [31, 28, 34, 24, 29, 37, 22, 30, 33, 26],
    usage: 32,
    matchup: 7,
    confidence: 74,
    note: "High on-ball load, strong late-clock usage, and a guard-friendly matchup profile.",
    hotspots: [[45, 72], [58, 58], [36, 42]]
  },
  {
    name: "Anthony Edwards",
    sport: "NBA",
    team: "MIN",
    opponent: "DEN",
    market: "Threes",
    line: 2.5,
    recent: [4, 3, 1, 5, 3, 2, 4, 4, 2, 3],
    usage: 30,
    matchup: 6,
    confidence: 69,
    note: "Volume is stable and the matchup tends to concede pull-up attempts above the break.",
    hotspots: [[28, 32], [70, 33], [52, 46]]
  },
  {
    name: "Christian McCaffrey",
    sport: "NFL",
    team: "SF",
    opponent: "SEA",
    market: "Rush+Rec Yards",
    line: 112.5,
    recent: [128, 99, 141, 118, 87, 132, 121, 109, 136, 115],
    usage: 29,
    matchup: 8,
    confidence: 78,
    note: "Elite snap share and target floor give this profile multiple ways to clear.",
    hotspots: [[44, 58], [54, 66], [50, 38]]
  },
  {
    name: "CeeDee Lamb",
    sport: "NFL",
    team: "DAL",
    opponent: "PHI",
    market: "Receptions",
    line: 6.5,
    recent: [9, 7, 6, 11, 8, 5, 10, 7, 8, 9],
    usage: 28,
    matchup: 7,
    confidence: 72,
    note: "Target share spikes against zone looks, with a favorable slot alignment path.",
    hotspots: [[33, 54], [60, 44], [68, 70]]
  },
  {
    name: "Mookie Betts",
    sport: "MLB",
    team: "LAD",
    opponent: "ARI",
    market: "Total Bases",
    line: 1.5,
    recent: [2, 1, 4, 0, 3, 2, 2, 1, 5, 2],
    usage: 24,
    matchup: 8,
    confidence: 71,
    note: "Recent hard-contact rate and platoon advantage both point in the same direction.",
    hotspots: [[42, 40], [60, 36], [50, 52]]
  },
  {
    name: "Bobby Witt Jr.",
    sport: "MLB",
    team: "KC",
    opponent: "CHW",
    market: "Hits",
    line: 1.5,
    recent: [2, 2, 1, 3, 0, 2, 1, 2, 2, 1],
    usage: 25,
    matchup: 6,
    confidence: 66,
    note: "Contact profile is strong, but the line needs two hits, so confidence stays moderate.",
    hotspots: [[38, 46], [56, 38], [63, 58]]
  },
  {
    name: "Islam Makhachev",
    sport: "MMA",
    team: "Makhachev",
    opponent: "Tsarukyan",
    market: "Takedowns",
    line: 2.5,
    recent: [4, 3, 5, 2, 6, 3, 4, 2, 5, 4],
    usage: 27,
    matchup: 8,
    confidence: 75,
    note: "Grappling pace and control-time paths create multiple ways to clear a takedown prop.",
    hotspots: [[44, 54], [52, 42], [58, 66]]
  },
  {
    name: "Sean O'Malley",
    sport: "MMA",
    team: "O'Malley",
    opponent: "Dvalishvili",
    market: "Significant Strikes",
    line: 74.5,
    recent: [91, 68, 104, 76, 82, 61, 95, 73, 88, 79],
    usage: 26,
    matchup: 6,
    confidence: 67,
    note: "Striking volume is attractive, but wrestling pressure adds round-by-round volatility.",
    hotspots: [[40, 36], [62, 46], [50, 62]]
  }
];

let customPlayers = loadCustomPlayers();
let players = [...basePlayers, ...customPlayers];

const insights = [
  {
    type: "Usage",
    sport: "NBA",
    title: "Brunson usage is holding above 31%",
    body: "His last-ten touch share is up while New York is shortening the rotation. The points line is fair, but the over has a clean workload argument.",
    player: "Jalen Brunson",
    score: 84
  },
  {
    type: "Matchup",
    sport: "NFL",
    title: "Seattle has struggled with RB receiving volume",
    body: "San Francisco can attack the linebackers in space. McCaffrey's combined yardage market gets a boost because both rushing and receiving paths are live.",
    player: "Christian McCaffrey",
    score: 88
  },
  {
    type: "Market",
    sport: "MLB",
    title: "Betts total bases remains playable",
    body: "The sample model grades his 1.5 total bases line as a small edge against a pitcher allowing elevated barrel contact.",
    player: "Mookie Betts",
    score: 76
  },
  {
    type: "Injury",
    sport: "NBA",
    title: "Minnesota wing depth watch",
    body: "If the rotation stays thin, Edwards should keep extra creation reps. His threes profile benefits more than his assists profile.",
    player: "Anthony Edwards",
    score: 72
  },
  {
    type: "Matchup",
    sport: "NFL",
    title: "Dallas slot leverage is real",
    body: "Philadelphia's pressure rate can force quick-game volume. Lamb's receptions line is a better fit than long-yardage exposure.",
    player: "CeeDee Lamb",
    score: 79
  },
  {
    type: "Market",
    sport: "MLB",
    title: "Witt hits line carries volatility",
    body: "The matchup is positive, but the two-hit threshold creates a narrower margin than total bases or runs markets.",
    player: "Bobby Witt Jr.",
    score: 68
  },
  {
    type: "Matchup",
    sport: "MMA",
    title: "Makhachev grappling path grades well",
    body: "The takedown line is supported by chain-wrestling volume and control-time upside, though MMA props remain highly state-dependent.",
    player: "Islam Makhachev",
    score: 81
  },
  {
    type: "Usage",
    sport: "MMA",
    title: "O'Malley volume depends on range control",
    body: "His significant-strike line improves in open-space rounds but weakens if cage pressure limits exchanges.",
    player: "Sean O'Malley",
    score: 70
  }
];

const quickPrompts = [
  "Is Brunson over 27.5 points worth researching?",
  "Build a 3 leg balanced parlay",
  "Compare McCaffrey and Lamb for safest prop",
  "What MLB insight has the strongest edge?",
  "Which MMA prop has the best model score?"
];

const titles = {
  research: "Ask a sports research question",
  insights: "Curated daily edges",
  players: "Player profiles",
  parlay: "Parlay builder",
  rankings: "Prop-centric rankings",
  engine: "Live betting engine"
};

let activeMode = "quick";
let engineSnapshot = null;
let catalog = {
  teams: {},
  markets: {},
  sample_players: []
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

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

function makeRecent(line, confidence) {
  const center = line * (0.9 + confidence / 180);
  return Array.from({ length: 10 }, (_, index) => {
    const wave = Math.sin(index * 1.7) * line * 0.14;
    const drift = (index % 3 - 1) * line * 0.07;
    return Number(Math.max(0, center + wave + drift).toFixed(1));
  });
}

function estimateConfidence(line, sport) {
  const sportBase = { NFL: 70, MLB: 66, NBA: 69, MMA: 63 }[sport] || 66;
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
  const teams = [...new Set(players
    .filter((player) => sport === "All" || player.sport === sport)
    .flatMap((player) => [player.team, player.opponent])
    .filter(Boolean)
  )].sort();

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
        MMA: ["UFC", "Bellator", "PFL", "ONE Championship"]
      },
      markets: {
        NFL: ["Passing Yards", "Rushing Yards", "Receiving Yards", "Receptions", "Anytime Touchdown"],
        MLB: ["Hits", "Total Bases", "Home Runs", "Pitcher Strikeouts"],
        NBA: ["Points", "Rebounds", "Assists", "Threes"],
        MMA: ["Moneyline", "Significant Strikes", "Takedowns", "Fight Goes Distance"]
      },
      sample_players: basePlayers
    };
  }
  renderPredictionSuggestions();
}

function renderPredictionSuggestions() {
  const sport = $("#predict-sport").value;
  const teams = catalog.teams?.[sport] || [];
  const markets = catalog.markets?.[sport] || [];
  const names = [...new Set([
    ...basePlayers.filter((player) => player.sport === sport).map((player) => player.name),
    ...customPlayers.filter((player) => player.sport === sport).map((player) => player.name)
  ])].sort();

  $("#team-suggestions").innerHTML = teams.map((team) => `<option value="${team}"></option>`).join("");
  $("#market-suggestions").innerHTML = markets.map((market) => `<option value="${market}"></option>`).join("");
  $("#player-suggestions").innerHTML = names.map((name) => `<option value="${name}"></option>`).join("");
}

function localPrediction(payload) {
  const confidence = estimateConfidence(payload.line, payload.sport);
  const recent = makeRecent(payload.line, confidence);
  const rate = recent.filter((value) => value > payload.line).length / recent.length;
  const implied = oddsToProbability(payload.odds || -110);
  const edge = rate - implied;
  const recommendation = edge > 0.06 ? "Play" : edge < -0.06 ? "Fade" : "Watch";

  return {
    ...payload,
    subject: payload.player || payload.team || "Unknown",
    projection: Number((recent.reduce((sum, value) => sum + value, 0) / recent.length).toFixed(2)),
    hit_rate: Number(rate.toFixed(3)),
    implied_probability: Number(implied.toFixed(3)),
    edge: Number(edge.toFixed(3)),
    confidence: Number((rate * (1 - Math.min(Math.abs(edge), 0.35))).toFixed(3)),
    recommendation,
    explanation: "Local browser model. Add ODDS_API_KEY in Render for live event and odds access."
  };
}

function oddsToProbability(odds) {
  return odds > 0 ? 100 / (odds + 100) : Math.abs(odds) / (Math.abs(odds) + 100);
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

function renderPrediction(result) {
  const statusClass = result.recommendation === "Play" ? "play" : result.recommendation === "Fade" ? "fade" : "";
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
      <div class="confidence">
        <strong>${Math.round(result.confidence * 100)}% confidence</strong>
        <div class="bar"><span style="width:${Math.round(result.confidence * 100)}%"></span></div>
      </div>
      <p>${result.explanation}</p>
      <div class="metric-row">
        <span class="pill">projection ${result.projection}</span>
        <span class="pill">hit ${Math.round(result.hit_rate * 100)}%</span>
        <span class="pill">implied ${Math.round(result.implied_probability * 100)}%</span>
        <span class="pill">edge ${result.edge}</span>
      </div>
    </div>
  `;
}

function renderChatIntro() {
  addMessage(
    "bot",
    "Ask me about a prop, player, matchup, insight, or parlay. I'll answer from the local sample slate and show the stats I used."
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

  if (lower.includes("mlb") || lower.includes("nba") || lower.includes("nfl") || lower.includes("mma") || lower.includes("insight")) {
    const sport = lower.includes("mlb") ? "MLB" : lower.includes("nfl") ? "NFL" : lower.includes("nba") ? "NBA" : lower.includes("mma") ? "MMA" : $("#sport-filter").value;
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
  $("#quick-prompts").innerHTML = quickPrompts
    .map((prompt) => `<button class="prompt" type="button">${prompt}</button>`)
    .join("");

  $$(".prompt").forEach((button) => {
    button.addEventListener("click", () => {
      $("#chat-input").value = button.textContent;
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
    title: `${player.name} added to your slate`,
    body: `${player.market} ${player.line} is now available in chat, rankings, profiles, and parlay generation.`,
    player: player.name,
    score: player.confidence
  }));
  const allInsights = [...insights, ...customInsights];
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
      </div>
    </article>
  `).join("") || `<p class="muted">No insights match those filters.</p>`;
}

function renderPlayers() {
  $("#player-grid").innerHTML = filteredPlayers().map((player) => `
    <article class="player-card">
      <div class="player-head">
        <div class="avatar">${player.name.split(" ").map((part) => part[0]).join("")}</div>
        <div>
          <h3>${player.name}</h3>
          <p class="muted">${player.team} vs ${player.opponent} · ${player.sport}</p>
        </div>
      </div>
      <div class="bars">
        <span>Confidence ${player.confidence}%</span>
        <div class="bar"><span style="width:${player.confidence}%"></span></div>
        <span>Recent hit rate ${hitRate(player)}%</span>
        <div class="bar"><span style="width:${hitRate(player)}%"></span></div>
      </div>
      <div class="metric-row">
        <button class="prompt open-player" data-player="${player.name}">Open profile</button>
        ${player.custom ? `<button class="remove-player" data-player="${player.name}">Remove</button>` : ""}
      </div>
    </article>
  `).join("");

  $$(".open-player").forEach((button) => button.addEventListener("click", () => openPlayer(button.dataset.player)));
  $$(".remove-player").forEach((button) => button.addEventListener("click", () => removeCustomPlayer(button.dataset.player)));
}

function openPlayer(name) {
  const player = players.find((item) => item.name === name);
  $("#dialog-content").innerHTML = `
    <div class="profile">
      <div>
        <div class="avatar">${player.name.split(" ").map((part) => part[0]).join("")}</div>
        <h2>${player.name}</h2>
        <p class="muted">${player.team} vs ${player.opponent}</p>
        <p>${player.note}</p>
        <div class="metric-row">
          <span class="pill">${player.market} ${player.line}</span>
          <span class="pill">${hitRate(player)}% hit rate</span>
          <span class="pill">${player.confidence}% confidence</span>
        </div>
      </div>
      <div>
        <h2>Usage map</h2>
        <div class="shot-map">
          ${player.hotspots.map(([x, y]) => `<span class="hotspot" style="left:${x}%; top:${y}%"></span>`).join("")}
        </div>
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

function formatParlayAnswer(card) {
  return `<strong>Generated ${card.pool.length}-leg research card</strong>${card.pool.map((player) => `${player.name} ${player.market} over ${player.line}: ${player.confidence}% confidence`).join("<br>")}<div class="metric-row"><span class="pill">Combined confidence ${card.combined}%</span><span class="pill">Check live lines before acting</span></div>`;
}

function renderParlay() {
  const legs = Number($("#legs-input").value);
  const risk = $("#risk-input").value;
  const focus = $("#focus-input").value;
  const card = buildParlay(legs, risk, focus);
  $("#parlay-output").innerHTML = `
    <h2>Generated card</h2>
    <div class="confidence">
      <strong>${card.combined}%</strong>
      <div class="bar"><span style="width:${card.combined}%"></span></div>
    </div>
    ${card.pool.map((player, index) => `
      <div class="leg">
        <strong>${index + 1}. ${player.name} over ${player.line} ${player.market}</strong>
        <span class="muted">${player.note}</span>
        <div class="metric-row">
          <span class="pill">${player.sport}</span>
          <span class="pill">${hitRate(player)}% last-ten</span>
          <span class="pill">${player.matchup}/10 matchup</span>
        </div>
      </div>
    `).join("")}
  `;
}

function renderRankings() {
  const rows = filteredPlayers().sort((a, b) => b.confidence - a.confidence);
  $("#ranking-table").innerHTML = `
    <div class="rank-row header">
      <span>Rank</span><span>Player</span><span>Sport</span><span>Market</span><span>Confidence</span>
    </div>
    ${rows.map((player, index) => `
      <div class="rank-row">
        <span>#${index + 1}</span>
        <span><strong>${player.name}</strong><br><span class="muted">${player.team} vs ${player.opponent}</span></span>
        <span>${player.sport}</span>
        <span>${player.market} ${player.line}</span>
        <span>${player.confidence}%</span>
      </div>
    `).join("")}
  `;
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
    mode: "local sample",
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
    engineSnapshot = localEngineSnapshot();
    $("#engine-status").textContent = "Local mode";
  }
  renderEngine();
}

function renderEngine() {
  const snapshot = engineSnapshot || localEngineSnapshot();
  const topBets = snapshot.top_bets?.length ? snapshot.top_bets : snapshot.all_bets?.slice(0, 5) || [];

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

  $("#engine-insights").innerHTML = (snapshot.insights || []).map((insight) => `
    <div class="engine-item">${insight}</div>
  `).join("") || `<p class="muted">No engine insights yet.</p>`;
}

function switchView(view) {
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  $$(".view").forEach((section) => section.classList.toggle("active", section.id === view));
  $("#view-title").textContent = titles[view];
}

function refreshAll() {
  renderTeamFilter();
  renderInsights();
  renderPlayers();
  renderParlay();
  renderRankings();
  renderEngine();
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
    note: "Custom slate entry. Replace the line or market any time by removing it and adding an updated version.",
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

$("#sport-filter").addEventListener("change", refreshAll);
$("#team-filter").addEventListener("change", refreshAll);
$("#predict-sport").addEventListener("change", renderPredictionSuggestions);
$("#edge-filter").addEventListener("change", renderInsights);
$("#insight-search").addEventListener("input", renderInsights);
$("#build-parlay").addEventListener("click", renderParlay);
$("#custom-player-form").addEventListener("submit", addCustomPlayer);
$("#prediction-form").addEventListener("submit", submitPrediction);
$("#refresh-btn").addEventListener("click", () => {
  players.forEach((player) => {
    player.confidence = Math.max(58, Math.min(91, player.confidence + Math.round(Math.random() * 6 - 3)));
  });
  refreshAll();
  loadEngineSnapshot();
});
$("#close-dialog").addEventListener("click", () => $("#player-dialog").close());

renderQuickPrompts();
renderChatIntro();
refreshAll();
loadCatalog();
loadEngineSnapshot();
setInterval(loadEngineSnapshot, 15000);
