# ASCII Foundry

ASCII Foundry is a desktop app and reusable Python engine for converting images,
image batches, and videos into ASCII-art outputs.

The first build focuses on a dependable still-image workflow:

- open an image in the PySide6 desktop app
- preview scaled rendered ASCII art
- preview a scaled rendered ASCII image without scrolling
- adjust width, character ramp, font, font weight, line height, spacing, invert,
  brightness, contrast, and gamma
- export plain `.txt`
- export rendered `.png`, `.jpg`, `.webp`, or `.bmp`
- choose fixed image/video output resolutions, including 4K UHD for video
- save custom ASCII and export presets
- preview a random or seeded sample frame from a selected video

The project also includes a reusable core package, a small CLI, tests, and
FFmpeg-backed video helpers for frame extraction and MP4 reconstruction.

## Install The App On Windows

For normal users, download `ASCII-Foundry-Portable-Windows-x64.zip`, extract it,
and double-click `ASCII Foundry.exe`.

No Git, Python, pip, or terminal setup is required for the portable release.
See [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md) for the end-user steps,
video dependency notes, and release build instructions.

## Requirements

The portable Windows release bundles the Python dependencies. When built with
the included release script, it also bundles FFmpeg and FFprobe for video work.

Source/development requirements:

- Python 3.10+
- Pillow
- NumPy
- PySide6 for the desktop GUI
- yt-dlp for YouTube URL sources
- pytest for tests
- FFmpeg and FFprobe on `PATH` for video workflows

Image conversion works without FFmpeg. Video commands fail gracefully when FFmpeg
is missing.

## Install For Development

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev,gui,video]"
```

If you only need the core and CLI:

```bash
python -m pip install -e .
```

## Run The App

```bash
ascii-foundry
```

or:

```bash
python -m ascii_foundry
```

## CLI Examples

Export plain text:

```bash
ascii-foundry image input.jpg --out output.txt --text --width 100
```

Export a rendered PNG:

```bash
ascii-foundry image input.jpg --out output.png --width 120 --preset "Classic Terminal"
```

Batch convert a folder:

```bash
ascii-foundry batch ./input_images --out ./ascii_output --format png --preset "Block Shade"
```

Run an FFmpeg-powered video conversion:

```bash
ascii-foundry video input.mp4 --out output.mp4 --width 140 --fps 30
```

Pick a container/codec and bitrate:

```bash
ascii-foundry video input.mp4 --out output --format webm --codec libvpx-vp9 --mbps 6 --width 140
ascii-foundry video input.mp4 --out output --format gif --fps 12 --width 100 --no-audio
ascii-foundry video input.mp4 --out output.mp4 --output-width 3840 --output-height 2160
```

## FFmpeg

Video conversion needs both `ffmpeg` and `ffprobe`. The portable Windows release
can bundle both tools. When running from source, install them separately and make
sure both commands are available on your `PATH`.

Useful checks:

```bash
ffmpeg -version
ffprobe -version
```

ASCII Foundry uses FFmpeg to extract image frames, converts each extracted frame
through the same core image renderer, and then asks FFmpeg to rebuild those
rendered frames into a video.

When **Keep intermediate frames** is enabled, extracted source frames and rendered
ASCII frames are cached and reused for matching future exports of the same video
and settings.

## Known Limitations

- The GUI implements still-image preview/export and video preview/export.
- Batch and video workflows are available through the CLI/core pipeline.
- The GUI supports grouped text, image, and video export controls and previews
  rendered video frames as they are created.
- Advanced image effects are intentionally lightweight and tuned for fast ASCII
  previews rather than full photo-editing control.

## Development

Run tests:

```bash
pytest
```

Build a portable Windows release zip:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

Project layout:

```text
src/ascii_foundry/
  core/       reusable conversion engine and video helpers
  gui/        PySide6 desktop UI
  cli/        command-line interface
  utils/      paths and logging helpers
tests/        focused core tests
docs/         user-facing notes
```
