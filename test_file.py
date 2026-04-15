import pytest
from Flask_routes import app
import Flask_routes


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    Flask_routes.limiter.enabled = False
    with app.test_client() as client:
        yield client

@pytest.fixture()
def register_employee(client):
    response = client.post("/api/v1/register_employee", json={
        "email": "employee@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 201

@pytest.fixture()
def register_admin(client):
    response = client.post("/api/v1/register_admin", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    assert response.status_code == 201

@pytest.fixture()
def admin_token(client, register_admin):
    response = client.post("/api/v1/login_admin", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    return response.get_json()["token"]

@pytest.fixture()
def employee_token(client, register_employee):
    response = client.post("/api/v1/login_employee", json={
        "email": "employee@test.com",
        "password": "testpass123"
    })
    return response.get_json()["token"]



def test_register_employee(client):
    response = client.post("/api/v1/register_employee", json={
        "email": "new@test.com",
        "password": "pass123"
    })
    assert response.status_code == 201
    assert "Registered" in response.get_json()["message"]

def test_register_admin(client):
    response = client.post("/api/v1/register_admin", json={
        "email": "adm@test.com",
        "password": "pass123"
    })
    assert response.status_code == 201

def test_duplicate_employee_email(client, register_employee):
    response = client.post("/api/v1/register_employee", json={
        "email": "employee@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 409
    assert "Email Already Exists" in response.get_json()["message"]

def test_duplicate_admin_email(client, register_admin):
    response = client.post("/api/v1/register_admin", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    assert response.status_code == 409

def test_login_employee(client, register_employee):
    response = client.post("/api/v1/login_employee", json={
        "email": "employee@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "token" in response.get_json()

def test_login_admin(client, register_admin):
    response = client.post("/api/v1/login_admin", json={
        "email": "admin@test.com",
        "password": "adminpass123"
    })
    assert response.status_code == 200
    assert "token" in response.get_json()

def test_wrong_password_employee(client, register_employee):
    response = client.post("/api/v1/login_employee", json={
        "email": "employee@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_wrong_password_admin(client, register_admin):
    response = client.post("/api/v1/login_admin", json={
        "email": "admin@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_missing_fields_register(client):
    response = client.post("/api/v1/register_employee", json={
        "email": "only@test.com"
    })
    assert response.status_code == 409




def test_create_task(client, employee_token):
    response = client.post("/api/v1/tasks",
        json={"title": "Buy groceries", "priority": "medium"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 201
    assert "task" in response.get_json()

def test_create_task_missing_title(client, employee_token):
    response = client.post("/api/v1/tasks",
        json={"priority": "medium"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 422
    assert "errors" in response.get_json()

def test_create_task_invalid_priority(client, employee_token):
    response = client.post("/api/v1/tasks",
        json={"title": "My Task", "priority": "ultra"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 422

def test_admin_cannot_create_task(client, admin_token):
    response = client.post("/api/v1/tasks",
        json={"title": "Admin task", "priority": "high"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 401

def test_get_all_tasks_by_admin(client, admin_token, employee_token):
    client.post("/api/v1/tasks",
        json={"title": "Task One", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    response = client.get("/api/v1/tasks",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)

def test_employee_cannot_get_all_tasks(client, employee_token):
    response = client.get("/api/v1/tasks",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 401

def test_get_my_tasks(client, employee_token):
    client.post("/api/v1/tasks",
        json={"title": "Personal task", "priority": "high"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    response = client.get("/api/v1/my_tasks",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert len(response.get_json()) >= 1

def test_get_task_by_id(client, employee_token):
    create = client.post("/api/v1/tasks",
        json={"title": "Specific task", "priority": "medium"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.get(f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert response.get_json()["id"] == task_id

def test_get_task_not_found(client, employee_token):
    response = client.get("/api/v1/tasks/9999",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 404

def test_update_task(client, employee_token):
    create = client.post("/api/v1/tasks",
        json={"title": "Old title", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.put(f"/api/v1/tasks/{task_id}",
        json={"title": "Updated title", "status": "in_progress", "priority": "high"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert response.get_json()["task"]["title"] == "Updated title"
    assert response.get_json()["task"]["status"] == "in_progress"

def test_update_task_invalid_status(client, employee_token):
    create = client.post("/api/v1/tasks",
        json={"title": "Task", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.put(f"/api/v1/tasks/{task_id}",
        json={"title": "Task", "status": "flying"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 422

def test_update_task_not_found(client, employee_token):
    response = client.put("/api/v1/tasks/9999",
        json={"title": "Ghost", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 404

def test_admin_can_update_any_task(client, employee_token, admin_token):
    create = client.post("/api/v1/tasks",
        json={"title": "Employee task", "priority": "medium"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.put(f"/api/v1/tasks/{task_id}",
        json={"title": "Admin updated", "priority": "high"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

def test_delete_task(client, employee_token):
    create = client.post("/api/v1/tasks",
        json={"title": "To be deleted", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.delete(f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert "deleted" in response.get_json()["message"]

def test_delete_task_not_found(client, employee_token):
    response = client.delete("/api/v1/tasks/9999",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 404

def test_admin_can_delete_any_task(client, employee_token, admin_token):
    create = client.post("/api/v1/tasks",
        json={"title": "Deletable", "priority": "low"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    task_id = create.get_json()["task"]["id"]
    response = client.delete(f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

def test_filter_tasks_by_status(client, employee_token):
    client.post("/api/v1/tasks",
        json={"title": "Pending task", "priority": "medium"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    response = client.get("/api/v1/tasks/filter?status=pending",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert all(t["status"] == "pending" for t in data)

def test_filter_tasks_by_priority(client, employee_token):
    client.post("/api/v1/tasks",
        json={"title": "High priority task", "priority": "high"},
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    response = client.get("/api/v1/tasks/filter?priority=high",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert all(t["priority"] == "high" for t in data)

def test_logout_employee(client, employee_token):
    response = client.post("/api/v1/logout",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200

def test_logout_admin(client, admin_token):
    response = client.post("/api/v1/logout",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

def test_blacklisted_token_blocked(client, employee_token):
    client.post("/api/v1/logout",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    response = client.get("/api/v1/my_tasks",
        headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 401
