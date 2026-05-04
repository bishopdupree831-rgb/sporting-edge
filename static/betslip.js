(function () {
  const STORAGE_KEY = "sportingEdge.betslip";
  const state = {
    legs: loadLegs(),
    stake: 10,
    analysis: null,
    message: "Direct sportsbook connection not available. Copy betslip."
  };

  const qs = (selector) => document.querySelector(selector);
  const roots = () => Array.from(document.querySelectorAll("#betslip-panel-root, .betslip-panel-root"));
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));

  function loadLegs() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch {
      return [];
    }
  }

  function saveLegs() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.legs));
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Request failed: ${response.status}`);
    return payload;
  }

  function addLeg(leg) {
    if (!leg || !leg.selection || !leg.odds) return;
    const key = [leg.event_id, leg.market_group, leg.selection, leg.sportsbook].join("|");
    const exists = state.legs.some((item) => [item.event_id, item.market_group, item.selection, item.sportsbook].join("|") === key);
    if (!exists) state.legs.push(leg);
    saveLegs();
    analyze();
    render();
  }

  function removeLeg(index) {
    state.legs.splice(index, 1);
    saveLegs();
    analyze();
    render();
  }

  function payload() {
    return {
      legs: state.legs,
      stake: Number(state.stake || 10),
      sport: state.legs[0]?.sport || "Mixed",
      sportsbook: state.legs[0]?.sportsbook || "Mixed"
    };
  }

  async function analyze() {
    if (!state.legs.length) {
      state.analysis = null;
      render();
      return;
    }
    try {
      state.analysis = await postJson("/api/betslip/analyze", payload());
      state.message = state.analysis.verdict || "Betslip analyzed.";
    } catch (error) {
      state.message = error.message;
    }
    render();
  }

  async function exportSlip() {
    if (!state.legs.length) return;
    try {
      const exported = await postJson("/api/betslip/export", payload());
      state.analysis = exported;
      state.message = "Betslip export ready.";
      render();
    } catch (error) {
      state.message = error.message;
      render();
    }
  }

  async function sendToBook() {
    if (!state.legs.length) return;
    try {
      const response = await postJson("/api/betslip/send-to-book", payload());
      state.message = response.message || "Direct sportsbook connection not available. Copy betslip.";
      render();
    } catch (error) {
      state.message = error.message;
      render();
    }
  }

  async function copySlip() {
    const text = state.analysis?.plain_text || state.analysis?.export_text || formatLocalText();
    try {
      await navigator.clipboard.writeText(text);
      state.message = "Betslip copied. Verify every line before placing manually.";
    } catch {
      state.message = "Copy failed. Select the export text manually.";
    }
    render();
  }

  function formatLocalText() {
    return [
      "Sporting Edge Betslip",
      ...state.legs.map((leg, index) => `${index + 1}. ${leg.selection} (${leg.sportsbook} ${Number(leg.odds) > 0 ? "+" : ""}${leg.odds})`),
      "",
      "Direct sportsbook connection not available. Copy betslip."
    ].join("\n");
  }

  function metric(label, value) {
    return `<div class="betslip-metric"><span>${label}</span><strong>${escapeHtml(value ?? "n/a")}</strong></div>`;
  }

  function renderLeg(leg, index) {
    const odds = Number(leg.odds) > 0 ? `+${leg.odds}` : leg.odds;
    return `
      <div class="betslip-leg">
        <button class="remove-slip-leg" data-index="${index}" type="button">x</button>
        <strong>${escapeHtml(leg.selection)}</strong>
        <span>${escapeHtml(leg.sport)} · ${escapeHtml(leg.sportsbook)} · ${escapeHtml(leg.market_group)} · ${escapeHtml(odds)}</span>
      </div>
    `;
  }

  function render() {
    const panels = roots();
    if (!panels.length) return;
    const analysis = state.analysis || {};
    const markup = `
      <div class="betslip-head">
        <div>
          <p class="markets-kicker">Safe manual placement</p>
          <h2>Betslip Builder</h2>
        </div>
        <span class="markets-pill gold">${state.legs.length} legs</span>
      </div>
      <label class="betslip-stake">
        Stake
        <input id="betslip-stake" type="number" min="1" step="1" value="${escapeHtml(state.stake)}" />
      </label>
      <div class="betslip-legs">
        ${state.legs.length ? state.legs.map(renderLeg).join("") : `<div class="empty-market-state">Add markets from the left to build a slip.</div>`}
      </div>
      <div class="betslip-metrics">
        ${metric("Combined odds", analysis.combined_odds)}
        ${metric("Implied probability", analysis.implied_probability != null ? `${Math.round(analysis.implied_probability * 1000) / 10}%` : "n/a")}
        ${metric("Model probability", analysis.model_probability != null ? `${Math.round(analysis.model_probability * 1000) / 10}%` : "needs model")}
        ${metric("EV", analysis.expected_value != null ? `$${Number(analysis.expected_value).toFixed(2)}` : "needs model")}
        ${metric("Edge score", analysis.edge_score ?? "n/a")}
      </div>
      <div class="betslip-warning">${escapeHtml(state.message || "Direct sportsbook connection not available. Copy betslip.")}</div>
      ${(analysis.warnings || []).map((warning) => `<div class="betslip-warning soft">${escapeHtml(warning)}</div>`).join("")}
      <div class="betslip-actions">
        <button id="betslip-analyze" type="button">Analyze</button>
        <button id="betslip-copy" type="button">Copy slip</button>
        <button id="betslip-export" type="button">Export</button>
        <button id="betslip-send" type="button">Send to book</button>
      </div>
      <div class="book-links">
        ${analysis.draftkings_link ? `<a href="${escapeHtml(analysis.draftkings_link)}" target="_blank" rel="noopener">Open DraftKings</a>` : ""}
        ${analysis.fanduel_link ? `<a href="${escapeHtml(analysis.fanduel_link)}" target="_blank" rel="noopener">Open FanDuel</a>` : ""}
      </div>
      ${analysis.plain_text ? `<textarea class="betslip-export" readonly>${escapeHtml(analysis.plain_text)}</textarea>` : ""}
    `;
    panels.forEach((root) => {
      root.innerHTML = markup;
    });
    bind();
  }

  function bind() {
    document.querySelectorAll("#betslip-stake").forEach((input) => input.addEventListener("input", (event) => {
      state.stake = Number(event.target.value || 10);
    }));
    document.querySelectorAll("#betslip-analyze").forEach((button) => button.addEventListener("click", analyze));
    document.querySelectorAll("#betslip-copy").forEach((button) => button.addEventListener("click", copySlip));
    document.querySelectorAll("#betslip-export").forEach((button) => button.addEventListener("click", exportSlip));
    document.querySelectorAll("#betslip-send").forEach((button) => button.addEventListener("click", sendToBook));
    document.querySelectorAll(".remove-slip-leg").forEach((button) => {
      button.addEventListener("click", () => removeLeg(Number(button.dataset.index)));
    });
  }

  window.SEBetSlip = { addLeg, removeLeg, analyze, exportSlip, render, state };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
}());
