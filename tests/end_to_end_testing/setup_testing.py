def test_start_chat(client):
    response = client.post("/chat/start")
    assert response.status_code == 200
    assert "session_id" in response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_invalid_session(client):
    # Test sending a message to a session that doesn't exist
    payload = {"session_id": "non-existent-id", "prompt": "hi"}
    response = client.post("/chat/message", json=payload)
    assert response.status_code == 404
