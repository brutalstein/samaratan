"""Runtime configuration; no global credentials and no external service required."""
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    godot_binary: str = "godot"
    cli_timeout: int = 180

    @classmethod
    def from_env(cls) -> "Settings":
        timeout = int(os.getenv("SAMARATAN_CLI_TIMEOUT", "180"))
        if not 1 <= timeout <= 3600:
            raise ValueError("SAMARATAN_CLI_TIMEOUT must be between 1 and 3600 seconds")
        return cls(
            root=Path(os.getenv("SAMARATAN_ROOT", ".samaratan")).resolve(),
            godot_binary=os.getenv("SAMARATAN_GODOT_BINARY", "godot"),
            cli_timeout=timeout,
        )
