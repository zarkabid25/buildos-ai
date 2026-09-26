"""These tests script a fake model to exercise *our* code: the tool loop, tenant
scoping, the propose-then-approve gate, and error mapping. They say nothing about
how Claude itself behaves; that needs a real API key and can't be tested here."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.ai.llm import FALLBACK_BETA, AnthropicLLMClient
from app.api.v1.ai import get_llm
from app.core.config import get_settings
from app.main import app
from tests.conftest import make_user_in_company


def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(name, input, id="tu_1"):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def reply(*blocks, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=list(blocks))


class FakeLLM:
    """Plays back scripted responses; a callable entry receives the messages so far."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def create_message(self, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return step(messages) if callable(step) else step


@pytest.fixture
def use_llm():
    def _use(fake):
        app.dependency_overrides[get_llm] = lambda: fake
        return fake

    yield _use
    app.dependency_overrides.pop(get_llm, None)


def make(client, headers, path, body):
    res = client.post(f"/api/v1{path}", headers=headers, json=body)
    assert res.status_code == 201, (path, res.text)
    return res.json()


def chat(client, headers, message="hi", conversation_id=None):
    body = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return client.post("/api/v1/ai/chat", headers=headers, json=body)


def tool_results(messages):
    """All tool_result blocks the fake model was shown, decoded."""
    out = []
    for m in messages:
        if m["role"] == "user" and isinstance(m["content"], list):
            out += [(b, json.loads(b["content"])) for b in m["content"] if b.get("type") == "tool_result"]
    return out


# ---- configuration -----------------------------------------------------------


def test_chat_is_503_with_a_clear_message_when_no_key_is_configured(client, auth_a):
    res = chat(client, auth_a)
    assert res.status_code == 503
    assert "LLM_API_KEY" in res.json()["detail"]


def test_status_reports_configuration_and_never_returns_the_key(client, auth_a, monkeypatch):
    assert client.get("/api/v1/ai/status", headers=auth_a).json()["configured"] is False

    monkeypatch.setenv("LLM_API_KEY", "sk-ant-test-secret")
    get_settings.cache_clear()
    try:
        res = client.get("/api/v1/ai/status", headers=auth_a)
    finally:
        monkeypatch.setenv("LLM_API_KEY", "")
        get_settings.cache_clear()
    assert res.json() == {"configured": True, "provider": "anthropic", "model": "claude-opus-5"}
    assert "sk-ant-test-secret" not in res.text


# ---- the tool loop -----------------------------------------------------------


def test_model_can_use_tools_and_answer_from_the_result(client, auth_a, use_llm):
    make(client, auth_a, "/projects", {"name": "Alpha Tower", "code": "ALPHA", "budget": "500"})
    fake = use_llm(FakeLLM(reply(tool_use("list_projects", {}), stop="tool_use"), reply(text("You have one project."))))

    res = chat(client, auth_a, "What projects do we have?")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reply"] == "You have one project."
    assert [c["name"] for c in body["tool_calls"]] == ["list_projects"]

    (_, result), = tool_results(fake.calls[1]["messages"])
    assert [p["name"] for p in result["items"]] == ["Alpha Tower"]


def test_conversation_is_saved_and_history_is_sent_on_the_next_turn(client, auth_a, use_llm):
    fake = use_llm(FakeLLM(reply(text("First answer.")), reply(text("Second answer."))))
    first = chat(client, auth_a, "First question").json()
    chat(client, auth_a, "Second question", first["conversation_id"])

    second_call_messages = fake.calls[1]["messages"]
    assert [m["content"] for m in second_call_messages] == ["First question", "First answer.", "Second question"]

    detail = client.get(f"/api/v1/ai/conversations/{first['conversation_id']}", headers=auth_a).json()
    assert [(m["role"], m["content"]) for m in detail["messages"]] == [
        ("user", "First question"), ("assistant", "First answer."),
        ("user", "Second question"), ("assistant", "Second answer."),
    ]


def test_unknown_tool_is_an_error_result_not_a_crash(client, auth_a, use_llm):
    fake = use_llm(FakeLLM(reply(tool_use("delete_everything", {}), stop="tool_use"), reply(text("Sorry."))))
    res = chat(client, auth_a)
    assert res.status_code == 200
    (block, result), = tool_results(fake.calls[1]["messages"])
    assert block["is_error"] is True and "Unknown tool" in result["error"]


def test_a_runaway_model_is_stopped_after_the_iteration_cap(client, auth_a, use_llm):
    fake = use_llm(FakeLLM(reply(tool_use("list_projects", {}), stop="tool_use")))  # loops forever
    res = chat(client, auth_a)
    assert res.status_code == 200
    assert len(fake.calls) == get_settings().llm_max_tool_iterations
    assert "couldn't finish" in res.json()["reply"]


def test_a_refusal_is_handled_without_reading_content(client, auth_a, use_llm):
    use_llm(FakeLLM(reply(stop="refusal")))
    assert chat(client, auth_a).json()["reply"] == "I can't help with that request."


# ---- tenant isolation: the assistant sees only the caller's company ----------


def test_model_cannot_reach_another_companys_data(client, auth_a, auth_b, use_llm):
    secret = make(client, auth_a, "/projects", {"name": "Company A Secret Tower", "code": "SECRET", "budget": "1"})
    make(client, auth_b, "/projects", {"name": "B Depot", "code": "DEPOT", "budget": "1"})

    fake = use_llm(FakeLLM(
        reply(
            tool_use("list_projects", {"company_id": "someone-elses"}, id="t1"),  # extra input must be ignored
            tool_use("get_project_overview", {"project_id": secret["id"]}, id="t2"),
            stop="tool_use",
        ),
        reply(text("done")),
    ))
    assert chat(client, auth_b).status_code == 200

    results = {b["tool_use_id"]: (b, r) for b, r in tool_results(fake.calls[1]["messages"])}
    assert [p["name"] for p in results["t1"][1]["items"]] == ["B Depot"]
    assert results["t2"][0]["is_error"] is True
    assert "Secret" not in json.dumps(results["t2"][1])
    assert "Secret" not in json.dumps(fake.calls[1]["messages"], default=str)


def test_conversations_are_private_to_the_user_who_started_them(client, auth_a, auth_b, use_llm):
    use_llm(FakeLLM(reply(text("ok"))))
    conv = chat(client, auth_a).json()["conversation_id"]
    viewer = make_user_in_company(client, auth_a, "viewer@example.com", "viewer")

    assert client.get(f"/api/v1/ai/conversations/{conv}", headers=auth_a).status_code == 200
    assert client.get(f"/api/v1/ai/conversations/{conv}", headers=auth_b).status_code == 404  # other company
    assert client.get(f"/api/v1/ai/conversations/{conv}", headers=viewer).status_code == 404  # same company
    assert chat(client, viewer, "continue", conv).status_code == 404
    assert client.get("/api/v1/ai/conversations", headers=viewer).json() == []


# ---- propose, then a person approves ----------------------------------------


@pytest.fixture
def setup(client, auth_a):
    project = make(client, auth_a, "/projects", {"name": "Tower", "code": "TWR", "budget": "1"})
    cement = make(client, auth_a, "/materials", {"name": "Cement", "sku": "CEM", "unit": "Bag"})
    return SimpleNamespace(project=project, cement=cement)


def propose_call(setup, quantity=500, **over):
    args = {"project_id": setup.project["id"], "items": [{"material_id": setup.cement["id"], "quantity": quantity}], **over}
    return reply(tool_use("propose_material_request", args), stop="tool_use")


def material_requests(client, headers):
    return client.get("/api/v1/material-requests", headers=headers).json()


def test_proposing_creates_only_a_draft(client, auth_a, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("I drafted it."))))
    body = chat(client, auth_a).json()

    assert len(body["proposals"]) == 1
    proposal = body["proposals"][0]
    assert proposal["status"] == "pending" and "Cement" in proposal["summary"] and "500" in proposal["summary"]
    assert material_requests(client, auth_a) == []  # nothing real was created by the model


def test_approving_creates_the_real_request_owned_by_the_approver(client, auth_a, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("drafted"))))
    proposal = chat(client, auth_a).json()["proposals"][0]
    me = client.get("/api/v1/auth/me", headers=auth_a).json()

    res = client.post(f"/api/v1/ai/proposals/{proposal['id']}/approve", headers=auth_a)
    assert res.status_code == 200, res.text
    approved = res.json()
    assert approved["status"] == "approved" and approved["result_ref"]

    (mr,) = material_requests(client, auth_a)
    assert mr["id"] == approved["result_ref"]
    assert mr["requested_by_id"] == me["id"]  # the person, not the assistant
    assert [(i["material_id"], i["quantity"]) for i in mr["items"]] == [(setup.cement["id"], "500.000")]


def test_a_proposal_cannot_be_decided_twice(client, auth_a, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("drafted"))))
    pid = chat(client, auth_a).json()["proposals"][0]["id"]

    assert client.post(f"/api/v1/ai/proposals/{pid}/approve", headers=auth_a).status_code == 200
    assert client.post(f"/api/v1/ai/proposals/{pid}/approve", headers=auth_a).status_code == 409
    assert client.post(f"/api/v1/ai/proposals/{pid}/reject", headers=auth_a).status_code == 409
    assert len(material_requests(client, auth_a)) == 1  # not duplicated


def test_rejecting_creates_nothing(client, auth_a, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("drafted"))))
    pid = chat(client, auth_a).json()["proposals"][0]["id"]

    res = client.post(f"/api/v1/ai/proposals/{pid}/reject", headers=auth_a)
    assert res.status_code == 200 and res.json()["status"] == "rejected"
    assert material_requests(client, auth_a) == []
    assert client.get("/api/v1/ai/proposals?status=pending", headers=auth_a).json() == []


def test_a_viewer_cannot_approve_or_reject(client, auth_a, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("drafted"))))
    pid = chat(client, auth_a).json()["proposals"][0]["id"]
    viewer = make_user_in_company(client, auth_a, "viewer@example.com", "viewer")

    assert client.post(f"/api/v1/ai/proposals/{pid}/approve", headers=viewer).status_code == 403
    assert client.post(f"/api/v1/ai/proposals/{pid}/reject", headers=viewer).status_code == 403
    assert client.get("/api/v1/ai/proposals", headers=viewer).status_code == 200  # can still see them
    assert material_requests(client, auth_a) == []


def test_another_company_cannot_decide_or_see_a_proposal(client, auth_a, auth_b, setup, use_llm):
    use_llm(FakeLLM(propose_call(setup), reply(text("drafted"))))
    pid = chat(client, auth_a).json()["proposals"][0]["id"]

    assert client.post(f"/api/v1/ai/proposals/{pid}/approve", headers=auth_b).status_code == 404
    assert client.get("/api/v1/ai/proposals", headers=auth_b).json() == []


@pytest.mark.parametrize("bad", ["foreign_material", "zero_quantity", "no_items", "bad_id"])
def test_bad_proposals_are_rejected_with_an_error_result_and_no_draft(client, auth_a, auth_b, setup, use_llm, bad):
    foreign = make(client, auth_b, "/materials", {"name": "B Steel", "sku": "BS", "unit": "Ton"})
    args = {
        "foreign_material": {"project_id": setup.project["id"], "items": [{"material_id": foreign["id"], "quantity": 1}]},
        "zero_quantity": {"project_id": setup.project["id"], "items": [{"material_id": setup.cement["id"], "quantity": 0}]},
        "no_items": {"project_id": setup.project["id"], "items": []},
        "bad_id": {"project_id": "not-a-uuid", "items": [{"material_id": setup.cement["id"], "quantity": 1}]},
    }[bad]
    fake = use_llm(FakeLLM(reply(tool_use("propose_material_request", args), stop="tool_use"), reply(text("sorry"))))

    body = chat(client, auth_a).json()
    (block, _), = tool_results(fake.calls[1]["messages"])
    assert block["is_error"] is True
    assert body["proposals"] == []
    assert client.get("/api/v1/ai/proposals", headers=auth_a).json() == []


# ---- provider failures -------------------------------------------------------


def _request():
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    "error,status",
    [
        (anthropic.APIConnectionError(request=_request()), 503),
        (anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=_request()), body=None), 429),
        (anthropic.AuthenticationError("bad key", response=httpx2.Response(401, request=_request()), body=None), 502),
        (anthropic.InternalServerError("boom", response=httpx2.Response(500, request=_request()), body=None), 502),
    ],
)
def test_provider_errors_map_to_safe_statuses_and_leave_no_empty_conversation(client, auth_a, use_llm, error, status):
    def boom(_messages):
        raise error

    use_llm(FakeLLM(boom))
    res = chat(client, auth_a)
    assert res.status_code == status
    assert "boom" not in res.text and "slow down" not in res.text and "bad key" not in res.text
    assert client.get("/api/v1/ai/conversations", headers=auth_a).json() == []


# ---- what the real client sends (checked against the SDK, not the live API) --


def _sdk_client(capture, response_json=None):
    def handler(request: httpx2.Request) -> httpx2.Response:
        capture["request"] = request
        capture["body"] = json.loads(request.content)
        return httpx2.Response(200, json=response_json or {
            "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5",
            "content": [{"type": "text", "text": "hello"}], "stop_reason": "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    return anthropic.Anthropic(api_key="test-key", http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def test_real_client_request_shape_with_fallbacks(client):
    captured = {}
    llm = AnthropicLLMClient("test-key", "claude-opus-5", 16000, True, sdk_client=_sdk_client(captured))
    tools = [{"name": "list_projects", "description": "d", "input_schema": {"type": "object", "properties": {}}}]

    response = llm.create_message("SYS", [{"role": "user", "content": "hi"}], tools)

    body = captured["body"]
    assert captured["request"].url.path == "/v1/messages"
    assert FALLBACK_BETA in captured["request"].headers["anthropic-beta"]
    assert body["model"] == "claude-opus-5" and body["max_tokens"] == 16000
    assert body["fallbacks"] == "default"
    assert body["system"] == "SYS" and body["tools"][0]["name"] == "list_projects"
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    for rejected_on_opus_5 in ("temperature", "top_p", "top_k", "thinking"):
        assert rejected_on_opus_5 not in body
    assert response.stop_reason == "end_turn" and response.content[0].text == "hello"


def test_real_client_without_fallbacks_uses_the_plain_endpoint(client):
    captured = {}
    llm = AnthropicLLMClient("test-key", "claude-opus-5", 1000, False, sdk_client=_sdk_client(captured))
    llm.create_message("SYS", [{"role": "user", "content": "hi"}], [])
    assert "fallbacks" not in captured["body"]
    assert "anthropic-beta" not in captured["request"].headers
