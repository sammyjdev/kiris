from kiris.phrase_matching import match_agent_phrase


def test_match_agent_phrase_extracts_request():
    assert match_agent_phrase("Kiris, abre o axon") == "abre o axon"
    assert match_agent_phrase("ola kiris que sessoes estao abertas") == (
        "que sessoes estao abertas"
    )
    assert match_agent_phrase("kiris") == ""


def test_match_agent_phrase_returns_none_for_plain_speech():
    assert match_agent_phrase("abre o axon") is None
    assert match_agent_phrase("bom dia") is None
