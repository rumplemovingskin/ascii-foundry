from __future__ import annotations

from pathlib import Path

from PIL import Image

from ascii_foundry.core.converter import convert_image_to_ascii_text
from ascii_foundry.core.settings import AsciiSettings


def test_convert_image_to_ascii_text_has_expected_dimensions(tmp_path: Path) -> None:
    image_path = tmp_path / "gradient.png"
    image = Image.new("RGB", (10, 10))
    for x in range(10):
        for y in range(10):
            value = x * 25
            image.putpixel((x, y), (value, value, value))
    image.save(image_path)

    text = convert_image_to_ascii_text(
        image_path,
        AsciiSettings(char_width=10, char_height=5, ramp=" .#"),
    )

    lines = text.splitlines()
    assert len(lines) == 5
    assert all(len(line) == 10 for line in lines)
    assert lines[0][0] == " "
    assert lines[0][-1] == "#"


def test_invert_flips_character_mapping(tmp_path: Path) -> None:
    image_path = tmp_path / "pixel.png"
    Image.new("RGB", (1, 1), (255, 255, 255)).save(image_path)

    normal = convert_image_to_ascii_text(image_path, AsciiSettings(char_width=1, char_height=1, ramp=" .#"))
    inverted = convert_image_to_ascii_text(
        image_path,
        AsciiSettings(char_width=1, char_height=1, ramp=" .#", invert=True),
    )

    assert normal == "#"
    assert inverted == " "

