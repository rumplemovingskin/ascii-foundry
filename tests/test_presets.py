from __future__ import annotations

from ascii_foundry.core.presets import (
    built_in_image_export_presets,
    built_in_presets,
    built_in_ramps,
    built_in_text_export_presets,
    built_in_video_export_presets,
    get_preset,
)
from ascii_foundry.core.settings import Preset


def test_built_in_presets_round_trip() -> None:
    presets = built_in_presets()
    assert "Classic Terminal" in presets
    for preset in presets.values():
        restored = Preset.from_dict(preset.to_dict())
        assert restored.name == preset.name


def test_built_in_ramps_include_named_options() -> None:
    ramps = built_in_ramps()
    assert "Classic Dense" in ramps
    assert "Binary" in ramps
    assert all(value for value in ramps.values())


def test_export_presets_are_group_specific() -> None:
    text_presets = built_in_text_export_presets()
    image_presets = built_in_image_export_presets()
    video_presets = built_in_video_export_presets()

    assert "Plain TXT" in text_presets
    assert "PNG Auto Size" in image_presets
    assert "MP4 1080p Balanced" in video_presets
    assert not set(text_presets) & set(video_presets)
    assert not set(text_presets) & set(image_presets)


def test_get_preset_reports_unknown_name() -> None:
    try:
        get_preset("Missing")
    except KeyError as exc:
        assert "Available presets" in str(exc)
    else:
        raise AssertionError("Expected KeyError")
