"""Spoken feedback via macOS `say` - fire and forget.

Popen, not run: the voice loop must never block behind speech synthesis.
Disable with VOICE_TTS=0; pick another voice with VOICE_TTS_VOICE
(default Luciana, the pt-BR system voice on this machine).
"""
from __future__ import annotations

import os
import subprocess

from kiris import config

VOICE = os.environ.get("VOICE_TTS_VOICE", "Luciana")
ENABLED = os.environ.get("VOICE_TTS", "1") != "0"


def speak(text: str) -> None:
    # all spoken feedback belongs to Kiris; Laris (VOICE_ASSISTANT=0) is mute
    if not ENABLED or not config.assistant_enabled():
        return
    try:
        subprocess.Popen(
            ["say", "-v", VOICE, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:  # noqa: BLE001 - feedback is cosmetic, never break the voice loop
        pass
