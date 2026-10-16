/*
 * Dynaframe card – served by the dynaframe integration, no resource setup needed.
 *
 *   type: custom:dynaframe-card
 *   entities:            # optional, defaults to every Dynaframe
 *     - media_player.dynaframe_fenster
 *   title: Bilderrahmen  # optional
 *   show_preview: true   # optional
 */

const CARD_VERSION = "1.1.1";

const t = (hass, de, en) => ((hass?.locale?.language || hass?.language || "en").startsWith("de") ? de : en);

const STATE_LABEL = {
  playing: ["Läuft", "Playing"],
  paused: ["Pausiert", "Paused"],
  idle: ["Gestoppt", "Stopped"],
  off: ["Bildschirm aus", "Display off"],
  unavailable: ["Nicht erreichbar", "Unavailable"],
};

function dynaframePlayers(hass) {
  return Object.values(hass.entities || {})
    .filter((e) => e.platform === "dynaframe" && e.entity_id.startsWith("media_player."))
    .map((e) => e.entity_id)
    .sort();
}

/** Sibling entity of the same device, found by its translation key. */
function sibling(hass, playerId, domain, key) {
  const player = hass.entities?.[playerId];
  if (!player?.device_id) return undefined;
  return Object.values(hass.entities).find(
    (e) =>
      e.device_id === player.device_id &&
      e.platform === "dynaframe" &&
      e.translation_key === key &&
      e.entity_id.startsWith(domain + "."),
  )?.entity_id;
}

const STYLE = `
  :host { display: block; }
  [hidden] { display: none !important; }
  ha-card { overflow: hidden; }
  .header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px 0; gap: 8px; }
  .header h2 { margin: 0; font-size: 1.15rem; font-weight: 500; color: var(--primary-text-color); }
  .tabs { display: flex; gap: 6px; flex-wrap: wrap; padding: 12px 16px 0; }
  .tab { border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color);
         border-radius: 999px; padding: 5px 12px; font: inherit; font-size: .85rem; cursor: pointer;
         display: inline-flex; align-items: center; gap: 6px; }
  .tab .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--disabled-color, #9e9e9e); }
  .tab .dot.playing { background: var(--success-color, #43a047); }
  .tab .dot.paused { background: var(--warning-color, #ffa000); }
  .tab[aria-selected="true"] { background: var(--primary-color); border-color: var(--primary-color);
         color: var(--text-primary-color, #fff); }
  .tab[aria-selected="true"] .dot { box-shadow: 0 0 0 2px var(--text-primary-color, #fff); }
  .body { padding: 12px 16px 16px; }
  .preview { position: relative; border-radius: 12px; overflow: hidden; aspect-ratio: 16 / 9;
             background: linear-gradient(135deg, var(--secondary-background-color), var(--card-background-color)); }
  .preview img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
                 transition: opacity .4s ease; }
  .preview .empty { position: absolute; inset: 0; display: grid; place-items: center;
                    color: var(--secondary-text-color); }
  .preview .empty ha-icon { --mdc-icon-size: 48px; opacity: .5; }
  .preview .shade { position: absolute; inset: auto 0 0 0; padding: 32px 14px 12px;
                    background: linear-gradient(transparent, rgba(0,0,0,.72)); color: #fff; }
  .preview .title { font-size: 1.05rem; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .preview .sub { font-size: .8rem; opacity: .85; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pill { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,.55); color: #fff;
          border-radius: 999px; padding: 3px 10px; font-size: .75rem; backdrop-filter: blur(4px); }
  .power { position: absolute; top: 8px; right: 8px; }
  .round { width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer; display: grid;
           place-items: center; background: rgba(0,0,0,.55); color: #fff; backdrop-filter: blur(4px); }
  .round.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .controls { display: flex; justify-content: center; align-items: center; gap: 18px; margin: 14px 0 6px; }
  .ctrl { border: none; background: none; color: var(--primary-text-color); cursor: pointer;
          border-radius: 50%; width: 44px; height: 44px; display: grid; place-items: center; }
  .ctrl:hover { background: var(--secondary-background-color); }
  .ctrl.main { width: 58px; height: 58px; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .ctrl.main ha-icon { --mdc-icon-size: 32px; }
  .ctrl.active { color: var(--primary-color); }
  .ctrl:disabled { opacity: .35; cursor: default; }
  .row { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
  .row ha-icon { color: var(--secondary-text-color); flex: none; }
  .row label { font-size: .9rem; color: var(--primary-text-color); flex: 1; }
  input[type=range] { flex: 1; accent-color: var(--primary-color); min-width: 0; }
  select, input[type=number] { font: inherit; color: var(--primary-text-color); background: var(--secondary-background-color);
           border: 1px solid var(--divider-color); border-radius: 8px; padding: 6px 8px; }
  select { flex: 1; min-width: 0; }
  input[type=number] { width: 72px; text-align: right; }
  .muted { color: var(--secondary-text-color); font-size: .8rem; min-width: 34px; text-align: right; }
  .iconbtn { border: none; background: none; cursor: pointer; padding: 0; color: var(--secondary-text-color); display: grid; }
  .none { padding: 24px 16px; color: var(--secondary-text-color); }
  .row label.toggle { position: relative; width: 40px; height: 22px; flex: none; }
  .pl-toggle { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; font: inherit; cursor: pointer;
               color: var(--primary-text-color); background: var(--secondary-background-color);
               border: 1px solid var(--divider-color); border-radius: 8px; padding: 6px 8px; text-align: left; }
  .pl-toggle .pl-label { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pl-toggle .chev { color: var(--secondary-text-color); transition: transform .2s; }
  .pl-toggle[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .pl-panel { margin: 8px 0 0 34px; border: 1px solid var(--divider-color); border-radius: 10px; padding: 6px; }
  .pl-list { max-height: 220px; overflow-y: auto; }
  .pl-item { display: flex; align-items: center; gap: 10px; padding: 7px 8px; border-radius: 8px; cursor: pointer;
             color: var(--primary-text-color); }
  .pl-item:hover { background: var(--secondary-background-color); }
  .pl-item input { width: 18px; height: 18px; accent-color: var(--primary-color); margin: 0; flex: none; }
  .pl-item span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pl-item.active span::after { content: " •"; color: var(--primary-color); }
  .pl-actions { display: flex; gap: 8px; align-items: center; padding: 8px 4px 2px; }
  .pl-actions .hint { flex: 1; font-size: .8rem; color: var(--secondary-text-color); }
  .pl-actions button { font: inherit; border-radius: 8px; padding: 6px 12px; cursor: pointer; border: none; }
  .pl-play { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .pl-play:disabled { opacity: .4; cursor: default; }
  .pl-cancel { background: none; color: var(--primary-text-color); }
  .settings-toggle { display: flex; align-items: center; gap: 10px; width: 100%; margin-top: 14px;
                     padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 10px;
                     background: none; color: var(--primary-text-color); font: inherit; cursor: pointer; }
  .settings-toggle:hover { background: var(--secondary-background-color); }
  .settings-toggle ha-icon { color: var(--secondary-text-color); }
  .settings-toggle .label { flex: 1; text-align: left; }
  .settings-toggle .summary { color: var(--secondary-text-color); font-size: .8rem; white-space: nowrap;
                              overflow: hidden; text-overflow: ellipsis; max-width: 45%; }
  .settings-toggle .chev { transition: transform .2s; }
  .settings-toggle[aria-expanded="true"] .chev { transform: rotate(180deg); }
  .settings { padding: 2px 4px 0; }
  .settings .row:first-child { margin-top: 8px; }
  .settings .unit { color: var(--secondary-text-color); font-size: .8rem; }
  .settings h4 { margin: 18px 0 2px; font-size: .75rem; font-weight: 500; letter-spacing: .06em;
                 text-transform: uppercase; color: var(--secondary-text-color); }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; margin-top: 10px; }
  .stat { background: var(--secondary-background-color); border-radius: 10px; padding: 8px 10px; }
  .stat .k { font-size: .72rem; color: var(--secondary-text-color); }
  .stat .v { font-size: .95rem; font-weight: 500; margin-top: 2px; color: var(--primary-text-color);
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .danger { margin-top: 12px; width: 100%; padding: 9px 12px; border-radius: 10px; font: inherit; cursor: pointer;
            display: flex; align-items: center; justify-content: center; gap: 8px;
            border: 1px solid var(--error-color, #db4437); color: var(--error-color, #db4437); background: none; }
  .danger:hover { background: rgba(219, 68, 55, .08); }
  .danger:disabled { opacity: .5; cursor: default; }
  .toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
  .toggle span { position: absolute; inset: 0; border-radius: 999px; cursor: pointer;
                 background: var(--disabled-color, #9e9e9e); transition: background .2s; }
  .toggle span::before { content: ""; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px;
                 border-radius: 50%; background: #fff; transition: transform .2s; }
  .toggle input:checked + span { background: var(--primary-color); }
  .toggle input:checked + span::before { transform: translateX(18px); }
  .toggle input:focus-visible + span { outline: 2px solid var(--primary-color); outline-offset: 2px; }
`;

class DynaframeCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("dynaframe-card-editor");
  }

  static getStubConfig() {
    return { show_preview: true };
  }

  setConfig(config) {
    this._config = { show_preview: true, ...config };
    this._selected = undefined;
    this._built = false;
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return this._config?.show_preview === false ? 4 : 8;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  get _players() {
    const configured = this._config.entities?.length ? this._config.entities : dynaframePlayers(this._hass);
    return configured.filter((id) => this._hass.states[id]);
  }

  _call(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  _render() {
    if (!this._config || !this._hass) return;
    const players = this._players;
    if (!this._selected || !players.includes(this._selected)) this._selected = players[0];
    const key = players.join(",") + "|" + this._selected;
    if (!this._built || key !== this._layoutKey) this._build(players, key);
    this._update(players);
  }

  _build(players, key) {
    this._layoutKey = key;
    this._built = true;
    const hass = this._hass;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const title = this._config.title?.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);
    const id = this._selected;

    if (!id) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>
        ${title ? `<div class="header"><h2>${title}</h2></div>` : ""}
        <div class="none">${t(hass, "Kein Dynaframe gefunden. Füge die Integration unter Einstellungen → Geräte & Dienste hinzu.", "No Dynaframe found. Add the integration under Settings → Devices & services.")}</div>
      </ha-card>`;
      return;
    }

    const tabs =
      players.length > 1
        ? `<div class="tabs" role="tablist">${players
            .map(
              (p) => `<button class="tab" role="tab" data-id="${p}" aria-selected="${p === id}">
                 <span class="dot"></span><span class="name"></span></button>`,
            )
            .join("")}</div>`
        : "";

    const preview =
      this._config.show_preview !== false
        ? `<div class="preview">
             <div class="empty"><ha-icon icon="mdi:image-frame"></ha-icon></div>
             <img alt="" hidden>
             <span class="pill"></span>
             <div class="power"><button class="round" data-act="power" title="${t(hass, "Bildschirm", "Display")}"><ha-icon icon="mdi:power"></ha-icon></button></div>
             <div class="shade"><div class="title"></div><div class="sub"></div></div>
           </div>`
        : `<div class="row"><ha-icon icon="mdi:image-frame"></ha-icon>
             <label class="title"></label><span class="state muted"></span>
             <button class="round" data-act="power"><ha-icon icon="mdi:power"></ha-icon></button></div>`;

    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>
      ${title ? `<div class="header"><h2>${title}</h2></div>` : ""}
      ${tabs}
      <div class="body">
        ${preview}
        <div class="controls">
          <button class="ctrl" data-act="shuffle" title="${t(hass, "Zufällig", "Shuffle")}"><ha-icon icon="mdi:shuffle-variant"></ha-icon></button>
          <button class="ctrl" data-act="prev" title="${t(hass, "Zurück", "Previous")}"><ha-icon icon="mdi:skip-previous"></ha-icon></button>
          <button class="ctrl main" data-act="playpause"><ha-icon icon="mdi:play"></ha-icon></button>
          <button class="ctrl" data-act="next" title="${t(hass, "Weiter", "Next")}"><ha-icon icon="mdi:skip-next"></ha-icon></button>
          <button class="ctrl" data-act="stop" title="Stop"><ha-icon icon="mdi:stop"></ha-icon></button>
        </div>
        <div class="row playlist-row">
          <ha-icon icon="mdi:playlist-play"></ha-icon>
          <button class="pl-toggle" data-act="pl-toggle" aria-expanded="false" aria-controls="dfPlaylists">
            <span class="pl-label"></span><ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
          </button>
        </div>
        <div class="pl-panel" id="dfPlaylists" hidden>
          <div class="pl-list" role="group" aria-label="${t(hass, "Wiedergabelisten", "Playlists")}"></div>
          <div class="pl-actions">
            <span class="hint"></span>
            <button class="pl-cancel" data-act="pl-cancel">${t(hass, "Abbrechen", "Cancel")}</button>
            <button class="pl-play" data-act="pl-play">${t(hass, "Abspielen", "Play")}</button>
          </div>
        </div>
        <div class="row volume-row">
          <button class="iconbtn" data-act="mute" title="${t(hass, "Stumm", "Mute")}"><ha-icon icon="mdi:volume-high"></ha-icon></button>
          <input type="range" min="0" max="100" step="1" data-act="volume" aria-label="${t(hass, "Lautstärke", "Volume")}">
          <span class="muted vol"></span>
        </div>
        <button class="settings-toggle" data-act="settings" aria-expanded="false" aria-controls="dfSettings">
          <ha-icon icon="mdi:tune-variant"></ha-icon>
          <span class="label">${t(hass, "Einstellungen", "Settings")}</span>
          <span class="summary"></span>
          <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
        </button>
        <div class="settings" id="dfSettings" hidden>
          <div class="row transition-row">
            <ha-icon icon="mdi:transition"></ha-icon>
            <select data-act="transition" aria-label="${t(hass, "Überblendung", "Transition")}"></select>
          </div>
          <div class="row transition-duration-row">
            <ha-icon icon="mdi:timer-sand"></ha-icon>
            <label for="dfTransDur">${t(hass, "Überblendungsdauer", "Transition duration")}</label>
            <input type="number" id="dfTransDur" min="0.1" max="30" step="0.1" data-act="transition-duration">
            <span class="unit">s</span>
          </div>
          <div class="row duration-row">
            <ha-icon icon="mdi:timer-outline"></ha-icon>
            <label for="dfSlideDur">${t(hass, "Anzeigedauer pro Bild", "Slide duration")}</label>
            <input type="number" id="dfSlideDur" min="3" max="3600" step="1" data-act="duration">
            <span class="unit">s</span>
          </div>
          <div class="row video-audio-row">
            <ha-icon icon="mdi:movie-open-play-outline"></ha-icon>
            <label for="dfVideoAudio">${t(hass, "Ton bei Videos", "Play video audio")}</label>
            <label class="toggle"><input type="checkbox" id="dfVideoAudio" data-act="videoaudio"><span></span></label>
          </div>
          <div class="row mute-row">
            <ha-icon icon="mdi:volume-off"></ha-icon>
            <label for="dfMute">${t(hass, "Stumm", "Mute")}</label>
            <label class="toggle"><input type="checkbox" id="dfMute" data-act="mute-toggle"><span></span></label>
          </div>
          <h4>Overlays</h4>
          <div class="row overlays-row">
            <ha-icon icon="mdi:layers-outline"></ha-icon>
            <label for="dfOverlays">${t(hass, "Overlays anzeigen", "Show overlays")}</label>
            <label class="toggle"><input type="checkbox" id="dfOverlays" data-act="overlays"><span></span></label>
          </div>
          <div class="row overlay-row">
            <ha-icon icon="mdi:card-text-outline"></ha-icon>
            <select data-act="overlay" aria-label="${t(hass, "Standard-Overlay", "Default overlay")}"></select>
          </div>
          <h4>${t(hass, "System", "System")}</h4>
          <div class="stats">
            <div class="stat" data-stat="sync_role"><div class="k">${t(hass, "Sync", "Sync")}</div><div class="v"></div></div>
            <div class="stat" data-stat="memory_used"><div class="k">${t(hass, "Arbeitsspeicher", "Memory")}</div><div class="v"></div></div>
            <div class="stat" data-stat="media_storage_used"><div class="k">${t(hass, "Medienspeicher", "Media storage")}</div><div class="v"></div></div>
            <div class="stat" data-stat="version"><div class="k">Version</div><div class="v"></div></div>
          </div>
          <button class="danger" data-act="reboot"><ha-icon icon="mdi:restart"></ha-icon>${t(hass, "Frame neu starten", "Reboot frame")}</button>
        </div>
      </div>
    </ha-card>`;

    const root = this.shadowRoot;
    let settingsOpen = false;
    try {
      settingsOpen = localStorage.getItem("dynaframe-card-settings-open") === "1";
    } catch {}
    root.querySelector('[data-act="settings"]')?.setAttribute("aria-expanded", String(settingsOpen));
    const settingsPanel = root.getElementById("dfSettings");
    if (settingsPanel) settingsPanel.hidden = !settingsOpen;
    root.querySelectorAll(".tab").forEach((b) =>
      b.addEventListener("click", () => {
        this._selected = b.dataset.id;
        this._plDraft = null;
        this._render();
      }),
    );
    const on = (act, ev, fn) => root.querySelectorAll(`[data-act="${act}"]`).forEach((el) => el.addEventListener(ev, fn));
    const target = () => ({ entity_id: this._selected });
    on("prev", "click", () => this._call("media_player", "media_previous_track", target()));
    on("next", "click", () => this._call("media_player", "media_next_track", target()));
    on("stop", "click", () => this._call("media_player", "media_stop", target()));
    on("playpause", "click", () => {
      const s = this._hass.states[this._selected]?.state;
      this._call("media_player", s === "playing" ? "media_pause" : "media_play", target());
    });
    on("power", "click", () => {
      const s = this._hass.states[this._selected]?.state;
      this._call("media_player", s === "off" ? "turn_on" : "turn_off", target());
    });
    on("shuffle", "click", () => {
      const sw = sibling(this._hass, this._selected, "switch", "shuffle");
      if (sw) this._call("switch", "toggle", { entity_id: sw });
    });
    on("mute", "click", () => {
      const sw = sibling(this._hass, this._selected, "switch", "mute");
      if (sw) return this._call("switch", "toggle", { entity_id: sw });
      const cur = this._hass.states[this._selected]?.attributes.is_volume_muted;
      this._call("media_player", "volume_mute", { ...target(), is_volume_muted: !cur });
    });
    on("settings", "click", (e) => {
      const btn = e.currentTarget;
      const open = btn.getAttribute("aria-expanded") !== "true";
      btn.setAttribute("aria-expanded", String(open));
      root.getElementById("dfSettings").hidden = !open;
      try {
        localStorage.setItem("dynaframe-card-settings-open", open ? "1" : "0");
      } catch {}
    });
    on("overlays", "change", (e) => {
      const sw = sibling(this._hass, this._selected, "switch", "overlays");
      if (sw) this._call("switch", e.target.checked ? "turn_on" : "turn_off", { entity_id: sw });
    });
    on("overlay", "change", (e) => {
      const sel = sibling(this._hass, this._selected, "select", "default_overlay");
      if (sel && e.target.value) this._call("select", "select_option", { entity_id: sel, option: e.target.value });
    });
    on("reboot", "click", (e) => {
      const target = e.currentTarget;
      const btn = sibling(this._hass, this._selected, "button", "reboot");
      const name = this._hass.devices?.[this._hass.entities?.[this._selected]?.device_id]?.name || this._selected;
      const question = t(
        this._hass,
        `${name} jetzt neu starten? Der Frame ist dann etwa eine Minute lang nicht erreichbar.`,
        `Reboot ${name} now? The frame will be unreachable for about a minute.`,
      );
      if (!btn || !confirm(question)) return;
      const button = target;
      button.disabled = true;
      this._call("button", "press", { entity_id: btn }).finally(() => setTimeout(() => (button.disabled = false), 60000));
    });
    on("mute-toggle", "change", (e) => {
      const sw = sibling(this._hass, this._selected, "switch", "mute");
      if (sw) this._call("switch", e.target.checked ? "turn_on" : "turn_off", { entity_id: sw });
    });
    on("transition", "change", (e) => {
      const sel = sibling(this._hass, this._selected, "select", "transition");
      if (sel && e.target.value) this._call("select", "select_option", { entity_id: sel, option: e.target.value });
    });
    on("transition-duration", "change", (e) => {
      const num = sibling(this._hass, this._selected, "number", "transition_duration");
      if (num) this._call("number", "set_value", { entity_id: num, value: Number(e.target.value) });
    });
    on("videoaudio", "change", (e) => {
      const sw = sibling(this._hass, this._selected, "switch", "video_audio");
      if (sw) this._call("switch", e.target.checked ? "turn_on" : "turn_off", { entity_id: sw });
    });
    on("volume", "input", (e) => (root.querySelector(".vol").textContent = `${e.target.value}%`));
    on("volume", "change", (e) => {
      const num = sibling(this._hass, this._selected, "number", "volume");
      if (num) return this._call("number", "set_value", { entity_id: num, value: Number(e.target.value) });
      this._call("media_player", "volume_set", { ...target(), volume_level: Number(e.target.value) / 100 });
    });
    const plPanel = root.getElementById("dfPlaylists");
    const plToggle = root.querySelector('[data-act="pl-toggle"]');
    const setPlOpen = (open) => {
      plToggle.setAttribute("aria-expanded", String(open));
      plPanel.hidden = !open;
      this._plDraft = open ? new Set(this._activePlaylists()) : null;
      this._renderPlaylistList(true);
    };
    on("pl-toggle", "click", () => setPlOpen(plPanel.hidden));
    on("pl-cancel", "click", () => setPlOpen(false));
    on("pl-play", "click", () => {
      const chosen = [...(this._plDraft || [])];
      if (!chosen.length) return;
      this._call("dynaframe", "play_playlists", { ...target(), playlists: chosen });
      setPlOpen(false);
    });
    plPanel.addEventListener("change", (e) => {
      if (!e.target.matches('input[type="checkbox"]')) return;
      if (e.target.checked) this._plDraft.add(e.target.value);
      else this._plDraft.delete(e.target.value);
      this._renderPlaylistList(false);
    });
    on("duration", "change", (e) => {
      const num = sibling(this._hass, this._selected, "number", "slide_duration");
      if (num) this._call("number", "set_value", { entity_id: num, value: Number(e.target.value) });
    });
  }

  /** Names of the playlists the selected frame is currently mixing. */
  _activePlaylists() {
    const hass = this._hass;
    const sel = hass.states[sibling(hass, this._selected, "select", "playlist")];
    const fromAttr = sel?.attributes.active_playlists;
    if (Array.isArray(fromAttr)) return fromAttr;
    return sel && (sel.attributes.options || []).includes(sel.state) ? [sel.state] : [];
  }

  /** Checklist of playlists; `rebuild` re-creates rows, otherwise only state is synced. */
  _renderPlaylistList(rebuild) {
    const root = this.shadowRoot;
    const list = root?.querySelector(".pl-list");
    if (!list || root.getElementById("dfPlaylists").hidden) return;
    const hass = this._hass;
    const sel = hass.states[sibling(hass, this._selected, "select", "playlist")];
    const options = sel?.attributes.options || [];
    const active = new Set(this._activePlaylists());
    const draft = this._plDraft || new Set();
    const sig = options.join("\u0000");
    if (rebuild || list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.innerHTML = "";
      options.forEach((name) => {
        const label = document.createElement("label");
        label.className = "pl-item";
        const box = document.createElement("input");
        box.type = "checkbox";
        box.value = name;
        const text = document.createElement("span");
        text.textContent = name;
        label.append(box, text);
        list.append(label);
      });
    }
    list.querySelectorAll(".pl-item").forEach((label) => {
      const box = label.querySelector("input");
      box.checked = draft.has(box.value);
      label.classList.toggle("active", active.has(box.value));
    });
    const n = draft.size;
    root.querySelector(".pl-actions .hint").textContent =
      n === 0
        ? t(hass, "Mindestens eine auswählen", "Select at least one")
        : n === 1
          ? t(hass, "1 ausgewählt", "1 selected")
          : t(hass, `${n} ausgewählt – werden gemischt`, `${n} selected – mixed together`);
    root.querySelector('[data-act="pl-play"]').disabled = n === 0;
  }

  _update(players) {
    const hass = this._hass;
    const root = this.shadowRoot;
    const id = this._selected;
    if (!id || !root) return;
    const st = hass.states[id];
    const a = st.attributes;
    const state = st.state;
    const off = state === "off" || state === "unavailable";

    const friendly = (p) => {
      const dev = hass.devices?.[hass.entities?.[p]?.device_id];
      return dev?.name_by_user || dev?.name || hass.states[p]?.attributes.friendly_name || p;
    };
    root.querySelectorAll(".tab").forEach((b) => {
      b.querySelector(".name").textContent = friendly(b.dataset.id);
      b.querySelector(".dot").className = `dot ${hass.states[b.dataset.id]?.state || ""}`;
    });

    const label = STATE_LABEL[state] || [state, state];
    const pill = root.querySelector(".pill, .state");
    if (pill) pill.textContent = (players.length > 1 ? "" : friendly(id) + " · ") + t(hass, label[0], label[1]);

    const titleEl = root.querySelector(".title");
    if (titleEl) titleEl.textContent = off ? friendly(id) : a.media_title || "—";
    const sub = root.querySelector(".sub");
    if (sub) {
      const parts = [];
      const active = this._activePlaylists();
      if (active.length) parts.push(active.join(" + "));
      if (a.item_count) parts.push(`${(a.item_index ?? 0) + 1} / ${a.item_count}`);
      if (a.media_artist) parts.push(a.media_artist);
      sub.textContent = parts.join(" · ");
    }

    const img = root.querySelector(".preview img");
    if (img) {
      const pic = !off && a.entity_picture ? hass.hassUrl(a.entity_picture) : "";
      if (pic && img.dataset.src !== pic) {
        img.dataset.src = pic;
        const next = new Image();
        next.onload = () => {
          img.src = pic;
          img.hidden = false;
        };
        next.src = pic;
      } else if (!pic) {
        img.hidden = true;
        img.dataset.src = "";
      }
    }

    root.querySelectorAll('[data-act="power"]').forEach((b) => b.classList.toggle("on", !off));
    const pp = root.querySelector('[data-act="playpause"] ha-icon');
    if (pp) pp.setAttribute("icon", state === "playing" ? "mdi:pause" : "mdi:play");
    root.querySelectorAll(".ctrl").forEach((b) => (b.disabled = state === "unavailable"));
    // Media player attributes are hidden while the display is off, so the
    // persistent settings are read from the frame's own entities.
    const shuffleId = sibling(hass, id, "switch", "shuffle");
    root.querySelector('[data-act="shuffle"]')?.classList.toggle("active", hass.states[shuffleId]?.state === "on");

    const plRow = root.querySelector(".playlist-row");
    const plEntity = hass.states[sibling(hass, id, "select", "playlist")];
    if (plRow) plRow.hidden = !plEntity || plEntity.state === "unavailable";
    const plLabel = root.querySelector(".pl-label");
    if (plLabel) {
      const active = this._activePlaylists();
      const pending = plEntity?.attributes.pending_playlists || [];
      plLabel.textContent = pending.length
        ? t(hass, `Wird zusammengestellt … (${pending.join(" + ")})`, `Assembling … (${pending.join(" + ")})`)
        : active.length
          ? active.join(" + ")
          : t(hass, "Wiedergabeliste wählen", "Choose playlist");
      plLabel.title = plLabel.textContent;
    }
    this._renderPlaylistList(false);

    const vol = root.querySelector('[data-act="volume"]');
    const volEntity = hass.states[sibling(hass, id, "number", "volume")];
    const muteEntity = hass.states[sibling(hass, id, "switch", "mute")];
    const volRaw = volEntity ? Number(volEntity.state) : a.volume_level !== undefined ? a.volume_level * 100 : NaN;
    const muted = muteEntity ? muteEntity.state === "on" : !!a.is_volume_muted;
    const volRow = root.querySelector(".volume-row");
    if (volRow) volRow.hidden = Number.isNaN(volRaw);
    const volPct = Math.round(Number.isNaN(volRaw) ? 0 : volRaw);
    if (vol && root.activeElement !== vol) vol.value = volPct;
    const volLabel = root.querySelector(".vol");
    if (volLabel && root.activeElement !== vol) volLabel.textContent = `${volPct}%`;
    root
      .querySelector('[data-act="mute"] ha-icon')
      ?.setAttribute("icon", muted ? "mdi:volume-off" : volPct < 35 ? "mdi:volume-low" : "mdi:volume-high");

    const videoAudio = hass.states[sibling(hass, id, "switch", "video_audio")];
    const vaRow = root.querySelector(".video-audio-row");
    if (vaRow) vaRow.hidden = !videoAudio || ["unavailable", "unknown"].includes(videoAudio.state);
    const vaBox = root.querySelector('[data-act="videoaudio"]');
    if (vaBox && videoAudio) vaBox.checked = videoAudio.state === "on";

    const muteBox = root.querySelector('[data-act="mute-toggle"]');
    root.querySelector(".mute-row").hidden = !muteEntity || muteEntity.state === "unavailable";
    if (muteBox && muteEntity) muteBox.checked = muteEntity.state === "on";

    const fmt = (stateObj, value) => {
      try {
        return hass.formatEntityState ? hass.formatEntityState(stateObj, value) : value;
      } catch {
        return value;
      }
    };
    const transition = hass.states[sibling(hass, id, "select", "transition")];
    const transSel = root.querySelector('[data-act="transition"]');
    root.querySelector(".transition-row").hidden = !transition || transition.state === "unavailable";
    if (transSel && transition && root.activeElement !== transSel) {
      const options = transition.attributes.options || [];
      const sig = options.join("\u0000") + "|" + transition.state;
      if (transSel.dataset.sig !== sig) {
        transSel.dataset.sig = sig;
        transSel.innerHTML = "";
        options
          .map((o) => [o, fmt(transition, o)])
          .sort((x, y) => (x[0] === "random" ? -1 : y[0] === "random" ? 1 : x[1].localeCompare(y[1])))
          .forEach(([o, text]) => transSel.add(new Option(text, o, false, o === transition.state)));
        transSel.value = transition.state;
      }
    }
    const transDur = hass.states[sibling(hass, id, "number", "transition_duration")];
    const transDurInput = root.querySelector('[data-act="transition-duration"]');
    root.querySelector(".transition-duration-row").hidden = !transDur || transDur.state === "unavailable";
    if (transDurInput && transDur && root.activeElement !== transDurInput) transDurInput.value = transDur.state;

    const overlays = hass.states[sibling(hass, id, "switch", "overlays")];
    root.querySelector(".overlays-row").hidden = !overlays || overlays.state === "unavailable";
    const overlaysBox = root.querySelector('[data-act="overlays"]');
    if (overlaysBox && overlays) overlaysBox.checked = overlays.state === "on";
    const overlay = hass.states[sibling(hass, id, "select", "default_overlay")];
    const overlaySel = root.querySelector('[data-act="overlay"]');
    root.querySelector(".overlay-row").hidden = !overlay || overlay.state === "unavailable";
    if (overlaySel && overlay && root.activeElement !== overlaySel) {
      const options = overlay.attributes.options || [];
      const sig = options.join("\u0000") + "|" + overlay.state;
      if (overlaySel.dataset.sig !== sig) {
        overlaySel.dataset.sig = sig;
        overlaySel.innerHTML = "";
        options.forEach((o) =>
          overlaySel.add(new Option(o === "—" ? t(hass, "Kein Standard-Overlay", "No default overlay") : o, o, false, o === overlay.state)),
        );
        overlaySel.value = overlay.state;
      }
    }
    root.querySelectorAll(".stat").forEach((el) => {
      const key = el.dataset.stat;
      const st = hass.states[sibling(hass, id, "sensor", key)];
      el.hidden = !st || ["unavailable", "unknown"].includes(st.state);
      if (st && !el.hidden) el.querySelector(".v").textContent = fmt(st, st.state);
    });
    const rebootBtn = root.querySelector('[data-act="reboot"]');
    if (rebootBtn) rebootBtn.hidden = !sibling(hass, id, "button", "reboot");

    const summary = root.querySelector(".settings-toggle .summary");
    if (summary) {
      const bits = [];
      if (transition && transition.state !== "unavailable") bits.push(fmt(transition, transition.state));
      if (videoAudio && videoAudio.state === "on") bits.push(t(hass, "Video-Ton an", "Video audio on"));
      if (muted) bits.push(t(hass, "Stumm", "Muted"));
      summary.textContent = bits.join(" · ");
    }

    const dur = root.querySelector('[data-act="duration"]');
    const durRow = root.querySelector(".duration-row");
    const numId = sibling(hass, id, "number", "slide_duration");
    if (durRow) durRow.hidden = !numId;
    if (dur && numId && root.activeElement !== dur) dur.value = hass.states[numId]?.state ?? "";
  }
}

class DynaframeCardEditor extends HTMLElement {
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
          entities: t(this._hass, "Frames (leer = alle)", "Frames (empty = all)"),
          title: t(this._hass, "Titel", "Title"),
          show_preview: t(this._hass, "Vorschaubild anzeigen", "Show preview"),
        })[s.name];
      this._form.addEventListener("value-changed", (e) => {
        const config = { ...e.detail.value };
        if (!config.entities?.length) delete config.entities;
        if (!config.title) delete config.title;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      { name: "entities", selector: { entity: { multiple: true, filter: { integration: "dynaframe", domain: "media_player" } } } },
      { name: "title", selector: { text: {} } },
      { name: "show_preview", selector: { boolean: {} } },
    ];
  }
}

// Some other custom cards install a scoped-registry polyfill that replaces
// window.customElements after this script ran, dropping our definitions.
// Re-register whenever that happens.
function registerDynaframeCard() {
  if (!customElements.get("dynaframe-card")) customElements.define("dynaframe-card", DynaframeCard);
  if (!customElements.get("dynaframe-card-editor")) customElements.define("dynaframe-card-editor", DynaframeCardEditor);
}

registerDynaframeCard();
// Cheap check; polyfills can arrive late when a view lazily loads its cards.
setInterval(registerDynaframeCard, 2000);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "dynaframe-card")) {
  window.customCards.push({
    type: "dynaframe-card",
    name: "Dynaframe",
    description: (navigator.language || "").startsWith("de")
      ? "Vorschau, Steuerung und Einstellungen deiner Dynaframes"
      : "Preview, control and settings for your Dynaframes",
    preview: true,
    documentationURL: "https://github.com/Archonw/dynaframe-homeassistant",
  });
  console.info(`%c DYNAFRAME-CARD %c ${CARD_VERSION} `, "background:#03a9f4;color:#fff", "");
}
