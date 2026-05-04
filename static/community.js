(function () {
  const state = { sport: "", market_type: "", confidence: "", sort: "newest", openPost: null };

  async function api(path, options = {}) {
    const response = await fetch(path, { cache: "no-store", ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.error || "Request failed");
    return data;
  }

  function post(path, body) {
    return api(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  }

  function qs() {
    const params = new URLSearchParams();
    Object.entries(state).forEach(([key, value]) => {
      if (["sport", "market_type", "confidence", "sort"].includes(key) && value) params.set(key, value);
    });
    return params.toString();
  }

  function resultClass(result) {
    return `community-result ${result || "pending"}`;
  }

  function postCard(item) {
    return `
      <article class="community-post" data-post-id="${item.id}">
        <div class="community-votes">
          <button type="button" data-vote="up" data-post="${item.id}">▲</button>
          <strong>${item.score}</strong>
          <button type="button" data-vote="down" data-post="${item.id}">▼</button>
        </div>
        <div class="community-post-body">
          <div class="community-post-top">
            <span>${item.sport}</span>
            <small>${item.market_type} - ${item.sportsbook} - ${item.odds}</small>
            <b class="${resultClass(item.result)}">${item.result}</b>
          </div>
          <h3>${item.pick}</h3>
          <p>${item.matchup} - confidence ${item.confidence} - ${item.units}u</p>
          <p>${item.reasoning.slice(0, 220)}${item.reasoning.length > 220 ? "..." : ""}</p>
          <div class="community-meta">
            <button type="button" data-expand="${item.id}">${item.comments_count} comments</button>
            <select data-grade="${item.id}">
              <option value="pending" ${item.result === "pending" ? "selected" : ""}>pending</option>
              <option value="win" ${item.result === "win" ? "selected" : ""}>win</option>
              <option value="loss" ${item.result === "loss" ? "selected" : ""}>loss</option>
              <option value="push" ${item.result === "push" ? "selected" : ""}>push</option>
            </select>
          </div>
          <div id="community-comments-${item.id}" class="community-comments"></div>
        </div>
      </article>
    `;
  }

  function shell(root) {
    root.innerHTML = `
      <section class="community-shell">
        <div class="community-head">
          <div>
            <p>Community Picks</p>
            <h2>Share picks, debate plays, and track results.</h2>
          </div>
          <div id="community-record" class="community-record">0-0-0 · +0.0 units</div>
        </div>
        <div class="community-grid">
          <form id="community-form" class="community-form">
            <h3>Create pick post</h3>
            <div class="community-form-grid">
              <label>Username<input id="cp-username" value="Guest" maxlength="40" /></label>
              <label>Sport<select id="cp-sport"><option>NBA</option><option>NFL</option><option>MLB</option><option>NHL</option><option>MMA</option></select></label>
              <label>Matchup<input id="cp-matchup" required placeholder="Knicks vs Hawks" /></label>
              <label>Pick<input id="cp-pick" required placeholder="Jalen Brunson over 6.5 assists" /></label>
              <label>Odds<input id="cp-odds" required type="number" value="-115" /></label>
              <label>Sportsbook<input id="cp-book" placeholder="DraftKings" /></label>
              <label>Market type<select id="cp-market"><option>Player Prop</option><option>Team Prop</option><option>Moneyline</option><option>Spread</option><option>Total</option><option>Live Bet</option><option>Future</option></select></label>
              <label>Confidence<select id="cp-confidence"><option>A+</option><option>A</option><option>A-</option><option>B+</option><option>B</option><option>C</option><option>PASS</option></select></label>
              <label>Units<input id="cp-units" type="number" min="0.1" max="100" step="0.25" value="1" /></label>
            </div>
            <label>Reasoning<textarea id="cp-reasoning" maxlength="1500" placeholder="Hit this in 7 of last 10..."></textarea></label>
            <button type="submit">Post pick</button>
          </form>
          <div class="community-feed-wrap">
            <div class="community-filters">
              <select id="cf-sport"><option value="">All sports</option><option>NBA</option><option>NFL</option><option>MLB</option><option>NHL</option><option>MMA</option></select>
              <select id="cf-market"><option value="">All markets</option><option>Player Prop</option><option>Team Prop</option><option>Moneyline</option><option>Spread</option><option>Total</option><option>Live Bet</option><option>Future</option></select>
              <select id="cf-confidence"><option value="">All confidence</option><option>A+</option><option>A</option><option>A-</option><option>B+</option><option>B</option><option>C</option><option>PASS</option></select>
              <select id="cf-sort"><option value="newest">Newest</option><option value="top">Top</option><option value="most_discussed">Most discussed</option></select>
            </div>
            <div id="community-feed" class="community-feed"></div>
          </div>
        </div>
      </section>
    `;
  }

  async function loadFeed() {
    const feed = document.getElementById("community-feed");
    if (!feed) return;
    feed.innerHTML = "<p>Loading community picks...</p>";
    try {
      const data = await api(`/api/community/posts?${qs()}`);
      document.getElementById("community-record").textContent = `${data.record.label} · ${data.record.units_label}`;
      feed.innerHTML = data.posts.length ? data.posts.map(postCard).join("") : "<p>No picks yet. Be first to post.</p>";
      bindFeed();
    } catch (error) {
      feed.innerHTML = `<p>${error.message}</p>`;
    }
  }

  async function expandPost(postId) {
    const box = document.getElementById(`community-comments-${postId}`);
    if (!box) return;
    if (box.dataset.open === "true") {
      box.innerHTML = "";
      box.dataset.open = "false";
      return;
    }
    const postData = await api(`/api/community/posts/${postId}`);
    box.dataset.open = "true";
    box.innerHTML = `
      <div class="community-comment-list">
        ${(postData.comments || []).map((comment) => `<p><strong>${comment.username}</strong> ${comment.comment}</p>`).join("") || "<p>No comments yet.</p>"}
      </div>
      <form class="community-comment-form" data-comment-form="${postId}">
        <input name="username" placeholder="Username" value="Guest" />
        <input name="comment" placeholder="Add a comment" required />
        <button type="submit">Comment</button>
      </form>
    `;
    box.querySelector("[data-comment-form]")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      await post(`/api/community/posts/${postId}/comments`, {
        username: form.get("username"),
        comment: form.get("comment")
      });
      box.dataset.open = "false";
      expandPost(postId);
      loadFeed();
    });
  }

  function bindFeed() {
    document.querySelectorAll("[data-vote]").forEach((button) => {
      button.addEventListener("click", async () => {
        const username = window.prompt("Username for vote?", "Guest") || "Guest";
        await post(`/api/community/posts/${button.dataset.post}/vote`, { username, vote: button.dataset.vote });
        loadFeed();
      });
    });
    document.querySelectorAll("[data-expand]").forEach((button) => {
      button.addEventListener("click", () => expandPost(button.dataset.expand));
    });
    document.querySelectorAll("[data-grade]").forEach((select) => {
      select.addEventListener("change", async () => {
        await post(`/api/community/posts/${select.dataset.grade}/grade`, { result: select.value });
        loadFeed();
      });
    });
  }

  function bindShell() {
    document.getElementById("community-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      await post("/api/community/posts", {
        username: document.getElementById("cp-username").value,
        sport: document.getElementById("cp-sport").value,
        matchup: document.getElementById("cp-matchup").value,
        pick: document.getElementById("cp-pick").value,
        odds: Number(document.getElementById("cp-odds").value),
        sportsbook: document.getElementById("cp-book").value || "Unknown",
        market_type: document.getElementById("cp-market").value,
        confidence: document.getElementById("cp-confidence").value,
        units: Number(document.getElementById("cp-units").value),
        reasoning: document.getElementById("cp-reasoning").value,
        tags: [document.getElementById("cp-sport").value, document.getElementById("cp-market").value]
      });
      event.currentTarget.reset();
      document.getElementById("cp-username").value = "Guest";
      loadFeed();
    });
    [["cf-sport", "sport"], ["cf-market", "market_type"], ["cf-confidence", "confidence"], ["cf-sort", "sort"]].forEach(([id, key]) => {
      document.getElementById(id)?.addEventListener("change", (event) => {
        state[key] = event.target.value;
        loadFeed();
      });
    });
  }

  function init() {
    const root = document.getElementById("community-picks-root");
    if (!root) return;
    shell(root);
    bindShell();
    loadFeed();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
