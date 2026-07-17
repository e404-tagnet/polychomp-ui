/**
 * Polychomp-UI Frontend
 * Catppuccin Mocha, dark mode, PRISM inspector
 */

const API_BASE = window.location.origin;
let currentProject = null;
let projects = [];
let settings = {
  modelEndpoint: "http://127.0.0.1:11434",
  modelName: "phi4-mini",
  usePrism: true,
  prismMode: "shadow",
  privacy: "local",
  prismVisible: false,
};

// ── DOM refs ────────────────────────────────────────────────
const projectList    = document.getElementById("project-list");
const messages       = document.getElementById("messages");
const messageInput   = document.getElementById("message-input");
const sendBtn        = document.getElementById("send-btn");
const projectName    = document.getElementById("project-name");
const prismPanel     = document.getElementById("prism-panel");
const prismContent   = document.getElementById("prism-content");
const appRoot        = document.getElementById("app");
const modelStatus    = document.getElementById("model-status");

// ── Init ─────────────────────────────────────────────────────
async function init() {
  loadSettings();
  const profile = await checkProfile();
  if (!profile) {
    showOnboarding();
  }
  await loadProjects();
  setupEventListeners();
  if (projects.length) selectProject(projects[0].id);
}

// ── Profile ─────────────────────────────────────────────────
async function checkProfile() {
  const res = await fetch(`${API_BASE}/api/profile`);
  const data = await res.json();
  if (data.exists) {
    // Apply profile defaults to settings
    const p = data.profile;
    if (p.privacy_default) settings.privacy = p.privacy_default;
    if (p.temperature_preference) {
      settings.temperature = p.temperature_preference === "cautious" ? 0.3 : p.temperature_preference === "creative" ? 0.8 : 0.5;
    }
    if (p.prism_visibility) {
      settings.prismVisible = p.prism_visibility === "visible";
    }
    return p;
  }
  return null;
}

function showOnboarding() {
  document.getElementById("onboarding-modal").classList.remove("hidden");
}

function closeOnboarding() {
  document.getElementById("onboarding-modal").classList.add("hidden");
}

async function saveOnboarding() {
  const getVal = (name) => document.querySelector(`input[name="${name}"]:checked`)?.value;
  
  const profile = {
    technical_level: getVal("q1"),
    interaction_style: getVal("q2"),
    correction_reaction: getVal("q3"),
    detail_preference: getVal("q4"),
    challenge_frequency: getVal("q5"),
    project_type: getVal("q6"),
    prism_visibility: getVal("q7"),
    temperature_preference: getVal("q8"),
    privacy_default: getVal("q9"),
    cross_project_memory: getVal("q10") === "true",
  };
  
  await fetch(`${API_BASE}/api/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  
  // Apply locally
  settings.privacy = profile.privacy_default;
  settings.temperature = profile.temperature_preference === "cautious" ? 0.3 : profile.temperature_preference === "creative" ? 0.8 : 0.5;
  settings.prismVisible = profile.prism_visibility === "visible";
  updateModelStatus();
  closeOnboarding();
}

// ── Projects ─────────────────────────────────────────────────
async function loadProjects() {
  const res = await fetch(`${API_BASE}/api/projects`);
  projects = await res.json();
  renderProjects();
}

function renderProjects() {
  projectList.innerHTML = "";
  for (const p of projects) {
    const el = document.createElement("div");
    el.className = "project-item" + (currentProject && p.id === currentProject.id ? " active" : "");
    el.dataset.id = p.id;
    el.innerHTML = `
      <span class="p-name">${escapeHtml(p.name)}</span>
      <span class="p-desc">${escapeHtml(p.description || "")}</span>
      <span class="p-date">${fmtDate(p.created)}</span>
    `;
    el.addEventListener("click", () => selectProject(p.id));
    projectList.appendChild(el);
  }
}

async function selectProject(pid) {
  const res = await fetch(`${API_BASE}/api/projects/${pid}`);
  currentProject = await res.json();
  projectName.textContent = currentProject.name;
  renderMessages();
  renderProjects();
}

async function createProject(name, description) {
  const res = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  const p = await res.json();
  projects.push(p);
  selectProject(p.id);
}

async function deleteProject(pid) {
  if (!confirm("Delete this project?")) return;
  await fetch(`${API_BASE}/api/projects/${pid}`, { method: "DELETE" });
  projects = projects.filter(p => p.id !== pid);
  if (currentProject && currentProject.id === pid) {
    currentProject = projects[0] || null;
    if (currentProject) await selectProject(currentProject.id);
    else { projectName.textContent = "Select a project"; messages.innerHTML = ""; }
  }
  renderProjects();
}

// ── Messages / Chat ──────────────────────────────────────────
function renderMessages() {
  messages.innerHTML = "";
  if (!currentProject || !currentProject.messages) return;
  for (const msg of currentProject.messages) {
    appendMessage(msg.role, msg.content, msg.prism_meta, false);
  }
  messages.scrollTop = messages.scrollHeight;
}

function appendMessage(role, content, prismMeta, animate = true) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}` + (animate ? "" : "");

  let chip = "";
  if (prismMeta && role === "user") {
    chip = `<button class="prism-chip route-${prismMeta.route}" data-meta='${JSON.stringify(prismMeta).replace(/'/g, "&#39;")}' title="Inspect PRISM analysis">${prismMeta.route} · ${Math.round(prismMeta.confidence * 100)}%</button>`;
  }

  wrapper.innerHTML = `
    <div class="message-bubble">${escapeHtml(content)}</div>
    <div class="message-meta">
      ${chip}
      <span class="ts">${fmtTime()}</span>
    </div>
  `;

  // Wire chip click to inspector
  const chipBtn = wrapper.querySelector(".prism-chip");
  if (chipBtn) {
    chipBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const meta = JSON.parse(chipBtn.dataset.meta);
      showPrismInspector(meta);
    });
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// ── PRISM Inspector ────────────────────────────────────────
function showPrismInspector(meta) {
  if (!meta) return;
  appRoot.classList.add("prism-open");
  prismPanel.classList.remove("hidden");

  const confClass = meta.confidence >= 0.7 ? "conf-high" : meta.confidence >= 0.4 ? "conf-med" : "conf-low";

  prismContent.innerHTML = `
    <div class="prism-block">
      <h4>Bias Detected</h4>
      <div class="prism-val bias">${meta.bias}</div>
    </div>
    <div class="prism-block">
      <h4>Confidence</h4>
      <div class="prism-val ${confClass}">${(meta.confidence * 100).toFixed(1)}%</div>
    </div>
    <div class="prism-block">
      <h4>Recommended Route</h4>
      <div class="prism-val route-${meta.route}">${meta.route.toUpperCase()}</div>
      <p style="margin-top:.4rem;color:var(--overlay0);font-size:.75rem;">${meta.reason}</p>
    </div>
    <div class="prism-block">
      <h4>Session Metrics</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-top:.3rem;">
        <div><span style="color:var(--overlay0)">Temp</span><br><span class="prism-val">${meta.temperature}</span></div>
        <div><span style="color:var(--overlay0)">Assertive</span><br><span class="prism-val">${meta.assertiveness}</span></div>
        <div><span style="color:var(--overlay0)">Topic Drift</span><br><span class="prism-val">${meta.topic_drift}</span></div>
        <div><span style="color:var(--overlay0)">Factual</span><br><span class="prism-val">${meta.factual ? "Yes" : "No"}</span></div>
      </div>
    </div>
  `;
}

function hidePrismInspector() {
  appRoot.classList.remove("prism-open");
  prismPanel.classList.add("hidden");
  prismContent.innerHTML = `<p class="prism-placeholder">Select a message to inspect.</p>`;
}

// ── Send Message ───────────────────────────────────────────
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || !currentProject) return;

  messageInput.value = "";
  messageInput.style.height = "auto";
  appendMessage("user", text, null, true);

  // Show typing indicator
  const typing = document.createElement("div");
  typing.className = "message assistant";
  typing.id = "typing";
  typing.innerHTML = `<div class="message-bubble" style="opacity:.6;">…</div>`;
  messages.appendChild(typing);
  messages.scrollTop = messages.scrollHeight;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: currentProject.id,
        message: text,
        model_endpoint: settings.modelEndpoint,
        model_name: settings.modelName,
        use_prism: settings.usePrism,
        mode: settings.prismMode,
      }),
    });
    const data = await res.json();

    typing.remove();
    appendMessage("assistant", data.response, data.prism_meta, true);

    // Refresh project state
    currentProject.messages.push({ role: "user", content: text, prism_meta: data.prism_meta });
    currentProject.messages.push({ role: "assistant", content: data.response });

  } catch (err) {
    typing.remove();
    appendMessage("assistant", `[Error: ${err.message}]`, null, true);
  }
}

// ── Settings ────────────────────────────────────────────────
function loadSettings() {
  const saved = localStorage.getItem("polychomp-settings");
  if (saved) Object.assign(settings, JSON.parse(saved));
  document.getElementById("model-endpoint").value = settings.modelEndpoint;
  document.getElementById("model-name").value = settings.modelName;
  document.getElementById("use-prism").checked = settings.usePrism;
  document.getElementById("prism-mode").value = settings.prismMode;
  document.querySelector(`input[name="privacy"][value="${settings.privacy}"]`).checked = true;
  updateModelStatus();
}

function saveSettings() {
  settings.modelEndpoint = document.getElementById("model-endpoint").value;
  settings.modelName = document.getElementById("model-name").value;
  settings.usePrism = document.getElementById("use-prism").checked;
  settings.prismMode = document.getElementById("prism-mode").value;
  settings.privacy = document.querySelector("input[name=\"privacy\"]:checked").value;
  localStorage.setItem("polychomp-settings", JSON.stringify(settings));
  updateModelStatus();
  closeSettings();
}

function updateModelStatus() {
  const priv = settings.privacy === "local" ? "Local" : settings.privacy === "hybrid" ? "Hybrid" : "Cloud";
  modelStatus.textContent = `${priv} · ${settings.modelName} · PRISM ${settings.prismMode}`;
}

// ── Event Listeners ─────────────────────────────────────────
function setupEventListeners() {
  sendBtn.addEventListener("click", sendMessage);
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = messageInput.scrollHeight + "px";
  });

  document.getElementById("prism-toggle").addEventListener("click", () => {
    if (prismPanel.classList.contains("hidden")) {
      appRoot.classList.add("prism-open");
      prismPanel.classList.remove("hidden");
    } else {
      hidePrismInspector();
    }
  });
  document.getElementById("prism-close").addEventListener("click", hidePrismInspector);

  document.getElementById("settings-btn").addEventListener("click", openSettings);
  document.getElementById("close-settings").addEventListener("click", closeSettings);
  document.getElementById("save-settings").addEventListener("click", saveSettings);

  document.getElementById("new-project-btn").addEventListener("click", openNewProject);
  document.getElementById("close-new-project").addEventListener("click", closeNewProject);
  document.getElementById("create-project").addEventListener("click", () => {
    const name = document.getElementById("project-name-input").value.trim();
    const desc = document.getElementById("project-desc-input").value.trim();
    if (!name) return;
    createProject(name, desc);
    closeNewProject();
    document.getElementById("project-name-input").value = "";
    document.getElementById("project-desc-input").value = "";
  });

  document.getElementById("close-onboarding").addEventListener("click", closeOnboarding);
  document.getElementById("save-onboarding").addEventListener("click", saveOnboarding);

  document.getElementById("clear-chat-btn").addEventListener("click", () => {
    if (!currentProject) return;
    if (!confirm("Clear messages for this project?")) return;
    currentProject.messages = [];
    messages.innerHTML = "";
    fetch(`${API_BASE}/api/projects/${currentProject.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentProject),
    });
  });
}

function openSettings() { document.getElementById("settings-modal").classList.remove("hidden"); }
function closeSettings() { document.getElementById("settings-modal").classList.add("hidden"); }
function openNewProject() { document.getElementById("new-project-modal").classList.remove("hidden"); }
function closeNewProject() { document.getElementById("new-project-modal").classList.add("hidden"); }

// ── Utils ───────────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
function fmtDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
function fmtTime() {
  return new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

// ── Start ───────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", init);
