from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "evals" / "fixtures"
DEFAULT_MEMORY_PATH = REPO_ROOT / "memory" / "failures.db"


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    model: str
    run_dir: Path
    log_level: str
    memory_path: Path

    @classmethod
    def from_env(cls) -> Settings:
        run_dir = Path(os.getenv("REFLECTCODER_RUN_DIR", REPO_ROOT / "runs")).resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        memory_path = Path(
            os.getenv("REFLECTCODER_MEMORY_PATH", DEFAULT_MEMORY_PATH)
        ).resolve()
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv("REFLECTCODER_MODEL", "llama-3.3-70b-versatile"),
            run_dir=run_dir,
            log_level=os.getenv("REFLECTCODER_LOG_LEVEL", "INFO"),
            memory_path=memory_path,
        )
