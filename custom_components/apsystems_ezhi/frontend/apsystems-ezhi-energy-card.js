const CARD_VERSION = "0.5.1";
const DOMAIN = "apsystems_ezhi";

const ENTITY_KEYS = [
  "pvP",
  "ogP",
  "ofgP",
  "batP",
  "batSoc",
  "batTemp",
  "devTemp",
  "batS",
];

const ALARM_KEYS = [
  "BatHTP", "BatLTP", "BatCE", "BatHV", "BatLV", "BatHI", "BatE",
  "DTP", "EE", "SBS", "ACA", "OfOI", "PvHV", "PvOC", "IRDE",
  "PVWE", "OfGS", "VRP", "BCC", "BCI",
];

class ApSystemsEzhiEnergyCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("apsystems-ezhi-energy-card-editor");
  }

  static getStubConfig() {
    return { type: "custom:apsystems-ezhi-energy-card" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._entities = {};
    this._alarms = [];
    this._resolvedDeviceId = undefined;
    this._resolving = false;
    this._lastRenderKey = "";
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid card configuration");
    this._config = {
      title: "Balcony Energy Storage System",
      grid_positive_is_export: true,
      battery_positive_is_charge: true,
      flow_threshold: 1,
      ...config,
    };
    this._resolvedDeviceId = undefined;
    this._entities = {};
    this._alarms = [];
    this._lastRenderKey = "";
    this._resolveEntities();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._resolvedDeviceId && !this._resolving) this._resolveEntities();
    this._render();
  }

  getCardSize() {
    return 7;
  }

  async _resolveEntities() {
    if (!this._hass || this._resolving) return;
    this._resolving = true;
    try {
      const [devices, entities] = await Promise.all([
        this._hass.callWS({ type: "config/device_registry/list" }),
        this._hass.callWS({ type: "config/entity_registry/list" }),
      ]);

      const ezhiDevices = devices.filter((device) =>
        (device.identifiers || []).some((identifier) => identifier[0] === DOMAIN)
      );
      const requestedId = this._config.device_id;
      const device = requestedId
        ? ezhiDevices.find((candidate) => candidate.id === requestedId)
        : ezhiDevices.length === 1 ? ezhiDevices[0] : undefined;

      if (!device) {
        this._resolutionError = requestedId
          ? "The configured EZHI device was not found."
          : ezhiDevices.length > 1
            ? "Select an EZHI device in the card editor."
            : "No APsystems EZHI device was found.";
        return;
      }

      const deviceEntities = entities.filter((entity) => entity.device_id === device.id);
      this._entities = Object.fromEntries(
        ENTITY_KEYS.map((key) => [
          key,
          deviceEntities.find((entity) => entity.unique_id?.endsWith(`_${key}`))?.entity_id,
        ])
      );
      this._alarms = ALARM_KEYS.map((key) =>
        deviceEntities.find((entity) => entity.unique_id?.endsWith(`_${key}`))?.entity_id
      ).filter(Boolean);
      this._resolvedDeviceId = device.id;
      this._deviceName = device.name_by_user || device.name || "APsystems EZHI";
      this._resolutionError = undefined;
      this._lastRenderKey = "";
    } catch (error) {
      this._resolutionError = `Could not discover EZHI entities: ${error.message}`;
    } finally {
      this._resolving = false;
      this._render();
    }
  }

  _state(key) {
    return this._hass?.states?.[this._entities[key]];
  }

  _number(key) {
    const value = Number.parseFloat(this._state(key)?.state);
    return Number.isFinite(value) ? value : 0;
  }

  _available(key) {
    const state = this._state(key)?.state;
    return state !== undefined && state !== "unknown" && state !== "unavailable";
  }

  _flow(power, direction) {
    const active = Math.abs(power) >= Number(this._config.flow_threshold);
    const duration = Math.max(0.55, Math.min(2.4, 2.5 - Math.abs(power) / 450));
    return `${active ? "active" : "idle"} ${direction === "reverse" ? "reverse" : "forward"}` +
      `" style="--flow-duration:${duration.toFixed(2)}s`;
  }

  _formatPower(value) {
    const absolute = Math.abs(value);
    if (absolute >= 1000) return `${(absolute / 1000).toFixed(2)} kW`;
    return `${Math.round(absolute)} W`;
  }

  _formatTemperature(key) {
    if (!this._available(key)) return "–";
    return `${Math.round(this._number(key))} °C`;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  _showMoreInfo(key) {
    const entityId = this._entities[key];
    if (!entityId) return;
    const event = new Event("hass-more-info", { bubbles: true, composed: true });
    event.detail = { entityId };
    this.dispatchEvent(event);
  }

  _bindClicks() {
    this.shadowRoot.querySelectorAll("[data-key]").forEach((element) => {
      element.addEventListener("click", () => this._showMoreInfo(element.dataset.key));
    });
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    if (!this._resolvedDeviceId) {
      const message = this._resolutionError || "Discovering APsystems EZHI entities…";
      this.shadowRoot.innerHTML = `<ha-card><div class="message">${this._escape(message)}</div></ha-card>${this._baseStyle()}`;
      return;
    }

    const pv = this._number("pvP");
    const grid = this._number("ogP");
    const offGrid = this._number("ofgP");
    const battery = this._number("batP");
    const batteryStatus = this._state("batS")?.state || "unknown";
    const soc = Math.max(0, Math.min(100, this._number("batSoc")));
    const online = this._available("pvP");
    const activeAlarms = this._alarms.filter((entityId) => this._hass.states[entityId]?.state === "on").length;

    const gridExport = this._config.grid_positive_is_export ? grid >= 0 : grid < 0;
    const gridDirection = gridExport ? "reverse" : "forward";
    let batteryDirection;
    if (batteryStatus === "charging") batteryDirection = "forward";
    else if (batteryStatus === "discharging") batteryDirection = "reverse";
    else {
      const charging = this._config.battery_positive_is_charge ? battery >= 0 : battery < 0;
      batteryDirection = charging ? "forward" : "reverse";
    }

    const renderKey = JSON.stringify([
      pv, grid, offGrid, battery, batteryStatus, soc, online, activeAlarms,
      this._formatTemperature("batTemp"), this._formatTemperature("devTemp"),
      this._hass.locale?.language,
    ]);
    if (renderKey === this._lastRenderKey) return;
    this._lastRenderKey = renderKey;

    const statusClass = !online || activeAlarms ? "problem" : "ok";
    const statusText = !online
      ? "Offline"
      : activeAlarms
        ? `${activeAlarms} active alarm${activeAlarms === 1 ? "" : "s"}`
        : "Online";
    const batteryLabel = batteryStatus.replaceAll("_", " ");

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="header">
          <div>
            <div class="title">${this._escape(this._config.title)}</div>
            <div class="device-name">${this._escape(this._deviceName)}</div>
          </div>
          <div class="status ${statusClass}"><span></span>${this._escape(statusText)}</div>
        </div>

        <div class="diagram" role="img" aria-label="Live energy flow diagram">
          <svg viewBox="0 0 440 500" preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="batteryFill" x1="0" y1="1" x2="0" y2="0">
                <stop offset="0" stop-color="var(--warning-color, #ffb300)"/>
                <stop offset="1" stop-color="var(--success-color, #2ecc71)"/>
              </linearGradient>
            </defs>

            <path class="track" d="M92 172 H172"/>
            <path class="flow ${this._flow(grid, gridDirection)}" d="M92 172 H172"/>
            <path class="track" d="M348 172 H268"/>
            <path class="flow ${this._flow(pv, "forward")}" d="M348 172 H268"/>
            <path class="track" d="M205 242 V345"/>
            <path class="flow ${this._flow(battery, batteryDirection)}" d="M205 242 V345"/>
            <path class="track" d="M172 215 H80 V345"/>
            <path class="flow ${this._flow(offGrid, "forward")}" d="M172 215 H80 V345"/>

            <g class="node clickable" data-key="ogP" transform="translate(50 150)">
              <path class="icon" d="M20 0 7 44h10l-8 27m11-71 13 44H23l8 27M8 31h25M4 44h33M0 71h41"/>
              <text class="node-label" x="20" y="94">ON-GRID</text>
              <text class="value" x="20" y="116">${this._formatPower(grid)}</text>
              <text class="direction" x="20" y="135">${Math.abs(grid) < this._config.flow_threshold ? "idle" : gridExport ? "export" : "import"}</text>
            </g>

            <g class="node clickable" data-key="pvP" transform="translate(332 153)">
              <path class="panel" d="M-27 15h55l10 38h-76zM-20 15l-7 38m20-38-3 38m17-38 3 38m18-38 7 38M-33 28h64M-36 41h70M0 53v14m-15 0h30"/>
              <text class="node-label" x="0" y="94">PV</text>
              <text class="value" x="0" y="116">${this._formatPower(pv)}</text>
              <text class="direction" x="0" y="135">${pv >= this._config.flow_threshold ? "producing" : "idle"}</text>
            </g>

            <g class="inverter clickable" data-key="devTemp" transform="translate(172 137)">
              <rect width="96" height="105" rx="14"/>
              <circle cx="48" cy="43" r="16"/>
              <path d="M48 27v32M32 43h32"/>
              <text x="48" y="80">EZHI</text>
              <text class="device-temp" x="48" y="98">${this._formatTemperature("devTemp")}</text>
            </g>

            <g class="node clickable" data-key="ofgP" transform="translate(42 350)">
              <rect class="outlet" x="13" y="0" width="50" height="68" rx="9"/>
              <circle cx="29" cy="23" r="4"/><circle cx="48" cy="23" r="4"/>
              <circle cx="29" cy="46" r="4"/><circle cx="48" cy="46" r="4"/>
              <text class="node-label" x="38" y="94">OFF-GRID</text>
              <text class="value" x="38" y="116">${this._formatPower(offGrid)}</text>
              <text class="direction" x="38" y="135">${offGrid >= this._config.flow_threshold ? "supplying" : "idle"}</text>
            </g>

            <g class="node clickable" data-key="batSoc" transform="translate(155 348)">
              <rect class="battery-shell" x="0" y="0" width="100" height="70" rx="9"/>
              <rect class="battery-cap" x="38" y="-7" width="24" height="8" rx="2"/>
              <rect class="battery-level" x="7" y="${63 - (soc * 0.56)}" width="86" height="${soc * 0.56}" rx="4"/>
              <path class="bolt" d="M55 10 38 37h14l-6 23 18-30H51z"/>
              <text class="node-label" x="50" y="94">BATTERY</text>
              <text class="value" x="50" y="116">${this._formatPower(battery)} · ${Math.round(soc)}%</text>
              <text class="direction" x="50" y="135">${this._escape(batteryLabel)} · ${this._formatTemperature("batTemp")}</text>
            </g>
          </svg>
        </div>

        <div class="footer">
          <span>Updates from local EZHI data</span>
          <span class="legend"><i></i> live flow</span>
        </div>
      </ha-card>
      ${this._baseStyle()}
      <style>
        .header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; padding:20px 20px 4px; }
        .title { color:var(--primary-text-color); font-size:20px; font-weight:650; line-height:1.25; }
        .device-name { color:var(--secondary-text-color); font-size:13px; margin-top:4px; }
        .status { align-items:center; border-radius:999px; display:flex; flex:0 0 auto; font-size:13px; font-weight:600; gap:7px; padding:7px 10px; }
        .status span { border-radius:50%; height:8px; width:8px; }
        .status.ok { background:color-mix(in srgb, var(--success-color, #2ecc71) 14%, transparent); color:var(--success-color, #209b55); }
        .status.ok span { background:var(--success-color, #2ecc71); box-shadow:0 0 0 4px color-mix(in srgb, var(--success-color, #2ecc71) 16%, transparent); }
        .status.problem { background:color-mix(in srgb, var(--error-color, #db4437) 14%, transparent); color:var(--error-color, #db4437); }
        .status.problem span { background:var(--error-color, #db4437); }
        .diagram { margin:0 auto; max-width:540px; padding:0 8px; }
        svg { display:block; height:auto; overflow:visible; width:100%; }
        .track { fill:none; stroke:var(--divider-color, #d8d8d8); stroke-linecap:round; stroke-linejoin:round; stroke-width:8; }
        .flow { fill:none; stroke:var(--success-color, #2ecc71); stroke-dasharray:2 14; stroke-linecap:round; stroke-linejoin:round; stroke-width:7; }
        .flow.idle { display:none; }
        .flow.active { animation:flow-forward var(--flow-duration) linear infinite; }
        .flow.active.reverse { animation-name:flow-reverse; }
        @keyframes flow-forward { to { stroke-dashoffset:-32; } }
        @keyframes flow-reverse { to { stroke-dashoffset:32; } }
        .node { color:var(--primary-text-color); cursor:pointer; }
        .node .icon, .node .panel { fill:none; stroke:currentColor; stroke-linecap:round; stroke-linejoin:round; stroke-width:4; }
        .node .outlet { fill:var(--card-background-color, #fff); stroke:var(--divider-color, #ddd); stroke-width:2; }
        .node circle { fill:var(--secondary-text-color); }
        text { font-family:var(--paper-font-body1_-_font-family, Roboto, sans-serif); text-anchor:middle; }
        .node-label { fill:var(--secondary-text-color); font-size:11px; font-weight:650; letter-spacing:1px; }
        .value { fill:var(--primary-text-color); font-size:17px; font-weight:700; }
        .direction { fill:var(--secondary-text-color); font-size:12px; text-transform:capitalize; }
        .inverter { cursor:pointer; }
        .inverter rect { fill:var(--primary-text-color); filter:drop-shadow(0 5px 8px rgba(0,0,0,.16)); }
        .inverter circle, .inverter path { fill:none; stroke:var(--card-background-color, #fff); stroke-width:4; }
        .inverter text { fill:var(--card-background-color, #fff); font-size:13px; font-weight:700; letter-spacing:1px; }
        .inverter .device-temp { font-size:10px; font-weight:500; letter-spacing:0; opacity:.8; }
        .battery-shell { fill:var(--card-background-color, #fff); stroke:var(--secondary-text-color); stroke-width:3; }
        .battery-cap { fill:var(--secondary-text-color); }
        .battery-level { fill:url(#batteryFill); opacity:.9; }
        .bolt { fill:var(--primary-text-color); }
        .footer { border-top:1px solid var(--divider-color); color:var(--secondary-text-color); display:flex; font-size:11px; justify-content:space-between; margin:0 20px; padding:12px 0 15px; }
        .legend { align-items:center; display:flex; gap:6px; }
        .legend i { background:var(--success-color, #2ecc71); border-radius:50%; display:inline-block; height:7px; width:7px; }
        .clickable:hover { opacity:.78; }
        @media (max-width:420px) {
          .header { padding:16px 16px 0; }
          .title { font-size:18px; }
          .device-name { display:none; }
          .status { font-size:12px; padding:6px 8px; }
          .footer { margin:0 16px; }
        }
        @media (prefers-reduced-motion:reduce) { .flow.active { animation:none; stroke-dasharray:none; opacity:.8; } }
      </style>
    `;
    this._bindClicks();
  }

  _baseStyle() {
    return `<style>
      :host { display:block; }
      ha-card { overflow:hidden; }
      .message { color:var(--secondary-text-color); padding:24px; }
    </style>`;
  }
}

class ApSystemsEzhiEnergyCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._loadDevices();
  }

  async _loadDevices() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      const devices = await this._hass.callWS({ type: "config/device_registry/list" });
      this._devices = devices.filter((device) =>
        (device.identifiers || []).some((identifier) => identifier[0] === DOMAIN)
      );
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _changed(key, value) {
    const config = { ...this._config, [key]: value };
    if (value === "") delete config[key];
    this._config = config;
    const event = new Event("config-changed", { bubbles: true, composed: true });
    event.detail = { config };
    this.dispatchEvent(event);
  }

  _render() {
    if (!this.shadowRoot) return;
    const options = (this._devices || []).map((device) =>
      `<option value="${device.id}" ${device.id === this._config?.device_id ? "selected" : ""}>${this._escape(device.name_by_user || device.name || device.id)}</option>`
    ).join("");
    this.shadowRoot.innerHTML = `
      <div class="form">
        <label>EZHI device<select id="device"><option value="">Auto-detect (one device)</option>${options}</select></label>
        <label>Card title<input id="title" value="${this._escape(this._config?.title || "")}" placeholder="Balcony Energy Storage System"></label>
        <label><input id="grid" type="checkbox" ${this._config?.grid_positive_is_export !== false ? "checked" : ""}> Positive grid power means export</label>
        <label><input id="battery" type="checkbox" ${this._config?.battery_positive_is_charge !== false ? "checked" : ""}> Positive battery power means charging</label>
      </div>
      <style>
        .form { display:grid; gap:18px; padding:8px 0; }
        label { color:var(--primary-text-color); display:grid; font-size:14px; gap:7px; }
        label:has(input[type=checkbox]) { align-items:center; display:flex; }
        select,input[type=text],input:not([type]) { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; box-sizing:border-box; color:var(--primary-text-color); font:inherit; padding:10px; width:100%; }
      </style>`;
    this.shadowRoot.querySelector("#device")?.addEventListener("change", (event) => this._changed("device_id", event.target.value));
    this.shadowRoot.querySelector("#title")?.addEventListener("change", (event) => this._changed("title", event.target.value));
    this.shadowRoot.querySelector("#grid")?.addEventListener("change", (event) => this._changed("grid_positive_is_export", event.target.checked));
    this.shadowRoot.querySelector("#battery")?.addEventListener("change", (event) => this._changed("battery_positive_is_charge", event.target.checked));
  }

  _escape(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  }
}

if (!customElements.get("apsystems-ezhi-energy-card")) {
  customElements.define("apsystems-ezhi-energy-card", ApSystemsEzhiEnergyCard);
}
if (!customElements.get("apsystems-ezhi-energy-card-editor")) {
  customElements.define("apsystems-ezhi-energy-card-editor", ApSystemsEzhiEnergyCardEditor);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "apsystems-ezhi-energy-card",
  name: "APsystems EZHI Energy Flow",
  description: "Live animated energy-flow visualization for APsystems EZHI.",
  preview: true,
  documentationURL: "https://github.com/apfohl/ha-apsystems-ezhi",
});

console.info(`%c APsystems EZHI Energy Card %c ${CARD_VERSION} `, "background:#2e7dff;color:white;font-weight:bold", "background:#e8eef7;color:#223");
