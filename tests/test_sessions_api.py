import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_list_sessions_empty(client):
    res = client.get("/api/sessions")
    assert res.status_code == 200
    assert res.json() == {"sessions": []}


def test_create_session(client):
    res = client.post("/api/session", json={"display_name": "Demo", "initial_prompt": "hi"})
    assert res.status_code == 201
    body = res.json()
    assert "session_id" in body
    assert body["display_name"] == "Demo"


def test_get_session_not_found(client):
    res = client.get("/api/session/does-not-exist")
    assert res.status_code == 404
    assert res.json()["detail"].startswith("Session does-not-exist not found")


def test_search_sessions_with_data(client):
    # Create a session via API (initial_prompt stored with session)
    create_res = client.post("/api/session", json={"display_name": "Demo", "initial_prompt": "hello world"})
    assert create_res.status_code == 201

    # Search for a term that should match the initial prompt-derived data
    res = client.get("/api/sessions/search", params={"q": "hello"})
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_session_list_after_create(client):
    # Create two sessions
    r1 = client.post("/api/session", json={"display_name": "One", "initial_prompt": "hi"})
    r2 = client.post("/api/session", json={"display_name": "Two", "initial_prompt": "hello"})
    assert r1.status_code == 201 and r2.status_code == 201

    # List sessions
    res = client.get("/api/sessions")
    assert res.status_code == 200
    data = res.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)
    assert len(data["sessions"]) >= 2
    # Ensure fields exist
    item = data["sessions"][0]
    for key in ("session_id", "display_name", "status", "created_at", "message_count"):
        assert key in item


def test_delete_session_flow(client):
    # Create a session
    resp = client.post("/api/session", json={"display_name": "ToDelete", "initial_prompt": "x"})
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    # Delete it
    del_resp = client.delete(f"/api/session/{session_id}")
    assert del_resp.status_code == 200

    # Verify not found and list excludes it
    not_found = client.get(f"/api/session/{session_id}")
    assert not_found.status_code == 404
    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    assert all(s["session_id"] != session_id for s in list_resp.json().get("sessions", []))


def test_session_history_initial_empty(client):
    resp = client.post("/api/session", json={"display_name": "WithHistory", "initial_prompt": "start"})
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]
    hist = client.get(f"/api/session/{session_id}/history")
    assert hist.status_code == 200
    hist_body = hist.json()
    assert hist_body["session_id"] == session_id
    assert isinstance(hist_body.get("messages", []), list)
    # No messages persisted at creation
    assert len(hist_body.get("messages", [])) == 0


def test_generate_session_name_on_missing_display(client):
    # No display_name provided, ensure API generates a non-empty display name from initial_prompt
    long_prompt = "This is a very long initial prompt that should be trimmed to a short display name"
    res = client.post("/api/session", json={"initial_prompt": long_prompt})
    assert res.status_code == 201
    body = res.json()
    assert body["display_name"]
    assert isinstance(body["display_name"], str)
    # should be <= 23 chars if truncated to 20 + '...'
    assert len(body["display_name"]) <= 23

