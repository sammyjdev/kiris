def test_speak_spawns_say_with_voice(monkeypatch):
    from kiris import tts

    spawned = []
    monkeypatch.setattr(tts.subprocess, "Popen", lambda argv, **kw: spawned.append(argv))
    monkeypatch.setattr(tts, "ENABLED", True)

    tts.speak("não entendi")

    assert spawned == [["say", "-v", tts.VOICE, "não entendi"]]


def test_speak_is_silent_when_disabled(monkeypatch):
    from kiris import tts

    spawned = []
    monkeypatch.setattr(tts.subprocess, "Popen", lambda argv, **kw: spawned.append(argv))
    monkeypatch.setattr(tts, "ENABLED", False)

    tts.speak("qualquer coisa")

    assert spawned == []


def test_speak_is_silent_when_assistant_disabled(monkeypatch):
    from kiris import tts

    spawned = []
    monkeypatch.setattr(tts.subprocess, "Popen", lambda argv, **kw: spawned.append(argv))
    monkeypatch.setattr(tts, "ENABLED", True)
    monkeypatch.setenv("VOICE_ASSISTANT", "0")

    tts.speak("qualquer coisa")

    assert spawned == []


def test_speak_swallows_spawn_failure(monkeypatch):
    from kiris import tts

    def exploding_popen(argv, **kw):
        raise OSError("say missing")

    monkeypatch.setattr(tts.subprocess, "Popen", exploding_popen)
    monkeypatch.setattr(tts, "ENABLED", True)

    tts.speak("não entendi")  # must not raise
