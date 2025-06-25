import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# --- ヘルパー関数 ---
def register_user(username: str, password: str):
    return client.post("/register", json={"username": username, "password": password})

def login_user(username: str, password: str):
    return client.post("/login", json={"username": username, "password": password})

def create_creator(token: str, revenue_share=0.5):
    return client.post("/creators/", json={
        "name": "Test Creator",
        "image_url": "http://example.com/image.png",
        "description": "Test description",
        "revenue_share": revenue_share
    }, headers={"Authorization": f"Bearer {token}"})

# --- DBリセット用フィクスチャ ---
@pytest.fixture(autouse=True)
def reset_db_before_and_after_tests():
    # テスト開始前にDBリセット
    response = client.post("/reset-db")
    assert response.status_code == 200

    yield  # テスト実行

    # テスト終了後にDBリセット
    response = client.post("/reset-db")
    assert response.status_code == 200


# --- テスト関数 ---

def test_register_success():
    res = register_user("testuser1", "password123")
    assert res.status_code in (200, 400)  # ユーザーが既に存在する場合もOK

def test_login_success():
    res_reg = register_user("testuser2", "password123")
    assert res_reg.status_code in (200, 400)

    res = login_user("testuser2", "password123")
    assert res.status_code == 200
    assert "access_token" in res.json()

def test_login_failure_wrong_password():
    register_user("testuser3", "correctpassword")
    res = login_user("testuser3", "wrongpassword")
    assert res.status_code == 401

def test_create_creator_success():
    username = "testuser4"
    password = "password"
    register_user(username, password)
    token = login_user(username, password).json()["access_token"]
    res = create_creator(token)
    assert res.status_code == 200
    assert res.json()["name"] == "Test Creator"

def test_create_creator_without_token():
    res = client.post("/creators/", json={
        "name": "No Token Creator",
        "image_url": "http://example.com/image.png",
        "description": "No token",
        "revenue_share": 0.5
    })
    assert res.status_code == 403

def test_update_creator_success():
    username = "testuser5"
    password = "password"
    register_user(username, password)
    token = login_user(username, password).json()["access_token"]
    creator = create_creator(token).json()
    creator_id = creator["id"]

    res = client.put(f"/creators/{creator_id}", json={
        "name": "Updated Name",
        "description": "Updated Description"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Name"

def test_create_creator_invalid_revenue_share():
    username = "testuser6"
    password = "password"
    register_user(username, password)
    token = login_user(username, password).json()["access_token"]
    res = create_creator(token, revenue_share=1.5)
    assert res.status_code == 422
