from dataclasses import dataclass, field
import json
from pathlib import Path

from fastapi import FastAPI

from sealed_secrets_mdhook.app import app as a


@dataclass
class Config:
    annotations: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)


def make_app(config_path: Path) -> FastAPI:
    with open(config_path) as f:
        config = Config(**json.load(f))
    a.state.config = config
    return a
