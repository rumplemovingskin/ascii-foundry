from __future__ import annotations

import json
from pathlib import Path

from ascii_foundry.core.settings import ExportPreset, Preset
from ascii_foundry.utils.paths import config_dir


def default_ascii_preset_path() -> Path:
    return config_dir() / "user_ascii_presets.json"


def default_export_preset_path() -> Path:
    return config_dir() / "user_export_presets.json"


def load_user_ascii_presets(path: str | Path | None = None) -> dict[str, Preset]:
    preset_path = Path(path) if path else default_ascii_preset_path()
    if not preset_path.exists():
        return {}
    data = json.loads(preset_path.read_text(encoding="utf-8"))
    return {item["name"]: Preset.from_dict(item) for item in data.get("presets", [])}


def save_user_ascii_preset(preset: Preset, path: str | Path | None = None) -> Path:
    preset_path = Path(path) if path else default_ascii_preset_path()
    presets = load_user_ascii_presets(preset_path)
    presets[preset.name] = preset
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "presets": [item.to_dict() for item in sorted(presets.values(), key=lambda p: p.name)]}
    preset_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return preset_path


def load_user_export_presets(path: str | Path | None = None) -> dict[str, ExportPreset]:
    preset_path = Path(path) if path else default_export_preset_path()
    if not preset_path.exists():
        return {}
    data = json.loads(preset_path.read_text(encoding="utf-8"))
    return {item["name"]: ExportPreset.from_dict(item) for item in data.get("presets", [])}


def save_user_export_preset(preset: ExportPreset, path: str | Path | None = None) -> Path:
    preset_path = Path(path) if path else default_export_preset_path()
    presets = load_user_export_presets(preset_path)
    presets[preset.name] = preset
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "presets": [item.to_dict() for item in sorted(presets.values(), key=lambda p: p.name)]}
    preset_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return preset_path
