/**
 * Polychomp-UI Frontend
 * Catppuccin Mocha, dark mode, Chat Analysis
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
  analysisVisible: false,
  temperature: 0.5,
  systemPrompt: "",
};

// ── DOM refs ────────────────────────────────────────────────
const projectList    = document.getElementById("project-list");
const messages       = document.getElementById("messages");
const messageInput   = document.getElementById("message-input");
const sendBtn        = document.getElementById("send-btn");
const projectName    = document.getElementById("project-name");
const analysisPanel  = document.getElementById("analysis-panel");
const analysisContent = document.getElementById("analysis-content");
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
  const p = data.profile;
  if (p.privacy_default) settings.privacy = p.privacy_default;
  if (p.temperature_preference) {
    settings.temperature = p.temperature_preference === "cautious" ? 0.2 : p.temperature_preference === "creative" ? 0.8 : 0.5;
  }
  if (p.prism_visibility) {
    settings.analysisVisible = p.prism_visibility === "visible";
  }
  if (p.system_prompt) {
    settings.systemPrompt = p.system_prompt;
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
  const getText = (name) => document.querySelector(`input[name="${name}"]`)?.value?.trim() || "";
  const getChecked = (name) => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(el => el.value);

  const promptMode = getVal("q10_prompt_mode");
  let systemPrompt = "";

  if (promptMode === "custom") {
    systemPrompt = document.getElementById("custom-system-prompt").value.trim();
  } else {
    // Build prompt from guided answers
    const role = getText("q10a_role");
    const focus = getText("q10b_focus");
    const tone = getVal("q10c_tone");
    const avoid = getChecked("q10d_avoid");
    const extra = document.querySelector(`textarea[name="q10e_extra"]`)?.value?.trim() || "";

    const parts = [];
    if (role) parts.push(`You are assisting a ${role}.`);
    if (focus) parts.push(`Their main focus is ${focus}.`);
    if (tone) {
      const toneMap = {
        professional: "Be professional and concise.",
        casual: "Be casual and friendly.",
        mentor: "Be mentor-like — teach them as you go, explain concepts clearly.",
        peer: "Be collaborative and treat them as a peer — no hierarchy."
      };
      parts.push(toneMap[tone] || "");
    }
    if (avoid.length) {
      const avoidMap = {
        jargon: "unnecessary jargon",
        assumptions: "making assumptions about the user's knowledge",
        verbose: "being overly verbose",
        apologies: "excessive apologies"
      };
      parts.push(`Avoid ${avoid.map(a => avoidMap[a]).join(", ")}.`);
    }
    if (extra) parts.push(extra);
    systemPrompt = parts.join("\n");
  }

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
    system_prompt: systemPrompt,
  };

  await fetch(`${API_BASE}/api/profile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });

  settings.privacy = profile.privacy_default;
  settings.temperature = profile.temperature_preference === "cautious" ? 0.2 : profile.temperature_preference === "creative" ? 0.8 : 0.5;
  settings.analysisVisible = profile.prism_visibility === "visible";
  settings.systemPrompt = systemPrompt;
  updateModelStatus();
  closeOnboarding();
}

function buildPromptPreview() {
  const promptMode = document.querySelector('input[name="q10_prompt_mode"]:checked')?.value || "guided";
  let systemPrompt = "";

  if (promptMode === "custom") {
    systemPrompt = document.getElementById("custom-system-prompt")?.value?.trim() || "(empty)";
  } else {
    const getText = (name) => document.querySelector(`input[name="${name}"]`)?.value?.trim() || "";
    const getVal = (name) => document.querySelector(`input[name="${name}"]:checked`)?.value;
    const getChecked = (name) => Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(el => el.value);

    const role = getText("q10a_role");
    const focus = getText("q10b_focus");
    const tone = getVal("q10c_tone");
    const avoid = getChecked("q10d_avoid");
    const extra = document.querySelector(`textarea[name="q10e_extra"]`)?.value?.trim() || "";

    const parts = [];
    if (role) parts.push(`You are assisting a ${role}.`);
    if (focus) parts.push(`Their main focus is ${focus}.`);
    if (tone) {
      const toneMap = {
        professional: "Be professional and concise.",
        casual: "Be casual and friendly.",
        mentor: "Be mentor-like — teach them as you go, explain concepts clearly.",
        peer: "Be collaborative and treat them as a peer — no hierarchy."
      };
      parts.push(toneMap[tone] || "");
    }
    if (avoid.length) {
      const avoidMap = {
        jargon: "unnecessary jargon",
        assumptions: "making assumptions about the user's knowledge",
        verbose: "being overly verbose",
        apologies: "excessive apologies"
      };
      parts.push(`Avoid ${avoid.map(a => avoidMap[a]).join(", ")}.`);
    }
    if (extra) parts.push(extra);
    systemPrompt = parts.length ? parts.join("\n") : "(answer the guided questions to build your prompt)";
  }

  document.getElementById("prompt-preview").classList.remove("hidden");
  document.getElementById("prompt-preview-text").textContent = systemPrompt;
}

function togglePromptMode() {
  const mode = document.querySelector('input[name="q10_prompt_mode"]:checked')?.value;
  const customBox = document.getElementById("custom-prompt-box");
  const guidedBox = document.getElementById("guided-prompt-box");
  if (mode === "custom") {
    customBox.classList.remove("hidden");
    guidedBox.classList.add("hidden");
  } else {
    customBox.classList.add("hidden");
    guidedBox.classList.remove("hidden");
  }
}

// ── Plugin Manager ────────────────────────────────────────
let pluginStore = [];
let pluginFilter = "all";

async function loadPlugins(force = false) {
  if (!force && pluginStore.length) return;
  const res = await fetch(`${API_BASE}/api/plugins`);
  pluginStore = await res.json();
  renderPluginList(pluginFilter);
}

function renderPluginList(filter) {
  pluginFilter = filter;
  const container = document.getElementById("plugin-list");
  container.innerHTML = "";

  const filtered = pluginStore.filter(p => filter === "all" || p.type === filter);
  if (!filtered.length) {
    container.innerHTML = `<p style="color:var(--overlay0);text-align:center;padding:1rem;">No plugins found.</p>`;
    return;
  }

  for (const p of filtered) {
    const icon = p.icon ? "📦" : "🔌";
    const tagsHtml = (p.tags || []).map(t => `<span class="plugin-tag">${t}</span>`).join("");
    const el = document.createElement("div");
    el.className = "plugin-card";
    el.innerHTML = `
      <div class="plugin-icon">${icon}</div>
      <div class="plugin-info">
        <div class="plugin-name">${escapeHtml(p.name)}</div>
        <div class="plugin-desc">${escapeHtml(p.description)}</div>
        <div class="plugin-meta">
          <span class="plugin-type ${p.type}">${p.type}</span>
          <span>v${p.version}</span>
          <span>${p.author}</span>
          <div class="plugin-tags">${tagsHtml}</div>
        </div>
      </div>
      <div class="plugin-toggle">
        <label>
          <input type="checkbox" data-id="${p.id}" ${p.enabled ? "checked" : ""}>
          ${p.enabled ? "On" : "Off"}
        </label>
      </div>
    `;
    const checkbox = el.querySelector('input[type="checkbox"]');
    checkbox.addEventListener("change", async () => {
      await togglePlugin(p.id, checkbox.checked);
    });
    container.appendChild(el);
  }
}

async function togglePlugin(pluginId, enable) {
  const endpoint = enable ? `/api/plugins/${pluginId}/enable` : `/api/plugins/${pluginId}/disable`;
  await fetch(`${API_BASE}${endpoint}`, { method: "POST" });
  await loadPlugins(true);
}

function openPluginManager() {
  document.getElementById("plugin-modal").classList.remove("hidden");
  loadPlugins();
}

function closePluginManager() {
  document.getElementById("plugin-modal").classList.add("hidden");
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
  wrapper.className = `message ${role}`;

  let chip = "";
  if (prismMeta && role === "user") {
    chip = `<button class="prism-chip route-${prismMeta.route}" data-meta='${JSON.stringify(prismMeta).replace(/'/g, "&#39;")}' title="Inspect analysis">${prismMeta.route} - ${Math.round(prismMeta.confidence * 100)}%</button>`;
  }

  wrapper.innerHTML = `
    <div class="message-bubble">${escapeHtml(content)}</div>
    <div class="message-meta">
      ${chip}
      <span class="ts">${fmtTime()}</span>
    </div>
  `;

  const chipBtn = wrapper.querySelector(".prism-chip");
  if (chipBtn) {
    chipBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const meta = JSON.parse(chipBtn.dataset.meta);
      showAnalysisInspector(meta);
    });
  }

  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

// ── Typewriter Effect ──────────────────────────────────────
async function typewriterText(element, text, speedMs = 30) {
  const words = text.split(/(\s+)/); // keep whitespace
  let html = "";
  element.innerHTML = "";
  element.classList.add("typewriter-cursor");

  for (let i = 0; i < words.length; i++) {
    html += escapeHtml(words[i]);
    element.innerHTML = html;
    messages.scrollTop = messages.scrollHeight;
    await sleep(speedMs);
  }

  element.classList.remove("typewriter-cursor");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── Chat Analysis Panel ────────────────────────────────────
function showAnalysisInspector(meta, tokenCount = 0, latencyMs = 0) {
  if (!meta) return;
  appRoot.classList.add("analysis-open");
  analysisPanel.classList.remove("hidden");

  const confClass = meta.confidence >= 0.7 ? "conf-high" : meta.confidence >= 0.4 ? "conf-med" : "conf-low";

  analysisContent.innerHTML = `
    <div class="analysis-block">
      <h4>Bias Detected</h4>
      <div class="analysis-val bias">${meta.bias}</div>
    </div>
    <div class="analysis-block">
      <h4>Confidence</h4>
      <div class="analysis-val ${confClass}">${(meta.confidence * 100).toFixed(1)}%</div>
    </div>
    <div class="analysis-block">
      <h4>Recommended Route</h4>
      <div class="analysis-val route-${meta.route}">${meta.route.toUpperCase()}</div>
      <p style="margin-top:.4rem;color:var(--overlay0);font-size:.75rem;">${meta.reason}</p>
    </div>
    <div class="analysis-block">
      <h4>Session Metrics</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-top:.3rem;">
        <div><span style="color:var(--overlay0)">Temp</span><br><span class="analysis-val">${meta.temperature}</span></div>
        <div><span style="color:var(--overlay0)">Assertive</span><br><span class="analysis-val">${meta.assertiveness}</span></div>
        <div><span style="color:var(--overlay0)">Topic Drift</span><br><span class="analysis-val">${meta.topic_drift}</span></div>
        <div><span style="color:var(--overlay0)">Factual</span><br><span class="analysis-val">${meta.factual ? "Yes" : "No"}</span></div>
      </div>
    </div>
    <div class="analysis-block">
      <h4>Tokens</h4>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-top:.3rem;">
        <div><span style="color:var(--overlay0)">Total</span><br><span class="analysis-val">${tokenCount > 0 ? tokenCount : '--'}</span></div>
        <div><span style="color:var(--overlay0)">Latency</span><br><span class="analysis-val">${latencyMs > 0 ? latencyMs + 'ms' : '--'}</span></div>
      </div>
    </div>
  `;
}

function hideAnalysisInspector() {
  appRoot.classList.remove("analysis-open");
  analysisPanel.classList.add("hidden");
  analysisContent.innerHTML = `<p class="analysis-placeholder">Send a message to see analysis.</p>`;
}

// ── Send Message ───────────────────────────────────────────
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || !currentProject) return;

  messageInput.value = "";
  messageInput.style.height = "auto";
  appendMessage("user", text, null, true);

  // Show animated thinking indicator
  const typing = document.createElement("div");
  typing.className = "message assistant";
  typing.id = "typing";
  typing.innerHTML = `
    <div class="message-bubble">
      <div class="thinking-bubble">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>
  `;
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
        temperature: settings.temperature,
        system_prompt: settings.systemPrompt || undefined,
      }),
    });
    const data = await res.json();

    typing.remove();

    // Create empty assistant bubble for typewriter
    const wrapper = document.createElement("div");
    wrapper.className = "message assistant";
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    wrapper.appendChild(bubble);
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;

    // Typewriter effect at 30ms
    await typewriterText(bubble, data.response, 30);

    // Add meta row after typing
    const metaDiv = document.createElement("div");
    metaDiv.className = "message-meta";
    metaDiv.innerHTML = `<span class="ts">${fmtTime()}</span>`;
    wrapper.appendChild(metaDiv);

    // Auto-show analysis if panel is open
    if (data.prism_meta && !analysisPanel.classList.contains("hidden")) {
      showAnalysisInspector(data.prism_meta, data.token_count || 0, data.latency_ms || 0);
    }

    // Refresh project state
    currentProject.messages.push({ role: "user", content: text, prism_meta: data.prism_meta });
    currentProject.messages.push({ role: "assistant", content: data.response });

    // Auto-show analysis panel on first message if user prefers visible
    if (data.prism_meta && settings.analysisVisible && analysisPanel.classList.contains("hidden")) {
      showAnalysisInspector(data.prism_meta, data.token_count || 0, data.latency_ms || 0);
    }

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

  // Temperature slider
  const tempSlider = document.getElementById("temperature");
  if (tempSlider) {
    tempSlider.value = Math.round(settings.temperature * 100);
    updateTempLabel(settings.temperature);
    tempSlider.addEventListener("input", () => {
      const val = tempSlider.value / 100;
      updateTempLabel(val);
    });
  }

  // System prompt
  const sysPrompt = document.getElementById("system-prompt");
  if (sysPrompt) sysPrompt.value = settings.systemPrompt || "";

  updateModelStatus();
}

function updateTempLabel(val) {
  const labels = [
    { max: 0.15, text: "Very Cautious" },
    { max: 0.35, text: "Cautious" },
    { max: 0.55, text: "Balanced" },
    { max: 0.75, text: "Exploratory" },
    { max: 1.0, text: "Creative" },
  ];
  const label = labels.find(l => val <= l.max)?.text || "Balanced";
  const el = document.getElementById("temp-label");
  if (el) el.textContent = label;
}

function saveSettings() {
  settings.modelEndpoint = document.getElementById("model-endpoint").value;
  settings.modelName = document.getElementById("model-name").value;
  settings.usePrism = document.getElementById("use-prism").checked;
  settings.prismMode = document.getElementById("prism-mode").value;
  settings.privacy = document.querySelector("input[name=\"privacy\"]:checked").value;
  const tempSlider = document.getElementById("temperature");
  if (tempSlider) settings.temperature = tempSlider.value / 100;
  const sysPrompt = document.getElementById("system-prompt");
  if (sysPrompt) settings.systemPrompt = sysPrompt.value;
  localStorage.setItem("polychomp-settings", JSON.stringify(settings));
  updateModelStatus();
  closeSettings();
}

function updateModelStatus() {
  const priv = settings.privacy === "local" ? "Local" : settings.privacy === "hybrid" ? "Hybrid" : "Cloud";
  const tempLabel = settings.temperature <= 0.3 ? "Cautious" : settings.temperature >= 0.7 ? "Creative" : "Balanced";
  modelStatus.textContent = `${priv} - ${settings.modelName} - Analysis ${settings.prismMode} - ${tempLabel}`;
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

  document.getElementById("analysis-toggle").addEventListener("click", () => {
    if (analysisPanel.classList.contains("hidden")) {
      appRoot.classList.add("analysis-open");
      analysisPanel.classList.remove("hidden");
    } else {
      hideAnalysisInspector();
    }
  });
  document.getElementById("analysis-close").addEventListener("click", hideAnalysisInspector);

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

  // Prompt mode toggle
  document.querySelectorAll('input[name="q10_prompt_mode"]').forEach(el => {
    el.addEventListener("change", togglePromptMode);
  });
  document.getElementById("preview-prompt-btn")?.addEventListener("click", buildPromptPreview);

  document.getElementById("plugins-btn").addEventListener("click", openPluginManager);
  document.getElementById("close-plugins").addEventListener("click", closePluginManager);
  document.getElementById("refresh-plugins").addEventListener("click", () => loadPlugins(true));

  // Plugin filter tabs
  document.querySelectorAll(".plugin-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".plugin-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      renderPluginList(tab.dataset.filter);
    });
  });

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
