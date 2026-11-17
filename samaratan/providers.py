"""Agent adapters use authenticated local CLIs, never consumer website scraping."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Protocol
from pydantic import ValidationError
from .models import GamePlan


SYSTEM_PROMPT = """You are a cinematic game preproduction director. Output ONE valid JSON object, no markdown.
It MUST satisfy this contract:
{
 "schema_version":1,"title":"Short title","genre":"genre","setting":"place/time",
 "characters":[{"id":"detective","name":"Alex","role":"playable protagonist"}],
 "start_scene":"arrival",
 "scenes":[{"id":"arrival","title":"Arrival","narration":"Action and dialogue.",
 "choices":[{"label":"Inspect the scene","next_scene":"investigation"}]},
 {"id":"investigation","title":"Investigation","narration":"A conclusion.","choices":[]}]
}
Rules: 1-12 characters, 1-24 scenes, all scene ids unique, every referenced scene exists,
all scenes reachable from start_scene, max four choices per scene. Write specific scenes,
interesting choices, cinematic staging and grounded character motivations. No executable code.
USER GAME IDEA:
"""


class ProviderError(RuntimeError):
    pass


class PlanProvider(Protocol):
    def generate(self, prompt: str) -> GamePlan: ...


def parse_plan(message: str) -> GamePlan:
    """Extract the first valid JSON object and validate the strict shared contract."""
    if len(message) > 200_000:
        raise ProviderError("Agent response exceeds size limit")
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", message):
        try:
            value, _ = decoder.raw_decode(message[match.start():])
            if isinstance(value, dict):
                return GamePlan.model_validate(value)
        except (json.JSONDecodeError, ValidationError):
            continue
    raise ProviderError("Agent did not return a valid GamePlan JSON object")


class DemoProvider:
    """Deterministic no-network fixture: validates the whole pipeline without AI credits."""

    def generate(self, prompt: str) -> GamePlan:
        return GamePlan.model_validate({
            "title": "Midnight Evidence",
            "genre": "Cinematic detective thriller",
            "setting": f"Rainy city after dark. Brief: {prompt[:160]}",
            "characters": [
                {"id": "detective", "name": "Alex Morgan", "role": "Controllable detective"},
                {"id": "witness", "name": "Sam Rivera", "role": "Unreliable witness"},
            ],
            "start_scene": "arrival",
            "scenes": [
                {"id": "arrival", "title": "Arrival", "narration": "Rain drums against the windshield. Alex steps into the deserted street. A witness waits under a streetlight.", "choices": [
                    {"label": "Question the witness", "next_scene": "interview"},
                    {"label": "Inspect the abandoned car", "next_scene": "evidence"},
                ]},
                {"id": "interview", "title": "A shaky alibi", "narration": "Sam glances toward a dark alley. 'I heard the engine, but never saw the driver.'", "choices": [
                    {"label": "Follow the witness's gaze", "next_scene": "revelation"},
                ]},
                {"id": "evidence", "title": "The missing key", "narration": "Inside the car is a warm cup of coffee and a note with tomorrow's date.", "choices": [
                    {"label": "Examine the note", "next_scene": "revelation"},
                ]},
                {"id": "revelation", "title": "A new lead", "narration": "A distant door slams. Whoever left the scene may still be nearby. To be continued.", "choices": []},
            ],
        })


class CLIProvider:
    """Isolated execution of an explicitly selected local agent; never uses a shell."""

    def __init__(self, name: str, timeout: int = 180) -> None:
        if name not in ("codex", "claude"):
            raise ValueError("Unsupported agent")
        self.name = name
        self.timeout = timeout

    def generate(self, prompt: str) -> GamePlan:
        full_prompt = SYSTEM_PROMPT + prompt
        with tempfile.TemporaryDirectory(prefix="samaratan-agent-") as tmp:
            workdir = Path(tmp)
            response_file = workdir / "response.txt"
            if self.name == "codex":
                argv = ["codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--output-last-message", str(response_file), "-"]
            else:
                argv = ["claude", "-p", "--output-format", "text", "--permission-mode", "plan", "--no-session-persistence"]
            try:
                result = subprocess.run(argv, input=full_prompt, text=True, capture_output=True,
                                        timeout=self.timeout, cwd=workdir, check=False)
            except FileNotFoundError as exc:
                raise ProviderError(f"{self.name} CLI not found. Install and log in locally first.") from exc
            except subprocess.TimeoutExpired as exc:
                raise ProviderError(f"{self.name} exceeded the {self.timeout}s timeout") from exc
            if result.returncode != 0:
                # Do not leak CLI stderr (which may include account or filesystem details).
                raise ProviderError(f"{self.name} failed with exit code {result.returncode}")
            message = response_file.read_text(encoding="utf-8") if response_file.exists() else result.stdout
            return parse_plan(message)


def get_provider(name: str, timeout: int) -> PlanProvider:
    if name == "demo":
        return DemoProvider()
    return CLIProvider(name, timeout)
