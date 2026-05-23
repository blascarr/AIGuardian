from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class AdGuardConfig(BaseModel):
    url: str = "http://127.0.0.1:3000"
    username: str = "admin"
    password: str = ""


class PiHoleConfig(BaseModel):
    url: str = "http://127.0.0.1"
    session_id: str = ""


class DNSConfig(BaseModel):
    provider: Literal["adguard", "pihole"] = "adguard"
    poll_interval_seconds: int = 5
    batch_size: int = 100
    adguard: AdGuardConfig = Field(default_factory=AdGuardConfig)
    pihole: PiHoleConfig = Field(default_factory=PiHoleConfig)


class PipelineConfig(BaseModel):
    light_classifier_threshold: float = 0.75
    heavy_classifier_threshold: float = 0.60
    gray_zone_min: float = 0.40
    gray_zone_max: float = 0.75


class ModelsConfig(BaseModel):
    fasttext_path: str = "models/risk_classifier.ftz"
    mobilebert_onnx_path: str = "models/mobilebert_quantized.onnx"
    llm_enabled: bool = False
    llm_model_path: str = "models/qwen2.5-0.5b-instruct-q4.gguf"


class DatabaseConfig(BaseModel):
    path: str = "data/pihole_blocker.db"


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080


class HeuristicsConfig(BaseModel):
    blocklists_dir: str = "config/blocklists"
    hard_block_categories: list[str] = Field(default_factory=lambda: ["malware", "phishing"])


class AppConfig(BaseModel):
    dns: DNSConfig = Field(default_factory=DNSConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    heuristics: HeuristicsConfig = Field(default_factory=HeuristicsConfig)


class Settings(BaseSettings):
    config_path: Path = Path("config/config.yaml")

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            example = self.config_path.parent / "config.example.yaml"
            if example.exists():
                raw = yaml.safe_load(example.read_text())
            else:
                return AppConfig()
        else:
            raw = yaml.safe_load(self.config_path.read_text())
        return AppConfig.model_validate(raw or {})

    def resolve(self, base: Path, relative: str) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else base / path
