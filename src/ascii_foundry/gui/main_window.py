from __future__ import annotations

from io import BytesIO
from pathlib import Path
import time

from PySide6.QtCore import QSize, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QToolButton,
    QWidget,
)

from ascii_foundry import __app_name__
from ascii_foundry.core.converter import convert_image_to_ascii
from ascii_foundry.core.preset_store import (
    load_user_ascii_presets,
    load_user_export_presets,
    save_user_ascii_preset,
    save_user_export_preset,
)
from ascii_foundry.core.presets import (
    built_in_export_presets,
    built_in_image_export_presets,
    built_in_presets,
    built_in_ramps,
    built_in_text_export_presets,
    built_in_video_export_presets,
)
from ascii_foundry.core.render_image import fit_image_to_resolution, render_ascii_to_pil_image
from ascii_foundry.core.settings import (
    AsciiSettings,
    ExportPreset,
    ImageExportSettings,
    Preset,
    RenderSettings,
    TextExportSettings,
    VideoSettings,
)
from ascii_foundry.core.video_pipeline import VideoAsciiJob
from ascii_foundry.gui.icon import create_app_icon
from ascii_foundry.gui.workers import ExportWorker, SampleFrameWorker, VideoExportWorker, YouTubeDownloadWorker


VIDEO_PROFILES = [
    {"label": "MP4 / H.264", "format": "mp4", "suffix": ".mp4", "codec": "libx264", "crf": 20, "pix_fmt": "yuv420p"},
    {"label": "MP4 / H.265", "format": "mp4", "suffix": ".mp4", "codec": "libx265", "crf": 24, "pix_fmt": "yuv420p"},
    {"label": "WebM / VP9", "format": "webm", "suffix": ".webm", "codec": "libvpx-vp9", "crf": 32, "pix_fmt": "yuv420p"},
    {"label": "GIF", "format": "gif", "suffix": ".gif", "codec": "gif", "crf": 0, "pix_fmt": "rgb24"},
]

FONT_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New", "Lucida Console"]


class CollapsibleGroup(QFrame):
    def __init__(self, title: str, content: QWidget, expanded: bool = True) -> None:
        super().__init__()
        self.title = title
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("exportCard")
        self.setStyleSheet(
            "#exportCard { border: 1px solid #474747; border-radius: 6px; background: #242424; margin-top: 6px; }"
            "#exportCard QLabel { font-weight: 500; }"
        )
        self.toggle_button = QToolButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setAutoRaise(True)
        self.toggle_button.clicked.connect(self._sync_state)
        self.content = content

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600;")
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(self.toggle_button)
        layout.addLayout(header)
        layout.addWidget(self.content)
        self._sync_state()

    def _sync_state(self) -> None:
        expanded = self.toggle_button.isChecked()
        self.content.setVisible(expanded)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)


class ScaledPreviewLabel(QLabel):
    def __init__(
        self,
        text: str,
        size_hint: QSize,
        minimum_hint: QSize,
        vertical_policy: QSizePolicy.Policy = QSizePolicy.Policy.Expanding,
    ) -> None:
        super().__init__(text)
        self._source_pixmap: QPixmap | None = None
        self._size_hint = size_hint
        self._minimum_hint = minimum_hint
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, vertical_policy)

    def set_source_pixmap(self, pixmap: QPixmap) -> None:
        self._source_pixmap = pixmap
        self.setText("")
        self.update()

    def clear_preview(self, text: str) -> None:
        self._source_pixmap = None
        self.setText(text)
        self.update()

    def sizeHint(self) -> QSize:
        return self._size_hint

    def minimumSizeHint(self) -> QSize:
        return self._minimum_hint

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self._source_pixmap or self._source_pixmap.isNull():
            return
        target = self.contentsRect()
        scaled = self._source_pixmap.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = target.x() + (target.width() - scaled.width()) // 2
        y = target.y() + (target.height() - scaled.height()) // 2
        painter = QPainter(self)
        painter.drawPixmap(x, y, scaled)


class SliderSpinBox(QWidget):
    valueChanged = Signal(int)

    def __init__(self, minimum: int, maximum: int, value: int, tooltip: str) -> None:
        super().__init__()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setFixedWidth(76)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, stretch=1)
        layout.addWidget(self.spin)
        self.slider.valueChanged.connect(self._slider_changed)
        self.spin.valueChanged.connect(self._spin_changed)
        self.setToolTip(tooltip)
        self.setValue(value)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, value: int) -> None:
        self.slider.setValue(value)

    def setToolTip(self, tooltip: str) -> None:
        super().setToolTip(tooltip)
        self.slider.setToolTip(tooltip)
        self.spin.setToolTip(tooltip)

    def _slider_changed(self, value: int) -> None:
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)
        self.valueChanged.emit(value)

    def _spin_changed(self, value: int) -> None:
        self.slider.setValue(value)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(create_app_icon())
        self.resize(1280, 820)

        self.thread_pool = QThreadPool.globalInstance()
        self.input_path: Path | None = None
        self.video_path: Path | None = None
        self.media_preview_pixmap: QPixmap | None = None
        self.output_preview_pixmap: QPixmap | None = None

        self.ramps = built_in_ramps()
        self.user_ascii_presets = self._load_user_ascii_presets()
        self.presets = {**built_in_presets(), **self.user_ascii_presets}
        self.user_export_presets = self._load_user_export_presets()
        self.export_presets = {**built_in_export_presets(), **self.user_export_presets}
        self._rebuild_export_preset_maps()

        self.ascii_settings = AsciiSettings()
        self.render_settings = RenderSettings()
        self._updating_ramp_controls = False
        self._updating_video_controls = False
        self._last_logged_video_frame = 0
        self._video_frame_timing: list[tuple[int, float]] = []
        self.video_started_at: float | None = None

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.refresh_preview)

        self._build_ui()
        self.statusBar().showMessage("Ready")
        self._refresh_preset_combo("Classic Terminal")
        self.apply_preset("Classic Terminal")
        self._refresh_export_preset_combos(
            text_selected="Plain TXT",
            image_selected="PNG Auto Size",
            video_selected="MP4 1080p Balanced",
        )
        self.apply_text_export_preset("Plain TXT")
        self.apply_image_export_preset("PNG Auto Size")
        self.apply_video_export_preset("MP4 1080p Balanced")
        self.update_source_actions()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._scroll_panel(self._build_left_panel(), 330))
        splitter.addWidget(self._build_preview_panel())
        splitter.addWidget(self._scroll_panel(self._build_export_panel(), 360))
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        self.setCentralWidget(splitter)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        open_row = QHBoxLayout()
        self.open_button = self._button("Open Image", "Choose a still image to convert.")
        self.open_button.clicked.connect(self.open_image)
        self.open_video_button = self._button("Open Video", "Choose a video for sample previews or export.")
        self.open_video_button.clicked.connect(self.open_video)
        open_row.addWidget(self.open_button)
        open_row.addWidget(self.open_video_button)
        layout.addLayout(open_row)

        youtube_row = QHBoxLayout()
        self.youtube_url_edit = QLineEdit()
        self.youtube_url_edit.setPlaceholderText("YouTube URL")
        self.youtube_url_edit.setToolTip("Paste a YouTube URL for a video you have rights or permission to process.")
        self.youtube_url_edit.returnPressed.connect(self.load_youtube_video)
        self.youtube_load_button = self._button("Use URL", "Download this YouTube video as the current video source.")
        self.youtube_load_button.clicked.connect(self.load_youtube_video)
        youtube_row.addWidget(self.youtube_url_edit, stretch=1)
        youtube_row.addWidget(self.youtube_load_button)
        layout.addLayout(youtube_row)

        self.media_preview = ScaledPreviewLabel(
            "Open an image or video.",
            QSize(300, 170),
            QSize(220, 140),
            QSizePolicy.Policy.Fixed,
        )
        self.media_preview.setMinimumHeight(150)
        self.media_preview.setMaximumHeight(190)
        self.media_preview.setToolTip("Thumbnail of the selected image or the sampled video frame.")
        layout.addWidget(self.media_preview)

        self.input_label = QLabel("No file selected")
        self.input_label.setWordWrap(True)
        self.input_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.input_label.setToolTip("Current input path.")
        layout.addWidget(self.input_label)

        sample_row = QHBoxLayout()
        self.sample_frame_button = self._button("Preview Sample Frame", "Extract one video frame and preview it as ASCII.")
        self.sample_frame_button.clicked.connect(self.preview_sample_frame)
        sample_row.addWidget(self.sample_frame_button)
        layout.addLayout(sample_row)

        sample_form = QFormLayout()
        self.random_sample_check = QCheckBox("Random sample")
        self.random_sample_check.setChecked(True)
        self.random_sample_check.toggled.connect(self.update_sample_frame_controls)
        self.random_sample_check.setToolTip("When checked, choose a random source frame from the selected video.")
        self.sample_frame_spin = QSpinBox()
        self.sample_frame_spin.setRange(1, 1_000_000_000)
        self.sample_frame_spin.setValue(1)
        self.sample_frame_spin.setToolTip("When Random sample is off, preview this exact source frame number.")
        sample_form.addRow("", self.random_sample_check)
        sample_form.addRow("Frame #", self.sample_frame_spin)
        layout.addLayout(sample_form)

        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip("Load built-in or saved ASCII appearance presets.")
        self._refresh_preset_combo()
        self.preset_combo.currentTextChanged.connect(self.apply_preset)
        self.save_ascii_preset_button = self._button("Save ASCII Preset", "Save the current ASCII and appearance settings.")
        self.save_ascii_preset_button.clicked.connect(self.save_ascii_preset)
        preset_row.addWidget(self.preset_combo, stretch=1)
        preset_row.addWidget(self.save_ascii_preset_button)
        layout.addLayout(preset_row)

        form = QFormLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(8, 500)
        self.width_spin.valueChanged.connect(self.schedule_preview)
        self.width_spin.setToolTip("Number of ASCII characters across the output.")

        self.ramp_combo = QComboBox()
        for name, ramp in sorted(self.ramps.items()):
            self.ramp_combo.addItem(name, ramp)
        self.ramp_combo.addItem("Custom", "")
        self.ramp_combo.currentIndexChanged.connect(self.apply_ramp_choice)
        self.ramp_combo.setToolTip("Named character ramps, from dark to light.")

        self.ramp_edit = QLineEdit()
        self.ramp_edit.textEdited.connect(self.ramp_text_edited)
        self.ramp_edit.textChanged.connect(self.schedule_preview)
        self.ramp_edit.setToolTip("Characters used to map brightness. Left is dark, right is light.")

        self.invert_check = QCheckBox("Invert brightness")
        self.invert_check.toggled.connect(self.schedule_preview)
        self.invert_check.setToolTip("Reverse how brightness maps to the character ramp.")

        self.brightness_slider = self._slider(-100, 100, 0, "Shift sampled brightness before character mapping.")
        self.contrast_slider = self._slider(0, 300, 100, "Increase or reduce tonal contrast.")
        self.gamma_slider = self._slider(20, 300, 100, "Adjust midtone response.")
        self.find_edges_check = QCheckBox("Find edges")
        self.find_edges_check.toggled.connect(self.schedule_preview)
        self.find_edges_check.setToolTip("Emphasize image edges before mapping brightness to characters.")
        self.edge_strength_slider = self._slider(0, 300, 100, "Strength of edge emphasis when Find edges is enabled.")
        self.sharpen_slider = self._slider(0, 300, 0, "Sharpen the resized source before ASCII conversion.")
        self.blur_slider = self._slider(0, 100, 0, "Slightly blur the resized source to simplify noisy detail.")
        self.posterize_spin = QSpinBox()
        self.posterize_spin.setRange(0, 32)
        self.posterize_spin.setSpecialValueText("Off")
        self.posterize_spin.setToolTip("Limit tonal levels before character mapping. Off keeps continuous tones.")
        self.posterize_spin.valueChanged.connect(self.schedule_preview)
        self.threshold_slider = self._slider(0, 100, 0, "Binary threshold. Zero disables thresholding.")

        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems(FONT_FAMILIES)
        self.font_family_combo.currentTextChanged.connect(self.schedule_preview)
        self.font_family_combo.setToolTip("Font family used to render ASCII image outputs and previews.")

        self.font_weight_combo = QComboBox()
        self.font_weight_combo.addItems(["regular", "bold"])
        self.font_weight_combo.currentTextChanged.connect(self.schedule_preview)
        self.font_weight_combo.setToolTip("Font weight used for rendered outputs.")

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(4, 96)
        self.font_size_spin.valueChanged.connect(self.schedule_preview)
        self.font_size_spin.setToolTip("Rendered font size in pixels.")

        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.5, 3.0)
        self.line_spacing_spin.setSingleStep(0.05)
        self.line_spacing_spin.setDecimals(2)
        self.line_spacing_spin.valueChanged.connect(self.schedule_preview)
        self.line_spacing_spin.setToolTip("Line-height multiplier for rendered ASCII rows.")

        self.character_spacing_spin = QDoubleSpinBox()
        self.character_spacing_spin.setRange(0.5, 3.0)
        self.character_spacing_spin.setSingleStep(0.05)
        self.character_spacing_spin.setDecimals(2)
        self.character_spacing_spin.valueChanged.connect(self.schedule_preview)
        self.character_spacing_spin.setToolTip("Horizontal character spacing multiplier.")

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["monochrome", "grayscale", "source_color", "ansi"])
        self.mode_combo.currentTextChanged.connect(self.schedule_preview)
        self.mode_combo.setToolTip("Color strategy for rendered output.")

        form.addRow("Character width", self.width_spin)
        form.addRow("Ramp preset", self.ramp_combo)
        form.addRow("Ramp", self.ramp_edit)
        form.addRow("", self.invert_check)
        form.addRow("Brightness", self.brightness_slider)
        form.addRow("Contrast", self.contrast_slider)
        form.addRow("Gamma", self.gamma_slider)
        form.addRow("", self.find_edges_check)
        form.addRow("Edge strength", self.edge_strength_slider)
        form.addRow("Sharpen", self.sharpen_slider)
        form.addRow("Blur", self.blur_slider)
        form.addRow("Posterize", self.posterize_spin)
        form.addRow("Threshold", self.threshold_slider)
        form.addRow("Font", self.font_family_combo)
        form.addRow("Weight", self.font_weight_combo)
        form.addRow("Font size", self.font_size_spin)
        form.addRow("Line height", self.line_spacing_spin)
        form.addRow("Char spacing", self.character_spacing_spin)
        form.addRow("Color mode", self.mode_combo)
        layout.addLayout(form)

        color_row = QHBoxLayout()
        self.foreground_button = self._button("Text Color", "Choose monochrome foreground text color.")
        self.foreground_button.clicked.connect(lambda: self.choose_color("foreground"))
        self.background_button = self._button("Background", "Choose rendered background color.")
        self.background_button.clicked.connect(lambda: self.choose_color("background"))
        color_row.addWidget(self.foreground_button)
        color_row.addWidget(self.background_button)
        layout.addLayout(color_row)
        layout.addStretch(1)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.output_preview = ScaledPreviewLabel("ASCII output preview will appear here.", QSize(700, 520), QSize(320, 240))
        self.output_preview.setToolTip("")
        layout.addWidget(self.output_preview)
        return panel

    def _build_export_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.text_export_group = CollapsibleGroup("Text Export", self._build_text_export_group(), expanded=False)
        self.image_export_group = CollapsibleGroup("Image Export", self._build_image_export_group(), expanded=False)
        self.video_export_group = CollapsibleGroup("Video Export", self._build_video_export_group(), expanded=True)
        layout.addWidget(self.text_export_group)
        layout.addWidget(self.image_export_group)
        layout.addWidget(self.video_export_group)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setToolTip("Overall export progress.")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Job messages")
        self.log.setToolTip("Recent export and conversion messages.")
        layout.addWidget(self.progress)
        layout.addWidget(self.log, stretch=1)
        return panel

    def _build_text_export_group(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        form = QFormLayout()
        self.text_export_preset_combo = QComboBox()
        self.text_export_preset_combo.setToolTip("Apply the text settings from a saved export preset.")
        self.text_export_preset_combo.currentTextChanged.connect(self.apply_text_export_preset)
        self.save_text_export_preset_button = self._button("Save Text Preset", "Save the current export settings as a reusable preset.")
        self.save_text_export_preset_button.clicked.connect(lambda _checked=False: self.save_export_preset("text"))
        self.text_format_combo = QComboBox()
        self.text_format_combo.addItem("Plain text (.txt)", "txt")
        self.text_format_combo.addItem("HTML (.html)", "html")
        self.text_format_combo.setToolTip("Choose plain ASCII text or an HTML preview document.")
        self.text_line_ending_combo = QComboBox()
        self.text_line_ending_combo.addItem("LF", "lf")
        self.text_line_ending_combo.addItem("CRLF", "crlf")
        self.text_line_ending_combo.setToolTip("Line ending style for text files.")
        self.text_ansi_check = QCheckBox("ANSI source colors")
        self.text_ansi_check.setToolTip("Write ANSI 24-bit color escapes for terminal playback.")
        self.text_header_check = QCheckBox("Include settings header")
        self.text_header_check.setToolTip("Add a short settings header at the top of text exports.")
        form.addRow("Preset", self.text_export_preset_combo)
        form.addRow("", self.save_text_export_preset_button)
        form.addRow("Format", self.text_format_combo)
        form.addRow("Line endings", self.text_line_ending_combo)
        form.addRow("", self.text_ansi_check)
        form.addRow("", self.text_header_check)
        layout.addLayout(form)
        self.export_txt_button = self._button("Export Text", "Export the selected image as text or HTML.")
        self.export_txt_button.clicked.connect(lambda: self.export_current(text_output=True))
        layout.addWidget(self.export_txt_button)
        return group

    def _build_image_export_group(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        form = QFormLayout()
        self.image_export_preset_combo = QComboBox()
        self.image_export_preset_combo.setToolTip("Apply the image settings from a saved export preset.")
        self.image_export_preset_combo.currentTextChanged.connect(self.apply_image_export_preset)
        self.save_image_export_preset_button = self._button("Save Image Preset", "Save the current export settings as a reusable preset.")
        self.save_image_export_preset_button.clicked.connect(lambda _checked=False: self.save_export_preset("image"))
        self.image_format_combo = QComboBox()
        for item in ["png", "jpg", "webp", "bmp"]:
            self.image_format_combo.addItem(item.upper(), item)
        self.image_format_combo.setToolTip("Rendered image file format.")
        self.image_quality_spin = QSpinBox()
        self.image_quality_spin.setRange(1, 100)
        self.image_quality_spin.setValue(95)
        self.image_quality_spin.setToolTip("JPEG/WebP quality. PNG and BMP ignore this.")
        self.transparent_check = QCheckBox("Transparent background")
        self.transparent_check.setToolTip("Use transparency for image formats that support it.")
        self.antialias_check = QCheckBox("Antialias text")
        self.antialias_check.setChecked(True)
        self.antialias_check.setToolTip("Keep rendered text smoothed where the font renderer supports it.")
        self.image_resolution_combo = QComboBox()
        self._populate_resolution_combo(self.image_resolution_combo, include_square=True)
        self.image_resolution_combo.currentIndexChanged.connect(lambda: self.apply_resolution_choice("image"))
        self.image_resolution_combo.setToolTip("Final rendered image resolution. Auto uses the natural ASCII render size.")
        self.image_width_spin = self._resolution_spin()
        self.image_height_spin = self._resolution_spin()
        form.addRow("Preset", self.image_export_preset_combo)
        form.addRow("", self.save_image_export_preset_button)
        form.addRow("Format", self.image_format_combo)
        form.addRow("Resolution", self.image_resolution_combo)
        form.addRow("Width", self.image_width_spin)
        form.addRow("Height", self.image_height_spin)
        form.addRow("Quality", self.image_quality_spin)
        form.addRow("", self.transparent_check)
        form.addRow("", self.antialias_check)
        layout.addLayout(form)
        self.export_image_button = self._button("Export Image", "Export the selected image as a rendered ASCII image.")
        self.export_image_button.clicked.connect(lambda: self.export_current(text_output=False))
        layout.addWidget(self.export_image_button)
        self.apply_resolution_choice("image")
        return group

    def _build_video_export_group(self) -> QWidget:
        group = QWidget()
        layout = QVBoxLayout(group)
        form = QFormLayout()
        self.video_export_preset_combo = QComboBox()
        self.video_export_preset_combo.setToolTip("Apply the video settings from a saved export preset.")
        self.video_export_preset_combo.currentTextChanged.connect(self.apply_video_export_preset)
        self.save_video_export_preset_button = self._button("Save Video Preset", "Save the current export settings as a reusable preset.")
        self.save_video_export_preset_button.clicked.connect(lambda _checked=False: self.save_export_preset("video"))
        self.video_format_combo = QComboBox()
        for profile in VIDEO_PROFILES:
            self.video_format_combo.addItem(profile["label"], profile)
        self.video_format_combo.currentIndexChanged.connect(self.apply_video_format_choice)
        self.video_format_combo.setToolTip("Container and common codec preset for video export.")
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.setEditable(True)
        self.video_codec_combo.addItems(["libx264", "libx265", "libvpx-vp9", "gif"])
        self.video_codec_combo.setToolTip("FFmpeg video codec name.")
        self.video_fps_spin = QDoubleSpinBox()
        self.video_fps_spin.setRange(1.0, 240.0)
        self.video_fps_spin.setValue(30.0)
        self.video_fps_spin.setDecimals(3)
        self.video_fps_spin.setToolTip("Custom output FPS, used only when source FPS is off.")
        self.video_crf_spin = QSpinBox()
        self.video_crf_spin.setRange(0, 63)
        self.video_crf_spin.setValue(20)
        self.video_crf_spin.setToolTip("Constant Rate Factor. Lower is higher quality and larger files.")
        self.video_bitrate_spin = QDoubleSpinBox()
        self.video_bitrate_spin.setRange(0.0, 200.0)
        self.video_bitrate_spin.setDecimals(1)
        self.video_bitrate_spin.setSingleStep(0.5)
        self.video_bitrate_spin.setSuffix(" Mbps")
        self.video_bitrate_spin.setSpecialValueText("CRF quality")
        self.video_bitrate_spin.setToolTip("Optional target bitrate in Mbps. Leave at zero to use CRF quality.")
        self.video_bitrate_spin.valueChanged.connect(self.update_crf_enabled)
        self.video_speed_combo = QComboBox()
        self.video_speed_combo.addItems(
            ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        )
        self.video_speed_combo.setCurrentText("medium")
        self.video_speed_combo.setToolTip("Encoder speed preset. Slower usually compresses better.")
        self.video_pix_fmt_combo = QComboBox()
        self.video_pix_fmt_combo.setEditable(True)
        self.video_pix_fmt_combo.addItems(["yuv420p", "yuv444p", "rgb24"])
        self.video_pix_fmt_combo.setToolTip("FFmpeg pixel format. yuv420p is safest for MP4 compatibility.")
        self.video_resolution_combo = QComboBox()
        self._populate_resolution_combo(self.video_resolution_combo, include_square=False)
        self.video_resolution_combo.currentIndexChanged.connect(lambda: self.apply_resolution_choice("video"))
        self.video_resolution_combo.setToolTip("Final video resolution. Supports up to 4K UHD.")
        self.video_width_spin = self._resolution_spin(maximum=3840)
        self.video_height_spin = self._resolution_spin(maximum=2160)
        self.source_fps_check = QCheckBox("Use source FPS")
        self.source_fps_check.setChecked(True)
        self.source_fps_check.toggled.connect(self.update_source_fps_enabled)
        self.source_fps_check.setToolTip("Use the source video's FPS when FFprobe can read it.")
        self.copy_audio_check = QCheckBox("Copy audio if possible")
        self.copy_audio_check.setChecked(True)
        self.copy_audio_check.setToolTip("Mux the original audio into the finished video when compatible.")
        self.keep_frames_check = QCheckBox("Keep intermediate frames")
        self.keep_frames_check.setToolTip("Leave extracted and rendered frames on disk after export.")
        form.addRow("Preset", self.video_export_preset_combo)
        form.addRow("", self.save_video_export_preset_button)
        form.addRow("Format", self.video_format_combo)
        form.addRow("Codec", self.video_codec_combo)
        form.addRow("Resolution", self.video_resolution_combo)
        form.addRow("Width", self.video_width_spin)
        form.addRow("Height", self.video_height_spin)
        form.addRow("Custom FPS", self.video_fps_spin)
        form.addRow("CRF", self.video_crf_spin)
        form.addRow("Bitrate", self.video_bitrate_spin)
        form.addRow("Speed", self.video_speed_combo)
        form.addRow("Pixel format", self.video_pix_fmt_combo)
        form.addRow("", self.source_fps_check)
        form.addRow("", self.copy_audio_check)
        form.addRow("", self.keep_frames_check)
        layout.addLayout(form)
        self.export_video_button = self._button("Export Video MP4", "Export the selected video with the current ASCII settings.")
        self.export_video_button.clicked.connect(self.export_video)
        layout.addWidget(self.export_video_button)
        self.update_source_fps_enabled()
        self.apply_resolution_choice("video")
        self.update_crf_enabled()
        return group

    def _scroll_panel(self, widget: QWidget, minimum_width: int) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(minimum_width)
        scroll.setWidget(widget)
        return scroll

    def _button(self, text: str, tooltip: str) -> QPushButton:
        button = QPushButton(text)
        button.setToolTip(tooltip)
        return button

    def _resolution_spin(self, maximum: int = 7680) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, maximum)
        spin.setSpecialValueText("Auto")
        spin.setToolTip("Set to Auto to use the natural rendered size.")
        return spin

    def _populate_resolution_combo(self, combo: QComboBox, include_square: bool) -> None:
        combo.addItem("Auto", (None, None))
        combo.addItem("HD 720p", (1280, 720))
        combo.addItem("Full HD 1080p", (1920, 1080))
        combo.addItem("QHD 1440p", (2560, 1440))
        combo.addItem("4K UHD", (3840, 2160))
        if include_square:
            combo.addItem("Square 1080", (1080, 1080))
        combo.addItem("Custom", "custom")

    def _slider(self, minimum: int, maximum: int, value: int, tooltip: str) -> SliderSpinBox:
        slider = SliderSpinBox(minimum, maximum, value, tooltip)
        slider.valueChanged.connect(self.schedule_preview)
        return slider

    def update_source_actions(self) -> None:
        has_video = self.video_path is not None
        self.sample_frame_button.setEnabled(has_video)
        self.update_sample_frame_controls()

    def update_sample_frame_controls(self) -> None:
        has_video = self.video_path is not None
        self.random_sample_check.setEnabled(has_video)
        self.sample_frame_spin.setEnabled(has_video and not self.random_sample_check.isChecked())

    def _load_user_ascii_presets(self) -> dict[str, Preset]:
        try:
            return load_user_ascii_presets()
        except Exception:
            return {}

    def _load_user_export_presets(self) -> dict[str, ExportPreset]:
        try:
            return load_user_export_presets()
        except Exception:
            return {}

    def _rebuild_export_preset_maps(self) -> None:
        self.text_export_presets = built_in_text_export_presets()
        self.image_export_presets = built_in_image_export_presets()
        self.video_export_presets = built_in_video_export_presets()
        for name, preset in self.user_export_presets.items():
            if preset.group == "text":
                self.text_export_presets[name] = preset.text
            elif preset.group == "image":
                self.image_export_presets[name] = preset.image
            elif preset.group == "video":
                self.video_export_presets[name] = preset.video
            elif preset.group is None:
                self.text_export_presets[name] = preset.text
                self.image_export_presets[name] = preset.image
                self.video_export_presets[name] = preset.video

    def _refresh_preset_combo(self, selected: str | None = None) -> None:
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.presets))
        if selected:
            self.preset_combo.setCurrentText(selected)
        self.preset_combo.blockSignals(False)

    def _refresh_export_preset_combos(
        self,
        selected: str | None = None,
        text_selected: str | None = None,
        image_selected: str | None = None,
        video_selected: str | None = None,
    ) -> None:
        selections = {
            self.text_export_preset_combo: (self.text_export_presets, text_selected or selected),
            self.image_export_preset_combo: (self.image_export_presets, image_selected or selected),
            self.video_export_preset_combo: (self.video_export_presets, video_selected or selected),
        }
        for combo, (presets, wanted) in selections.items():
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(sorted(presets))
            if wanted and wanted in presets:
                combo.setCurrentText(wanted)
            combo.blockSignals(False)

    def open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff)",
        )
        if not path:
            return
        self.input_path = Path(path)
        self.video_path = None
        self.media_preview_pixmap = QPixmap(str(self.input_path))
        self.input_label.setText(str(self.input_path))
        self.statusBar().showMessage(f"Loaded image: {self.input_path.name}")
        self.show_media_preview()
        self.update_source_actions()
        self.refresh_preview()

    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm)",
        )
        if not path:
            return
        self.set_video_path(Path(path))

    def set_video_path(self, path: Path, source_label: str | None = None) -> None:
        self.video_path = path
        self.input_path = None
        self.media_preview_pixmap = None
        self.output_preview_pixmap = None
        self.input_label.setText(source_label or str(self.video_path))
        self.media_preview.clear_preview(f"Video selected:\n{self.video_path.name}")
        self.output_preview.clear_preview("Use Preview Sample Frame or start export to see rendered ASCII frames.")
        self.statusBar().showMessage(f"Loaded video: {self.video_path.name}")
        self.update_source_actions()

    def load_youtube_video(self) -> None:
        url = self.youtube_url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "No URL", "Paste a YouTube URL before loading.")
            return
        self.youtube_load_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.log.appendPlainText(f"Loading YouTube source: {url}")
        self.statusBar().showMessage("Loading YouTube video...")
        worker = YouTubeDownloadWorker(url)
        worker.signals.progress.connect(self.youtube_progress)
        worker.signals.finished.connect(self.youtube_download_finished)
        worker.signals.error.connect(self.youtube_download_failed)
        self.thread_pool.start(worker)

    def youtube_progress(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        percent = payload.get("percent")
        status = str(payload.get("status", "downloading"))
        if isinstance(percent, int):
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
            self.statusBar().showMessage(f"YouTube {status}: {percent}%")
        else:
            self.progress.setRange(0, 0)
            self.statusBar().showMessage(f"YouTube {status}...")

    def youtube_download_finished(self, output: object) -> None:
        self.youtube_load_button.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        path = Path(str(output))
        self.set_video_path(path, f"YouTube source:\n{self.youtube_url_edit.text().strip()}\n{path}")
        self.log.appendPlainText(f"YouTube source ready: {path}")
        self.statusBar().showMessage(f"YouTube source ready: {path.name}")

    def youtube_download_failed(self, message: str) -> None:
        self.youtube_load_button.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.log.appendPlainText(f"Error: {message}")
        self.statusBar().showMessage(f"Error: {message}")
        QMessageBox.critical(self, "YouTube Load Failed", message)

    def preview_sample_frame(self) -> None:
        if not self.video_path:
            QMessageBox.information(self, "No Video", "Open a video before previewing a sample frame.")
            return
        try:
            self.read_settings()
            video_settings = self.current_video_settings()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Settings", str(exc))
            return
        self.progress.setRange(0, 0)
        self.log.appendPlainText("Extracting sample frame...")
        self.statusBar().showMessage("Extracting sample frame...")
        self.sample_frame_button.setEnabled(False)
        worker = SampleFrameWorker(
            self.video_path,
            AsciiSettings.from_dict(self.ascii_settings.to_dict()),
            RenderSettings.from_dict(self.render_settings.to_dict()),
            ImageExportSettings(
                output_format="png",
                output_width=video_settings.output_width,
                output_height=video_settings.output_height,
            ),
            self.random_sample_check.isChecked(),
            self.sample_frame_number(),
        )
        worker.signals.finished.connect(self.sample_frame_finished)
        worker.signals.error.connect(self.sample_frame_failed)
        self.thread_pool.start(worker)

    def sample_frame_finished(self, payload: object) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        if not isinstance(payload, dict):
            self.update_source_actions()
            return
        source_frame = Path(str(payload["source_frame"]))
        preview_frame = Path(str(payload["preview_frame"]))
        self.media_preview_pixmap = QPixmap(str(source_frame))
        self.show_media_preview()
        self.show_output_preview_from_path(preview_frame)
        self.log.appendPlainText("Sample frame preview ready.")
        self.statusBar().showMessage("Sample frame preview ready")
        self.update_source_actions()

    def sample_frame_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.log.appendPlainText(f"Error: {message}")
        self.statusBar().showMessage(f"Error: {message}")
        self.update_source_actions()
        QMessageBox.warning(self, "Sample Frame Failed", message)

    def sample_frame_number(self) -> int | None:
        if self.random_sample_check.isChecked():
            return None
        return self.sample_frame_spin.value()

    def show_media_preview(self) -> None:
        if not self.media_preview_pixmap:
            return
        if self.media_preview_pixmap.isNull():
            self.media_preview.clear_preview("Could not preview this media.")
            return
        self.media_preview.set_source_pixmap(self.media_preview_pixmap)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.media_preview.update()
        self.output_preview.update()

    def apply_preset(self, name: str) -> None:
        if name not in self.presets:
            return
        preset = self.presets[name]
        self.ascii_settings = AsciiSettings.from_dict(preset.ascii.to_dict())
        self.render_settings = RenderSettings.from_dict(preset.render.to_dict())
        self.width_spin.setValue(self.ascii_settings.char_width)
        self.ramp_edit.setText(self.ascii_settings.ramp)
        self.invert_check.setChecked(self.ascii_settings.invert)
        self.brightness_slider.setValue(round(self.ascii_settings.brightness * 100))
        self.contrast_slider.setValue(round(self.ascii_settings.contrast * 100))
        self.gamma_slider.setValue(round(self.ascii_settings.gamma * 100))
        self.find_edges_check.setChecked(self.ascii_settings.edge_mode != "none")
        self.edge_strength_slider.setValue(round(self.ascii_settings.edge_strength * 100))
        self.sharpen_slider.setValue(round(self.ascii_settings.sharpen * 100))
        self.blur_slider.setValue(round(self.ascii_settings.blur * 100))
        self.posterize_spin.setValue(self.ascii_settings.posterize_levels or 0)
        self.threshold_slider.setValue(round((self.ascii_settings.threshold or 0.0) * 100))
        self.font_family_combo.setCurrentText(self.render_settings.font_family or "Consolas")
        self.font_weight_combo.setCurrentText(self.render_settings.font_weight)
        self.font_size_spin.setValue(self.render_settings.font_size)
        self.line_spacing_spin.setValue(self.render_settings.line_spacing)
        self.character_spacing_spin.setValue(self.render_settings.character_spacing)
        self.mode_combo.setCurrentText(self.render_settings.mode)
        self._sync_ramp_combo(self.ascii_settings.ramp)
        self.schedule_preview()

    def apply_export_preset(self, name: str) -> None:
        if name not in self.export_presets:
            return
        preset = self.export_presets[name]
        self._apply_text_export_settings(preset.text)
        self._apply_image_export_settings(preset.image)
        self._apply_video_settings(preset.video)

    def apply_text_export_preset(self, name: str) -> None:
        if name in self.text_export_presets:
            self._apply_text_export_settings(self.text_export_presets[name])

    def apply_image_export_preset(self, name: str) -> None:
        if name in self.image_export_presets:
            self._apply_image_export_settings(self.image_export_presets[name])

    def apply_video_export_preset(self, name: str) -> None:
        if name in self.video_export_presets:
            self._apply_video_settings(self.video_export_presets[name])

    def save_ascii_preset(self) -> None:
        try:
            self.read_settings()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Settings", str(exc))
            return
        name, ok = QInputDialog.getText(self, "Save ASCII Preset", "Preset name:")
        if not ok or not name.strip():
            return
        preset = Preset(
            name=name.strip(),
            ascii=AsciiSettings.from_dict(self.ascii_settings.to_dict()),
            render=RenderSettings.from_dict(self.render_settings.to_dict()),
        )
        try:
            save_user_ascii_preset(preset)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        self.user_ascii_presets[preset.name] = preset
        self.presets = {**built_in_presets(), **self.user_ascii_presets}
        self._refresh_preset_combo(preset.name)
        self.statusBar().showMessage(f"Saved ASCII preset: {preset.name}")

    def save_export_preset(self, group: str = "text") -> None:
        name, ok = QInputDialog.getText(self, "Save Export Preset", "Preset name:")
        if not ok or not name.strip():
            return
        try:
            preset = ExportPreset(
                name=name.strip(),
                text=self.current_text_export_settings(),
                image=self.current_image_export_settings(),
                video=self.current_video_settings(),
                group=group if group in {"text", "image", "video"} else None,
            )
            save_user_export_preset(preset)
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            return
        self.user_export_presets[preset.name] = preset
        self.export_presets = {**built_in_export_presets(), **self.user_export_presets}
        self._rebuild_export_preset_maps()
        self._refresh_export_preset_combos(
            text_selected=preset.name if preset.group == "text" else self.text_export_preset_combo.currentText(),
            image_selected=preset.name if preset.group == "image" else self.image_export_preset_combo.currentText(),
            video_selected=preset.name if preset.group == "video" else self.video_export_preset_combo.currentText(),
        )
        self.statusBar().showMessage(f"Saved export preset: {preset.name}")

    def read_settings(self) -> None:
        self.ascii_settings.char_width = self.width_spin.value()
        self.ascii_settings.ramp = self.ramp_edit.text()
        self.ascii_settings.invert = self.invert_check.isChecked()
        self.ascii_settings.brightness = self.brightness_slider.value() / 100.0
        self.ascii_settings.contrast = self.contrast_slider.value() / 100.0
        self.ascii_settings.gamma = self.gamma_slider.value() / 100.0
        self.ascii_settings.edge_mode = "sobel" if self.find_edges_check.isChecked() else "none"
        self.ascii_settings.edge_strength = self.edge_strength_slider.value() / 100.0
        self.ascii_settings.sharpen = self.sharpen_slider.value() / 100.0
        self.ascii_settings.blur = self.blur_slider.value() / 100.0
        posterize_levels = self.posterize_spin.value()
        self.ascii_settings.posterize_levels = posterize_levels if posterize_levels >= 2 else None
        threshold = self.threshold_slider.value()
        self.ascii_settings.threshold = threshold / 100.0 if threshold else None
        self.render_settings.font_family = self.font_family_combo.currentText()
        self.render_settings.font_weight = self.font_weight_combo.currentText()
        self.render_settings.font_size = self.font_size_spin.value()
        self.render_settings.line_spacing = self.line_spacing_spin.value()
        self.render_settings.character_spacing = self.character_spacing_spin.value()
        self.render_settings.mode = self.mode_combo.currentText()
        self.ascii_settings.validate()
        self.render_settings.validate()

    def schedule_preview(self) -> None:
        self.preview_timer.start(250)

    def refresh_preview(self) -> None:
        if not self.input_path:
            return
        try:
            self.read_settings()
            image_settings = self.current_image_export_settings()
            art = convert_image_to_ascii(self.input_path, self.ascii_settings)
            image = render_ascii_to_pil_image(art, self.render_settings)
            if image_settings.output_width and image_settings.output_height:
                image = fit_image_to_resolution(
                    image,
                    (image_settings.output_width, image_settings.output_height),
                    self.render_settings,
                )
        except Exception as exc:
            self.output_preview_pixmap = None
            self.output_preview.clear_preview(f"Preview error: {exc}")
            self.statusBar().showMessage(f"Preview error: {exc}")
            return
        self.output_preview_pixmap = self._pil_image_to_pixmap(image)
        self.show_output_preview()
        self.statusBar().showMessage(
            f"Preview: {art.character_size[0]} x {art.character_size[1]} chars | source {art.source_size[0]} x {art.source_size[1]}"
        )

    def choose_color(self, target: str) -> None:
        initial = self.render_settings.foreground if target == "foreground" else self.render_settings.background
        color = QColorDialog.getColor(QColor(initial), self, f"Choose {target}")
        if not color.isValid():
            return
        if target == "foreground":
            self.render_settings.foreground = color.name()
        else:
            self.render_settings.background = color.name()
        self.schedule_preview()

    def export_current(self, text_output: bool) -> None:
        if not self.input_path:
            QMessageBox.information(self, "No Image", "Open an image before exporting.")
            return
        try:
            self.read_settings()
            text_settings = self.current_text_export_settings()
            image_settings = self.current_image_export_settings()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Settings", str(exc))
            return

        if text_output:
            suffix = ".html" if text_settings.output_format == "html" else ".txt"
            path, _ = QFileDialog.getSaveFileName(self, "Export ASCII Text", "", "Text (*.txt);;HTML (*.html)")
        else:
            suffix = f".{image_settings.output_format}"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export ASCII Image",
                "",
                "PNG (*.png);;JPEG (*.jpg *.jpeg);;WEBP (*.webp);;BMP (*.bmp)",
            )
        if not path:
            return
        output_path = Path(path)
        if output_path.suffix.lower() != suffix:
            output_path = output_path.with_suffix(suffix)

        render_settings = RenderSettings.from_dict(self.render_settings.to_dict())
        render_settings.transparent = image_settings.transparent
        render_settings.antialias = image_settings.antialias
        self.progress.setRange(0, 0)
        self.log.appendPlainText(f"Starting export: {output_path}")
        self.statusBar().showMessage(f"Exporting {output_path.name}...")
        worker = ExportWorker(
            self.input_path,
            output_path,
            AsciiSettings.from_dict(self.ascii_settings.to_dict()),
            render_settings,
            text_settings,
            image_settings,
            text_output,
        )
        worker.signals.finished.connect(self.export_finished)
        worker.signals.error.connect(self.export_failed)
        self.thread_pool.start(worker)

    def export_finished(self, output: object) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.log.appendPlainText(f"Finished: {output}")
        if self.video_started_at is not None:
            self.statusBar().showMessage(f"Finished in {self._format_duration(time.monotonic() - self.video_started_at)}")
            self.video_started_at = None
            self._video_frame_timing = []
        else:
            self.statusBar().showMessage(f"Finished: {output}")

    def export_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.log.appendPlainText(f"Error: {message}")
        self.statusBar().showMessage(f"Error: {message}")
        self.video_started_at = None
        self._video_frame_timing = []
        QMessageBox.critical(self, "Export Failed", message)

    def export_video(self) -> None:
        if not self.video_path:
            QMessageBox.information(self, "No Video", "Open a video before exporting.")
            return
        try:
            self.read_settings()
            video_settings = self.current_video_settings()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid Settings", str(exc))
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export ASCII Video",
            "",
            "MP4 (*.mp4);;WebM (*.webm);;GIF (*.gif)",
        )
        if not path:
            return
        output_path = Path(path)
        suffix = self.current_video_suffix()
        if output_path.suffix.lower() != suffix:
            output_path = output_path.with_suffix(suffix)

        job = VideoAsciiJob(
            input_video=self.video_path,
            output_video=output_path,
            settings=AsciiSettings.from_dict(self.ascii_settings.to_dict()),
            render_settings=RenderSettings.from_dict(self.render_settings.to_dict()),
            video_settings=video_settings,
        )
        self.progress.setRange(0, 0)
        self._last_logged_video_frame = 0
        self._video_frame_timing = []
        self.video_started_at = time.monotonic()
        self.log.appendPlainText(f"Starting video export: {output_path}")
        self.statusBar().showMessage("Starting video export...")
        worker = VideoExportWorker(job)
        worker.signals.progress.connect(self.video_progress)
        worker.signals.finished.connect(self.export_finished)
        worker.signals.error.connect(self.export_failed)
        self.thread_pool.start(worker)

    def video_progress(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        stage = str(payload.get("stage", "video"))
        percent = payload.get("percent")
        preview_path = payload.get("preview_path")
        source_preview_path = payload.get("source_preview_path")
        current = payload.get("current")
        total = payload.get("total")
        if isinstance(percent, int):
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
        if preview_path:
            self.show_output_preview_from_path(Path(str(preview_path)))
        if source_preview_path:
            self.show_media_preview_from_path(Path(str(source_preview_path)))
        if stage == "convert" and isinstance(current, int):
            self._record_video_frame_timing(current)
            if current == 1 or current == total or current - self._last_logged_video_frame >= 10:
                self._last_logged_video_frame = current
                suffix = f"/{total}" if total else ""
                self.log.appendPlainText(f"Converted frame {current}{suffix}")
        elif stage != "command":
            self.log.appendPlainText(stage)
        self._update_video_status(stage, current if isinstance(current, (int, float)) else None, total if isinstance(total, (int, float)) else None)

    def current_text_export_settings(self) -> TextExportSettings:
        return TextExportSettings(
            output_format=self.text_format_combo.currentData(),
            line_ending=self.text_line_ending_combo.currentData(),
            ansi_color=self.text_ansi_check.isChecked(),
            include_settings_header=self.text_header_check.isChecked(),
        )

    def current_image_export_settings(self) -> ImageExportSettings:
        return ImageExportSettings(
            output_format=self.image_format_combo.currentData(),
            quality=self.image_quality_spin.value(),
            transparent=self.transparent_check.isChecked(),
            antialias=self.antialias_check.isChecked(),
            output_width=self._spin_resolution_value(self.image_width_spin),
            output_height=self._spin_resolution_value(self.image_height_spin),
        )

    def current_video_settings(self) -> VideoSettings:
        profile = self.current_video_profile()
        output_format = str(profile["format"])
        return VideoSettings(
            fps_mode="source" if self.source_fps_check.isChecked() else "custom",
            fps=self.video_fps_spin.value(),
            output_format=output_format,
            codec=self.video_codec_combo.currentText().strip() or str(profile["codec"]),
            crf=self.video_crf_spin.value(),
            bitrate=self.video_bitrate(),
            preset=self.video_speed_combo.currentText(),
            pix_fmt=self.video_pix_fmt_combo.currentText().strip(),
            copy_audio=self.copy_audio_check.isChecked() and output_format != "gif",
            keep_intermediate_frames=self.keep_frames_check.isChecked(),
            output_width=self._spin_resolution_value(self.video_width_spin),
            output_height=self._spin_resolution_value(self.video_height_spin),
        )

    def _apply_text_export_settings(self, settings: TextExportSettings) -> None:
        self.text_format_combo.setCurrentIndex(max(0, self.text_format_combo.findData(settings.output_format)))
        self.text_line_ending_combo.setCurrentIndex(max(0, self.text_line_ending_combo.findData(settings.line_ending)))
        self.text_ansi_check.setChecked(settings.ansi_color)
        self.text_header_check.setChecked(settings.include_settings_header)

    def _apply_image_export_settings(self, settings: ImageExportSettings) -> None:
        self.image_format_combo.setCurrentIndex(max(0, self.image_format_combo.findData(settings.output_format)))
        self.image_quality_spin.setValue(settings.quality)
        self.transparent_check.setChecked(settings.transparent)
        self.antialias_check.setChecked(settings.antialias)
        self._set_resolution_controls("image", settings.output_width, settings.output_height)

    def _apply_video_settings(self, settings: VideoSettings) -> None:
        self._updating_video_controls = True
        try:
            self._select_video_profile(settings.output_format, settings.codec)
            self.video_codec_combo.setCurrentText(settings.codec)
            self.video_fps_spin.setValue(settings.fps)
            self.video_crf_spin.setValue(settings.crf)
            self.video_bitrate_spin.setValue(self._bitrate_to_mbps(settings.bitrate))
            self.video_speed_combo.setCurrentText(settings.preset)
            self.video_pix_fmt_combo.setCurrentText(settings.pix_fmt)
            self.source_fps_check.setChecked(settings.fps_mode == "source")
            self.copy_audio_check.setChecked(settings.copy_audio and settings.output_format != "gif")
            self.keep_frames_check.setChecked(settings.keep_intermediate_frames)
            self._set_resolution_controls("video", settings.output_width, settings.output_height)
            self.apply_video_format_choice()
        finally:
            self._updating_video_controls = False
        self.update_source_fps_enabled()
        self.update_crf_enabled()

    def apply_ramp_choice(self) -> None:
        if self._updating_ramp_controls:
            return
        ramp = self.ramp_combo.currentData()
        if not ramp:
            return
        self.ramp_edit.setText(str(ramp))

    def ramp_text_edited(self) -> None:
        self._sync_ramp_combo(self.ramp_edit.text())

    def _sync_ramp_combo(self, ramp: str) -> None:
        self._updating_ramp_controls = True
        try:
            for index in range(self.ramp_combo.count()):
                if self.ramp_combo.itemData(index) == ramp:
                    self.ramp_combo.setCurrentIndex(index)
                    return
            self.ramp_combo.setCurrentText("Custom")
        finally:
            self._updating_ramp_controls = False

    def current_video_profile(self) -> dict[str, object]:
        profile = self.video_format_combo.currentData()
        if isinstance(profile, dict):
            return profile
        return VIDEO_PROFILES[0]

    def apply_video_format_choice(self) -> None:
        profile = self.current_video_profile()
        if not self._updating_video_controls:
            self.video_codec_combo.setCurrentText(str(profile["codec"]))
            self.video_crf_spin.setValue(int(profile["crf"]))
            self.video_pix_fmt_combo.setCurrentText(str(profile["pix_fmt"]))
        is_gif = profile["format"] == "gif"
        self.copy_audio_check.setEnabled(not is_gif)
        if is_gif:
            self.copy_audio_check.setChecked(False)
        self.update_video_export_button()
        self.update_crf_enabled()

    def _select_video_profile(self, output_format: str, codec: str) -> None:
        fallback_index = 0
        for index in range(self.video_format_combo.count()):
            profile = self.video_format_combo.itemData(index)
            if not isinstance(profile, dict):
                continue
            if profile["format"] == output_format:
                fallback_index = index
            if profile["format"] == output_format and profile["codec"] == codec:
                self.video_format_combo.setCurrentIndex(index)
                return
        self.video_format_combo.setCurrentIndex(fallback_index)

    def current_video_suffix(self) -> str:
        return str(self.current_video_profile()["suffix"])

    def update_video_export_button(self) -> None:
        self.export_video_button.setText(f"Export Video {str(self.current_video_profile()['format']).upper()}")

    def update_source_fps_enabled(self) -> None:
        self.video_fps_spin.setEnabled(not self.source_fps_check.isChecked())

    def update_crf_enabled(self) -> None:
        enabled = self.video_bitrate_spin.value() <= 0
        self.video_crf_spin.setEnabled(enabled)
        if enabled:
            self.video_crf_spin.setToolTip("Constant Rate Factor. Lower is higher quality and larger files.")
        else:
            self.video_crf_spin.setToolTip("CRF is disabled while a custom bitrate is set.")

    def video_bitrate(self) -> str | None:
        value = self.video_bitrate_spin.value()
        if value <= 0:
            return None
        return f"{value:g}M"

    def _bitrate_to_mbps(self, bitrate: str | None) -> float:
        if not bitrate:
            return 0.0
        value = bitrate.strip().lower()
        try:
            if value.endswith("m"):
                return float(value[:-1])
            if value.endswith("k"):
                return float(value[:-1]) / 1000.0
            return float(value)
        except ValueError:
            return 0.0

    def apply_resolution_choice(self, target: str) -> None:
        combo, width_spin, height_spin = self._resolution_widgets(target)
        value = combo.currentData()
        if value == "custom":
            width_spin.setEnabled(True)
            height_spin.setEnabled(True)
            return
        width, height = value
        width_spin.setValue(width or 0)
        height_spin.setValue(height or 0)
        width_spin.setEnabled(False)
        height_spin.setEnabled(False)

    def _set_resolution_controls(self, target: str, width: int | None, height: int | None) -> None:
        combo, width_spin, height_spin = self._resolution_widgets(target)
        wanted = (width, height)
        for index in range(combo.count()):
            if combo.itemData(index) == wanted:
                combo.setCurrentIndex(index)
                self.apply_resolution_choice(target)
                return
        combo.setCurrentText("Custom")
        width_spin.setEnabled(True)
        height_spin.setEnabled(True)
        width_spin.setValue(width or 0)
        height_spin.setValue(height or 0)

    def _resolution_widgets(self, target: str) -> tuple[QComboBox, QSpinBox, QSpinBox]:
        if target == "image":
            return self.image_resolution_combo, self.image_width_spin, self.image_height_spin
        return self.video_resolution_combo, self.video_width_spin, self.video_height_spin

    def _spin_resolution_value(self, spin: QSpinBox) -> int | None:
        return spin.value() or None

    def show_output_preview_from_path(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self.output_preview_pixmap = pixmap
        self.show_output_preview()

    def show_media_preview_from_path(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self.media_preview_pixmap = pixmap
        self.show_media_preview()

    def show_output_preview(self) -> None:
        if not self.output_preview_pixmap:
            return
        self.output_preview.set_source_pixmap(self.output_preview_pixmap)

    def _pil_image_to_pixmap(self, image) -> QPixmap:
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap

    def _record_video_frame_timing(self, frame_number: int) -> None:
        now = time.monotonic()
        if self._video_frame_timing and frame_number <= self._video_frame_timing[-1][0]:
            if frame_number < self._video_frame_timing[-1][0]:
                self._video_frame_timing = []
            else:
                return
        self._video_frame_timing.append((frame_number, now))
        self._video_frame_timing = self._video_frame_timing[-21:]

    def _recent_frame_eta(self, current: int | float | None, total: int | float | None) -> float | None:
        if not isinstance(current, int) or not isinstance(total, int) or len(self._video_frame_timing) < 2:
            return None
        first_frame, first_time = self._video_frame_timing[0]
        last_frame, last_time = self._video_frame_timing[-1]
        frame_delta = last_frame - first_frame
        time_delta = last_time - first_time
        if frame_delta <= 0 or time_delta <= 0:
            return None
        seconds_per_frame = time_delta / frame_delta
        return max(0.0, (total - current) * seconds_per_frame)

    def _update_video_status(self, stage: str, current: int | float | None, total: int | float | None) -> None:
        if self.video_started_at is None:
            self.statusBar().showMessage(stage)
            return
        elapsed = time.monotonic() - self.video_started_at
        parts = [stage, f"elapsed {self._format_duration(elapsed)}"]
        if current and total:
            if stage.startswith("extract"):
                parts.append(f"{current:.1f}/{total:.1f}s")
            else:
                parts.append(f"frame {int(current)}/{int(total)}")
            eta = self._recent_frame_eta(current, total) if stage == "convert" else None
            if eta is not None:
                parts.append(f"ETA {self._format_duration(eta)}")
        self.statusBar().showMessage(" | ".join(parts))

    def _format_duration(self, seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, sec = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"
