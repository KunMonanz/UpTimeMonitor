def test_create_personal_monitor_route_creates_monitor(
    client, create_user, auth_headers
):
    user = create_user("alice", "alice@example.com")

    response = client.post(
        "/api/v1/monitors/",
        headers=auth_headers(user),
        json={"url": "https://example.com"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com/"
    assert data["owner_user_id"] == str(user.id)
    assert data["owner_group_id"] is None


def test_create_group_owned_monitor_route_creates_monitor(
    client, create_user, create_group, auth_headers
):
    admin = create_user("admin", "admin@example.com")
    group = create_group("ops", admin.id)

    response = client.post(
        "/api/v1/monitors/",
        headers=auth_headers(admin),
        json={"url": "https://example.com", "group_id": str(group.id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["owner_group_id"] == str(group.id)
    assert data["owner_user_id"] is None


def test_create_personal_monitor_route_rejects_duplicate_normalized_url_for_same_user(
    client, create_user, auth_headers
):
    user = create_user("alice-dup", "alice-dup@example.com")

    first_response = client.post(
        "/api/v1/monitors/",
        headers=auth_headers(user),
        json={"url": "https://example.com"},
    )
    second_response = client.post(
        "/api/v1/monitors/",
        headers=auth_headers(user),
        json={"url": "https://example.com/"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert "already exists" in second_response.json()["detail"]


def test_get_all_monitors_route_returns_accessible_monitors(
    client, create_user, create_group, create_monitor, auth_headers
):
    user = create_user("alice", "alice@example.com")
    group = create_group("ops", user.id)
    create_monitor("https://personal.example.com", owner_user_id=user.id)
    create_monitor("https://group.example.com", owner_group_id=group.id)

    response = client.get("/api/v1/monitors/", headers=auth_headers(user))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["offset"] == 0
    assert data["limit"] == 20
    urls = {item["url"] for item in data["items"]}
    assert urls == {"https://personal.example.com/", "https://group.example.com/"}


def test_get_all_monitors_route_supports_pagination(
    client, create_user, create_monitor, auth_headers
):
    user = create_user("alice", "alice@example.com")
    create_monitor("https://one.example.com", owner_user_id=user.id)
    create_monitor("https://two.example.com", owner_user_id=user.id)

    response = client.get(
        "/api/v1/monitors/?offset=0&limit=1", headers=auth_headers(user)
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["offset"] == 0
    assert data["limit"] == 1
    assert len(data["items"]) == 1


def test_get_monitor_route_returns_monitor(
    client, create_user, create_monitor, auth_headers
):
    user = create_user("alice", "alice@example.com")
    monitor = create_monitor("https://example.com", owner_user_id=user.id)

    response = client.get(f"/api/v1/monitors/{monitor.id}", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json()["id"] == str(monitor.id)
    assert response.json()["url"] == "https://example.com/"


def test_update_monitor_route_updates_monitor(
    client, create_user, create_monitor, auth_headers, get_monitor
):
    user = create_user("alice", "alice@example.com")
    monitor = create_monitor("https://example.com", owner_user_id=user.id)

    response = client.patch(
        f"/api/v1/monitors/{monitor.id}",
        headers=auth_headers(user),
        json={"url": "https://updated.example.com", "status": True},
    )

    assert response.status_code == 200
    assert response.json()["url"] == "https://updated.example.com/"
    assert get_monitor(monitor.id).url == "https://updated.example.com/"


def test_update_monitor_route_rejects_duplicate_normalized_url_for_same_user(
    client, create_user, create_monitor, auth_headers
):
    user = create_user("alice-update-dup", "alice-update-dup@example.com")
    first_monitor = create_monitor("https://one.example.com", owner_user_id=user.id)
    create_monitor("https://two.example.com", owner_user_id=user.id)

    response = client.patch(
        f"/api/v1/monitors/{first_monitor.id}",
        headers=auth_headers(user),
        json={"url": "https://two.example.com/", "status": True},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_delete_monitor_route_deletes_monitor(
    client, create_user, create_monitor, auth_headers, get_monitor
):
    user = create_user("alice", "alice@example.com")
    monitor = create_monitor("https://example.com", owner_user_id=user.id)

    response = client.delete(
        f"/api/v1/monitors/{monitor.id}", headers=auth_headers(user)
    )

    assert response.status_code == 204
    assert get_monitor(monitor.id) is None
