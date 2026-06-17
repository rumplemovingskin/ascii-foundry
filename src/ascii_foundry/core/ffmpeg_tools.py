from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FfmpegAvailability:
    ffmpeg_path: str | None
    ffprobe_path: str | None

    @property
    def available(self) -> bool:
        return bool(self.ffmpeg_path and self.ffprobe_path)


def find_ffmpeg(ffmpeg_path: str | None = None, ffprobe_path: str | None = None) -> FfmpegAvailability:
    return FfmpegAvailability(
        ffmpeg_path=ffmpeg_path or _find_bundled_binary("ffmpeg") or shutil.which("ffmpeg"),
        ffprobe_path=ffprobe_path or _find_bundled_binary("ffprobe") or shutil.which("ffprobe"),
    )


def require_ffmpeg(availability: FfmpegAvailability | None = None) -> FfmpegAvailability:
    found = availability or find_ffmpeg()
    if not found.available:
        raise RuntimeError("FFmpeg and FFprobe are required for video conversion but were not found on PATH.")
    return found


def ffprobe_metadata(input_video: str | Path, ffprobe_path: str | None = None) -> dict[str, Any]:
    availability = require_ffmpeg(find_ffmpeg(ffprobe_path=ffprobe_path))
    command = [
        availability.ffprobe_path or "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_video),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def run_command(command: list[str], progress_callback: Any | None = None) -> None:
    if progress_callback:
        progress_callback({"stage": "command", "command": command})
    subprocess.run(command, check=True)


def _find_bundled_binary(name: str) -> str | None:
    executable_name = f"{name}.exe" if sys.platform.startswith("win") else name
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir))
        candidates.extend(
            [
                exe_dir / executable_name,
                exe_dir / "bin" / executable_name,
                bundle_dir / executable_name,
                bundle_dir / "bin" / executable_name,
            ]
        )
    package_root = Path(__file__).resolve().parents[3]
    candidates.extend(
        [
            package_root / "vendor" / "ffmpeg" / "bin" / executable_name,
            package_root / "bin" / executable_name,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None
