"""KIRIS enablement flag."""
import os


def assistant_enabled() -> bool:
    """VOICE_ASSISTANT=0 boots Laris alone (pure transcriber: mute, no LLM).
    Default keeps Kiris, the name-gated assistant, on. Read at call time so
    tests don't need a module reload."""
    return os.environ.get("VOICE_ASSISTANT", "1") != "0"
