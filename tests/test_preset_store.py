from __future__ import annotations

from ascii_foundry.core.preset_store import (
    load_user_ascii_presets,
    load_user_export_presets,
    save_user_ascii_preset,
    save_user_export_preset,
)
from ascii_foundry.core.settings import ExportPreset, Preset


def test_user_ascii_preset_round_trip(tmp_path) -> None:
    path = tmp_path / "ascii.json"
    preset = Preset(name="My ASCII")

    save_user_ascii_preset(preset, path)
    loaded = load_user_ascii_presets(path)

    assert loaded["My ASCII"].name == "My ASCII"


def test_user_export_preset_round_trip(tmp_path) -> None:
    path = tmp_path / "export.json"
    preset = ExportPreset(name="My Export")

    save_user_export_preset(preset, path)
    loaded = load_user_export_presets(path)

    assert loaded["My Export"].name == "My Export"
