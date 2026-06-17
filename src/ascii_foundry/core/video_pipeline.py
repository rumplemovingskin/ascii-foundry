from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from ascii_foundry.core.ffmpeg_tools import (
    ffprobe_metadata,
    find_ffmpeg,
    require_ffmpeg,
    run_command,
    subprocess_startup_options,
)
from ascii_foundry.core.render_image import render_image_to_ascii_image
from ascii_foundry.core.settings import AsciiSettings, ImageExportSettings, RenderSettings, VideoSettings
from ascii_foundry.utils.paths import cache_dir

ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(slots=True)
class VideoAsciiJob:
    input_video: str | Path
    output_video: str | Path
    frame_output_dir: str | Path | None = None
    settings: AsciiSettings | None = None
    render_settings: RenderSettings | None = None
    video_settings: VideoSettings | None = None
    temp_root: str | Path | None = None
    ffmpeg_path: str | None = None
    ffprobe_path: str | None = None


def run_video_ascii_job(job: VideoAsciiJob, progress_callback: ProgressCallback | None = None) -> Path:
    ascii_settings = job.settings or AsciiSettings(char_width=120)
    render_settings = job.render_settings or RenderSettings()
    video_settings = job.video_settings or VideoSettings()
    ascii_settings.validate()
    render_settings.validate()
    video_settings.validate()

    availability = require_ffmpeg(find_ffmpeg(job.ffmpeg_path, job.ffprobe_path))
    output_video = Path(job.output_video)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    fps = resolve_output_fps(job.input_video, video_settings, job.ffprobe_path)

    with _working_directory(job, fps) as workdir:
        extracted_dir = workdir / "source_frames"
        ascii_dir = Path(job.frame_output_dir) if job.frame_output_dir else workdir / "ascii_frames" / _settings_cache_key(
            ascii_settings,
            render_settings,
            video_settings,
        )
        extracted_dir.mkdir(parents=True, exist_ok=True)
        ascii_dir.mkdir(parents=True, exist_ok=True)

        if _stage_complete(extracted_dir, "extracted"):
            _emit(progress_callback, stage="extract-reuse", current=1, total=1, percent=10)
        else:
            _clear_png_frames(extracted_dir)
            _emit(progress_callback, stage="extract", current=0, total=None, percent=0)
            extract_frames(
                job.input_video,
                extracted_dir,
                fps,
                availability.ffmpeg_path or "ffmpeg",
                progress_callback,
                ffprobe_path=job.ffprobe_path,
            )
            _mark_stage_complete(extracted_dir, "extracted")

        frames = sorted(extracted_dir.glob("*.png"))
        if not frames:
            raise RuntimeError("FFmpeg did not extract any frames from the input video.")

        if _stage_complete(ascii_dir, "converted") and len(list(ascii_dir.glob("frame_*.png"))) >= len(frames):
            preview = ascii_dir / "frame_00000001.png"
            _emit(
                progress_callback,
                stage="convert-reuse",
                current=len(frames),
                total=len(frames),
                percent=90,
                source_preview_path=str(frames[0]),
                preview_path=str(preview),
            )
        else:
            _clear_png_frames(ascii_dir)
            _convert_frames(frames, ascii_dir, ascii_settings, render_settings, video_settings, progress_callback)
            _mark_stage_complete(ascii_dir, "converted")
        copy_audio = video_settings.copy_audio and video_settings.output_format != "gif"
        silent_video = workdir / f"silent_video{output_video.suffix}" if copy_audio else output_video
        _emit(progress_callback, stage="rebuild", current=0, total=len(frames), percent=90)
        rebuild_video(
            ascii_dir,
            silent_video,
            fps,
            video_settings,
            availability.ffmpeg_path or "ffmpeg",
            progress_callback,
        )

        if copy_audio:
            muxed = mux_audio_if_possible(
                input_video=job.input_video,
                silent_video=silent_video,
                output_video=output_video,
                ffmpeg_path=availability.ffmpeg_path or "ffmpeg",
                progress_callback=progress_callback,
            )
            if not muxed:
                shutil.copy2(silent_video, output_video)

        if job.frame_output_dir and not video_settings.keep_intermediate_frames:
            _emit(progress_callback, stage="frames-kept", current=len(frames), total=len(frames), percent=100)

    _emit(progress_callback, stage="complete", current=1, total=1, percent=100)
    return output_video


def resolve_output_fps(
    input_video: str | Path,
    video_settings: VideoSettings,
    ffprobe_path: str | None = None,
) -> float:
    if video_settings.fps_mode == "custom":
        return video_settings.fps
    try:
        metadata = ffprobe_metadata(input_video, ffprobe_path)
    except Exception:
        return video_settings.fps
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") != "video":
            continue
        fps = _parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        if fps:
            return fps
    return video_settings.fps


def extract_frames(
    input_video: str | Path,
    output_dir: str | Path,
    fps: float,
    ffmpeg_path: str = "ffmpeg",
    progress_callback: ProgressCallback | None = None,
    ffprobe_path: str | None = None,
) -> None:
    output = Path(output_dir) / "frame_%08d.png"
    duration = video_duration_seconds(input_video, ffprobe_path)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"fps={fps:g}",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output),
    ]
    run_ffmpeg_with_progress(command, duration, "extract", 0, 10, progress_callback)


def extract_sample_frame(
    input_video: str | Path,
    output_path: str | Path,
    random_frame: bool = True,
    frame_number: int | None = None,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    availability = require_ffmpeg(find_ffmpeg(ffmpeg_path, ffprobe_path))
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    selected_frame, _ = choose_sample_frame_number(input_video, random_frame, frame_number, ffprobe_path)
    frame_index = selected_frame - 1
    command = [
        availability.ffmpeg_path or "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"select=eq(n\\,{frame_index})",
        "-vsync",
        "0",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(output),
    ]
    run_command(command, progress_callback)
    if not output.exists():
        raise RuntimeError("FFmpeg did not create a sample frame.")
    return output


def choose_sample_frame_number(
    input_video: str | Path,
    random_frame: bool = True,
    frame_number: int | None = None,
    ffprobe_path: str | None = None,
) -> tuple[int, int]:
    total_frames = video_frame_count(input_video, ffprobe_path)
    if total_frames < 1:
        raise RuntimeError("Could not determine the number of frames in this video.")
    if random_frame:
        return random.randint(1, total_frames), total_frames
    selected_frame = frame_number or 1
    if selected_frame < 1:
        selected_frame = 1
    if selected_frame > total_frames:
        raise ValueError(f"Frame {selected_frame} is outside this video. Total frames: {total_frames}.")
    return selected_frame, total_frames


def choose_sample_timestamp(
    input_video: str | Path,
    random_frame: bool = True,
    seed: int | None = None,
    ffprobe_path: str | None = None,
) -> float:
    duration = video_duration_seconds(input_video, ffprobe_path)
    if duration <= 0:
        return 0.0
    if not random_frame:
        if seed is None:
            return max(0.0, min(duration * 0.5, duration - _sample_seek_margin(duration)))
        rng = random.Random(seed)
        return rng.uniform(0.0, max(0.0, duration - _sample_seek_margin(duration)))
    rng = random.Random()
    return rng.uniform(0.0, max(0.0, duration - _sample_seek_margin(duration)))


def video_duration_seconds(input_video: str | Path, ffprobe_path: str | None = None) -> float:
    try:
        metadata = ffprobe_metadata(input_video, ffprobe_path)
    except Exception:
        return 0.0
    duration = metadata.get("format", {}).get("duration")
    try:
        return float(duration)
    except (TypeError, ValueError):
        return 0.0


def video_frame_count(input_video: str | Path, ffprobe_path: str | None = None) -> int:
    try:
        metadata = ffprobe_metadata(input_video, ffprobe_path)
    except Exception:
        return 0
    format_duration = _float_or_zero(metadata.get("format", {}).get("duration"))
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") != "video":
            continue
        frame_count = _int_or_zero(stream.get("nb_frames"))
        if frame_count:
            return frame_count
        duration = _float_or_zero(stream.get("duration")) or format_duration
        fps = _parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        if duration and fps:
            return max(1, round(duration * fps))
    return 0


def _sample_seek_margin(duration: float) -> float:
    if duration <= 2.0:
        return max(0.05, duration * 0.55)
    return min(1.0, duration * 0.15)


def rebuild_video(
    ascii_frame_dir: str | Path,
    output_video: str | Path,
    fps: float,
    video_settings: VideoSettings,
    ffmpeg_path: str = "ffmpeg",
    progress_callback: ProgressCallback | None = None,
) -> None:
    frame_pattern = Path(ascii_frame_dir) / video_settings.frame_pattern
    if video_settings.output_format == "gif" or video_settings.codec == "gif":
        command = [
            ffmpeg_path,
            "-y",
            "-framerate",
            f"{fps:g}",
            "-i",
            str(frame_pattern),
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            str(output_video),
        ]
        run_command(command, progress_callback)
        return

    command = [
        ffmpeg_path,
        "-y",
        "-framerate",
        f"{fps:g}",
        "-i",
        str(frame_pattern),
        "-vf",
        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
        "-c:v",
        video_settings.codec,
    ]
    if _codec_supports_crf(video_settings.codec):
        command.extend(["-crf", str(video_settings.crf)])
    if video_settings.bitrate:
        command.extend(["-b:v", video_settings.bitrate])
    elif video_settings.codec.startswith("libvpx"):
        command.extend(["-b:v", "0"])
    if _codec_supports_preset(video_settings.codec):
        command.extend(["-preset", video_settings.preset])
    if video_settings.pix_fmt:
        command.extend(["-pix_fmt", video_settings.pix_fmt])
    command.append(str(output_video))
    run_command(command, progress_callback)


def mux_audio_if_possible(
    input_video: str | Path,
    silent_video: str | Path,
    output_video: str | Path,
    ffmpeg_path: str = "ffmpeg",
    progress_callback: ProgressCallback | None = None,
) -> bool:
    output = Path(output_video)
    temp_output = output.with_name(f".{output.stem}.with_audio{output.suffix}")
    temp_output.unlink(missing_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(silent_video),
        "-i",
        str(input_video),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        str(temp_output),
    ]
    try:
        run_command(command, progress_callback)
    except Exception:
        temp_output.unlink(missing_ok=True)
        return False
    output.unlink(missing_ok=True)
    temp_output.replace(output)
    return True


def iter_supported_images(path: str | Path) -> Iterable[Path]:
    supported = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
    root = Path(path)
    for item in sorted(root.iterdir()):
        if item.is_file() and item.suffix.lower() in supported:
            yield item


def _convert_frames(
    frames: list[Path],
    ascii_dir: Path,
    ascii_settings: AsciiSettings,
    render_settings: RenderSettings,
    video_settings: VideoSettings,
    progress_callback: ProgressCallback | None,
) -> None:
    total = len(frames)
    image_settings = ImageExportSettings(
        output_format="png",
        output_width=video_settings.output_width,
        output_height=video_settings.output_height,
    )
    for index, frame in enumerate(frames, start=1):
        output = ascii_dir / f"frame_{index:08d}.png"
        render_image_to_ascii_image(frame, output, ascii_settings, render_settings, image_settings)
        percent = 10 + math.floor((index / total) * 80)
        _emit(
            progress_callback,
            stage="convert",
            current=index,
            total=total,
            percent=percent,
            item=str(frame),
            source_preview_path=str(frame),
            preview_path=str(output),
        )


def _parse_fps(value: str | None) -> float | None:
    if not value:
        return None
    if "/" not in value:
        try:
            fps = float(value)
        except ValueError:
            return None
        return fps if fps > 0 else None
    numerator, denominator = value.split("/", 1)
    try:
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None
    return fps if fps > 0 else None


def _int_or_zero(value: object) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return result if result > 0 else 0


def _float_or_zero(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if result > 0 else 0.0


def _emit(callback: ProgressCallback | None, **payload: object) -> None:
    if callback:
        callback(payload)


def run_ffmpeg_with_progress(
    command: list[str],
    duration: float,
    stage: str,
    start_percent: int,
    end_percent: int,
    progress_callback: ProgressCallback | None,
) -> None:
    _emit(progress_callback, stage=stage, current=0, total=duration or None, percent=start_percent)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        **subprocess_startup_options(),
    )
    assert process.stdout is not None
    last_percent = start_percent
    for line in process.stdout:
        key, _, value = line.strip().partition("=")
        if key not in {"out_time_ms", "out_time_us"} or not duration:
            continue
        try:
            current_seconds = int(value) / 1_000_000
        except ValueError:
            continue
        progress = min(1.0, max(0.0, current_seconds / duration))
        percent = start_percent + math.floor((end_percent - start_percent) * progress)
        if percent != last_percent:
            last_percent = percent
            _emit(progress_callback, stage=stage, current=current_seconds, total=duration, percent=percent)
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)
    _emit(progress_callback, stage=stage, current=duration or 1, total=duration or 1, percent=end_percent)


def _codec_supports_crf(codec: str) -> bool:
    return codec in {"libx264", "libx265", "libvpx-vp9", "libaom-av1", "libsvtav1"}


def _codec_supports_preset(codec: str) -> bool:
    return codec in {"libx264", "libx265", "libsvtav1"}


class _working_directory:
    def __init__(self, job: VideoAsciiJob, fps: float) -> None:
        self.job = job
        self.fps = fps
        self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.path: Path | None = None

    def __enter__(self) -> Path:
        keep = bool(self.job.video_settings and self.job.video_settings.keep_intermediate_frames)
        if keep:
            root = Path(self.job.temp_root) if self.job.temp_root else cache_dir() / "intermediate_frames"
            self.path = root / _video_cache_key(self.job.input_video, self.fps)
            self.path.mkdir(parents=True, exist_ok=True)
        elif self.job.temp_root:
            root = Path(self.job.temp_root)
            root.mkdir(parents=True, exist_ok=True)
            self.path = Path(tempfile.mkdtemp(prefix="ascii_foundry_", dir=root))
        else:
            self.path = Path(tempfile.mkdtemp(prefix="ascii_foundry_"))
        return self.path

    def __exit__(self, exc_type, exc, traceback) -> None:
        keep = bool(self.job.video_settings and self.job.video_settings.keep_intermediate_frames)
        if self.path and not keep:
            shutil.rmtree(self.path, ignore_errors=True)


def _video_cache_key(input_video: str | Path, fps: float) -> str:
    path = Path(input_video)
    try:
        stat = path.stat()
        payload = {"path": str(path.resolve()), "mtime": stat.st_mtime, "size": stat.st_size, "fps": fps}
    except OSError:
        payload = {"path": str(path), "fps": fps}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def _settings_cache_key(
    ascii_settings: AsciiSettings,
    render_settings: RenderSettings,
    video_settings: VideoSettings,
) -> str:
    payload = {
        "ascii": ascii_settings.to_dict(),
        "render": render_settings.to_dict(),
        "video_resolution": [video_settings.output_width, video_settings.output_height],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def _stage_marker(directory: Path, stage: str) -> Path:
    return directory / f".{stage}.complete"


def _stage_complete(directory: Path, stage: str) -> bool:
    return _stage_marker(directory, stage).exists()


def _mark_stage_complete(directory: Path, stage: str) -> None:
    _stage_marker(directory, stage).write_text("ok", encoding="utf-8")


def _clear_png_frames(directory: Path) -> None:
    for path in directory.glob("frame_*.png"):
        path.unlink(missing_ok=True)
    for marker in directory.glob(".*.complete"):
        marker.unlink(missing_ok=True)
