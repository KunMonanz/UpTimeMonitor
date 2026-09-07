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


def test_get_all_monitors_route_returns_accessible_monitors(
    client, create_user, create_group, create_monitor, auth_headers
):
    user = create_user("alice", "alice@example.com")
    group = create_group("ops", user.id)
    create_monitor("https://personal.example.com", owner_user_id=user.id)
    create_monitor("https://group.example.com", owner_group_id=group.id)

    response = client.get("/api/v1/monitors/", headers=auth_headers(user))

    assert response.status_code == 200
    urls = {item["url"] for item in response.json()}
    assert urls == {"https://personal.example.com/", "https://group.example.com/"}


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
