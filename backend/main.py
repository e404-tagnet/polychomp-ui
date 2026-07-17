"""FastAPI backend for Polychomp-UI."""
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add PRISM src to path
PRISM_ROOT = Path(__file__).resolve().parents[1] / ".." / "prism-scaffold" / "src"
sys.path.insert(0, str(PRISM_ROOT))

from prism.core.pipeline import PrismPipeline, PipelineResult
from prism.core.memory import MemoryStore, MemoryEntry

APP_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = APP_ROOT / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Polychomp-UI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────

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
    projects = []
    for f in sorted(PROJECTS_DIR.glob("*.json")):
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
    path = _project_path(project_id)
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

# ── Static Frontend ───────────────────────────────────────

app.mount("/", StaticFiles(directory=APP_ROOT / "frontend", html=True), name="frontend")
