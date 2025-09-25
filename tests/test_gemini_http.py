from unittest.mock import patch, MagicMock

import ai_backend.gemini_client as gemini


def make_resp(status=200, data=None):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data or {}
    return m


@patch("ai_backend.gemini_client.requests")
def test_custom_url_path(mock_requests):
    # simulate GEMINI_API_KEY and GEMINI_API_URL being set in config
    import ai_backend.gemini_client as gemini_mod
    gemini_mod.GEMINI_API_KEY = "fake-key"
    gemini_mod.GEMINI_API_URL = "https://example.test/api"
    mock_requests.post.return_value = make_resp(200, {"text": "ok", "raw": {"suggested_steps": [{"command": "terminal.run", "args": {"command": "echo hi"}}]}})
    # call query_gemini which should use the custom GEMINI_API_URL path when configured
    res = gemini.query_gemini("do something")
    assert isinstance(res, dict)
    assert "text" in res
    assert res["text"] == "ok"
    assert res.get("raw", {}).get("suggested_steps")


@patch("ai_backend.gemini_client.requests")
def test_google_genai_path(mock_requests):
    # simulate Google GenAI response shape
    import ai_backend.gemini_client as gemini_mod
    gemini_mod.GEMINI_API_KEY = "fake-key"
    gemini_mod.GEMINI_API_URL = ""
    mock_requests.post.return_value = make_resp(200, {"candidates": [{"content": "step1"}, {"content": "step2"}]})
    res = gemini.query_gemini("please plan for me")
    assert isinstance(res, dict)
    assert "text" in res
    assert "step1" in res["text"]


def test_genai_client_path(monkeypatch):
    # Create a fake genai module with Client and configure
    import sys
    class DummyResponse:
        def __init__(self, text, suggested_steps=None):
            self.text = text
            self.raw = {"suggested_steps": suggested_steps or []}

    class DummyClient:
        def __init__(self, resp: DummyResponse):
            self._resp = resp

        def generate_text(self, prompt=None, **kwargs):
            return self._resp

    fake_genai = type("G", (), {})()

    def configure(api_key=None):
        fake_genai._configured = api_key

    fake_genai.configure = configure
    resp = DummyResponse("Plan from genai", suggested_steps=[
        {"command": "files.list", "args": {"path": "."}},
        {"command": "terminal.run", "args": {"command": "echo hi"}},
    ])

    def Client():
        return DummyClient(resp)

    fake_genai.Client = Client

    monkeypatch.setitem(sys.modules, "genai", fake_genai)

    # reload the module to pick up genai
    import importlib
    import ai_backend.gemini_client as gemini_mod
    importlib.reload(gemini_mod)
    gemini_mod.GEMINI_API_KEY = "fake-key"

    plan = gemini_mod.generate_plan("please make a plan")
    assert plan["plan"] == "Plan from genai"
    assert len(plan["steps"]) == 2
