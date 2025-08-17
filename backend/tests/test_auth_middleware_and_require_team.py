import pytest
from fastapi.testclient import TestClient
from app.main import app

# We'll monkeypatch stack_auth functions to avoid real HTTP requests


@pytest.fixture
def client():
    return TestClient(app)


class DummyResp:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def patch_stack_auth(monkeypatch):
    # Default: valid token and membership
    def fake_verify_token(token: str):
        assert token == "valid-token"
        return {"id": "user_1", "selectedTeamId": "team_1"}

    def fake_verify_team(team_id: str, token: str):
        if token != "valid-token":
            raise Exception("invalid token")
        if team_id != "team_1":
            raise Exception("not a member")
        return {"id": team_id}

    monkeypatch.setattr(
        "app.security.stack_auth.verify_stack_access_token", fake_verify_token
    )
    monkeypatch.setattr(
        "app.security.stack_auth.verify_team_membership", fake_verify_team
    )


@pytest.fixture(autouse=True, scope="module")
def ensure_tables():
    # Ensure tables exist for SQLite runs (memory or file)
    from app.db.session import Base, engine
    from app.db import models  # noqa: F401  - ensure models are imported and registered

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_require_team_happy_path(client):
    res = client.post(
        "/v1/agents",
        json={"brief": "hello"},
        headers={"Authorization": "Bearer valid-token", "X-Team-Id": "team_1"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["org_id"] == "team_1"
    assert body["created_by"] == "user_1"


def test_require_team_missing_header(client):
    res = client.post(
        "/v1/agents",
        json={"brief": "hello"},
        headers={"Authorization": "Bearer valid-token"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "X-Team-Id header is required"


def test_require_team_forbidden_membership(client, monkeypatch):
    # Patch membership to fail
    def fake_verify_team(team_id: str, token: str):
        raise Exception("not a member")

    monkeypatch.setattr(
        "app.security.stack_auth.verify_team_membership", fake_verify_team
    )

    res = client.post(
        "/v1/agents",
        json={"brief": "hello"},
        headers={"Authorization": "Bearer valid-token", "X-Team-Id": "team_1"},
    )
    assert res.status_code in (401, 403, 500)  # underlying exception surface


def test_middleware_blocks_missing_token(client):
    res = client.post(
        "/v1/agents", json={"brief": "x"}, headers={"X-Team-Id": "team_1"}
    )
    assert res.status_code == 401


def test_middleware_allows_public_paths(client):
    res = client.get("/health")
    assert res.status_code == 200
