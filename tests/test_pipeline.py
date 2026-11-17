import json
import subprocess
import zipfile
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from samaratan.api import create_app
from samaratan.config import Settings
from samaratan.godot import EngineError, GodotAdapter
from samaratan.models import GamePlan
from samaratan.providers import CLIProvider, DemoProvider, ProviderError, parse_plan
from samaratan.service import JobService
from samaratan.store import NotFound, Store


@pytest.fixture
def spec():
    return DemoProvider().generate("A detective explores an abandoned street at night")


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(Settings(root=tmp_path, godot_binary="not-installed-godot")))


def test_fixture_is_complete(spec):
    assert spec.title == "Midnight Evidence"
    assert len(spec.scenes) == 4
    assert all(c.next_scene in {s.id for s in spec.scenes} for s in spec.scenes for c in s.choices)


def test_duplicate_scene_rejected(spec):
    data = spec.model_dump()
    data["scenes"].append(data["scenes"][0])
    with pytest.raises(ValidationError, match="Duplicate scene"):
        GamePlan.model_validate(data)


def test_unknown_choice_rejected(spec):
    data = spec.model_dump()
    data["scenes"][0]["choices"][0]["next_scene"] = "does_not_exist"
    with pytest.raises(ValidationError, match="Unknown scene"):
        GamePlan.model_validate(data)


def test_unreachable_scene_rejected(spec):
    data = spec.model_dump()
    data["scenes"].append({"id": "isolated", "title": "Lost", "narration": "No route", "choices": []})
    with pytest.raises(ValidationError, match="reachable"):
        GamePlan.model_validate(data)


def test_untrusted_extra_field_rejected(spec):
    data = spec.model_dump()
    data["shell_command"] = "rm -rf /"
    with pytest.raises(ValidationError):
        GamePlan.model_validate(data)


def test_duplicate_characters_rejected(spec):
    data = spec.model_dump()
    data["characters"].append(data["characters"][0])
    with pytest.raises(ValidationError, match="Duplicate character"):
        GamePlan.model_validate(data)


def test_parse_json_with_markdown(spec):
    assert parse_plan("Here is your game:\n```json\n" + spec.model_dump_json() + "\n```").title == spec.title


def test_parse_invalid_agent_response():
    with pytest.raises(ProviderError):
        parse_plan("No game here")


def test_parse_agent_response_size_cap():
    with pytest.raises(ProviderError, match="size limit"):
        parse_plan("z" * 200001)


def test_unknown_cli_rejected():
    with pytest.raises(ValueError):
        CLIProvider("bash")


def test_agent_cli_not_found(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError()
    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(ProviderError, match="not found"):
        CLIProvider("claude").generate("some game prompt")


def test_agent_cli_is_shell_free_and_read_only(monkeypatch, spec):
    observed = {}
    def fake(argv, **kw):
        observed.update(argv=argv, kwargs=kw)
        return subprocess.CompletedProcess(argv, 0, stdout=spec.model_dump_json(), stderr="")
    monkeypatch.setattr(subprocess, "run", fake)
    assert CLIProvider("codex").generate("A character story").title == spec.title
    assert observed["argv"][0] == "codex"
    assert "read-only" in observed["argv"]
    assert observed["kwargs"].get("shell") is None
    assert "A character story" in observed["kwargs"]["input"]


def test_generate_real_engine_sources(tmp_path, spec):
    project = GodotAdapter().generate(spec, tmp_path)
    assert (project / "main.tscn").is_file()
    assert "extends Node3D" in (project / "main.gd").read_text()
    assert json.loads((project / "game_data.json").read_text())["title"] == spec.title
    assert (project / "export_presets.cfg").exists()


def test_bundle_contains_expected_files(tmp_path, spec):
    adapter = GodotAdapter()
    project = adapter.generate(spec, tmp_path)
    artifact = adapter.bundle(project, tmp_path / "output.zip")
    with zipfile.ZipFile(artifact) as archive:
        names = archive.namelist()
        assert "samaratan-game/main.tscn" in names
        assert "samaratan-game/game_data.json" in names
        assert all(".." not in n for n in names)


def test_missing_godot_is_clear_error(tmp_path, spec):
    project = GodotAdapter().generate(spec, tmp_path)
    with pytest.raises(EngineError, match="Godot 4 CLI missing"):
        GodotAdapter().export_windows(project, tmp_path / "demo.exe", "nonexistent-engine-binary-xyz")


def test_store_refuses_path_traversal(tmp_path):
    store = Store(tmp_path)
    with pytest.raises(NotFound):
        store.directory("../../outside")
    with pytest.raises(NotFound):
        store.get("not-a-real-job")


def test_store_jobs_are_independent(tmp_path):
    store = Store(tmp_path)
    one = store.create("demo", "one prompt", False)
    two = store.create("demo", "another prompt", False)
    assert one["id"] != two["id"]
    store.update(one["id"], "succeeded", title="First")
    assert store.get(two["id"])["status"] == "queued"


def test_store_restart_recovers_orphan_jobs(tmp_path):
    store = Store(tmp_path)
    job = store.create("demo", "some prompt", False)
    store.update(job["id"], "running")
    fresh = Store(tmp_path)
    assert fresh.get(job["id"])["status"] == "failed"


def test_store_rejects_arbitrary_update_field(tmp_path):
    store = Store(tmp_path)
    job = store.create("demo", "some prompt", False)
    with pytest.raises(ValueError):
        store.update(job["id"], "running", user_sql="attack")


def test_health_endpoint(client):
    assert client.get("/health").json()["status"] == "ok"


def test_frontend_loaded(client):
    assert "Your story" in client.get("/").text


def test_capabilities_reflect_absent_engine(client):
    caps = client.get("/api/capabilities").json()
    assert caps["providers"]["demo"] is True
    assert caps["engines"]["godot4"]["windows_export"] is False
    assert caps["billing_enabled"] is False


def test_demo_job_produces_download(client):
    response = client.post("/api/jobs", json={"prompt": "A rainy dramatic police story", "provider": "demo"})
    assert response.status_code == 202
    job_id = response.json()["id"]
    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "succeeded"
    response = client.get(f"/api/jobs/{job_id}/source")
    assert response.status_code == 200
    assert response.content[:2] == b"PK"


def test_uninstalled_agent_fails_validation(client, monkeypatch):
    monkeypatch.setattr("samaratan.api.shutil.which", lambda arg: None)
    response = client.post("/api/jobs", json={"prompt": "A cinematic mystery", "provider": "claude"})
    assert response.status_code == 422


def test_unknown_provider_rejected(client):
    response = client.post("/api/jobs", json={"prompt": "A cinematic mystery", "provider": "evil"})
    assert response.status_code == 422


def test_short_prompt_rejected(client):
    response = client.post("/api/jobs", json={"prompt": "hi", "provider": "demo"})
    assert response.status_code == 422


def test_no_artifact_before_job_ready(client):
    assert client.get("/api/jobs/" + "f" * 32 + "/source").status_code == 404


def test_export_failure_is_not_falsely_successful(client):
    response = client.post("/api/jobs", json={"prompt": "A cinematic mystery", "provider": "demo", "export_windows": True})
    job = client.get("/api/jobs/" + response.json()["id"]).json()
    assert job["status"] == "failed"
    assert "Godot 4 CLI missing" in job["error"]
    assert job["windows_exe"] is None


def test_escaping_title_cannot_inject_project_config(tmp_path, spec):
    data = spec.model_dump()
    data["title"] = 'A "quoted" title\n[evil]'
    project = GodotAdapter().generate(GamePlan.model_validate(data), tmp_path)
    text = (project / "project.godot").read_text()
    assert 'config/name="A \\"quoted\\" title\\n[evil]"' in text


def test_bad_store_artifact_path_refused(tmp_path):
    store = Store(tmp_path)
    job = store.create("demo", "some prompt", False)
    store.update(job["id"], "succeeded", source_zip="../../outside.zip")
    with pytest.raises(NotFound):
        store.output(job["id"], "source_zip")
