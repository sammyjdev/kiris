"""Standalone entrypoint: `python -m kiris`. Boots the HTTP daemon on
127.0.0.1:8422, reads peers.json to find the panel, and constructs an
Assistant whose panel-side callables are PanelClient-backed HTTP wrappers
(or stubs when the panel is offline)."""
from __future__ import annotations

import uvicorn

from kiris import peer_discovery
from kiris.daemon import PanelClient, _run_llm_via_claude_cli, build_app
from kiris.tts import speak


KIRIS_PORT = 8422


def main() -> None:
    peer_discovery.write_peer("kiris", f"http://127.0.0.1:{KIRIS_PORT}", token=None)
    panel_url = peer_discovery.peer_url("panel")
    panel_token = peer_discovery.peer_token("panel")
    panel_client = PanelClient(panel_url=panel_url, panel_token=panel_token)

    from kiris.assistant import Assistant

    assistant = Assistant(
        run_llm=_run_llm_via_claude_cli,
        speak=speak,
        get_sessions=panel_client.get_sessions,
        list_projects=panel_client.list_projects,
        spawn=panel_client.spawn,
        send_text=panel_client.send_text,
        send_enter=panel_client.send_enter,
        kill=panel_client.kill,
    )

    app = build_app(assistant)
    print(f"[Kiris] daemon ouvindo em http://127.0.0.1:{KIRIS_PORT}")
    uvicorn.run(app, host="127.0.0.1", port=KIRIS_PORT)


if __name__ == "__main__":
    main()
