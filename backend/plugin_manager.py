"""Polychomp Plugin Manager

A lightweight plugin system for scaffolds, skills, and tools.

Plugin Format
-------------
A plugin is a folder under `plugins/` containing:
  manifest.json   — metadata, hooks, config schema
  main.py         — entry point (optional, for code plugins)
  icon.svg        — optional icon

manifest.json schema:
{
    "id": "unique-plugin-id",
    "name": "Display Name",
    "description": "What it does",
    "version": "1.0.0",
    "author": "Author Name",
    "type": "scaffold|skill|tool|theme",
    "entry_point": "main.py",
    "hooks": ["pre_send", "post_receive"],
    "commands": {
        "/summarize": "handle_summarize"
    },
    "config_schema": {
        "max_length": {"type": "int", "default": 200}
    },
    "tags": ["productivity", "text"],
    "icon": "icon.svg"
}

main.py must expose:
    async def on_load(config) -> None
    async def pre_send(message, context) -> str|None  (return modified message or None)
    async def post_receive(response, context) -> str|None
    async def handle_command(command, args, context) -> str|None
"""

import os
import sys
import json
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from fastapi import UploadFile


class Plugin:
    """Represents a loaded plugin."""

    def __init__(self, manifest: Dict, plugin_dir: Path):
        self.manifest = manifest
        self.id = manifest["id"]
        self.name = manifest.get("name", self.id)
        self.description = manifest.get("description", "")
        self.version = manifest.get("version", "0.1.0")
        self.author = manifest.get("author", "")
        self.type = manifest.get("type", "skill")  # scaffold | skill | tool | theme
        self.plugin_dir = plugin_dir
        self.enabled = False
        self.module = None
        self.config = {}
        self._hooks = {}

    def __repr__(self) -> str:
        return f"Plugin({self.id}, {self.type}, enabled={self.enabled})"


class PluginManager:
    """Discovers, loads, and executes plugins."""

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._registry: Dict[str, Plugin] = {}
        self._commands: Dict[str, Callable] = {}
        self.discover()

    # ── Discovery ─────────────────────────────

    def discover(self) -> None:
        """Scan plugins/ for valid plugin folders."""
        self._registry.clear()
        for entry in self.plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
                if "id" not in manifest:
                    continue
                plugin = Plugin(manifest, entry)
                self._registry[plugin.id] = plugin
            except Exception:
                continue

    # ── Loading ─────────────────────────────────

    def load(self, plugin_id: str, config: Optional[Dict] = None) -> bool:
        """Import a plugin's entry_point and cache its hooks."""
        plugin = self._registry.get(plugin_id)
        if not plugin:
            return False

        ep = plugin.manifest.get("entry_point", "")
        if not ep:
            # Manifest-only plugin (no code)
            plugin.enabled = True
            plugin.config = config or {}
            return True

        entry_file = plugin.plugin_dir / ep
        if not entry_file.exists():
            plugin.enabled = True
            return True

        try:
            spec = importlib.util.spec_from_file_location(
                f"polychomp_plugin_{plugin_id}", entry_file
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            plugin.module = module
            plugin.enabled = True
            plugin.config = config or self._default_config(plugin)

            # Cache hooks
            for hook_name in plugin.manifest.get("hooks", []):
                handler = getattr(module, hook_name, None)
                if callable(handler):
                    plugin._hooks[hook_name] = handler

            # Cache commands
            for cmd, func_name in plugin.manifest.get("commands", {}).items():
                func = getattr(module, func_name, None)
                if callable(func):
                    self._commands[cmd] = func

            # Call lifecycle hook
            on_load = getattr(module, "on_load", None)
            if callable(on_load):
                try:
                    if inspect.iscoroutinefunction(on_load):
                        import asyncio
                        asyncio.get_event_loop().run_until_complete(on_load(plugin.config))
                    else:
                        on_load(plugin.config)
                except Exception:
                    pass

            return True
        except Exception:
            plugin.enabled = False
            return False

    def unload(self, plugin_id: str) -> None:
        plugin = self._registry.get(plugin_id)
        if plugin:
            plugin.enabled = False
            plugin.module = None
            plugin._hooks.clear()
        # Remove commands from this plugin
        for cmd, func in list(self._commands.items()):
            p = self._registry.get(plugin_id)
            if p and func.__module__ == getattr(p.module, "__name__", None):
                del self._commands[cmd]

    # ── Execution ───────────────────────────────

    async def run_hook(self, hook_name: str, data: Any, context: Dict = None) -> Any:
        """Run a hook across all enabled plugins. First non-None return wins."""
        context = context or {}
        for plugin in self._registry.values():
            if not plugin.enabled:
                continue
            handler = plugin._hooks.get(hook_name)
            if handler:
                try:
                    if inspect.iscoroutinefunction(handler):
                        result = await handler(data, context)
                    else:
                        result = handler(data, context)
                    if result is not None:
                        data = result
                except Exception:
                    continue
        return data

    async def run_command(self, cmd: str, args: str, context: Dict = None) -> Optional[str]:
        handler = self._commands.get(cmd)
        if not handler:
            return None
        try:
            if inspect.iscoroutinefunction(handler):
                return await handler(cmd, args, context or {})
            return handler(cmd, args, context or {})
        except Exception:
            return None

    # ── Registry ────────────────────────────────

    def list_plugins(self, type_filter: Optional[str] = None) -> List[Dict]:
        result = []
        for p in self._registry.values():
            if type_filter and p.type != type_filter:
                continue
            result.append({
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "version": p.version,
                "author": p.author,
                "type": p.type,
                "enabled": p.enabled,
                "tags": p.manifest.get("tags", []),
                "icon": p.manifest.get("icon"),
            })
        return sorted(result, key=lambda x: x["name"])

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self._registry.get(plugin_id)

    # ── Upload / Install ────────────────────────

    def install(self, source_dir: Path, manifest: Dict) -> bool:
        target = self.plugins_dir / manifest["id"]
        if target.exists():
            return False
        import shutil
        shutil.copytree(source_dir, target)
        plugin = Plugin(manifest, target)
        self._registry[plugin.id] = plugin
        return True

    def delete(self, plugin_id: str) -> bool:
        plugin = self._registry.pop(plugin_id, None)
        if plugin and plugin.plugin_dir.exists():
            import shutil
            shutil.rmtree(plugin.plugin_dir)
            return True
        return False

    # ── Helpers ─────────────────────────────────

    def _default_config(self, plugin: Plugin) -> Dict:
        schema = plugin.manifest.get("config_schema", {})
        return {k: v.get("default") for k, v in schema.items()}

    def save_state(self, path: Path) -> None:
        state = {
            pid: {
                "enabled": p.enabled,
                "config": p.config,
            }
            for pid, p in self._registry.items()
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    def load_state(self, path: Path) -> None:
        if not path.exists():
            return
        with open(path, "r") as f:
            state = json.load(f)
        for pid, cfg in state.items():
            plugin = self._registry.get(pid)
            if plugin and cfg.get("enabled"):
                self.load(pid, cfg.get("config"))
