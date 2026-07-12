"""KIRIS-only phrase matching: recognizing the assistant's name to route a
free-form request to the LLM planner. Own copy of _normalize (8 lines) - not
worth a shared micro-package. Same mishearing-driven approach as LARIS's
wake phrases: whisper pt-BR renders "kiris" inconsistently; add variants as
they show up live."""
import re
import unicodedata


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[.,!?;:]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if unicodedata.category(ch) != "Mn"
    )
    return text.strip()


AGENT_NAMES = {"kiris", "kitties", "kyrus", "curios", "curies"}
_GREETINGS = {"ola", "oi", "ei", "hey", "e"}


def match_agent_phrase(text: str) -> str | None:
    """Return the request after the agent's name ("Kiris, abre o axon" ->
    "abre o axon"), "" when only the name was spoken, None otherwise.
    Tolerates a leading greeting ("ola kiris ...")."""
    words = _normalize(text).split()
    if len(words) >= 2 and words[0] in _GREETINGS and words[1] in AGENT_NAMES:
        return " ".join(words[2:])
    if words and words[0] in AGENT_NAMES:
        return " ".join(words[1:])
    return None
