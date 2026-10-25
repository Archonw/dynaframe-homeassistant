/*
 * Dynaframe store card – download numbers of the packs in a DynaFrame Pro store.
 * Served by the dynaframe integration, no resource setup needed.
 *
 *   type: custom:dynaframe-store-card
 *   title: Store-Downloads                     # optional
 *   repo: owner/my-dynaframe-store             # required, GitHub repo with the releases
 *   entity: sensor.store_downloads_total       # optional, total sensor for "downloads per day"
 *   days: 30                                   # optional
 *
 * Total and per-pack numbers come straight from the GitHub releases API (cached for an hour),
 * so new packs show up without any configuration. GitHub only reports running totals, so the
 * per-day chart needs a history: it reads the long-term statistics of the total sensor.
 */

const STORE_CARD_VERSION = "1.2.1";
const REPO_RE = /^[\w.-]+\/[\w.-]+$/;
const CACHE_MS = 60 * 60 * 1000;
const STATS_MS = 15 * 60 * 1000;

const tr = (hass, de, en) => ((hass?.locale?.language || hass?.language || "en").startsWith("de") ? de : en);

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// "playlist-button-1.6.3" -> "playlist-button", "Playlist Button 1.6.3" -> "Playlist Button"
const packId = (tag) => tag.replace(/-v?\d[\w.+-]*$/, "");
const packName = (name, fallback) => (name || fallback).replace(/\s+v?\d[\w.+-]*$/, "").trim() || fallback;

/** Releases are shared by every card on the page and kept across reloads for an hour. */
const releaseCache = new Map();

async function fetchReleases(repo) {
  const releases = [];
  for (let page = 1; page <= 10; page++) {
    const res = await fetch(`https://api.github.com/repos/${repo}/releases?per_page=100&page=${page}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!res.ok) {
      const reset = res.headers.get("x-ratelimit-reset");
      const err = new Error(`GitHub ${res.status}`);
      err.retryAt = res.status === 403 && reset ? Number(reset) * 1000 : 0;
      throw err;
    }
    const batch = await res.json();
    releases.push(...batch);
    if (batch.length < 100) break;
  }
  return releases;
}

function summarize(releases) {
  const packs = new Map();
  for (const r of releases) {
    if (r.draft) continue;
    const id = packId(r.tag_name);
    const n = (r.assets || []).reduce((sum, a) => sum + (a.download_count || 0), 0);
    const pack = packs.get(id);
    if (pack) {
      pack.n += n;
      pack.releases += 1;
    } else {
      // The API lists newest first, so the first release names the pack and its version.
      packs.set(id, { id, name: packName(r.name, id), version: r.tag_name.slice(id.length + 1), n, releases: 1 });
    }
  }
  const rows = [...packs.values()].sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
  return { rows, total: rows.reduce((s, p) => s + p.n, 0), fetched: Date.now() };
}

function loadStore(repo, force = false) {
  const key = `dynaframe-store:${repo}`;
  let entry = releaseCache.get(repo);
  if (!entry) {
    entry = {};
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "null");
      if (saved?.rows) entry.data = saved;
    } catch (_) {
      // Storage blocked or garbage; fetch fresh.
    }
    releaseCache.set(repo, entry);
  }
  const fresh = entry.data && Date.now() - entry.data.fetched < CACHE_MS;
  if (entry.pending || (fresh && !force) || (entry.retryAt && Date.now() < entry.retryAt)) {
    return entry.pending || Promise.resolve(entry);
  }
  entry.pending = fetchReleases(repo)
    .then((releases) => {
      entry.data = summarize(releases);
      entry.error = undefined;
      entry.retryAt = 0;
      try {
        localStorage.setItem(key, JSON.stringify(entry.data));
      } catch (_) {
        // Only a convenience cache.
      }
    })
    .catch((err) => {
      entry.error = err.message;
      entry.retryAt = err.retryAt || Date.now() + 5 * 60 * 1000;
    })
    .then(() => {
      entry.pending = undefined;
      return entry;
    });
  return entry.pending;
}

const STORE_STYLE = `
  :host { display: block; }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px 0; gap: 8px; }
  .header h2 { margin: 0; font-size: 1.15rem; font-weight: 500; color: var(--primary-text-color); }
  .refresh { border: none; background: none; color: var(--secondary-text-color); cursor: pointer;
             border-radius: 50%; width: 36px; height: 36px; display: grid; place-items: center; }
  .refresh:hover { background: var(--secondary-background-color); }
  .refresh.busy ha-icon { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .body { padding: 8px 16px 16px; }
  .total { display: flex; align-items: center; gap: 14px; padding: 4px 0 12px; }
  .total .icon { width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center; flex: none;
                 background: rgba(var(--rgb-primary-color, 3, 169, 244), .15); color: var(--primary-color); }
  .total .n { font-size: 2rem; font-weight: 500; line-height: 1.1; color: var(--primary-text-color); }
  .total .label { font-size: .85rem; color: var(--secondary-text-color); }
  h3 { margin: 12px 0 6px; font-size: .8rem; font-weight: 500; text-transform: uppercase; letter-spacing: .04em;
       color: var(--secondary-text-color); }
  table { width: 100%; border-collapse: collapse; font-size: .9rem; }
  td { padding: 5px 0; border-top: 1px solid var(--divider-color); vertical-align: middle; }
  td.rank { width: 1.8em; color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
  td.name { color: var(--primary-text-color); }
  td.name .ver { color: var(--secondary-text-color); font-size: .78rem; margin-left: 4px; }
  td.n { text-align: right; font-weight: 500; color: var(--primary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; padding-left: 10px; }
  .meter { height: 3px; border-radius: 2px; background: var(--primary-color); opacity: .45; margin-top: 3px; }
  .chart svg { display: block; width: 100%; height: 120px; overflow: visible; }
  .chart rect.bar { fill: var(--primary-color); }
  .chart rect.bar.zero { fill: var(--divider-color); }
  .chart text { fill: var(--secondary-text-color); font-size: 10px; }
  .chart .grid { stroke: var(--divider-color); stroke-width: 1; }
  .axis { display: flex; justify-content: space-between; font-size: .75rem; color: var(--secondary-text-color); margin-top: 4px; }
  .hint { font-size: .85rem; color: var(--secondary-text-color); padding: 6px 0; }
  .hint code { font-size: .8rem; }
  .foot { font-size: .75rem; color: var(--secondary-text-color); margin-top: 10px; }
  .error { color: var(--error-color, #db4437); }
`;

class DynaframeStoreCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("dynaframe-store-card-editor");
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    const repo = String(config.repo || "").trim().replace(/^https:\/\/github\.com\//, "").replace(/\/+$/, "");
    this._config = { days: 30, ...config, repo: REPO_RE.test(repo) ? repo : "" };
    this._entry = undefined;
    this._rowsKey = undefined;
    this._days = Math.max(7, Math.min(365, Number(this._config.days) || 30));
    this._statsAt = 0;
    this._stats = undefined;
    this._render();
    if (this.isConnected) this._load();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._render();
    const st = hass.states[this._config?.entity];
    // A new sensor value means new statistics will follow; re-read them now and then.
    if (st && st.state !== this._lastState) {
      this._lastState = st.state;
      this._statsAt = Math.min(this._statsAt, Date.now() - STATS_MS + 60 * 1000);
    }
    this._loadStats();
    this._update();
  }

  getCardSize() {
    return 3 + Math.ceil((this._entry?.data?.rows.length || 6) / 2);
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  connectedCallback() {
    this._load();
    this._timer = setInterval(() => this._load(), 10 * 60 * 1000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  async _load(force = false) {
    if (!this._config?.repo) return;
    const repo = this._config.repo;
    const cached = releaseCache.get(repo);
    if (cached) this._entry = cached;
    this._busy = true;
    this._update();
    const entry = await loadStore(repo, force);
    if (repo !== this._config.repo) return;
    this._entry = entry;
    this._busy = false;
    this._update();
  }

  async _loadStats() {
    const id = this._config?.entity;
    if (!this._hass || !id || !this._hass.states[id] || this._statsPending) return;
    if (Date.now() - this._statsAt < STATS_MS) return;
    this._statsPending = true;
    this._statsAt = Date.now();
    const end = new Date();
    const start = new Date(end);
    start.setHours(0, 0, 0, 0);
    start.setDate(start.getDate() - (this._days - 1));
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        statistic_ids: [id],
        period: "day",
        types: ["change"],
      });
      const byDay = new Map();
      for (const s of res[id] || []) {
        const d = new Date(s.start);
        byDay.set(d.toDateString(), Math.max(0, Math.round(s.change || 0)));
      }
      const days = [];
      for (let i = 0; i < this._days; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        days.push({ date: d, n: byDay.get(d.toDateString()) ?? 0, known: byDay.has(d.toDateString()) });
      }
      this._stats = { days, recorded: byDay.size > 0 };
      this._statsError = undefined;
    } catch (err) {
      this._statsError = err?.message || String(err);
    }
    this._statsPending = false;
    this._update();
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const hass = this._hass;
    const title = this._config.title ?? tr(hass, "Store-Downloads", "Store downloads");
    this.shadowRoot.innerHTML = `
      <style>${STORE_STYLE}</style>
      <ha-card>
        <div class="header">
          <h2>${esc(title)}</h2>
          <button class="refresh" ${this._config.repo ? "" : "hidden"} title="${esc(tr(hass, "Jetzt aktualisieren", "Refresh now"))}">
            <ha-icon icon="mdi:refresh"></ha-icon>
          </button>
        </div>
        <div class="body setup" ${this._config.repo ? "hidden" : ""}>
          <div class="hint">${tr(
            hass,
            "Trag in den Karteneinstellungen das GitHub-Repo deines Stores ein, z. B. <code>name/mein-store</code>.",
            "Enter your store's GitHub repo in the card settings, e.g. <code>name/my-store</code>.",
          )}</div>
        </div>
        <div class="body" ${this._config.repo ? "" : "hidden"}>
          <div class="total">
            <div class="icon"><ha-icon icon="mdi:storefront"></ha-icon></div>
            <div><div class="n">–</div><div class="label">${esc(tr(hass, "Downloads gesamt", "Total downloads"))}</div></div>
          </div>
          <h3>${esc(tr(hass, "Downloads pro Pack", "Downloads per pack"))}</h3>
          <table><tbody class="rows"></tbody></table>
          <div class="hint packs-hint"></div>
          <h3>${esc(tr(hass, `Downloads pro Tag (${this._days} Tage)`, `Downloads per day (${this._days} days)`))}</h3>
          <div class="chart"></div>
          <div class="foot"></div>
        </div>
      </ha-card>`;
    this.shadowRoot.querySelector(".refresh").addEventListener("click", () => {
      this._statsAt = 0;
      this._loadStats();
      this._load(true);
    });
    this._update();
  }

  _update() {
    const root = this.shadowRoot;
    if (!root || !this._config) return;
    const hass = this._hass;
    const lang = hass?.locale?.language || hass?.language || navigator.language;
    const num = (n) => Number(n).toLocaleString(lang);
    const data = this._entry?.data;
    const error = this._entry?.error;

    root.querySelector(".refresh").classList.toggle("busy", !!this._busy);
    root.querySelector(".total .n").textContent = data ? num(data.total) : "–";

    const rows = data?.rows || [];
    const max = rows[0]?.n || 1;
    const rowsKey = JSON.stringify(rows.map((r) => [r.id, r.n, r.version]));
    if (rowsKey !== this._rowsKey) {
      this._rowsKey = rowsKey;
      root.querySelector(".rows").innerHTML = rows
        .map(
          (r, i) => `
          <tr>
            <td class="rank">${i + 1}</td>
            <td class="name">${esc(r.name)}<span class="ver">${esc(r.version)}</span>
              <div class="meter" style="width:${Math.max(2, (r.n / max) * 100)}%"></div></td>
            <td class="n">${num(r.n)}</td>
          </tr>`,
        )
        .join("");
    }
    const packsHint = root.querySelector(".packs-hint");
    packsHint.hidden = !!data && !error;
    packsHint.classList.toggle("error", !!error);
    packsHint.textContent = error
      ? tr(hass, `GitHub nicht erreichbar (${error}). Neuer Versuch in ein paar Minuten.`, `GitHub unreachable (${error}). Retrying in a few minutes.`)
      : tr(hass, "Lade Releases …", "Loading releases …");

    this._updateChart(hass, lang);

    root.querySelector(".foot").textContent = data
      ? tr(hass, "Stand", "As of") +
        " " +
        new Date(data.fetched).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" }) +
        " · " +
        this._config.repo
      : "";
  }

  _updateChart(hass, lang) {
    const chart = this.shadowRoot.querySelector(".chart");
    const id = this._config.entity;
    if (!id || !hass?.states[id]) {
      chart.innerHTML = `<div class="hint">${
        id
          ? tr(hass, `Sensor <code>${esc(id)}</code> nicht gefunden.`, `Sensor <code>${esc(id)}</code> not found.`)
          : tr(
              hass,
              `GitHub liefert nur Gesamtzahlen. Für den Tagesverlauf in den Karteneinstellungen einen Sensor mit den
               Gesamt-Downloads (<code>state_class: total_increasing</code>) wählen, Anleitung in der README.`,
              `GitHub only reports totals. For the daily chart, pick a sensor with the total downloads
               (<code>state_class: total_increasing</code>) in the card settings, see the README.`,
            )
      }</div>`;
      this._chartKey = undefined;
      return;
    }
    if (this._statsError) {
      chart.innerHTML = `<div class="hint error">${esc(this._statsError)}</div>`;
      this._chartKey = undefined;
      return;
    }
    if (!this._stats) {
      chart.innerHTML = `<div class="hint">${tr(hass, "Lade Statistik …", "Loading statistics …")}</div>`;
      return;
    }
    const { days, recorded } = this._stats;
    const key = JSON.stringify(days.map((d) => d.n));
    if (key === this._chartKey) return;
    this._chartKey = key;
    if (!recorded) {
      chart.innerHTML = `<div class="hint">${tr(
        hass,
        "Noch keine Tageswerte. Home Assistant schreibt die Statistik stündlich, der erste Balken erscheint im Lauf des Tages.",
        "No daily values yet. Home Assistant writes statistics hourly, the first bar shows up later today.",
      )}</div>`;
      return;
    }
    const W = 300;
    const H = 110;
    const peak = Math.max(1, ...days.map((d) => d.n));
    const slot = W / days.length;
    const gap = Math.min(2, slot * 0.25);
    const fmtDay = (d) => d.toLocaleDateString(lang, { day: "numeric", month: "short" });
    const bars = days
      .map((d) => {
        const h = d.n ? Math.max(2, (d.n / peak) * (H - 14)) : 1.5;
        return `<rect class="bar${d.n ? "" : " zero"}" x="${(slot * days.indexOf(d) + gap / 2).toFixed(2)}"
          y="${(H - h).toFixed(2)}" width="${(slot - gap).toFixed(2)}" height="${h.toFixed(2)}" rx="1">
          <title>${esc(fmtDay(d.date))}: ${Number(d.n).toLocaleString(lang)}${d.known ? "" : " (–)"}</title></rect>`;
      })
      .join("");
    const sum = days.reduce((s, d) => s + d.n, 0);
    chart.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img"
           aria-label="${esc(tr(hass, "Downloads pro Tag", "Downloads per day"))}">
        <line class="grid" x1="0" x2="${W}" y1="14" y2="14" vector-effect="non-scaling-stroke"></line>
        <line class="grid" x1="0" x2="${W}" y1="${H}" y2="${H}" vector-effect="non-scaling-stroke"></line>
        ${bars}
      </svg>
      <div class="axis">
        <span>${esc(fmtDay(days[0].date))}</span>
        <span>${esc(tr(hass, `max. ${peak.toLocaleString(lang)}/Tag · ${sum.toLocaleString(lang)} im Zeitraum`,
          `max ${peak.toLocaleString(lang)}/day · ${sum.toLocaleString(lang)} in range`))}</span>
        <span>${esc(tr(hass, "heute", "today"))}</span>
      </div>`;
  }
}

class DynaframeStoreCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._renderForm();
  }

  set hass(hass) {
    this._hass = hass;
    this._renderForm();
  }

  _renderForm() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) =>
        ({
          title: tr(this._hass, "Titel", "Title"),
          repo: tr(this._hass, "GitHub-Repo des Stores (name/repo)", "Store GitHub repo (owner/repo)"),
          entity: tr(this._hass, "Gesamt-Sensor für Downloads pro Tag", "Total sensor for downloads per day"),
          days: tr(this._hass, "Tage im Diagramm", "Days in chart"),
        })[s.name];
      this._form.addEventListener("value-changed", (e) => {
        const config = { ...e.detail.value };
        for (const k of ["title", "repo", "entity"]) if (!config[k]) delete config[k];
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { days: 30, ...this._config };
    this._form.schema = [
      { name: "title", selector: { text: {} } },
      { name: "repo", required: true, selector: { text: {} } },
      { name: "entity", selector: { entity: { domain: "sensor" } } },
      { name: "days", selector: { number: { min: 7, max: 365, mode: "box" } } },
    ];
  }
}

// Same re-registration guard as the main card: scoped-registry polyfills can drop definitions.
function registerDynaframeStoreCard() {
  if (!customElements.get("dynaframe-store-card")) customElements.define("dynaframe-store-card", DynaframeStoreCard);
  if (!customElements.get("dynaframe-store-card-editor"))
    customElements.define("dynaframe-store-card-editor", DynaframeStoreCardEditor);
}

registerDynaframeStoreCard();
setInterval(registerDynaframeStoreCard, 2000);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "dynaframe-store-card")) {
  window.customCards.push({
    type: "dynaframe-store-card",
    name: "Dynaframe Store-Downloads",
    description: (navigator.language || "").startsWith("de")
      ? "Downloads der Packs aus deinem DynaFrame-Pro-Store auf GitHub: gesamt, pro Pack und pro Tag"
      : "Downloads of the packs in your DynaFrame Pro store on GitHub: total, per pack and per day",
    preview: true,
    documentationURL: "https://github.com/Archonw/dynaframe-homeassistant#store-downloads-card",
  });
  console.info(`%c DYNAFRAME-STORE-CARD %c ${STORE_CARD_VERSION} `, "background:#03a9f4;color:#fff", "");
}
