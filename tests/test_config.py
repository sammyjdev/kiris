def test_assistant_enabled_by_default(monkeypatch):
    from kiris import config

    monkeypatch.delenv("VOICE_ASSISTANT", raising=False)

    assert config.assistant_enabled() is True
