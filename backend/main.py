import os
import sys
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Prism-UI-UI")
PRISM_ROOT = Path(__file__).resolve().parents[1] / ".." / "prism-scaffold" / "src"
sys.path.insert(0, str(PRISM_ROOT))

from prism.core.pipeline import PrismPipeline, PipelineResult
from prism.core.memory import MemoryStore, MemoryEntry

APP_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = APP_ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

# ── Plugin Manager ────────────────────────────────────────
from plugin_manager import PluginManager

PLUGINS_DIR = APP_ROOT / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
plugin_mgr = PluginManager(PLUGINS_DIR)

# Load persisted state
PLUGIN_STATE_PATH = APP_ROOT / "projects" / "__plugin_state__.json"
if PLUGIN_STATE_PATH.exists():
    plugin_mgr.load_state(PLUGIN_STATE_PATH)
else:
    # Auto-enable built-in plugins
    for pid in ["skill-summarize", "tool-web-search", "scaffold-prism"]:
        if pid in plugin_mgr._registry:
            plugin_mgr.load(pid)

app = FastAPI(title="Prism-UI-UI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────

class UserProfile(BaseModel):
    technical_level: str       # beginner / intermediate / advanced / expert
    interaction_style: str       # direct / exploratory / step_by_step
    correction_reaction: str   # appreciate / neutral / defensive
    detail_preference: str     # concise / balanced / detailed
    challenge_frequency: str   # often / sometimes / rarely / never
    project_type: str          # creative / analytical / mixed
    prism_visibility: str      # visible / hidden
    temperature_preference: str # cautious / balanced / creative
    privacy_default: str       # local / hybrid / cloud
    system_prompt: Optional[str] = None  # custom or built system prompt

class ChatMessage(BaseModel):
    role: str
    content: str
    prism_meta: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    project_id: str
    message: str
    model_endpoint: str = "http://127.0.0.1:11434"
    model_name: str = "phi4-mini"
    use_prism: bool = True
    mode: str = "shadow"  # shadow | active
    temperature: Optional[float] = None  # override PRISM temperature
    system_prompt: Optional[str] = None  # custom system prompt

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    workspace_path: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: str
    created: str
    workspace_path: Optional[str] = None

# ── Helpers ───────────────────────────────────────────────

def _project_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"

def _load_project(project_id: str) -> Dict:
    path = _project_path(project_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    with open(path, "r") as f:
        return json.load(f)

def _save_project(project_id: str, data: Dict) -> None:
    with open(_project_path(project_id), "w") as f:
        json.dump(data, f, indent=2)

def _ensure_welcome_project() -> Dict:
    """Create or return the built-in Welcome project."""
    welcome_id = "__welcome__"
    path = _project_path(welcome_id)
    if path.exists():
        return json.load(open(path))
    welcome = {
        "id": welcome_id,
        "name": "📘 Welcome",
        "description": "Getting started with Prism-UI",
        "created": datetime.utcnow().isoformat(),
        "messages": [
            {"role": "assistant", "content": "👋 Welcome to Prism-UI!\n\nI'm your scaffold-aware chat companion. Here's how I work:", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "🧠 **Projects**\nEach project is a separate workspace with its own memory. Create projects for different tasks — coding, writing, research, etc.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "🔍 **PRISM Shadow Analysis**\nEvery message you send gets analysed for bias (authority, confirmation, sunk cost, etc.). Click the coloured chip on your messages to see the full inspector.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "🎚️ **Adaptive Behaviour**\nPRISM adjusts temperature, assertiveness, and routing based on what it detects. If it spots sunk cost, it challenges gently. If you're stuck, it reframes.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "🛡️ **Privacy Tiers**\nLocal = everything on your machine. Hybrid = PRISM local, LLM optionally cloud. Cloud = hosted. You can switch per project or per message.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "⚙️ **Settings** (gear icon)\nChange model endpoint, PRISM mode (shadow vs active), and default privacy. Shadow = log only. Active = injects routing into the LLM prompt.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "📊 **Tiered Memory**\nCore memory (who you are, what you like) persists across projects. Session memory is per-project. Decision logs track what worked.", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": "💡 **Tips**\n• Create a project before chatting\n• Try the PRISM inspector on any message\n• Switch models per project if needed\n• The system learns from your corrections — correct it when it's wrong", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
        ],
        "prism_state": None,
        "is_system": True,
    }
    _save_project(welcome_id, welcome)
    return welcome

def _profile_path() -> Path:
    return APP_ROOT / "projects" / "__user_profile__.json"

def _load_profile() -> Optional[Dict]:
    path = _profile_path()
    if path.exists():
        return json.load(open(path))
    return None

def _save_profile(data: Dict) -> None:
    _profile_path().parent.mkdir(parents=True, exist_ok=True)
    with open(_profile_path(), "w") as f:
        json.dump(data, f, indent=2)

# ── Endpoints ─────────────────────────────────────────────

@app.post("/api/projects", response_model=Project)
def create_project(req: ProjectCreate):
    pid = str(uuid.uuid4())[:8]
    project = {
        "id": pid,
        "name": req.name,
        "description": req.description,
        "workspace_path": req.workspace_path,
        "created": datetime.utcnow().isoformat(),
        "messages": [],
        "prism_state": None,
    }
    _save_project(pid, project)
    return Project(**project)

@app.get("/api/projects", response_model=List[Project])
def list_projects():
    _ensure_welcome_project()  # Ensure Welcome exists
    projects = []
    for f in sorted(PROJECTS_DIR.glob("*.json")):
        if f.name.startswith("__"):  # Skip system files
            continue
        with open(f, "r") as fh:
            data = json.load(fh)
        projects.append(Project(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            created=data["created"],
            workspace_path=data.get("workspace_path"),
        ))
    return projects

@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return _load_project(project_id)

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    if project_id == "__welcome__":
        raise HTTPException(status_code=403, detail="Cannot delete system project")
    path = _project_path(project_id)
    if path.exists():
        path.unlink()
    return {"ok": True}

# ── Profile Endpoints ─────────────────────────────────────

@app.get("/api/profile")
def get_profile():
    profile = _load_profile()
    if not profile:
        return {"exists": False}
    return {"exists": True, "profile": profile}

@app.post("/api/profile")
def save_profile(req: UserProfile):
    _save_profile(req.dict())
    return {"ok": True}

@app.delete("/api/profile")
def reset_profile():
    path = _profile_path()
    if path.exists():
        path.unlink()
    return {"ok": True}

class MemoryEntry(BaseModel):
    id: str
    content: str
    tier: str  # hot / warm / cool
    created: str
    last_accessed: str
    access_count: int = 0
    tags: List[str] = []

class MemoryCreate(BaseModel):
    content: str
    tier: str = "hot"
    tags: List[str] = []

class MemoryUpdate(BaseModel):
    tier: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None

class ProjectUpdate(BaseModel):
    messages: List[Dict[str, Any]] = []
    workspace_path: Optional[str] = None

@app.put("/api/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdate):
    project = _load_project(project_id)
    if req.messages:
        project["messages"] = req.messages
    if req.workspace_path is not None:
        project["workspace_path"] = req.workspace_path
    _save_project(project_id, project)
    return {"ok": True}

@app.post("/api/chat")
def chat(req: ChatRequest):
    project = _load_project(req.project_id)
    
    # ── PRISM Analysis ──
    prism_meta = None
    if req.use_prism:
        # Create a fresh pipeline per project (in real version we'd persist state)
        pipeline = PrismPipeline()
        result = pipeline.process(req.message)
        prism_meta = {
            "bias": result.classification.bias,
            "confidence": round(result.classification.confidence, 3),
            "route": result.route.route,
            "reason": result.route.reason,
            "temperature": round(result.temperature, 2),
            "assertiveness": round(result.bayesian_state.assertiveness, 3),
            "factual": result.intent.is_factual,
            "topic_drift": round(result.meta.get("topic_drift", 1.0), 3),
            "frustrated": result.meta.get("is_frustrated", False),
        }
    
    # ── Run plugin pre_send hooks ──
    plugin_context = {
        "project_id": req.project_id,
        "last_user_message": req.message,
        "prism_meta": prism_meta,
    }
    loop = asyncio.new_event_loop()
    modified_message = loop.run_until_complete(plugin_mgr.run_hook("pre_send", req.message, plugin_context))
    loop.close()
    if modified_message != req.message:
        req.message = modified_message  # plugins may rewrite or intercept

    # ── LLM Response via Ollama ──
    llm_response = "[LLM unavailable — Analysis shadow mode only]"
    token_count = 0
    latency_ms = 0
    try:
        import requests, time
        ollama_url = f"{req.model_endpoint.rstrip('/')}/api/generate"
        
        # Temperature: use override, then PRISM, then default
        temp = req.temperature if req.temperature is not None else (prism_meta["temperature"] if prism_meta else 0.7)
        
        # Build system prompt
        system_parts = []
        if req.system_prompt:
            system_parts.append(req.system_prompt)
        if req.mode == "active" and prism_meta:
            system_parts.append(f"[{prism_meta['route'].upper()} MODE: {prism_meta['reason']}]")
        
        ollama_payload = {
            "model": req.model_name,
            "prompt": req.message,
            "stream": False,
            "options": {"temperature": temp},
        }
        if system_parts:
            ollama_payload["system"] = "\n".join(system_parts)

        t0 = time.time()
        ollama_resp = requests.post(ollama_url, json=ollama_payload, timeout=60)
        latency_ms = round((time.time() - t0) * 1000)
        ollama_data = ollama_resp.json()
        llm_response = ollama_data.get("response", llm_response)
        token_count = ollama_data.get("eval_count", 0) + ollama_data.get("prompt_eval_count", 0)
    except Exception as e:
        llm_response = f"[Ollama error: {e}]"

    # ── Run plugin post_receive hooks ──
    plugin_context["response"] = llm_response
    loop = asyncio.new_event_loop()
    modified_response = loop.run_until_complete(plugin_mgr.run_hook("post_receive", llm_response, plugin_context))
    loop.close()
    if modified_response != llm_response:
        llm_response = modified_response
    
    # Store messages
    project["messages"].append({
        "role": "user",
        "content": req.message,
        "prism_meta": prism_meta,
        "timestamp": datetime.utcnow().isoformat(),
    })
    project["messages"].append({
        "role": "assistant",
        "content": llm_response,
        "token_count": token_count,
        "latency_ms": latency_ms,
        "timestamp": datetime.utcnow().isoformat(),
    })
    _save_project(req.project_id, project)

    return {
        "response": llm_response,
        "prism_meta": prism_meta,
        "token_count": token_count,
        "latency_ms": latency_ms,
    }

# ── Memory API ────────────────────────────────────────────

MEMORIES_DIR = APP_ROOT / "projects" / "__memories__"
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)

def _memory_path(project_id: str) -> Path:
    return MEMORIES_DIR / f"{project_id}.json"

def _load_memories(project_id: str) -> List[Dict]:
    path = _memory_path(project_id)
    if path.exists():
        return json.load(open(path))
    return []

def _save_memories(project_id: str, memories: List[Dict]) -> None:
    with open(_memory_path(project_id), "w") as f:
        json.dump(memories, f, indent=2)

def _decay_memories(memories: List[Dict]) -> List[Dict]:
    """Move memories between tiers based on age and access."""
    now = datetime.utcnow()
    for m in memories:
        created = datetime.fromisoformat(m["created"])
        age_hours = (now - created).total_seconds() / 3600
        if m["tier"] == "hot" and age_hours > 24:
            m["tier"] = "warm"
        if m["tier"] == "warm" and age_hours > 168:  # 1 week
            m["tier"] = "cool"
    return memories

@app.get("/api/projects/{project_id}/memories")
def list_memories(project_id: str):
    memories = _load_memories(project_id)
    memories = _decay_memories(memories)
    # Sort by tier (hot first) then by last_accessed
    tier_order = {"hot": 0, "warm": 1, "cool": 2}
    memories.sort(key=lambda m: (tier_order.get(m["tier"], 3), m["last_accessed"]), reverse=True)
    return {"memories": memories}

@app.post("/api/projects/{project_id}/memories")
def create_memory(project_id: str, req: MemoryCreate):
    mid = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    memory = {
        "id": mid,
        "content": req.content,
        "tier": req.tier,
        "created": now,
        "last_accessed": now,
        "access_count": 0,
        "tags": req.tags,
    }
    memories = _load_memories(project_id)
    memories.append(memory)
    _save_memories(project_id, memories)
    return memory

@app.put("/api/projects/{project_id}/memories/{memory_id}")
def update_memory(project_id: str, memory_id: str, req: MemoryUpdate):
    memories = _load_memories(project_id)
    for m in memories:
        if m["id"] == memory_id:
            if req.tier: m["tier"] = req.tier
            if req.content: m["content"] = req.content
            if req.tags: m["tags"] = req.tags
            m["last_accessed"] = datetime.utcnow().isoformat()
            _save_memories(project_id, memories)
            return m
    raise HTTPException(status_code=404, detail="Memory not found")

@app.post("/api/projects/{project_id}/memories/{memory_id}/access")
def access_memory(project_id: str, memory_id: str):
    memories = _load_memories(project_id)
    for m in memories:
        if m["id"] == memory_id:
            m["access_count"] = m.get("access_count", 0) + 1
            m["last_accessed"] = datetime.utcnow().isoformat()
            # Promote on frequent access
            if m["tier"] == "cool" and m["access_count"] >= 2:
                m["tier"] = "warm"
            if m["tier"] == "warm" and m["access_count"] >= 5:
                m["tier"] = "hot"
            _save_memories(project_id, memories)
            return m
    raise HTTPException(status_code=404, detail="Memory not found")

@app.delete("/api/projects/{project_id}/memories/{memory_id}")
def delete_memory(project_id: str, memory_id: str):
    memories = _load_memories(project_id)
    memories = [m for m in memories if m["id"] != memory_id]
    _save_memories(project_id, memories)
    return {"ok": True}

# ── Workspace API ─────────────────────────────────────────

@app.get("/api/projects/{project_id}/workspace")
def list_workspace_files(project_id: str):
    project = _load_project(project_id)
    path_str = project.get("workspace_path")
    if not path_str:
        return {"files": [], "linked": False}
    path = Path(path_str).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        return {"files": [], "linked": True, "error": "Path not found or not a directory"}
    files = []
    for f in sorted(path.iterdir()):
        if f.is_file() and f.stat().st_size < 10 * 1024 * 1024:  # Skip files > 10MB
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return {"files": files, "linked": True, "path": str(path)}

@app.get("/api/projects/{project_id}/workspace/{filename}")
def read_workspace_file(project_id: str, filename: str):
    project = _load_project(project_id)
    path_str = project.get("workspace_path")
    if not path_str:
        raise HTTPException(status_code=404, detail="No workspace linked")
    base = Path(path_str).expanduser().resolve()
    path = base / filename
    # Security: prevent path traversal
    try:
        path.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if path.stat().st_size > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    return {"content": path.read_text(encoding="utf-8", errors="replace")}

# ── Plugin API ──────────────────────────────────────────────

@app.get("/api/plugins")
def list_plugins(type_filter: Optional[str] = None):
    return plugin_mgr.list_plugins(type_filter=type_filter)

@app.post("/api/plugins/{plugin_id}/enable")
def enable_plugin(plugin_id: str, config: Optional[Dict] = None):
    ok = plugin_mgr.load(plugin_id, config)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to enable plugin")
    plugin_mgr.save_state(PLUGIN_STATE_PATH)
    return {"ok": True, "plugin": plugin_id}

@app.post("/api/plugins/{plugin_id}/disable")
def disable_plugin(plugin_id: str):
    plugin_mgr.unload(plugin_id)
    plugin_mgr.save_state(PLUGIN_STATE_PATH)
    return {"ok": True, "plugin": plugin_id}

@app.delete("/api/plugins/{plugin_id}")
def delete_plugin(plugin_id: str):
    plugin_mgr.unload(plugin_id)
    ok = plugin_mgr.delete(plugin_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Plugin not found")
    plugin_mgr.save_state(PLUGIN_STATE_PATH)
    return {"ok": True}

# ── Static Frontend ───────────────────────────────────────

app.mount("/", StaticFiles(directory=APP_ROOT / "frontend", html=True), name="frontend")

# ── SSL Runner ────────────────────────────────────────────
if __name__ == "__main__":
    import ssl
    import uvicorn

    SSL_KEY = Path(__file__).parent / "localhost-key.pem"
    SSL_CERT = Path(__file__).parent / "localhost-cert.pem"

    if SSL_KEY.exists() and SSL_CERT.exists():
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8788,
            ssl_keyfile=str(SSL_KEY),
            ssl_certfile=str(SSL_CERT),
            log_level="error",
        )
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8788, log_level="error")
