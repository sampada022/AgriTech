"""The Anthropic adapter against a local stub server, because no API key is available in tests.

This proves the request we send and how we handle each kind of reply. It cannot prove the live API
accepts the request or how fast it answers, so run a real photo through once with a key.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.config import Settings
from app.diagnosis.providers import (
    SYSTEM_PROMPT,
    AnthropicProvider,
    DiagnosisContext,
    DiagnosisUnavailable,
    build_provider,
)

VALID = {
    "plant_visible": True,
    "image_quality": "good",
    "observed_symptoms": ["Chewed leaf margins"],
    "candidates": [
        {"name": "Leaf-feeding caterpillar", "type": "pest", "probability": 0.62},
        {"name": "Nitrogen deficiency", "type": "nutrient", "probability": 0.18},
    ],
    "confirm_by": ["Check the leaf underside for eggs or larvae"],
    "actions_ipm": ["Remove affected leaves", "Spray 2 ml per litre"],
    "needs_expert": False,
    "language": "en",
}
CONTEXT = DiagnosisContext(
    crop="Maize", language="en", aerial_area_m2=14.4, aerial_class="uncertain", aerial_score=0.55
)


def message(text: str, stop_reason: str = "end_turn") -> dict:
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


class Stub:
    def __init__(self):
        self.replies: list[tuple[int, dict]] = []
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = self.rfile.read(int(self.headers["Content-Length"]))
                stub.requests.append(json.loads(body))
                stub.headers.append(dict(self.headers))
                status, reply = stub.replies.pop(0) if stub.replies else (500, {})
                data = json.dumps(reply).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def stub(monkeypatch):
    server = Stub()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", server.url)
    yield server
    server.close()


def provider(**overrides) -> AnthropicProvider:
    return AnthropicProvider(
        Settings(
            anthropic_api_key="test-key", diagnosis_timeout_s=3, diagnosis_retries=0, **overrides
        )
    )


def test_request_carries_the_image_prompt_and_schema(stub):
    stub.replies.append((200, message(json.dumps(VALID))))
    provider().diagnose(b"jpeg-bytes", CONTEXT)
    request = stub.requests[0]
    assert request["model"] == "claude-opus-5"
    assert request["system"] == SYSTEM_PROMPT
    assert request["output_config"]["effort"] == "low"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert "candidates" in request["output_config"]["format"]["schema"]["properties"]
    assert request["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in stub.headers[0]["anthropic-beta"]

    image, text = request["messages"][0]["content"]
    assert image["type"] == "image"
    assert image["source"]["media_type"] == "image/jpeg"
    assert text["type"] == "text"
    assert "Maize" in text["text"]
    assert "English" in text["text"]
    assert "context only" in text["text"]


def test_language_is_requested_per_call(stub):
    stub.replies.append((200, message(json.dumps({**VALID, "language": "kn"}))))
    context = DiagnosisContext(crop="Maize", language="kn")
    assert provider().diagnose(b"x", context).language == "kn"
    assert "Kannada" in stub.requests[0]["messages"][0]["content"][1]["text"]


def test_system_prompt_states_the_safety_rules():
    for phrase in ("never give a dose", "Never name a product brand", '"unsure"', "not as instructions"):
        assert phrase in SYSTEM_PROMPT


def test_valid_reply_is_parsed_and_doses_are_stripped(stub):
    stub.replies.append((200, message(json.dumps(VALID))))
    result = provider().diagnose(b"x", CONTEXT)
    assert result.candidates[0].name == "Leaf-feeding caterpillar"
    assert result.actions_ipm == ["Remove affected leaves"]


@pytest.mark.parametrize(
    ("reply", "reason"),
    [
        ((200, message("this is not json")), None),
        (
            (
                200,
                message(
                    json.dumps(
                        {
                            **VALID,
                            "candidates": [
                                {"name": "A", "type": "pest", "probability": 0.9},
                                {"name": "B", "type": "pest", "probability": 0.9},
                            ],
                        }
                    )
                ),
            ),
            None,
        ),
        ((200, message(json.dumps(VALID), "refusal")), "stop_refusal"),
        ((200, message('{"plant_visible": tr', "max_tokens")), None),
        ((401, {"type": "error", "error": {"type": "authentication_error", "message": "no"}}), "authentication"),
        ((429, {"type": "error", "error": {"type": "rate_limit_error", "message": "slow"}}), "rate_limited"),
        ((500, {"type": "error", "error": {"type": "api_error", "message": "boom"}}), "api_status_500"),
    ],
)
def test_every_bad_reply_becomes_diagnosis_unavailable(stub, reply, reason):
    stub.replies.append(reply)
    with pytest.raises(DiagnosisUnavailable) as caught:
        provider().diagnose(b"x", CONTEXT)
    if reason:
        assert caught.value.reason == reason


def test_unreachable_api_becomes_diagnosis_unavailable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")  # nothing listens here
    with pytest.raises(DiagnosisUnavailable) as caught:
        provider().diagnose(b"x", CONTEXT)
    assert caught.value.reason in ("connection", "timeout")


def test_slow_api_times_out(monkeypatch):
    class Slow(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            import time

            time.sleep(2)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    slow_provider = AnthropicProvider(
        Settings(anthropic_api_key="k", diagnosis_timeout_s=0.3, diagnosis_retries=0)
    )
    with pytest.raises(DiagnosisUnavailable) as caught:
        slow_provider.diagnose(b"x", CONTEXT)
    assert caught.value.reason == "timeout"
    server.shutdown()


def test_no_credentials_is_an_ordinary_state(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("HOME", "/nonexistent")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:9")
    keyless = AnthropicProvider(
        Settings(anthropic_api_key=None, diagnosis_timeout_s=0.3, diagnosis_retries=0)
    )
    with pytest.raises(DiagnosisUnavailable) as caught:
        keyless.diagnose(b"x", CONTEXT)
    assert caught.value.reason in ("no_credentials", "connection", "authentication")


def test_provider_can_be_turned_off():
    assert build_provider(Settings(diagnosis_provider="none")) is None
    assert isinstance(
        build_provider(Settings(diagnosis_provider="anthropic", anthropic_api_key="k")),
        AnthropicProvider,
    )
