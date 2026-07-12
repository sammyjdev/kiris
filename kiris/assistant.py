"""Voice assistant: "Kiris, <pedido>" goes through an LLM that plans a
spoken reply plus a list of ALLOWLISTED actions (spawn / send_text /
send_enter / kill on tmux sessions - the same powers the deterministic
voice flow already has, nothing more). The LLM proposes; this module
disposes: unknown action types are dropped and kill always waits for a
spoken confirmation, regardless of what the model said.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from kiris.phrase_matching import _normalize

_MAX_ACTIONS = 5
_CONFIRM_WORDS = {"sim", "pode", "confirma", "confirmado", "manda", "vai", "isso", "claro"}

_PROMPT_TEMPLATE = """Você é Kiris, assistente de voz do Claude Code Ops \
(painel de sessões tmux rodando agentes claude).

Sessões tmux abertas agora: {sessions}
Projetos que você pode abrir: {projects}

Pedido do usuário (transcrito por voz, pode conter erros): "{request}"

Responda APENAS um JSON válido, sem markdown:
{{"say": "<resposta curta em pt-BR para falar em voz alta>", "actions": [], "needs_confirmation": false}}

Tipos de ação permitidos em "actions":
- {{"type": "spawn", "project": "<projeto>"}} abre uma sessão tmux com claude no projeto (a sessão nova recebe o nome do projeto)
- {{"type": "send_text", "session": "<sessão>", "text": "<instrução>"}} digita a instrução na sessão
- {{"type": "send_enter", "session": "<sessão>"}} envia a instrução digitada (Enter)
- {{"type": "kill", "session": "<sessão>"}} fecha a sessão

Regras:
- Pergunta simples: "actions" vazia, resposta em "say".
- Para instruir um agente claude: send_text seguido de send_enter.
- Para "abrir X e pedir Y": spawn, depois send_text e send_enter na sessão nova.
- Máximo {max_actions} ações.
- "needs_confirmation": true se o pedido for ambíguo ou arriscado; nesse caso "say" \
é a pergunta de confirmação e as ações só rodam depois de um "sim"."""


@dataclass
class Assistant:
    run_llm: Callable[[str], str]
    speak: Callable[[str], None]
    get_sessions: Callable[[], list]
    list_projects: Callable[[], list[str]]
    spawn: Callable[[str], object | None]
    send_text: Callable[[str, str], None]
    send_enter: Callable[[str], None]
    kill: Callable[[str], None]
    _pending: list | None = field(default=None, init=False)

    def handle(self, request: str) -> None:
        if not request.strip():
            self.speak("pois não? fala o pedido junto com o meu nome")
            return
        self.speak("deixa eu ver")
        try:
            plan = self._parse(self.run_llm(self._build_prompt(request)))
        except Exception:  # noqa: BLE001 - a dead LLM must not kill the voice loop
            plan = None
        if plan is None:
            self.speak("não consegui entender o pedido")
            return

        say = str(plan.get("say") or "")
        actions = [a for a in (plan.get("actions") or []) if isinstance(a, dict)]
        actions = actions[:_MAX_ACTIONS]
        needs_confirmation = bool(plan.get("needs_confirmation")) or any(
            a.get("type") == "kill" for a in actions  # destructive: never skip
        )

        if actions and needs_confirmation:
            self._pending = actions
            self.speak(say or "confirma?")
            return
        if say:
            self.speak(say)
        self._execute(actions)

    def handle_followup(self, text: str) -> bool:
        """Consume the utterance after a confirmation question.
        Returns True when it was handled here."""
        if self._pending is None:
            return False
        actions, self._pending = self._pending, None
        words = _normalize(text).split()
        if words and words[0] in _CONFIRM_WORDS:
            self._execute(actions)
            self.speak("feito")
        else:
            self.speak("cancelado")
        return True

    def _build_prompt(self, request: str) -> str:
        sessions = ", ".join(
            f"{s.name} ({getattr(s.state, 'value', s.state)})" for s in self.get_sessions()
        ) or "nenhuma"
        projects = ", ".join(self.list_projects()) or "nenhum"
        return _PROMPT_TEMPLATE.format(
            sessions=sessions,
            projects=projects,
            request=request,
            max_actions=_MAX_ACTIONS,
        )

    @staticmethod
    def _parse(raw: str) -> dict | None:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _execute(self, actions: list[dict]) -> None:
        for action in actions:
            try:
                kind = action.get("type")
                if kind == "spawn":
                    if self.spawn(str(action.get("project", ""))) is None:
                        self.speak("não consegui abrir o projeto")
                        return
                elif kind == "send_text":
                    self.send_text(
                        str(action.get("session", "")), str(action.get("text", ""))
                    )
                elif kind == "send_enter":
                    self.send_enter(str(action.get("session", "")))
                elif kind == "kill":
                    self.kill(str(action.get("session", "")))
                # any other type: dropped - the allowlist IS the security boundary
            except Exception:  # noqa: BLE001 - one bad action must not kill the loop
                self.speak("uma das ações falhou")
                return
