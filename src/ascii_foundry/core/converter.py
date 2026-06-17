from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ascii_foundry.core.preprocessing import apply_luminance_preprocessing, preprocess_image
from ascii_foundry.core.settings import AsciiSettings


@dataclass(slots=True)
class AsciiArt:
    text: str
    characters: list[str]
    colors: list[list[tuple[int, int, int]]] | None
    luminance: list[list[float]] | None
    source_size: tuple[int, int]
    character_size: tuple[int, int]


def calculate_character_height(image_size: tuple[int, int], settings: AsciiSettings) -> int:
    width, height = image_size
    if settings.char_height is not None:
        return settings.char_height
    if not settings.preserve_aspect:
        return max(1, round(settings.char_width * 0.5))
    ratio = height / width
    return max(1, round(settings.char_width * ratio * settings.aspect_correction))


def resize_for_ascii(image: Image.Image, settings: AsciiSettings) -> Image.Image:
    settings.validate()
    target = (settings.char_width, calculate_character_height(image.size, settings))

    if settings.crop_mode == "stretch":
        return image.resize(target, Image.Resampling.LANCZOS)

    if settings.crop_mode == "fill":
        return ImageOps.fit(image, target, method=Image.Resampling.LANCZOS)

    return image.resize(target, Image.Resampling.LANCZOS)


def map_luminance_to_characters(luminance: np.ndarray, ramp: str) -> list[str]:
    ramp_chars = list(ramp)
    if len(ramp_chars) == 1:
        return [ramp_chars[0] * luminance.shape[1] for _ in range(luminance.shape[0])]

    indices = np.rint(luminance * (len(ramp_chars) - 1)).astype(np.int32)
    rows: list[str] = []
    for row in indices:
        rows.append("".join(ramp_chars[index] for index in row))
    return rows


def convert_image_to_ascii(image_or_path: str | Path | Image.Image, settings: AsciiSettings) -> AsciiArt:
    settings.validate()
    if isinstance(image_or_path, Image.Image):
        source = image_or_path.convert("RGB")
        source_size = image_or_path.size
    else:
        with Image.open(image_or_path) as opened:
            source = opened.convert("RGB")
            source_size = opened.size

    resized = preprocess_image(resize_for_ascii(source, settings), settings)
    grayscale = resized.convert("L")
    values = np.asarray(grayscale, dtype=np.float32) / 255.0
    values = apply_luminance_preprocessing(values, settings)
    lines = map_luminance_to_characters(values, settings.ramp)
    color_rows = _extract_colors(resized)
    return AsciiArt(
        text="\n".join(lines),
        characters=lines,
        colors=color_rows,
        luminance=_extract_luminance(values),
        source_size=source_size,
        character_size=resized.size,
    )


def convert_image_to_ascii_text(image_or_path: str | Path | Image.Image, settings: AsciiSettings) -> str:
    return convert_image_to_ascii(image_or_path, settings).text


def write_ascii_text(image_path: str | Path, output_path: str | Path, settings: AsciiSettings) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(convert_image_to_ascii_text(image_path, settings), encoding="utf-8")
    return output


def _extract_colors(image: Image.Image) -> list[list[tuple[int, int, int]]]:
    arr = np.asarray(image.convert("RGB"), dtype=np.uint8)
    rows: list[list[tuple[int, int, int]]] = []
    for row in arr:
        rows.append([tuple(int(channel) for channel in pixel) for pixel in row])
    return rows


def _extract_luminance(values: np.ndarray) -> list[list[float]]:
    return [[float(value) for value in row] for row in values]
