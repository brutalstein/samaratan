"""Versioned game contract shared by agents, editors and engine adapters."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Character(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=64)
    role: str = Field(min_length=1, max_length=240)


class Choice(StrictModel):
    label: str = Field(min_length=1, max_length=120)
    next_scene: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")


class Scene(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    title: str = Field(min_length=1, max_length=120)
    narration: str = Field(min_length=1, max_length=2000)
    choices: list[Choice] = Field(default_factory=list, max_length=4)


class GamePlan(StrictModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=100)
    genre: str = Field(min_length=1, max_length=120)
    setting: str = Field(min_length=1, max_length=400)
    characters: list[Character] = Field(min_length=1, max_length=12)
    start_scene: str
    scenes: list[Scene] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def validate_story_graph(self) -> "GamePlan":
        ids = [s.id for s in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate scene IDs")
        if len(set(c.id for c in self.characters)) != len(self.characters):
            raise ValueError("Duplicate character IDs")
        if self.start_scene not in ids:
            raise ValueError("start_scene must reference a scene")
        for scene in self.scenes:
            for choice in scene.choices:
                if choice.next_scene not in ids:
                    raise ValueError(f"Unknown scene in choice: {choice.next_scene}")
        visited = set()
        pending = [self.start_scene]
        lookup = {s.id: s for s in self.scenes}
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(c.next_scene for c in lookup[current].choices)
        if visited != set(ids):
            raise ValueError("Every scene must be reachable from start_scene")
        return self


class JobRequest(StrictModel):
    prompt: str = Field(min_length=8, max_length=6000)
    provider: Literal["demo", "codex", "claude"] = "demo"
    export_windows: bool = False
