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

app = FastAPI(title="Polychomp-UI")
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

app = FastAPI(title="Polychomp-UI", version="0.1.0")

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
    cross_project_memory: bool # true / false

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

class ProjectCreate(BaseModel):
    name: str
    description: str = ""

class Project(BaseModel):
    id: str
    name: str
    description: str
    created: str

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
        "description": "Getting started with Polychomp",
        "created": datetime.utcnow().isoformat(),
        "messages": [
            {"role": "assistant", "content": "👋 Welcome to Polychomp!\n\nI'm your scaffold-aware chat companion. Here's how I work:", "prism_meta": None, "timestamp": datetime.utcnow().isoformat()},
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

class ProjectUpdate(BaseModel):
    messages: List[Dict[str, Any]]

@app.put("/api/projects/{project_id}")
def update_project(project_id: str, req: ProjectUpdate):
    project = _load_project(project_id)
    project["messages"] = req.messages
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
    llm_response = "[LLM unavailable — PRISM shadow mode only]"
    try:
        import requests
        ollama_url = f"{req.model_endpoint.rstrip('/')}/api/generate"
        ollama_payload = {
            "model": req.model_name,
            "prompt": req.message,
            "stream": False,
            "options": {"temperature": prism_meta["temperature"] if prism_meta else 0.7},
        }
        # If PRISM is active, prepend route suggestion to system prompt area
        if req.mode == "active" and prism_meta:
            route_addition = f"[{prism_meta['route'].upper()} MODE: {prism_meta['reason']}]"
            ollama_payload["system"] = route_addition

        ollama_resp = requests.post(ollama_url, json=ollama_payload, timeout=60)
        ollama_data = ollama_resp.json()
        llm_response = ollama_data.get("response", llm_response)
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
        "timestamp": datetime.utcnow().isoformat(),
    })
    _save_project(req.project_id, project)
    
    return {
        "response": llm_response,
        "prism_meta": prism_meta,
    }

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
