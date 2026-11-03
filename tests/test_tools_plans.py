from pathlib import Path

import pytest


def tool(client, name, arguments):
    return client.post("/v1/tools/execute", json={"tool": name, "arguments": arguments})


def test_real_calculator(client):
    assert tool(client, "calculate", {"expression": "(4 + 6) / 2"}).json()["result"]["value"] == 5


@pytest.mark.parametrize("expression", ["__import__('os').system('id')", "2 ** 999999999", "1/0"])
def test_unsafe_calculator(client, expression):
    assert tool(client, "calculate", {"expression": expression}).json()["status"] == "failed"


def test_approval_replay_and_verified_file(client, configured):
    args = {"path": "note.txt", "content": "Hello"}
    response = tool(client, "file.create", args).json()
    assert response["status"] == "waiting_for_authorization"
    assert not (Path(configured[0].files_root) / "note.txt").exists()
    aid = response["approval_id"]
    result = client.post(f"/v1/approvals/{aid}/decision", json={"approve": True}).json()
    assert result["result"]["value"]["verified"] is True
    assert client.post(f"/v1/approvals/{aid}/decision", json={"approve": True}).status_code == 400
    assert tool(client, "file.read", {"path": "note.txt"}).json()["result"]["value"] == "Hello"


def test_denial(client, configured):
    aid = tool(client, "file.create", {"path": "no.txt", "content": "No"}).json()["approval_id"]
    assert (
        client.post(f"/v1/approvals/{aid}/decision", json={"approve": False}).json()["status"]
        == "denied"
    )
    assert not (Path(configured[0].files_root) / "no.txt").exists()


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", "a/../../outside", "a\\b"])
def test_traversal(client, path):
    assert tool(client, "file.read", {"path": path}).json()["status"] == "failed"


def test_symlink(client, configured, tmp_path):
    (tmp_path / "secret").write_text("private")
    (Path(configured[0].files_root) / "link").symlink_to(tmp_path / "secret")
    assert tool(client, "file.read", {"path": "link"}).json()["status"] == "failed"
    (Path(configured[0].files_root) / "dir").symlink_to(tmp_path, target_is_directory=True)
    assert tool(client, "file.read", {"path": "dir/secret"}).json()["status"] == "failed"


def test_validation_no_authorization_override(client):
    assert tool(client, "shell", {"command": "ls"}).status_code == 400
    assert tool(client, "time", {"authorized": True}).status_code == 400
    assert (
        client.post(
            "/v1/tools/execute", json={"tool": "time", "arguments": {}, "authorized": True}
        ).status_code
        == 422
    )


def test_plan_dependencies_approval_resume(client):
    plan = {
        "title": "Create a note",
        "steps": [
            {"id": "a", "tool": "calculate", "arguments": {"expression": "2+2"}},
            {
                "id": "b",
                "tool": "file.create",
                "arguments": {"path": "plan.txt", "content": "four"},
                "depends_on": ["a"],
            },
            {
                "id": "c",
                "tool": "file.read",
                "arguments": {"path": "plan.txt"},
                "depends_on": ["b"],
            },
        ],
    }
    tid = client.post("/v1/tasks", json=plan).json()["id"]
    task = client.post(f"/v1/tasks/{tid}/run").json()
    assert task["status"] == "waiting_for_authorization"
    aid = task["steps"][1]["result"]["approval_id"]
    assert client.post(f"/v1/approvals/{aid}/decision", json={"approve": True}).status_code == 200
    final = client.post(f"/v1/tasks/{tid}/run").json()
    assert final["status"] == "completed"
    assert final["steps"][2]["result"]["result"]["value"] == "four"


def test_invalid_dependencies(client):
    response = client.post(
        "/v1/tasks",
        json={
            "title": "bad",
            "steps": [{"id": "a", "tool": "time", "arguments": {}, "depends_on": ["a"]}],
        },
    )
    assert response.status_code == 400


def test_plan_failure_and_cancel(client):
    plan = {
        "title": "bad",
        "steps": [{"id": "a", "tool": "calculate", "arguments": {"expression": "1/0"}}],
    }
    tid = client.post("/v1/tasks", json=plan).json()["id"]
    assert client.post(f"/v1/tasks/{tid}/run").json()["status"] == "failed"
    plan["steps"][0] = {
        "id": "a",
        "tool": "file.create",
        "arguments": {"path": "cancelled", "content": "no"},
    }
    tid = client.post("/v1/tasks", json=plan).json()["id"]
    task = client.post(f"/v1/tasks/{tid}/run").json()
    aid = task["steps"][0]["result"]["approval_id"]
    assert client.post(f"/v1/tasks/{tid}/cancel").json()["status"] == "cancelled"
    assert client.post(f"/v1/approvals/{aid}/decision", json={"approve": True}).status_code == 400
    assert client.post(f"/v1/tasks/{tid}/run").json()["status"] == "cancelled"
