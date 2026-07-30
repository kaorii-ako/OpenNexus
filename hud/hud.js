/* NEXUS HUD.
 *
 * Requirement 1c is enforced here structurally: `renderEvent()` is the only
 * function in this file that turns an event into DOM. The live poll calls it,
 * and replay calls it. There is no second renderer, so a replayed event cannot
 * look different from a live one — and the render models both consume come from
 * the same server-side `render.render_model`.
 *
 * Everything drawn is read from vault/ and memory/events.jsonl. Where there is
 * no real data, the HUD says so out loud rather than showing a zero.
 */

const $ = (id) => document.getElementById(id);

const state = {
  mode: "live",          // "live" | "replay"
  seenSeq: 0,            // highest seq rendered, for incremental live polling
  speeds: [1, 2, 4, 8],
  speedIdx: 0,
  replayAbort: null,
  pollTimer: null,
  graph: { nodes: [], edges: [] },
};

/* ── the single render path ─────────────────────────────────────────────── */

function renderEvent(model) {
  const el = document.createElement("div");
  const kind = model.outcome || (model.type.startsWith("evolve") ? "evolve" : "");
  el.className = `ev ${kind}`;

  const top = document.createElement("div");
  top.className = "ev-top";
  top.innerHTML =
    `<span class="ev-seq">#${model.seq}</span>` +
    `<span class="ev-clock">${model.clock}</span>` +
    `<span class="ev-type ${model.type}">${model.type.replace(/_/g, " ")}</span>` +
    (model.outcome ? `<span class="ev-outcome">${model.outcome}</span>` : "");
  el.appendChild(top);

  const head = document.createElement("div");
  head.className = "ev-head";
  head.textContent = model.headline || "";
  el.appendChild(head);

  (model.detail || []).forEach((d) => {
    const row = document.createElement("div");
    row.className = "ev-detail";
    row.textContent = d;
    el.appendChild(row);
  });

  const stream = $("event-stream");
  stream.appendChild(el);
  stream.scrollTop = stream.scrollHeight;
  return el;
}

function clearStream() {
  $("event-stream").innerHTML = "";
}

/* ── metrics ────────────────────────────────────────────────────────────── */

function setMetric(id, value, { placeholder = "no data yet" } = {}) {
  const el = $(id);
  if (value === null || value === undefined) {
    el.textContent = placeholder;
    el.classList.add("placeholder");
  } else {
    el.textContent = value;
    el.classList.remove("placeholder");
  }
}

function renderMetrics(m, graph) {
  setMetric("m-notes", m.vault_notes);
  setMetric("m-links", graph ? graph.edges.length : null);
  setMetric("m-branches", m.skill_branches);
  setMetric("m-pointers", m.skill_pointers);
  setMetric("m-triggers", m.triggers);
  setMetric("m-routes", m.routes_total);
  setMetric("m-clean", m.outcomes.clean);
  setMetric("m-corrected", m.outcomes.corrected);
  setMetric("m-unused", m.outcomes.unused);
  setMetric("m-applied", m.evolve_applied);
  setMetric("m-rejected", m.evolve_rejected);
  setMetric("m-reverted", m.evolve_reverted);
  setMetric("m-events", m.events_total);
  $("events-count").textContent = `${m.events_total} logged`;

  // How far the log is from the evidence threshold `evolve` requires. Shown so
  // "not enough signal yet" is a visible distance rather than a surprise.
  const need = m.evolve_min_events;
  if (need === null || need === undefined) {
    setMetric("m-signal", null);
    $("signal-fill").style.width = "0%";
    $("signal-note").textContent = "";
  } else {
    const have = m.routes_total;
    setMetric("m-signal", `${have}/${need}`);
    $("signal-fill").style.width = `${Math.min(100, (100 * have) / need)}%`;
    $("signal-fill").className = m.evolve_ready ? "ready" : "";
    $("signal-note").textContent = m.evolve_ready
      ? "enough history — evolve can propose"
      : `${need - have} more routing event(s) before evolve will propose`;
  }

  // Hero stat. `clean_route_rate` is null until routing has actually happened;
  // showing 0% there would read as a real score for a system with no history.
  const fig = $("hero-figure");
  if (m.clean_route_rate === null || m.clean_route_rate === undefined) {
    fig.textContent = "no routing history yet";
    fig.classList.add("placeholder");
    $("hero-sub").textContent = "run `nexus route \"…\"` or ask a question — this fills in from real events";
  } else {
    fig.textContent = `${m.clean_route_rate}%`;
    fig.classList.remove("placeholder");
    $("hero-sub").textContent =
      `${m.outcomes.clean} of ${m.routes_total} routing decisions needed no mid-turn correction`;
  }

  const bar = $("hero-bar");
  bar.innerHTML = "";
  const total = m.routes_total || 0;
  if (total > 0) {
    [["clean", m.outcomes.clean], ["corrected", m.outcomes.corrected], ["unused", m.outcomes.unused]]
      .forEach(([name, n]) => {
        if (!n) return;
        const seg = document.createElement("i");
        seg.className = `b-${name}`;
        seg.style.width = `${(100 * n) / total}%`;
        bar.appendChild(seg);
      });
  }

  const badge = $("integrity-badge");
  badge.className = `badge ${m.log_intact ? "ok" : "bad"}`;
  $("integrity-text").textContent = m.log_intact ? "log intact" : "log tampered";
}

/* ── vault graph ────────────────────────────────────────────────────────── */

const DOMAIN_COLOR = {
  orchestrator: "#a78bfa",
  dev: "#4fd6c8",
  trading: "#f0b429",
};
const DANGLING = "#ff6b5f";

const canvas = $("graph-canvas");
const ctx = canvas.getContext("2d");
let sim = { nodes: [], edges: [], hover: null };

function sizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return rect;
}

function buildGraph(graph) {
  state.graph = graph;
  const rect = canvas.getBoundingClientRect();
  const cx = rect.width / 2 || 300;
  const cy = rect.height / 2 || 250;

  const byId = new Map();
  const nodes = graph.nodes.map((n, i) => {
    const angle = (i / Math.max(graph.nodes.length, 1)) * Math.PI * 2;
    const node = {
      ...n,
      dangling: false,
      x: cx + Math.cos(angle) * 90 + (Math.random() - 0.5) * 20,
      y: cy + Math.sin(angle) * 90 + (Math.random() - 0.5) * 20,
      vx: 0, vy: 0,
    };
    byId.set(n.id, node);
    return node;
  });

  // A links: entry pointing at a note that does not exist is drawn as a ghost
  // node rather than dropped, so a broken link is visible instead of invisible.
  graph.edges.forEach((e) => {
    if (!e.resolved && !byId.has(e.target)) {
      const ghost = {
        id: e.target, title: e.target, domain: "missing", tags: [],
        kind: "dangling", degree: 1, dangling: true,
        x: cx + (Math.random() - 0.5) * 200,
        y: cy + (Math.random() - 0.5) * 200,
        vx: 0, vy: 0,
      };
      byId.set(e.target, ghost);
      nodes.push(ghost);
    }
  });

  sim.nodes = nodes;
  sim.edges = graph.edges
    .map((e) => ({ s: byId.get(e.source), t: byId.get(e.target), resolved: e.resolved }))
    .filter((e) => e.s && e.t);

  $("graph-empty").classList.toggle("show", nodes.length === 0);
}

function stepPhysics(rect) {
  const cx = rect.width / 2;
  const cy = rect.height / 2;
  const n = sim.nodes;

  for (let i = 0; i < n.length; i++) {
    const a = n[i];
    a.vx += (cx - a.x) * 0.0016;
    a.vy += (cy - a.y) * 0.0016;

    for (let j = i + 1; j < n.length; j++) {
      const b = n[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx * dx + dy * dy || 0.01;
      const d = Math.sqrt(d2);
      const force = 2400 / d2;
      const fx = (dx / d) * force, fy = (dy / d) * force;
      a.vx -= fx; a.vy -= fy;
      b.vx += fx; b.vy += fy;
    }
  }

  sim.edges.forEach((e) => {
    const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const force = (d - 110) * 0.012;
    const fx = (dx / d) * force, fy = (dy / d) * force;
    e.s.vx += fx; e.s.vy += fy;
    e.t.vx -= fx; e.t.vy -= fy;
  });

  n.forEach((node) => {
    node.vx *= 0.86; node.vy *= 0.86;
    node.x += node.vx; node.y += node.vy;
    node.x = Math.max(24, Math.min(rect.width - 24, node.x));
    node.y = Math.max(24, Math.min(rect.height - 24, node.y));
  });
}

function nodeRadius(node) {
  return 4 + Math.min(node.degree || 0, 6) * 1.5;
}

function draw(rect) {
  ctx.clearRect(0, 0, rect.width, rect.height);

  sim.edges.forEach((e) => {
    ctx.beginPath();
    ctx.moveTo(e.s.x, e.s.y);
    ctx.lineTo(e.t.x, e.t.y);
    if (e.resolved) {
      ctx.strokeStyle = "rgba(79, 214, 200, 0.2)";
      ctx.setLineDash([]);
    } else {
      ctx.strokeStyle = "rgba(255, 107, 95, 0.4)";
      ctx.setLineDash([3, 3]);
    }
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);
  });

  sim.nodes.forEach((node) => {
    const r = nodeRadius(node);
    const color = node.dangling ? DANGLING : (DOMAIN_COLOR[node.domain] || "#5c6b7a");

    ctx.beginPath();
    ctx.arc(node.x, node.y, r * 2.6, 0, Math.PI * 2);
    ctx.fillStyle = color + "1a";
    ctx.fill();

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    if (sim.hover === node) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    if (sim.nodes.length <= 28 || sim.hover === node) {
      ctx.font = "10px ui-monospace, Menlo, monospace";
      ctx.fillStyle = "#5c6b7a";
      ctx.textAlign = "center";
      const label = node.title.length > 22 ? node.title.slice(0, 21) + "…" : node.title;
      ctx.fillText(label, node.x, node.y + r + 12);
    }
  });
}

function animate() {
  const rect = sizeCanvas();
  if (rect.width > 0) {
    stepPhysics(rect);
    draw(rect);
  }
  requestAnimationFrame(animate);
}

canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  sim.hover = sim.nodes.find((n) => Math.hypot(n.x - mx, n.y - my) < nodeRadius(n) + 7) || null;

  const tip = $("node-tip");
  if (sim.hover) {
    const n = sim.hover;
    tip.innerHTML = n.dangling
      ? `<b>${n.id}</b><span>dangling link — no note with this slug exists</span>`
      : `<b>${n.title}</b><span>${n.domain} · ${n.kind} · ${n.date || "no date"}<br>${n.degree} link(s)${n.tags.length ? "<br>" + n.tags.join(", ") : ""}</span>`;
    tip.classList.add("show");
    tip.style.left = Math.min(mx + 14, rect.width - 270) + "px";
    tip.style.top = (my + 14) + "px";
  } else {
    tip.classList.remove("show");
  }
});
canvas.addEventListener("mouseleave", () => {
  sim.hover = null;
  $("node-tip").classList.remove("show");
});

/* ── data flow ──────────────────────────────────────────────────────────── */

async function loadState() {
  const res = await fetch("/api/state");
  const data = await res.json();
  renderMetrics(data.metrics, data.graph);
  buildGraph(data.graph);

  if (state.mode === "live") {
    clearStream();
    state.seenSeq = 0;
    data.events.forEach((m) => {
      renderEvent(m);
      state.seenSeq = Math.max(state.seenSeq, m.seq);
    });
  }
  return data;
}

async function pollLive() {
  if (state.mode !== "live") return;
  try {
    const res = await fetch(`/api/events?since_seq=${state.seenSeq}`);
    const { events } = await res.json();
    if (events.length) {
      events.forEach((m) => {
        renderEvent(m);
        state.seenSeq = Math.max(state.seenSeq, m.seq);
      });
      const m = await (await fetch("/api/metrics")).json();
      renderMetrics(m, state.graph);
      const g = await (await fetch("/api/graph")).json();
      if (g.nodes.length !== state.graph.nodes.length || g.edges.length !== state.graph.edges.length) {
        buildGraph(g);
      }
    }
  } catch (err) {
    /* server stopped — the badge below reflects it on the next successful poll */
  }
}

/* ── replay ─────────────────────────────────────────────────────────────── */

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => { clearTimeout(t); reject(new Error("aborted")); }, { once: true });
  });

function setMode(mode) {
  state.mode = mode;
  $("btn-live").classList.toggle("active", mode === "live");
  $("replay-banner").classList.toggle("show", mode === "replay");
  $("btn-stop").disabled = mode !== "replay";
  $("feed-badge").className = `badge ${mode === "live" ? "ok" : ""}`;
  $("feed-text").textContent = mode === "live" ? "live" : "replaying";
}

async function startReplay(limit) {
  stopReplay();
  setMode("replay");
  clearStream();

  const res = await fetch("/api/state");
  const data = await res.json();
  let events = data.events;
  if (limit) events = events.slice(-limit);

  const controller = new AbortController();
  state.replayAbort = controller;
  const speed = state.speeds[state.speedIdx];

  try {
    let prev = null;
    for (const model of events) {
      const now = new Date(model.ts).getTime();
      // Real inter-event gaps, capped at 3s — same policy as replay.py, so the
      // shape of the history is preserved without waiting out idle periods.
      let delay = prev === null ? 0 : Math.min(Math.max(now - prev, 0), 3000);
      prev = now;
      if (delay) await sleep(delay / speed, controller.signal);
      renderEvent(model);
    }
    $("replay-banner").textContent = `replay finished — ${events.length} real event(s) from memory/events.jsonl`;
  } catch {
    /* aborted by the stop button */
  }
}

function stopReplay() {
  state.replayAbort?.abort();
  state.replayAbort = null;
}

async function goLive() {
  stopReplay();
  setMode("live");
  $("replay-banner").textContent = "replaying history — same log, same renderer as live";
  await loadState();
}

/* ── wiring ─────────────────────────────────────────────────────────────── */

$("btn-live").onclick = goLive;
$("btn-replay").onclick = () => startReplay(0);
$("btn-replay-20").onclick = () => startReplay(20);
$("btn-stop").onclick = () => { stopReplay(); setMode("replay"); $("btn-stop").disabled = true; };
$("btn-speed").onclick = () => {
  state.speedIdx = (state.speedIdx + 1) % state.speeds.length;
  $("btn-speed").innerHTML = `${state.speeds[state.speedIdx]}&times;`;
};

/* ── conversation ───────────────────────────────────────────────────────── */

/* Minimal inline markdown: fenced code, inline code, bold. Deliberately small —
   answers are terminal-flavoured text, not documents. Everything goes through
   textContent first so model output can never inject HTML. */
function formatAnswer(text) {
  const escape = (s) => { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; };
  const parts = text.split(/```/);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      const body = part.replace(/^[a-z]*\n/i, "");
      return `<pre><code>${escape(body)}</code></pre>`;
    }
    return escape(part)
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  }).join("");
}

function addMessage(role, text = "") {
  $("convo-hint")?.remove();
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.innerHTML = `<div class="msg-role">${role === "user" ? "you" : "nexus"}</div>
                  <div class="msg-body"></div>`;
  el.querySelector(".msg-body").textContent = text;
  const stream = $("convo-stream");
  stream.appendChild(el);
  stream.scrollTop = stream.scrollHeight;
  return el;
}

let asking = false;

async function ask(query) {
  if (asking || !query) return;
  asking = true;
  $("btn-send").disabled = true;

  addMessage("user", query);
  const reply = addMessage("nexus", "");
  const body = reply.querySelector(".msg-body");
  body.classList.add("caret");

  let answer = "";
  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop();

      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const msg = JSON.parse(line.slice(5).trim());

        if (msg.type === "route") {
          // Same render model the events panel uses — one schema, one meaning.
          renderEvent(msg.event);
          state.seenSeq = Math.max(state.seenSeq, msg.event.seq);
          const branches = msg.event.branches || [];
          const corrected = msg.event.outcome === "corrected";
          const meta = document.createElement("div");
          meta.className = "msg-meta";
          meta.innerHTML = branches
            .map((b) => `<span class="branch ${corrected ? "corrected" : ""}">${b}</span>`)
            .join("") + (corrected ? " routing corrected mid-turn" : "");
          reply.appendChild(meta);
        } else if (msg.type === "token") {
          answer += msg.text;
          body.textContent = answer;
          $("convo-stream").scrollTop = $("convo-stream").scrollHeight;
        } else if (msg.type === "error") {
          body.classList.remove("caret");
          const err = document.createElement("div");
          err.className = "msg-error";
          err.textContent = msg.error;
          reply.appendChild(err);
        } else if (msg.type === "done") {
          renderEvent(msg.event);
          state.seenSeq = Math.max(state.seenSeq, msg.event.seq);
          body.innerHTML = formatAnswer(answer);
          if (speakOn && answer) speak(answer);
        }
      }
    }
  } catch (err) {
    const el = document.createElement("div");
    el.className = "msg-error";
    el.textContent = String(err);
    reply.appendChild(el);
  } finally {
    body.classList.remove("caret");
    asking = false;
    $("btn-send").disabled = false;
    const m = await (await fetch("/api/metrics")).json();
    renderMetrics(m, state.graph);
  }
}

$("ask-form").onsubmit = (e) => {
  e.preventDefault();
  const input = $("ask-input");
  const query = input.value.trim();
  input.value = "";
  ask(query);
};

$("btn-route-only").onclick = async () => {
  const input = $("ask-input");
  const query = input.value.trim();
  if (!query) return;
  input.value = "";
  if (state.mode !== "live") await goLive();
  await fetch("/api/route", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  await pollLive();
};

document.querySelectorAll(".convo-examples .ex").forEach((btn) => {
  btn.onclick = () => ask(btn.textContent.trim());
});

/* ── voice — browser-native, nothing leaves the machine ─────────────────── */

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recogniser = null;
let micOn = false;
let speakOn = false;

if (SR) {
  recogniser = new SR();
  recogniser.continuous = false;
  recogniser.interimResults = true;
  recogniser.lang = navigator.language || "en-US";

  recogniser.onresult = (e) => {
    const transcript = [...e.results].map((r) => r[0].transcript).join("");
    $("ask-input").value = transcript;
    if (e.results[e.results.length - 1].isFinal) {
      const q = transcript.trim();
      $("ask-input").value = "";
      if (q) ask(q);
    }
  };
  recogniser.onend = () => {
    $("btn-mic").classList.remove("listening");
    if (micOn) { try { recogniser.start(); $("btn-mic").classList.add("listening"); } catch {} }
  };
  recogniser.onerror = () => $("btn-mic").classList.remove("listening");
} else {
  $("btn-mic").disabled = true;
  $("btn-mic").title = "this browser has no SpeechRecognition — try Chrome";
}

$("btn-mic").onclick = () => {
  if (!recogniser) return;
  micOn = !micOn;
  $("btn-mic").textContent = micOn ? "mic on" : "mic off";
  $("btn-mic").classList.toggle("on", micOn);
  if (micOn) {
    try { recogniser.start(); $("btn-mic").classList.add("listening"); } catch {}
  } else {
    recogniser.stop();
    $("btn-mic").classList.remove("listening");
  }
};

function speak(text) {
  if (!window.speechSynthesis) return;
  // Strip code blocks — reading punctuation aloud is useless.
  const spoken = text.replace(/```[\s\S]*?```/g, " code block ").replace(/`([^`]+)`/g, "$1");
  const utter = new SpeechSynthesisUtterance(spoken.slice(0, 1200));
  utter.rate = 1.05;
  utter.onstart = () => $("btn-speak").classList.add("speaking");
  utter.onend = () => $("btn-speak").classList.remove("speaking");
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utter);
}

if (!window.speechSynthesis) {
  $("btn-speak").disabled = true;
  $("btn-speak").title = "this browser has no speech synthesis";
}

$("btn-speak").onclick = () => {
  speakOn = !speakOn;
  $("btn-speak").textContent = speakOn ? "speak on" : "speak off";
  $("btn-speak").classList.toggle("on", speakOn);
  if (!speakOn) window.speechSynthesis?.cancel();
};

window.addEventListener("resize", () => sizeCanvas());

loadState().then(() => {
  animate();
  state.pollTimer = setInterval(pollLive, 2000);
});
