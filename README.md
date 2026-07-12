# KIRIS

Keyword-Initiated Request Interpretation System - the name-gated voice
assistant layered on [LARIS](https://github.com/sammyjdev/laris) in
[claude-code-ops](https://github.com/sammyjdev/claude-code-ops): say "kiris,
<pedido>" and an LLM planner (`claude -p --model haiku`) proposes a spoken
reply plus a list of allowlisted actions (spawn / send_text / send_enter /
kill) over tmux sessions. Kill always asks for a spoken confirmation first,
regardless of what the model said.

`Assistant` is fully dependency-injected - it never imports tmux or session
code itself; see `claude-code-ops`'s `backend/main.py` for how the panel
wires its real tmux functions in.

## Testing

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q
```
