from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from ascii_foundry.core.converter import AsciiArt, convert_image_to_ascii
from ascii_foundry.core.settings import AsciiSettings, ImageExportSettings, RenderSettings

ANSI_PALETTE = (
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
)


def render_image_to_ascii_image(
    input_path: str | Path,
    output_path: str | Path,
    ascii_settings: AsciiSettings,
    render_settings: RenderSettings,
    image_settings: ImageExportSettings | None = None,
) -> Path:
    art = convert_image_to_ascii(input_path, ascii_settings)
    return render_ascii_to_image(art, output_path, render_settings, image_settings)


def render_ascii_to_image(
    art_or_text: AsciiArt | str,
    output_path: str | Path,
    render_settings: RenderSettings,
    image_settings: ImageExportSettings | None = None,
) -> Path:
    image_settings = image_settings or ImageExportSettings()
    image_settings.validate()
    image = render_ascii_to_pil_image(art_or_text, render_settings)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_image = image
    if image_settings.output_width and image_settings.output_height:
        save_image = fit_image_to_resolution(
            save_image,
            (image_settings.output_width, image_settings.output_height),
            render_settings,
        )
    suffix = output.suffix.lower() or f".{image_settings.output_format.lower()}"
    if suffix in {".jpg", ".jpeg", ".bmp"} and save_image.mode == "RGBA":
        flattened = Image.new("RGB", save_image.size, ImageColor.getrgb(render_settings.background))
        flattened.paste(save_image, mask=save_image.getchannel("A"))
        save_image = flattened
    save_kwargs = {}
    if suffix in {".jpg", ".jpeg", ".webp"}:
        save_kwargs["quality"] = image_settings.quality
    save_image.save(output, **save_kwargs)
    return output


def ascii_settings_for_render_target(
    ascii_settings: AsciiSettings,
    render_settings: RenderSettings,
    image_settings: ImageExportSettings | None,
) -> AsciiSettings:
    return ascii_settings


def fit_image_to_resolution(
    image: Image.Image,
    target_size: tuple[int, int],
    render_settings: RenderSettings,
) -> Image.Image:
    target_width, target_height = target_size
    if image.size == target_size:
        return image
    scale = min(target_width / image.width, target_height / image.height)
    resized_size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    resample = Image.Resampling.NEAREST if scale >= 1.0 else Image.Resampling.LANCZOS
    resized = image.resize(resized_size, resample)
    background = _background(render_settings)
    canvas = Image.new("RGBA" if render_settings.transparent else "RGB", target_size, background)
    x = (target_width - resized.width) // 2
    y = (target_height - resized.height) // 2
    if resized.mode == "RGBA" and canvas.mode == "RGB":
        canvas.paste(resized, (x, y), resized.getchannel("A"))
    else:
        canvas.paste(resized, (x, y))
    return canvas


def render_ascii_to_pil_image(
    art_or_text: AsciiArt | str,
    render_settings: RenderSettings,
) -> Image.Image:
    render_settings.validate()
    art = _coerce_art(art_or_text)
    font = load_font(render_settings)
    char_width, line_height = measure_font(font)
    char_width = max(1, round(char_width * render_settings.character_spacing))
    line_height = max(1, round(line_height * render_settings.line_spacing))
    width = max(1, max((len(line) for line in art.characters), default=1) * char_width)
    height = max(1, len(art.characters) * line_height)

    background = _background(render_settings)
    mode = "RGBA" if render_settings.transparent else "RGB"
    image = Image.new(mode, (width, height), background)
    draw = ImageDraw.Draw(image)
    for row_index, line in enumerate(art.characters):
        y = row_index * line_height
        for column_index, char in enumerate(line):
            x = column_index * char_width
            fill = _fill_for_character(render_settings, art, row_index, column_index)
            draw.text((x, y), char, font=font, fill=fill)
    return image


def load_font(settings: RenderSettings) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    if settings.font_path:
        try:
            return ImageFont.truetype(settings.font_path, settings.font_size)
        except OSError as exc:
            raise ValueError(f"Could not load font: {settings.font_path}") from exc

    candidates = []
    if settings.font_family:
        candidates.extend(_font_candidates(settings.font_family, settings.font_weight))
    candidates.extend(_font_candidates("DejaVu Sans Mono", settings.font_weight))
    candidates.extend(_font_candidates("Cascadia Mono", settings.font_weight))
    candidates.extend(_font_candidates("Consolas", settings.font_weight))
    candidates.extend(_font_candidates("Courier New", settings.font_weight))
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, settings.font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _font_candidates(font_family: str, font_weight: str) -> list[str]:
    family = font_family.strip()
    if not family:
        return []
    bold = font_weight == "bold"
    known = {
        "Cascadia Mono": ("CascadiaMono.ttf", "CascadiaMono-Bold.ttf"),
        "Consolas": ("consola.ttf", "consolab.ttf"),
        "Courier New": ("cour.ttf", "courbd.ttf"),
        "DejaVu Sans Mono": ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
        "Lucida Console": ("lucon.ttf", "lucon.ttf"),
    }
    regular_file, bold_file = known.get(family, (family, family))
    candidates = [bold_file if bold else regular_file, family]
    if bold:
        candidates.insert(1, f"{family} Bold")
    return candidates


def measure_font(font: ImageFont.ImageFont | ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = font.getbbox("M")
    char_width = bbox[2] - bbox[0]
    line_height = bbox[3] - bbox[1]
    if hasattr(font, "getmetrics"):
        ascent, descent = font.getmetrics()
        line_height = max(line_height, ascent + descent)
    return max(1, char_width), max(1, line_height)


def _coerce_art(art_or_text: AsciiArt | str) -> AsciiArt:
    if isinstance(art_or_text, AsciiArt):
        return art_or_text
    lines = art_or_text.splitlines() or [""]
    return AsciiArt(
        text=art_or_text,
        characters=lines,
        colors=None,
        luminance=None,
        source_size=(0, 0),
        character_size=(max((len(line) for line in lines), default=0), len(lines)),
    )


def _background(settings: RenderSettings) -> tuple[int, int, int] | tuple[int, int, int, int]:
    rgb = ImageColor.getrgb(settings.background)
    if settings.transparent:
        return rgb + (0,)
    return rgb


def _fill_for_character(
    settings: RenderSettings,
    art: AsciiArt,
    row_index: int,
    column_index: int,
) -> tuple[int, int, int] | tuple[int, int, int, int]:
    if settings.mode == "source_color" and art.colors:
        color = art.colors[row_index][column_index]
    elif settings.mode == "grayscale":
        if art.luminance:
            value = round(art.luminance[row_index][column_index] * 255)
            color = (value, value, value)
        else:
            color = ImageColor.getrgb(settings.foreground)
    elif settings.mode == "ansi" and art.colors:
        color = nearest_ansi_color(art.colors[row_index][column_index])
    else:
        color = ImageColor.getrgb(settings.foreground)
    if settings.transparent:
        return color + (255,)
    return color


def nearest_ansi_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    red, green, blue = color
    return min(
        ANSI_PALETTE,
        key=lambda item: (item[0] - red) ** 2 + (item[1] - green) ** 2 + (item[2] - blue) ** 2,
    )
