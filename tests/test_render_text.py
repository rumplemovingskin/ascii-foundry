from __future__ import annotations

from pathlib import Path

from PIL import Image

from ascii_foundry.core.render_text import render_image_to_text_file
from ascii_foundry.core.settings import AsciiSettings, RenderSettings, TextExportSettings


def test_render_html_text_export(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    output_path = tmp_path / "output.html"
    Image.new("RGB", (4, 4), (255, 255, 255)).save(image_path)

    render_image_to_text_file(
        image_path,
        output_path,
        AsciiSettings(char_width=4, char_height=2),
        TextExportSettings(output_format="html"),
        RenderSettings(font_family="Consolas"),
    )

    content = output_path.read_text(encoding="utf-8")
    assert "<pre" in content
    assert "font-family" in content


def test_render_text_export_with_header_and_crlf(tmp_path: Path) -> None:
    image_path = tmp_path / "input.png"
    output_path = tmp_path / "output.txt"
    Image.new("RGB", (4, 4), (0, 0, 0)).save(image_path)

    render_image_to_text_file(
        image_path,
        output_path,
        AsciiSettings(char_width=4, char_height=2),
        TextExportSettings(include_settings_header=True, line_ending="crlf"),
    )

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        content = handle.read()
    assert content.startswith("# ASCII Foundry export\r\n")
