"""Job orchestration separates planning, compilation, packaging and future billing."""
import json
from .config import Settings
from .godot import EngineError, GodotAdapter
from .providers import ProviderError, get_provider
from .store import Store


class JobService:
    def __init__(self, settings: Settings, store: Store):
        self.settings = settings
        self.store = store
        self.engine = GodotAdapter()

    def run(self, job_id: str) -> None:
        job = self.store.get(job_id)
        self.store.update(job_id, "running")
        try:
            plan = get_provider(job["provider"], self.settings.cli_timeout).generate(job["prompt"])
            folder = self.store.directory(job_id)
            (folder / "game-plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
            project = self.engine.generate(plan, folder)
            zip_path = self.engine.bundle(project, folder / "game-source.zip")
            outputs = {"title": plan.title, "source_zip": zip_path.name}
            if job["export_windows"]:
                exe = self.engine.export_windows(project, folder / "samaratan-game.exe", self.settings.godot_binary)
                outputs["windows_exe"] = exe.name
            self.store.update(job_id, "succeeded", **outputs)
        except (EngineError, ProviderError, ValueError, OSError, RuntimeError) as exc:
            # Never surface raw CLI output or system secrets through the web API.
            self.store.update(job_id, "failed", error=str(exc)[:300])
        except Exception:
            self.store.update(job_id, "failed", error="Unexpected build failure; consult server logs")
            raise
