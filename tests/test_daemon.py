import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def test_ask_endpoint_routes_to_assistant_handle():
    from kiris.daemon import build_app

    fake_assistant = MagicMock()
    app = build_app(assistant=fake_assistant)

    response = TestClient(app).post("/ask", json={"request": "abre o axon"})

    assert response.status_code == 200
    fake_assistant.handle.assert_called_once_with("abre o axon")
    assert response.json() == {"ok": True}


def test_ask_endpoint_returns_422_on_missing_request_field():
    from kiris.daemon import build_app

    app = build_app(assistant=MagicMock())
    response = TestClient(app).post("/ask", json={})

    assert response.status_code == 422


def test_ask_endpoint_returns_500_on_assistant_exception():
    from kiris.daemon import build_app

    fake_assistant = MagicMock()
    fake_assistant.handle.side_effect = RuntimeError("boom")
    app = build_app(assistant=fake_assistant)

    response = TestClient(app).post("/ask", json={"request": "x"})

    assert response.status_code == 500
    body = response.json()
    assert "error" in body.get("detail", body) or "error" in body


def test_panel_client_get_sessions_returns_empty_when_offline():
    from kiris.daemon import PanelClient

    client = PanelClient(panel_url=None, panel_token=None)
    assert client.get_sessions() == []


def test_panel_client_get_sessions_calls_panel_http():
    from kiris.daemon import PanelClient

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a: None
    fake_resp.read.return_value = json.dumps(
        [{"name": "lina", "cwd": "/tmp", "state": "WORKING", "tmux_pid": 1, "tmux_name": "lina",
          "git_branch": None, "project": "lina", "last_active": None}]
    ).encode()

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_open:
        client = PanelClient(panel_url="http://127.0.0.1:8420", panel_token="t")
        sessions = client.get_sessions()

    assert len(sessions) == 1
    assert sessions[0].name == "lina"


def test_panel_client_send_text_posts_to_panel():
    from kiris.daemon import PanelClient

    fake_resp = MagicMock(status=200)
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a: None
    fake_resp.read.return_value = b'{"sent": "lina"}'

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_open:
        client = PanelClient(panel_url="http://127.0.0.1:8420", panel_token="t")
        client.send_text("lina", "roda os testes")

    request = mock_open.call_args[0][0]
    assert request.method == "POST"
    assert "/api/sessions/lina/send-text" in request.full_url


def test_panel_client_kill_posts_to_end_route():
    from kiris.daemon import PanelClient

    fake_resp = MagicMock(status=200)
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a: None
    fake_resp.read.return_value = b'{"ended": "lina"}'

    with patch("urllib.request.urlopen", return_value=fake_resp) as mock_open:
        client = PanelClient(panel_url="http://127.0.0.1:8420", panel_token="t")
        client.kill("lina")

    request = mock_open.call_args[0][0]
    assert request.method == "POST"
    assert "/api/sessions/lina/end" in request.full_url


def test_panel_client_spawn_returns_none_when_url_none():
    from kiris.daemon import PanelClient

    client = PanelClient(panel_url=None, panel_token=None)
    assert client.spawn("axon") is None
