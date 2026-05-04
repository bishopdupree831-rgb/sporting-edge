(function () {
  const state = {
    catalog: null,
    markets: [],
    filters: {
      sport: "NBA",
      sportsbook: "DraftKings",
      query: "",
      market_group: "",
      team: "",
      player_name: ""
    }
  };

  const rootId = "sportsbook-markets-root";
  const qs = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));

  function statusText(payload) {
    return payload?.message || "Live sportsbook provider not connected.";
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  async function loadCatalog() {
    try {
      state.catalog = await fetchJson("/api/markets/catalog");
    } catch (error) {
      state.catalog = {
        sports: ["NBA", "NFL", "MLB", "NHL", "MMA"],
        sportsbooks: ["DraftKings", "FanDuel"],
        market_groups: {},
        message: error.message
      };
    }
  }

  function marketGroupOptions() {
    const groups = state.catalog?.market_groups?.[state.filters.sport] || [];
    return [`<option value="">All markets</option>`]
      .concat(groups.map((group) => `<option value="${escapeHtml(group)}" ${state.filters.market_group === group ? "selected" : ""}>${escapeHtml(group)}</option>`))
      .join("");
  }

  function renderShell() {
    const root = qs(`#${rootId}`);
    if (!root) return;
    const sports = state.catalog?.sports || ["NBA", "NFL", "MLB", "NHL", "MMA"];
    const books = state.catalog?.sportsbooks || ["DraftKings", "FanDuel"];
    root.innerHTML = `
      <div class="markets-terminal">
        <section class="markets-main">
          <div class="markets-header">
            <div>
              <p class="markets-kicker">DraftKings / FanDuel normalized markets</p>
              <h2>Sportsbook Markets</h2>
              <p class="muted">Search live sportsbook markets by player, team, matchup, prop type, or market group.</p>
            </div>
            <button id="markets-refresh" class="mini-btn" type="button">Refresh markets</button>
          </div>
          <div class="markets-toolbar">
            <select id="markets-sport">${sports.map((sport) => `<option value="${sport}" ${state.filters.sport === sport ? "selected" : ""}>${sport}</option>`).join("")}</select>
            <select id="markets-book">${books.map((book) => `<option value="${book}" ${state.filters.sportsbook === book ? "selected" : ""}>${book}</option>`).join("")}</select>
            <select id="markets-group">${marketGroupOptions()}</select>
            <input id="markets-search" type="search" placeholder="Search Brunson, Knicks, assists, UFC..." value="${escapeHtml(state.filters.query)}" />
            <input id="markets-team" type="search" placeholder="Team or matchup" value="${escapeHtml(state.filters.team)}" />
          </div>
          <div id="markets-status" class="markets-status">${escapeHtml(state.catalog?.message || "Ready")}</div>
          <div id="markets-list" class="markets-list"></div>
        </section>
        <aside class="betslip-panel betslip-panel-root"></aside>
      </div>
    `;
    bindControls();
    renderMarkets();
    window.SEBetSlip?.render?.();
  }

  function bindControls() {
    qs("#markets-sport")?.addEventListener("change", (event) => {
      state.filters.sport = event.target.value;
      state.filters.market_group = "";
      renderShell();
      loadMarkets();
    });
    qs("#markets-book")?.addEventListener("change", (event) => {
      state.filters.sportsbook = event.target.value;
      loadMarkets();
    });
    qs("#markets-group")?.addEventListener("change", (event) => {
      state.filters.market_group = event.target.value;
      loadMarkets();
    });
    qs("#markets-team")?.addEventListener("input", debounce((event) => {
      state.filters.team = event.target.value.trim();
      loadMarkets();
    }, 350));
    qs("#markets-search")?.addEventListener("input", debounce((event) => {
      state.filters.query = event.target.value.trim();
      loadMarkets();
    }, 350));
    qs("#markets-refresh")?.addEventListener("click", loadMarkets);
  }

  function debounce(callback, wait) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => callback(...args), wait);
    };
  }

  function marketParams() {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(state.filters)) {
      if (value && key !== "query") params.set(key, value);
    }
    return params;
  }

  async function loadMarkets() {
    const status = qs("#markets-status");
    if (status) status.textContent = "Loading live sportsbook markets...";
    try {
      const params = marketParams();
      let payload;
      if (state.filters.query) {
        params.set("q", state.filters.query);
        payload = await fetchJson(`/api/markets/search?${params.toString()}`);
      } else {
        payload = await fetchJson(`/api/markets?${params.toString()}`);
      }
      state.markets = payload.markets || [];
      if (status) {
        const freshness = payload.data_freshness ? ` Last updated ${new Date(payload.data_freshness).toLocaleString()}.` : "";
        status.textContent = `${statusText(payload)}${freshness}`;
      }
      renderMarkets();
    } catch (error) {
      state.markets = [];
      if (status) status.textContent = error.message || "Live sportsbook provider not connected.";
      renderMarkets();
    }
  }

  function marketCard(market, index) {
    const odds = Number.isFinite(Number(market.odds)) ? `${Number(market.odds) > 0 ? "+" : ""}${market.odds}` : "n/a";
    const line = market.line !== null && market.line !== undefined ? ` · line ${market.line}` : "";
    const player = market.player_name ? `<span class="markets-pill">${escapeHtml(market.player_name)}</span>` : "";
    return `
      <article class="market-card">
        <div>
          <div class="market-title">${escapeHtml(market.selection)}</div>
          <div class="market-meta">${escapeHtml(market.sport)} · ${escapeHtml(market.sportsbook)} · ${escapeHtml(market.game)}${line}</div>
        </div>
        <div class="market-tags">
          <span class="markets-pill gold">${escapeHtml(market.market_group)}</span>
          ${player}
          <span class="markets-pill">${odds}</span>
        </div>
        <button class="add-market-leg" data-index="${index}" type="button">Add to slip</button>
      </article>
    `;
  }

  function renderMarkets() {
    const list = qs("#markets-list");
    if (!list) return;
    if (!state.markets.length) {
      list.innerHTML = `
        <div class="empty-market-state">
          <strong>No live markets loaded.</strong>
          <p>Live sportsbook provider not connected, the provider returned no matching props, or your API plan does not include this market. No fake odds are shown.</p>
        </div>
      `;
      return;
    }
    list.innerHTML = state.markets.slice(0, 80).map(marketCard).join("");
    document.querySelectorAll(".add-market-leg").forEach((button) => {
      button.addEventListener("click", () => {
        const market = state.markets[Number(button.dataset.index)];
        window.SEBetSlip?.addLeg?.(market);
      });
    });
  }

  async function init() {
    if (!qs(`#${rootId}`)) return;
    await loadCatalog();
    renderShell();
    await loadMarkets();
  }

  window.SEMarkets = { init, loadMarkets, state };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
