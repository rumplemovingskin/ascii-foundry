from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from ascii_foundry.core.render_image import render_image_to_ascii_image
from ascii_foundry.core.render_text import render_image_to_text_file
from ascii_foundry.core.settings import AsciiSettings, ImageExportSettings, RenderSettings, TextExportSettings
from ascii_foundry.core.video_pipeline import VideoAsciiJob, extract_sample_frame, run_video_ascii_job
from ascii_foundry.core.youtube_source import download_youtube_video


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(object)


class ExportWorker(QRunnable):
    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        ascii_settings: AsciiSettings,
        render_settings: RenderSettings,
        text_settings: TextExportSettings,
        image_settings: ImageExportSettings,
        text_output: bool,
    ) -> None:
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.ascii_settings = ascii_settings
        self.render_settings = render_settings
        self.text_settings = text_settings
        self.image_settings = image_settings
        self.text_output = text_output
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.text_output:
                output = render_image_to_text_file(
                    self.input_path,
                    self.output_path,
                    self.ascii_settings,
                    self.text_settings,
                    self.render_settings,
                )
            else:
                output = render_image_to_ascii_image(
                    self.input_path,
                    self.output_path,
                    self.ascii_settings,
                    self.render_settings,
                    self.image_settings,
                )
        except Exception as exc:
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(output)


class SampleFrameWorker(QRunnable):
    def __init__(
        self,
        input_video: Path,
        ascii_settings: AsciiSettings,
        render_settings: RenderSettings,
        image_settings: ImageExportSettings,
        random_frame: bool,
        frame_number: int | None,
    ) -> None:
        super().__init__()
        self.input_video = input_video
        self.ascii_settings = ascii_settings
        self.render_settings = render_settings
        self.image_settings = image_settings
        self.random_frame = random_frame
        self.frame_number = frame_number
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            workdir = Path(tempfile.mkdtemp(prefix="ascii_foundry_sample_"))
            source_frame = extract_sample_frame(
                self.input_video,
                workdir / "source_sample.png",
                random_frame=self.random_frame,
                frame_number=self.frame_number,
                progress_callback=self.signals.progress.emit,
            )
            preview_frame = workdir / "ascii_sample.png"
            render_image_to_ascii_image(
                source_frame,
                preview_frame,
                self.ascii_settings,
                self.render_settings,
                self.image_settings,
            )
        except Exception as exc:
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit({"source_frame": source_frame, "preview_frame": preview_frame})


class VideoExportWorker(QRunnable):
    def __init__(self, job: VideoAsciiJob) -> None:
        super().__init__()
        self.job = job
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            output = run_video_ascii_job(self.job, progress_callback=self.signals.progress.emit)
        except Exception as exc:
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(output)


class YouTubeDownloadWorker(QRunnable):
    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            output = download_youtube_video(self.url, progress_callback=self.signals.progress.emit)
        except Exception as exc:
            self.signals.error.emit(str(exc))
            return
        self.signals.finished.emit(output)
