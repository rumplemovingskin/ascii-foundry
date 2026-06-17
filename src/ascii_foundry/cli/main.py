from __future__ import annotations

import argparse
from pathlib import Path

from ascii_foundry.core.converter import write_ascii_text
from ascii_foundry.core.presets import built_in_presets, get_preset
from ascii_foundry.core.render_image import render_image_to_ascii_image
from ascii_foundry.core.settings import AsciiSettings, ImageExportSettings, RenderSettings, VideoSettings
from ascii_foundry.core.video_pipeline import VideoAsciiJob, iter_supported_images, run_video_ascii_job


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        parser.exit(1, f"ascii-foundry: error: {exc}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ascii-foundry", description="Convert images and videos into ASCII art.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    image = subparsers.add_parser("image", help="Convert one image.")
    add_common_image_options(image)
    image.add_argument("input", type=Path)
    image.add_argument("--out", required=True, type=Path)
    image.add_argument("--text", action="store_true", help="Write plain text instead of rendered image.")
    image.set_defaults(func=run_image_command)

    batch = subparsers.add_parser("batch", help="Convert images in a folder.")
    add_common_image_options(batch)
    batch.add_argument("input", type=Path)
    batch.add_argument("--out", required=True, type=Path)
    batch.add_argument("--format", default="png", choices=["txt", "png", "jpg", "jpeg", "webp", "bmp"])
    batch.add_argument("--text", action="store_true", help="Write text files; equivalent to --format txt.")
    batch.set_defaults(func=run_batch_command)

    video = subparsers.add_parser("video", help="Convert a video into an ASCII-rendered video.")
    add_common_image_options(video)
    video.add_argument("input", type=Path)
    video.add_argument("--out", required=True, type=Path)
    video.add_argument("--fps", type=float, default=30.0)
    video.add_argument("--source-fps", action="store_true", help="Use source FPS when ffprobe can read it.")
    video.add_argument("--format", choices=["mp4", "webm", "gif"], default=None)
    video.add_argument("--codec", default=None)
    video.add_argument("--crf", type=int, default=20)
    video.add_argument("--mbps", "--bitrate-mbps", dest="mbps", type=float, default=0.0)
    video.add_argument("--preset-speed", default="medium")
    video.add_argument("--pix-fmt", default="yuv420p")
    video.add_argument("--no-audio", action="store_true")
    video.add_argument("--keep-frames", action="store_true")
    video.add_argument("--frames-dir", type=Path)
    video.set_defaults(func=run_video_command)

    presets = subparsers.add_parser("presets", help="List built-in presets.")
    presets.set_defaults(func=run_presets_command)

    return parser


def add_common_image_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--preset", default="Classic Terminal")
    parser.add_argument("--ramp", default=None)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--brightness", type=float, default=None)
    parser.add_argument("--contrast", type=float, default=None)
    parser.add_argument("--gamma", type=float, default=None)
    parser.add_argument("--font-size", type=int, default=None)
    parser.add_argument("--mode", choices=["monochrome", "grayscale", "source_color", "ansi"], default=None)
    parser.add_argument("--output-width", type=int, default=None)
    parser.add_argument("--output-height", type=int, default=None)


def settings_from_args(args: argparse.Namespace) -> tuple[AsciiSettings, RenderSettings]:
    preset = get_preset(args.preset)
    ascii_settings = preset.ascii
    render_settings = preset.render
    if args.width is not None:
        ascii_settings.char_width = args.width
    if args.ramp is not None:
        ascii_settings.ramp = args.ramp
    if args.invert:
        ascii_settings.invert = True
    if args.brightness is not None:
        ascii_settings.brightness = args.brightness
    if args.contrast is not None:
        ascii_settings.contrast = args.contrast
    if args.gamma is not None:
        ascii_settings.gamma = args.gamma
    if args.font_size is not None:
        render_settings.font_size = args.font_size
    if args.mode is not None:
        render_settings.mode = args.mode
    return ascii_settings, render_settings


def run_image_command(args: argparse.Namespace) -> int:
    ascii_settings, render_settings = settings_from_args(args)
    if args.text or args.out.suffix.lower() == ".txt":
        write_ascii_text(args.input, args.out, ascii_settings)
    else:
        render_image_to_ascii_image(
            args.input,
            args.out,
            ascii_settings,
            render_settings,
            image_export_settings_from_args(args, args.out.suffix.lstrip(".") or "png"),
        )
    print(args.out)
    return 0


def run_batch_command(args: argparse.Namespace) -> int:
    ascii_settings, render_settings = settings_from_args(args)
    args.out.mkdir(parents=True, exist_ok=True)
    output_format = "txt" if args.text else args.format
    count = 0
    for input_path in iter_supported_images(args.input):
        count += 1
        output_path = args.out / f"{input_path.stem}.{output_format}"
        if output_format == "txt":
            write_ascii_text(input_path, output_path, ascii_settings)
        else:
            render_image_to_ascii_image(
                input_path,
                output_path,
                ascii_settings,
                render_settings,
                image_export_settings_from_args(args, output_format),
            )
        print(output_path)
    if count == 0:
        raise RuntimeError(f"No supported images found in {args.input}")
    return 0


def run_video_command(args: argparse.Namespace) -> int:
    ascii_settings, render_settings = settings_from_args(args)
    output_format = args.format or args.out.suffix.lower().lstrip(".") or "mp4"
    codec = args.codec or default_codec_for_format(output_format)
    output_path = args.out if args.out.suffix else args.out.with_suffix(f".{output_format}")
    bitrate = f"{args.mbps:g}M" if args.mbps > 0 else None
    video_settings = VideoSettings(
        fps_mode="source" if args.source_fps else "custom",
        fps=args.fps,
        output_format=output_format,
        codec=codec,
        crf=args.crf,
        bitrate=bitrate,
        preset=args.preset_speed,
        pix_fmt=args.pix_fmt,
        copy_audio=not args.no_audio and output_format != "gif",
        keep_intermediate_frames=args.keep_frames,
        output_width=args.output_width,
        output_height=args.output_height,
    )
    job = VideoAsciiJob(
        input_video=args.input,
        output_video=output_path,
        frame_output_dir=args.frames_dir,
        settings=ascii_settings,
        render_settings=render_settings,
        video_settings=video_settings,
    )

    def progress(payload: dict[str, object]) -> None:
        stage = payload.get("stage", "work")
        percent = payload.get("percent")
        if percent is None:
            print(stage)
        else:
            print(f"{stage}: {percent}%")

    run_video_ascii_job(job, progress_callback=progress)
    print(output_path)
    return 0


def run_presets_command(args: argparse.Namespace) -> int:
    for name in sorted(built_in_presets()):
        print(name)
    return 0


def image_export_settings_from_args(args: argparse.Namespace, output_format: str) -> ImageExportSettings:
    return ImageExportSettings(
        output_format=output_format,
        output_width=args.output_width,
        output_height=args.output_height,
    )


def default_codec_for_format(output_format: str) -> str:
    if output_format == "webm":
        return "libvpx-vp9"
    if output_format == "gif":
        return "gif"
    return "libx264"
