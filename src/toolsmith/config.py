"""Configuration loaded from environment variables with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application-wide settings, populated from env vars on import."""

    log_level: str = "INFO"
    sandbox_timeout: int = 30
    audit_log_path: str = "./logs/audit.jsonl"
    max_tools: int = 100

    def __post_init__(self) -> None:
        self.log_level = os.getenv("TOOLSMITH_LOG_LEVEL", self.log_level)
        self.sandbox_timeout = int(
            os.getenv("TOOLSMITH_SANDBOX_TIMEOUT", str(self.sandbox_timeout))
        )
        self.audit_log_path = os.getenv(
            "TOOLSMITH_AUDIT_LOG_PATH", self.audit_log_path
        )
        self.max_tools = int(os.getenv("TOOLSMITH_MAX_TOOLS", str(self.max_tools)))


# Singleton used throughout the package
settings = Settings()
