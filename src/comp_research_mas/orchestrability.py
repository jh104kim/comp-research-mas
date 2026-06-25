from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import CATEGORIES, PRIMARY_COMPETITORS, SECONDARY_COMPETITORS, TYPE_LABELS

CONFIG_FILES = {
    "competitors": "config/competitors.yaml",
    "compressor_types": "config/compressor_types.yaml",
    "agent_roles": "config/agent_roles.yaml",
    "source_policy": "config/source_policy.yaml",
    "rubric": "config/rubric.yaml",
}


def load_yaml_config(name: str) -> dict[str, Any]:
    path = Path(CONFIG_FILES[name])
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_competitor_config() -> dict[str, Any]:
    data = load_yaml_config("competitors")
    return data or {"primary": PRIMARY_COMPETITORS, "secondary": SECONDARY_COMPETITORS}


def load_compressor_type_config() -> dict[str, Any]:
    data = load_yaml_config("compressor_types")
    return data or {"types": TYPE_LABELS}


def validate_runtime_config() -> dict[str, Any]:
    competitors = load_competitor_config()
    compressor_types = load_compressor_type_config()
    errors: list[str] = []
    for ctype in compressor_types.get("types", {}).keys():
        if ctype not in {"Re", "Ro", "Sc"}:
            errors.append(f"unknown compressor type: {ctype}")
    for key in ["primary", "secondary"]:
        if key in competitors and not isinstance(competitors[key], dict):
            errors.append(f"competitors.{key} must be mapping")
    rubric = load_yaml_config("rubric")
    if rubric and sum(int(v.get("points", 0)) for v in rubric.get("items", {}).values()) not in {0, 10}:
        errors.append("rubric total points must be 10")
    return {"valid": not errors, "errors": errors, "competitors": competitors, "compressor_types": compressor_types, "categories": list(CATEGORIES)}
