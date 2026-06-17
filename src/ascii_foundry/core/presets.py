from __future__ import annotations

import json
from pathlib import Path

from ascii_foundry.core.settings import (
    AsciiSettings,
    ExportPreset,
    ImageExportSettings,
    Preset,
    RenderSettings,
    TextExportSettings,
    VideoSettings,
)


def built_in_ramps() -> dict[str, str]:
    return {
        "Classic Dense": "@%#*+=-:. ",
        "Classic Reversed": " .:-=+*#%@",
        "High Detail ASCII": "MWN$@%#*+=-:. ",
        "Soft Detail": "@#*+=:. ",
        "Blocks": "█▓▒░ ",
        "Blocks Reversed": " ░▒▓█",
        "Minimal": "#. ",
        "Binary": "10 ",
        "Numeric": "9876543210 ",
        "Alphabet": "WMBRXVYIti+=;:,. ",
        "Ink Wash": "Ñ@#W$9876543210?!abc;:+=-,._ ",
        "Thin Lines": "##XXxxx+++===---:::...   ",
        "Terminal Dots": "@8&oe*+=-:. ",
    }


def built_in_presets() -> dict[str, Preset]:
    ramps = built_in_ramps()
    presets = [
        Preset(
            name="Classic Terminal",
            ascii=AsciiSettings(char_width=120, ramp=ramps["Classic Dense"]),
            render=RenderSettings(mode="monochrome", background="#000000", foreground="#F0F0F0", font_size=12),
        ),
        Preset(
            name="Block Shade",
            ascii=AsciiSettings(char_width=100, ramp=ramps["Blocks"]),
            render=RenderSettings(mode="monochrome", background="#000000", foreground="#F4F4F4", font_size=12),
        ),
        Preset(
            name="High Detail",
            ascii=AsciiSettings(char_width=180, ramp=ramps["High Detail ASCII"], contrast=1.15),
            render=RenderSettings(mode="monochrome", background="#050505", foreground="#FFFFFF", font_size=10),
        ),
        Preset(
            name="Soft Poster",
            ascii=AsciiSettings(char_width=80, ramp=ramps["Soft Detail"], contrast=0.9),
            render=RenderSettings(mode="monochrome", background="#111111", foreground="#EFE7D0", font_size=16),
        ),
        Preset(
            name="Source Color",
            ascii=AsciiSettings(char_width=120, ramp=ramps["Classic Dense"]),
            render=RenderSettings(mode="source_color", background="#000000", foreground="#FFFFFF", font_size=12),
        ),
        Preset(
            name="Amber CRT",
            ascii=AsciiSettings(char_width=132, ramp=ramps["Terminal Dots"], contrast=1.08, gamma=0.95),
            render=RenderSettings(mode="monochrome", background="#120900", foreground="#FFB000", font_size=12),
        ),
        Preset(
            name="Green Phosphor",
            ascii=AsciiSettings(char_width=132, ramp=ramps["Classic Reversed"], contrast=1.1),
            render=RenderSettings(mode="monochrome", background="#001600", foreground="#58FF72", font_size=12),
        ),
        Preset(
            name="Blueprint",
            ascii=AsciiSettings(char_width=120, ramp=ramps["Thin Lines"], contrast=1.2, brightness=-0.05),
            render=RenderSettings(mode="monochrome", background="#071A33", foreground="#B9E2FF", font_size=12),
        ),
        Preset(
            name="Newsprint",
            ascii=AsciiSettings(char_width=110, ramp=ramps["Ink Wash"], contrast=1.25, gamma=0.9),
            render=RenderSettings(mode="monochrome", background="#F4F0E6", foreground="#171717", font_size=12),
        ),
        Preset(
            name="Binary Glow",
            ascii=AsciiSettings(char_width=120, ramp=ramps["Binary"], contrast=1.3),
            render=RenderSettings(mode="monochrome", background="#000000", foreground="#7CFFCB", font_size=12),
        ),
        Preset(
            name="ANSI Poster",
            ascii=AsciiSettings(char_width=100, ramp=ramps["Blocks Reversed"], contrast=1.1),
            render=RenderSettings(mode="ansi", background="#000000", foreground="#FFFFFF", font_size=14),
        ),
        Preset(
            name="Video Fast Preview",
            ascii=AsciiSettings(char_width=90, ramp=ramps["Classic Dense"]),
            render=RenderSettings(mode="monochrome", background="#000000", foreground="#F0F0F0", font_size=10),
            video=VideoSettings(fps_mode="custom", fps=12, crf=24, preset="veryfast", bitrate="4M"),
        ),
        Preset(
            name="Video Final Render",
            ascii=AsciiSettings(char_width=160, ramp=ramps["High Detail ASCII"], contrast=1.05),
            render=RenderSettings(mode="source_color", background="#000000", foreground="#FFFFFF", font_size=10),
            video=VideoSettings(fps_mode="source", fps=30, crf=20, preset="medium"),
        ),
        Preset(
            name="Video WebM Compact",
            ascii=AsciiSettings(char_width=120, ramp=ramps["Classic Dense"], contrast=1.05),
            render=RenderSettings(mode="source_color", background="#000000", foreground="#FFFFFF", font_size=10),
            video=VideoSettings(
                fps_mode="custom",
                fps=24,
                output_format="webm",
                codec="libvpx-vp9",
                crf=32,
                bitrate="3M",
                pix_fmt="yuv420p",
                copy_audio=False,
            ),
        ),
    ]
    return {preset.name: preset for preset in presets}


def built_in_export_presets() -> dict[str, ExportPreset]:
    presets = [
        ExportPreset(
            name="Balanced Export Defaults",
            text=built_in_text_export_presets()["Plain TXT"],
            image=built_in_image_export_presets()["PNG Auto Size"],
            video=built_in_video_export_presets()["MP4 1080p Balanced"],
        ),
        ExportPreset(
            name="Compact Web Defaults",
            text=built_in_text_export_presets()["Plain TXT CRLF"],
            image=built_in_image_export_presets()["WebP 1080p"],
            video=built_in_video_export_presets()["WebM 720p Compact"],
        ),
        ExportPreset(
            name="High Quality Defaults",
            text=built_in_text_export_presets()["HTML Preview"],
            image=built_in_image_export_presets()["PNG 4K Crisp"],
            video=built_in_video_export_presets()["MP4 4K Crisp"],
        ),
    ]
    return {preset.name: preset for preset in presets}


def built_in_text_export_presets() -> dict[str, TextExportSettings]:
    return {
        "Plain TXT": TextExportSettings(output_format="txt", line_ending="lf"),
        "Plain TXT CRLF": TextExportSettings(output_format="txt", line_ending="crlf"),
        "TXT with Header": TextExportSettings(output_format="txt", line_ending="lf", include_settings_header=True),
        "ANSI Color TXT": TextExportSettings(output_format="txt", line_ending="lf", ansi_color=True),
        "HTML Preview": TextExportSettings(output_format="html", line_ending="lf"),
    }


def built_in_image_export_presets() -> dict[str, ImageExportSettings]:
    return {
        "PNG Auto Size": ImageExportSettings(output_format="png", quality=95, transparent=False),
        "PNG 1080p": ImageExportSettings(output_format="png", quality=95, output_width=1920, output_height=1080),
        "PNG 4K Crisp": ImageExportSettings(output_format="png", quality=100, output_width=3840, output_height=2160),
        "Transparent PNG": ImageExportSettings(output_format="png", quality=95, transparent=True),
        "WebP 1080p": ImageExportSettings(output_format="webp", quality=86, output_width=1920, output_height=1080),
        "JPEG 4K": ImageExportSettings(output_format="jpg", quality=92, output_width=3840, output_height=2160),
    }


def built_in_video_export_presets() -> dict[str, VideoSettings]:
    return {
        "MP4 720p Preview": VideoSettings(
            fps_mode="custom",
            fps=12,
            output_format="mp4",
            codec="libx264",
            crf=24,
            preset="veryfast",
            output_width=1280,
            output_height=720,
        ),
        "MP4 1080p Balanced": VideoSettings(
            output_format="mp4",
            codec="libx264",
            crf=20,
            bitrate=None,
            preset="medium",
            output_width=1920,
            output_height=1080,
        ),
        "MP4 4K Crisp": VideoSettings(
            output_format="mp4",
            codec="libx264",
            crf=18,
            bitrate="24M",
            preset="slow",
            output_width=3840,
            output_height=2160,
        ),
        "H.265 4K Compact": VideoSettings(
            output_format="mp4",
            codec="libx265",
            crf=24,
            preset="slow",
            output_width=3840,
            output_height=2160,
        ),
        "WebM 720p Compact": VideoSettings(
            fps_mode="custom",
            fps=12,
            output_format="webm",
            codec="libvpx-vp9",
            crf=34,
            bitrate="2M",
            copy_audio=False,
            output_width=1280,
            output_height=720,
        ),
        "GIF 720p Loop": VideoSettings(
            fps_mode="custom",
            fps=12,
            output_format="gif",
            codec="gif",
            crf=0,
            pix_fmt="rgb24",
            copy_audio=False,
            output_width=1280,
            output_height=720,
        ),
    }


def get_preset(name: str) -> Preset:
    presets = built_in_presets()
    try:
        return presets[name]
    except KeyError as exc:
        available = ", ".join(sorted(presets))
        raise KeyError(f"Unknown preset '{name}'. Available presets: {available}") from exc


def load_preset(path: str | Path) -> Preset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Preset.from_dict(data)


def save_preset(preset: Preset, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(preset.to_dict(), indent=2), encoding="utf-8")
    return output
