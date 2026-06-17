from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


DEFAULT_RAMP = "@%#*+=-:. "

RenderMode = Literal["monochrome", "grayscale", "source_color", "ansi"]
FontWeight = Literal["regular", "bold"]
CropMode = Literal["fit", "fill", "stretch"]
EdgeMode = Literal["none", "sobel", "canny"]
DitherMode = Literal["none", "floyd_steinberg", "ordered"]
TextOutputFormat = Literal["txt", "html"]
LineEnding = Literal["lf", "crlf"]
ExportPresetGroup = Literal["text", "image", "video"]


@dataclass(slots=True)
class AsciiSettings:
    char_width: int = 120
    char_height: int | None = None
    ramp: str = DEFAULT_RAMP
    invert: bool = False
    preserve_aspect: bool = True
    aspect_correction: float = 0.45
    brightness: float = 0.0
    contrast: float = 1.0
    gamma: float = 1.0
    crop_mode: CropMode = "fit"
    edge_mode: EdgeMode = "none"
    edge_strength: float = 1.0
    sharpen: float = 0.0
    blur: float = 0.0
    posterize_levels: int | None = None
    threshold: float | None = None
    dither_mode: DitherMode = "none"

    def validate(self) -> None:
        if self.char_width < 1:
            raise ValueError("Character width must be at least 1.")
        if self.char_height is not None and self.char_height < 1:
            raise ValueError("Character height must be at least 1 when provided.")
        if not self.ramp:
            raise ValueError("Character ramp cannot be empty.")
        if self.gamma <= 0:
            raise ValueError("Gamma must be greater than 0.")
        if self.aspect_correction <= 0:
            raise ValueError("Aspect correction must be greater than 0.")
        if self.contrast < 0:
            raise ValueError("Contrast cannot be negative.")
        if self.edge_mode not in {"none", "sobel", "canny"}:
            raise ValueError("Edge mode must be none, sobel, or canny.")
        if self.edge_strength < 0:
            raise ValueError("Edge strength cannot be negative.")
        if self.sharpen < 0:
            raise ValueError("Sharpen cannot be negative.")
        if self.blur < 0:
            raise ValueError("Blur cannot be negative.")
        if self.posterize_levels is not None and not 2 <= self.posterize_levels <= 32:
            raise ValueError("Posterize levels must be between 2 and 32 when provided.")
        if self.threshold is not None and not 0.0 <= self.threshold <= 1.0:
            raise ValueError("Threshold must be between 0 and 1 when provided.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "AsciiSettings":
        settings = cls(**values)
        settings.validate()
        return settings


@dataclass(slots=True)
class RenderSettings:
    mode: RenderMode = "monochrome"
    font_family: str | None = None
    font_path: str | None = None
    font_weight: FontWeight = "regular"
    font_size: int = 12
    background: str = "#000000"
    foreground: str = "#F0F0F0"
    transparent: bool = False
    line_spacing: float = 1.0
    character_spacing: float = 1.0
    antialias: bool = True

    def validate(self) -> None:
        if self.font_size < 1:
            raise ValueError("Font size must be at least 1.")
        if self.line_spacing <= 0:
            raise ValueError("Line spacing must be greater than 0.")
        if self.character_spacing <= 0:
            raise ValueError("Character spacing must be greater than 0.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "RenderSettings":
        settings = cls(**values)
        settings.validate()
        return settings


@dataclass(slots=True)
class TextExportSettings:
    output_format: TextOutputFormat = "txt"
    line_ending: LineEnding = "lf"
    ansi_color: bool = False
    include_settings_header: bool = False

    def validate(self) -> None:
        if self.output_format not in {"txt", "html"}:
            raise ValueError("Text output format must be txt or html.")
        if self.line_ending not in {"lf", "crlf"}:
            raise ValueError("Line ending must be lf or crlf.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "TextExportSettings":
        settings = cls(**values)
        settings.validate()
        return settings


@dataclass(slots=True)
class ImageExportSettings:
    output_format: str = "png"
    quality: int = 95
    transparent: bool = False
    antialias: bool = True
    output_width: int | None = None
    output_height: int | None = None

    def validate(self) -> None:
        if self.quality < 1 or self.quality > 100:
            raise ValueError("Image quality must be between 1 and 100.")
        if not self.output_format:
            raise ValueError("Image output format cannot be empty.")
        if self.output_width is not None and self.output_width < 1:
            raise ValueError("Image output width must be at least 1 when provided.")
        if self.output_height is not None and self.output_height < 1:
            raise ValueError("Image output height must be at least 1 when provided.")
        if (self.output_width is None) != (self.output_height is None):
            raise ValueError("Image output width and height must both be set, or both be blank.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ImageExportSettings":
        settings = cls(**values)
        settings.validate()
        return settings


@dataclass(slots=True)
class VideoSettings:
    fps_mode: Literal["source", "custom"] = "source"
    fps: float = 30.0
    output_format: str = "mp4"
    codec: str = "libx264"
    crf: int = 20
    bitrate: str | None = None
    preset: str = "medium"
    pix_fmt: str = "yuv420p"
    copy_audio: bool = True
    keep_intermediate_frames: bool = False
    frame_pattern: str = "frame_%08d.png"
    output_width: int | None = None
    output_height: int | None = None

    def validate(self) -> None:
        if self.fps <= 0:
            raise ValueError("FPS must be greater than 0.")
        if self.crf < 0:
            raise ValueError("CRF cannot be negative.")
        if not self.codec:
            raise ValueError("Codec cannot be empty.")
        if not self.output_format:
            raise ValueError("Output format cannot be empty.")
        if self.bitrate is not None and not self.bitrate.strip():
            raise ValueError("Bitrate cannot be blank when provided.")
        if self.output_width is not None and self.output_width < 1:
            raise ValueError("Video output width must be at least 1 when provided.")
        if self.output_height is not None and self.output_height < 1:
            raise ValueError("Video output height must be at least 1 when provided.")
        if (self.output_width is None) != (self.output_height is None):
            raise ValueError("Video output width and height must both be set, or both be blank.")
        if self.output_width and self.output_height and (self.output_width > 3840 or self.output_height > 2160):
            raise ValueError("Video output resolution is limited to 4K UHD (3840 x 2160).")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "VideoSettings":
        settings = cls(**values)
        settings.validate()
        return settings


@dataclass(slots=True)
class Preset:
    name: str
    ascii: AsciiSettings = field(default_factory=AsciiSettings)
    render: RenderSettings = field(default_factory=RenderSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "ascii": self.ascii.to_dict(),
            "render": self.render.to_dict(),
            "video": self.video.to_dict(),
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "Preset":
        return cls(
            schema_version=values.get("schema_version", 1),
            name=values["name"],
            ascii=AsciiSettings.from_dict(values.get("ascii", {})),
            render=RenderSettings.from_dict(values.get("render", {})),
            video=VideoSettings.from_dict(values.get("video", {})),
        )


@dataclass(slots=True)
class ExportPreset:
    name: str
    text: TextExportSettings = field(default_factory=TextExportSettings)
    image: ImageExportSettings = field(default_factory=ImageExportSettings)
    video: VideoSettings = field(default_factory=VideoSettings)
    group: ExportPresetGroup | None = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "text": self.text.to_dict(),
            "image": self.image.to_dict(),
            "video": self.video.to_dict(),
            "group": self.group,
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "ExportPreset":
        return cls(
            schema_version=values.get("schema_version", 1),
            name=values["name"],
            text=TextExportSettings.from_dict(values.get("text", {})),
            image=ImageExportSettings.from_dict(values.get("image", {})),
            video=VideoSettings.from_dict(values.get("video", {})),
            group=values.get("group"),
        )
