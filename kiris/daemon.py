"""KIRIS standalone HTTP daemon - listens on 127.0.0.1:8422 and exposes
POST /ask, which LARIS calls when it transcribes 'kiris <pedido>'.

Panel-agnostic: takes a pre-built Assistant (whose panel-side callables are
either PanelClient-backed HTTP wrappers or no-op stubs when the panel is
offline). See __main__.py for the composition root that wires peers.json."""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kiris.assistant import Assistant


class AskPayload(BaseModel):
    request: str


def build_app(assistant: Assistant) -> FastAPI:
    app = FastAPI()

    @app.post("/ask")
    def ask(payload: AskPayload) -> dict:
        try:
            assistant.handle(payload.request)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001 - one bad request must not crash kiris
            raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc

    return app


@dataclass(frozen=True)
class SessionInfoLike:
    """Lightweight session representation returned by PanelClient.get_sessions;
    field names match what kiris.Assistant._build_prompt reads (s.name,
    getattr(s.state, 'value', s.state))."""
    name: str
    cwd: str
    state: str
    tmux_pid: int
    tmux_name: str
    project: str
    git_branch: str | None
    last_active: str | None


class PanelClient:
    """HTTP client for the panel's REST surface. Returns empty/stub values
    when the panel is offline (panel_url=None), so kiris.Assistant can
    degrade gracefully - speak replies with empty session context instead
    of crashing."""

    def __init__(self, panel_url: str | None, panel_token: str | None) -> None:
        self.panel_url = panel_url.rstrip("/") if panel_url else None
        self.panel_token = panel_token

    def _request(self, method: str, path: str, body: dict | None = None) -> Any:
        if self.panel_url is None:
            return None
        url = f"{self.panel_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if self.panel_token:
            req.add_header("X-Session-Token", self.panel_token)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return json.loads(resp.read())

    def get_sessions(self) -> list[SessionInfoLike]:
        if self.panel_url is None:
            return []
        try:
            raw = self._request("GET", "/api/sessions") or []
            return [
                SessionInfoLike(
                    name=s["name"],
                    cwd=s["cwd"],
                    state=s.get("state", "WORKING"),
                    tmux_pid=s.get("tmux_pid", 0),
                    tmux_name=s["tmux_name"],
                    project=s.get("project", s["name"]),
                    git_branch=s.get("git_branch"),
                    last_active=s.get("last_active"),
                )
                for s in raw
            ]
        except Exception:  # noqa: BLE001 - panel offline -> empty session list
            return []

    def list_projects(self) -> list[str]:
        # The panel has no explicit list-projects endpoint; derive from
        # get_sessions. A richer /api/projects endpoint can be added later.
        sessions = self.get_sessions()
        return sorted({s.project for s in sessions})

    def spawn(self, project: str) -> object | None:
        if self.panel_url is None:
            return None
        from pathlib import Path
        for root in (Path.home() / "code", Path.home() / "dev"):
            cwd = root / project
            if cwd.is_dir():
                try:
                    self._request("POST", "/api/sessions/spawn", {"name": project, "cwd": str(cwd)})
                    return {"spawned": project}
                except Exception:  # noqa: BLE001
                    return None
        return None

    def send_text(self, session: str, text: str) -> None:
        if self.panel_url is None:
            return
        try:
            self._request("POST", f"/api/sessions/{session}/send-text", {"text": text})
        except Exception:  # noqa: BLE001
            raise

    def send_enter(self, session: str) -> None:
        if self.panel_url is None:
            return
        try:
            self._request("POST", f"/api/sessions/{session}/send-enter")
        except Exception:  # noqa: BLE001
            raise

    def kill(self, session: str) -> None:
        if self.panel_url is None:
            return
        try:
            self._request("POST", f"/api/sessions/{session}/end")
        except Exception:  # noqa: BLE001
            raise


def _run_llm_via_claude_cli(prompt: str) -> str:
    """The in-process composition had this logic in claude-code-ops/main.py's
    _run_assistant_llm. In Phase 4 it lives in the kiris daemon because the
    claude CLI is invoked locally wherever kiris runs."""
    import subprocess
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "haiku", "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:])
    return json.loads(result.stdout).get("result", "")
