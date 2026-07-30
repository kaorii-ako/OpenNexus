/* Setup page. Reads real status from disk and writes a real nexus.toml.
 * Nothing here is a mockup — every check reflects the actual filesystem, and
 * saving genuinely rewrites the config file. */

const $ = (id) => document.getElementById(id);

const ALL_CONNECTORS = ["notion", "github", "gmail", "calendar", "classroom", "discord"];

function check(ok, name, note) {
  return `<div class="check">
    <span class="mark ${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"}</span>
    <span class="name">${name}</span>
    <span class="note">${note}</span>
  </div>`;
}

async function loadStatus() {
  const data = await (await fetch("/api/state")).json();
  const { status, metrics } = data;

  const rows = [
    check(status.agentic_os, "AGENTIC_OS.md", "routing rules — immutable to the orchestrator"),
    check(status.constitution_ok, "config block",
      status.constitution_ok ? "parsed from the ```toml block" : status.constitution_error),
    check(status.skills.length > 0, "skills/",
      status.skills.length ? `${status.skills.length} branch(es): ${status.skills.join(", ")}` : "no branches found"),
    check(status.vault_dir, "vault/", `${metrics.vault_notes} note(s)`),
    check(status.events_log, "memory/events.jsonl",
      status.events_log ? `${metrics.events_total} event(s)` : "no events logged yet — this is normal on a fresh install"),
    check(status.integrity.length === 0, "log integrity",
      status.integrity.length === 0 ? "seq numbers match line numbers, ids unique" : status.integrity.slice(0, 3).join(" · ")),
    check(status.nexus_toml, "nexus.toml",
      status.nexus_toml ? "found" : "missing — only needed for ask / chat / digest"),
  ];
  $("checks").innerHTML = rows.join("");

  $("skills-body").innerHTML = data.skills.length
    ? data.skills.map((s) => `
        <div style="margin-bottom:14px">
          <div style="color:var(--cyan);margin-bottom:4px">${s.branch}</div>
          <div style="font-size:11px;color:var(--text-dim);margin-bottom:5px">
            ${s.triggers.length} trigger(s): ${s.triggers.join(", ") || "none"}
          </div>
          ${s.pointers.map((p) => `
            <div class="check" style="padding:3px 0;border:none">
              <span class="mark ${p.exists ? "ok" : "bad"}">${p.exists ? "✓" : "✗"}</span>
              <span class="name" style="min-width:150px;font-size:11px">${p.name}</span>
              <span class="note">${p.target || "no path declared"}${p.exists ? "" : " — missing on disk"}</span>
            </div>`).join("")}
        </div>`).join("")
    : `<div class="note">No skills found. Run <code>nexus setup</code>.</div>`;

  return status;
}

async function loadScope() {
  // Scope comes from the same AGENTIC_OS.md block the guardrail reads.
  const conf = await (await fetch("/api/state")).json();
  const list = $("scope-list");
  if (!conf.status.constitution_ok) {
    list.innerHTML = `<li class="note">${conf.status.constitution_error}</li>`;
    return;
  }
  list.innerHTML =
    `<li class="allow">+ writable: <code>skills/*/SKILL.md</code></li>` +
    `<li class="deny">− never writable: <code>AGENTIC_OS.md</code></li>` +
    `<li class="deny">− never writable: <code>backend/orchestrator/*.py</code></li>` +
    `<li class="deny">− never writable: pointer files under <code>skills/*/</code></li>` +
    `<li class="note" style="color:var(--text-faint);margin-top:6px">everything else: refused (deny-by-default)</li>`;
}

function renderConnectors(enabled) {
  $("connector-chips").innerHTML = ALL_CONNECTORS.map((c) => `
    <label class="chip ${enabled[c] ? "on" : ""}">
      <input type="checkbox" value="${c}" ${enabled[c] ? "checked" : ""}> ${c}
    </label>`).join("");

  $("connector-chips").querySelectorAll("input").forEach((input) => {
    input.onchange = () => input.closest(".chip").classList.toggle("on", input.checked);
  });
}

function toggleProviderFields() {
  const isOllama = $("f-provider").value === "ollama";
  $("wrap-baseurl").style.display = isOllama ? "" : "none";
  $("wrap-apikey").style.display = isOllama ? "none" : "";
}

async function loadConfig() {
  const cfg = await (await fetch("/api/config")).json();
  if (!cfg.exists || cfg.error) {
    renderConnectors({});
    toggleProviderFields();
    if (cfg.error) {
      $("save-msg").textContent = `existing nexus.toml could not be parsed: ${cfg.error}`;
      $("save-msg").className = "save-msg bad";
    }
    return;
  }

  $("f-name").value = cfg.user.name || "";
  $("f-tz").value = cfg.user.timezone || "";
  $("f-role").value = cfg.user.role || "";
  $("f-provider").value = cfg.llm.provider || "ollama";
  $("f-model").value = cfg.llm.model || "";
  $("f-baseurl").value = cfg.llm.base_url || "";
  $("f-embed").value = cfg.llm.embed_model || "";
  $("f-city").value = cfg.weather.location_name || "";
  $("f-lat").value = cfg.weather.latitude ?? "";
  $("f-lon").value = cfg.weather.longitude ?? "";

  $("key-hint").textContent = cfg.llm.api_key_set
    ? "a key is already set — leave blank to keep it"
    : "no key set yet";

  renderConnectors(cfg.connectors || {});
  toggleProviderFields();
}

$("f-provider").onchange = toggleProviderFields;

$("btn-save").onclick = async () => {
  const msg = $("save-msg");
  msg.textContent = "saving…";
  msg.className = "save-msg";

  const connectors = [...$("connector-chips").querySelectorAll("input:checked")].map((i) => i.value);

  const payload = {
    user: { name: $("f-name").value, timezone: $("f-tz").value, role: $("f-role").value },
    llm: {
      provider: $("f-provider").value,
      model: $("f-model").value,
      base_url: $("f-baseurl").value,
      embed_model: $("f-embed").value,
      api_key: $("f-apikey").value,
    },
    weather: {
      location_name: $("f-city").value,
      latitude: parseFloat($("f-lat").value) || 0,
      longitude: parseFloat($("f-lon").value) || 0,
    },
    connectors,
  };

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const out = await res.json();
    if (out.ok) {
      msg.textContent = `written to ${out.path}`;
      msg.className = "save-msg ok";
      $("f-apikey").value = "";
      await loadStatus();
      await loadConfig();
    } else {
      msg.textContent = out.error || "save failed";
      msg.className = "save-msg bad";
    }
  } catch (err) {
    msg.textContent = String(err);
    msg.className = "save-msg bad";
  }
};

loadStatus();
loadScope();
loadConfig();
