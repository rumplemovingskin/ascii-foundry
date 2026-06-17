from __future__ import annotations

import html
from pathlib import Path

from ascii_foundry.core.converter import convert_image_to_ascii, convert_image_to_ascii_text
from ascii_foundry.core.settings import AsciiSettings, RenderSettings, TextExportSettings


def render_image_to_text_file(
    input_path: str | Path,
    output_path: str | Path,
    settings: AsciiSettings,
    text_settings: TextExportSettings | None = None,
    render_settings: RenderSettings | None = None,
) -> Path:
    text_settings = text_settings or TextExportSettings()
    text_settings.validate()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if text_settings.output_format == "html":
        content = render_image_to_html(input_path, settings, render_settings or RenderSettings())
    elif text_settings.ansi_color:
        content = render_image_to_ansi(input_path, settings)
    else:
        content = convert_image_to_ascii_text(input_path, settings)
    if text_settings.include_settings_header:
        content = _settings_header(settings, text_settings) + content
    if text_settings.line_ending == "crlf":
        content = content.replace("\n", "\r\n")
    output.write_text(content, encoding="utf-8", newline="")
    return output


def render_image_to_html(
    input_path: str | Path,
    settings: AsciiSettings,
    render_settings: RenderSettings,
) -> str:
    art = convert_image_to_ascii(input_path, settings)
    foreground = html.escape(render_settings.foreground)
    background = html.escape(render_settings.background)
    font_family = html.escape(render_settings.font_family or "monospace")
    rows = []
    for row_index, line in enumerate(art.characters):
        cells = []
        for column_index, char in enumerate(line):
            escaped = html.escape(char)
            if render_settings.mode == "source_color" and art.colors:
                red, green, blue = art.colors[row_index][column_index]
                cells.append(f'<span style="color: rgb({red}, {green}, {blue})">{escaped}</span>')
            else:
                cells.append(escaped)
        rows.append("".join(cells))
    body = "\n".join(rows)
    return (
        "<!doctype html>\n"
        "<meta charset=\"utf-8\">\n"
        f"<pre style=\"margin:0; color:{foreground}; background:{background}; "
        f"font-family:'{font_family}', monospace; font-size:{render_settings.font_size}px; "
        f"line-height:{render_settings.line_spacing};\">{body}</pre>\n"
    )


def render_image_to_ansi(input_path: str | Path, settings: AsciiSettings) -> str:
    art = convert_image_to_ascii(input_path, settings)
    if not art.colors:
        return art.text
    rows = []
    for row_index, line in enumerate(art.characters):
        cells = []
        for column_index, char in enumerate(line):
            red, green, blue = art.colors[row_index][column_index]
            cells.append(f"\033[38;2;{red};{green};{blue}m{char}\033[0m")
        rows.append("".join(cells))
    return "\n".join(rows)


def _settings_header(settings: AsciiSettings, text_settings: TextExportSettings) -> str:
    return (
        f"# ASCII Foundry export\n"
        f"# width={settings.char_width} ramp={settings.ramp!r} invert={settings.invert} "
        f"format={text_settings.output_format}\n\n"
    )
