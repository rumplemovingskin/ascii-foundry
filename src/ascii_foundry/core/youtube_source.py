from __future__ import annotations

from pathlib import Path
from typing import Callable

from ascii_foundry.utils.paths import cache_dir

ProgressCallback = Callable[[dict[str, object]], None]


def download_youtube_video(
    url: str,
    output_dir: str | Path | None = None,
    progress_callback: ProgressCallback | None = None,
) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError(
            "YouTube URL support requires yt-dlp. Install the video dependencies, then try again."
        ) from exc

    cleaned_url = url.strip()
    if not cleaned_url:
        raise ValueError("Enter a YouTube URL first.")
    target_dir = Path(output_dir) if output_dir else cache_dir() / "youtube_sources"
    target_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    def hook(payload: dict[str, object]) -> None:
        status = str(payload.get("status", "download"))
        filename = payload.get("filename")
        if status == "finished" and filename:
            downloaded.append(Path(str(filename)))
        total = _numeric(payload.get("total_bytes")) or _numeric(payload.get("total_bytes_estimate"))
        current = _numeric(payload.get("downloaded_bytes"))
        percent = None
        if total and current is not None:
            percent = max(0, min(100, round((current / total) * 100)))
        _emit(
            progress_callback,
            stage="youtube",
            status=status,
            current=current,
            total=total,
            percent=percent,
            item=str(filename) if filename else cleaned_url,
        )

    options = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "outtmpl": str(target_dir / "%(id)s.%(ext)s"),
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
    }
    _emit(progress_callback, stage="youtube", status="starting", percent=None, item=cleaned_url)
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(cleaned_url, download=True)

    output = _find_downloaded_video(target_dir, info, downloaded)
    _emit(progress_callback, stage="youtube", status="complete", percent=100, item=str(output))
    return output


def _find_downloaded_video(target_dir: Path, info: dict[str, object], downloaded: list[Path]) -> Path:
    candidates = [path for path in downloaded if path.exists()]
    for entry in info.get("requested_downloads", []) or []:
        if not isinstance(entry, dict):
            continue
        filepath = entry.get("filepath") or entry.get("filename")
        if filepath:
            candidates.append(Path(str(filepath)))
    video_id = str(info.get("id", "")).strip()
    if video_id:
        candidates.extend(target_dir.glob(f"{video_id}.*"))
    supported = {".mp4", ".webm", ".mkv", ".mov", ".avi"}
    candidates = [path for path in candidates if path.exists() and path.suffix.lower() in supported]
    if not candidates:
        raise RuntimeError("yt-dlp finished but no downloaded video file could be found.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _numeric(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _emit(callback: ProgressCallback | None, **payload: object) -> None:
    if callback:
        callback(payload)
