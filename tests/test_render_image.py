from __future__ import annotations

from pathlib import Path

from PIL import Image

from ascii_foundry.core.converter import convert_image_to_ascii
from ascii_foundry.core.render_image import (
    ascii_settings_for_render_target,
    render_ascii_to_image,
    render_ascii_to_pil_image,
    render_image_to_ascii_image,
)
from ascii_foundry.core.settings import AsciiSettings, ImageExportSettings, RenderSettings


def test_render_ascii_to_png(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.new("RGB", (4, 4), (255, 255, 255)).save(image_path)

    art = convert_image_to_ascii(image_path, AsciiSettings(char_width=4, char_height=2))
    render_ascii_to_image(art, output_path, RenderSettings(font_size=12))

    assert output_path.exists()
    with Image.open(output_path) as rendered:
        assert rendered.width > 0
        assert rendered.height > 0


def test_render_ascii_to_pil_image_returns_image(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    Image.new("RGB", (4, 4), (255, 255, 255)).save(image_path)

    art = convert_image_to_ascii(image_path, AsciiSettings(char_width=4, char_height=2))
    rendered = render_ascii_to_pil_image(art, RenderSettings(font_size=12))

    assert rendered.width > 0
    assert rendered.height > 0


def test_render_image_to_ascii_image_respects_fixed_resolution(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    output_path = tmp_path / "output.png"
    Image.new("RGB", (32, 16), (255, 255, 255)).save(image_path)

    render_image_to_ascii_image(
        image_path,
        output_path,
        AsciiSettings(char_width=20),
        RenderSettings(font_size=12, line_spacing=1.8),
        ImageExportSettings(output_width=320, output_height=180),
    )

    with Image.open(output_path) as rendered:
        assert rendered.size == (320, 180)


def test_target_resolution_does_not_change_ascii_grid() -> None:
    ascii_settings = AsciiSettings(char_width=20)
    target = ImageExportSettings(output_width=320, output_height=180)
    compact = ascii_settings_for_render_target(ascii_settings, RenderSettings(font_size=12, line_spacing=0.8), target)
    loose = ascii_settings_for_render_target(ascii_settings, RenderSettings(font_size=12, line_spacing=1.8), target)

    assert compact.char_height is None
    assert loose.char_height is None
    assert compact.char_width == loose.char_width == ascii_settings.char_width
