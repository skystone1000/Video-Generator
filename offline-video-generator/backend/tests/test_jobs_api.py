from fastapi.testclient import TestClient

from app.main import app


def test_create_and_list_job() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            json={
                "prompt": "mock shot of a brass robot painting a mural",
                "negative_prompt": "",
                "runtime": "mock",
                "width": 320,
                "height": 180,
                "video_length": 12,
                "fps": 12,
                "steps": 4,
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["prompt"] == "mock shot of a brass robot painting a mural"
        assert payload["status"] in {"queued", "loading_model", "generating", "failed"}

        list_response = client.get("/api/jobs")
        assert list_response.status_code == 200
        assert any(job["id"] == payload["id"] for job in list_response.json())
