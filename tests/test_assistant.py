import json
from types import SimpleNamespace


def _make_assistant(llm_response):
    from kiris.assistant import Assistant

    calls = SimpleNamespace(spoken=[], spawned=[], sent=[], entered=[], killed=[], prompts=[])

    def run_llm(prompt):
        calls.prompts.append(prompt)
        if isinstance(llm_response, Exception):
            raise llm_response
        return llm_response

    def spawn(project):
        calls.spawned.append(project)
        return SimpleNamespace(name=project, tmux_name=project)

    assistant = Assistant(
        run_llm=run_llm,
        speak=calls.spoken.append,
        get_sessions=lambda: [SimpleNamespace(name="lina", state=SimpleNamespace(value="working"))],
        list_projects=lambda: ["axon", "lina"],
        spawn=spawn,
        send_text=lambda session, text: calls.sent.append((session, text)),
        send_enter=calls.entered.append,
        kill=calls.killed.append,
    )
    return assistant, calls


def test_question_only_speaks_the_answer():
    plan = {"say": "tem uma sessão aberta: lina", "actions": [], "needs_confirmation": False}
    assistant, calls = _make_assistant(json.dumps(plan))

    assistant.handle("quantas sessões estão abertas")

    assert "tem uma sessão aberta: lina" in calls.spoken
    assert calls.spawned == [] and calls.sent == [] and calls.killed == []


def test_spawn_and_instruct_plan_executes_in_order():
    plan = {
        "say": "abrindo o axon e pedindo o estado do repo",
        "actions": [
            {"type": "spawn", "project": "axon"},
            {"type": "send_text", "session": "axon", "text": "verifique o estado do repo"},
            {"type": "send_enter", "session": "axon"},
        ],
        "needs_confirmation": False,
    }
    assistant, calls = _make_assistant(json.dumps(plan))

    assistant.handle("abra um terminal claude no axon e verifique o estado do repo")

    assert calls.spawned == ["axon"]
    assert calls.sent == [("axon", "verifique o estado do repo")]
    assert calls.entered == ["axon"]
    assert "abrindo o axon e pedindo o estado do repo" in calls.spoken


def test_kill_always_requires_confirmation():
    plan = {
        "say": "fecho a lina?",
        "actions": [{"type": "kill", "session": "lina"}],
        "needs_confirmation": False,  # LLM forgot - local rule must force it
    }
    assistant, calls = _make_assistant(json.dumps(plan))

    assistant.handle("fecha a lina")
    assert calls.killed == []  # not yet

    handled = assistant.handle_followup("sim")

    assert handled is True
    assert calls.killed == ["lina"]


def test_negative_followup_cancels_pending_actions():
    plan = {
        "say": "fecho a lina?",
        "actions": [{"type": "kill", "session": "lina"}],
        "needs_confirmation": True,
    }
    assistant, calls = _make_assistant(json.dumps(plan))
    assistant.handle("fecha a lina")

    handled = assistant.handle_followup("não, deixa")

    assert handled is True
    assert calls.killed == []
    assert "cancelado" in calls.spoken


def test_followup_without_pending_is_not_consumed():
    assistant, _ = _make_assistant("{}")

    assert assistant.handle_followup("sim") is False


def test_malformed_llm_output_speaks_fallback():
    assistant, calls = _make_assistant("desculpa, não sei responder em JSON")

    assistant.handle("faz algo")

    assert any("não consegui" in s for s in calls.spoken)
    assert calls.spawned == [] and calls.killed == []


def test_llm_failure_speaks_fallback():
    assistant, calls = _make_assistant(RuntimeError("claude CLI exploded"))

    assistant.handle("faz algo")

    assert any("não consegui" in s for s in calls.spoken)


def test_unknown_action_types_are_skipped():
    plan = {
        "say": "ok",
        "actions": [
            {"type": "run_shell", "command": "rm -rf /"},  # NOT in the allowlist
            {"type": "send_enter", "session": "lina"},
        ],
        "needs_confirmation": False,
    }
    assistant, calls = _make_assistant(json.dumps(plan))

    assistant.handle("roda um comando")

    assert calls.entered == ["lina"]  # allowlisted action still ran


def test_empty_request_asks_for_the_request_without_llm():
    assistant, calls = _make_assistant("{}")

    assistant.handle("")

    assert calls.prompts == []
    assert len(calls.spoken) == 1


def test_json_wrapped_in_fences_still_parses():
    plan = {"say": "ok", "actions": [], "needs_confirmation": False}
    assistant, calls = _make_assistant(f"```json\n{json.dumps(plan)}\n```")

    assistant.handle("pergunta")

    assert "ok" in calls.spoken


def test_prompt_includes_sessions_projects_and_request():
    assistant, calls = _make_assistant(json.dumps({"say": "ok", "actions": []}))

    assistant.handle("abre o axon")

    prompt = calls.prompts[0]
    assert "lina" in prompt and "axon" in prompt and "abre o axon" in prompt
