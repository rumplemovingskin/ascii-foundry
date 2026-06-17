# ASCII Foundry

ASCII Foundry turns images, videos, and YouTube sources into crisp ASCII art.
It is built for people who want a visual tool first: open a source, tune the
look, preview the result, and export it in the format they need.

Use it for stylized posters, terminal-inspired art, social clips, retro video
effects, print textures, stream graphics, and weird little experiments that
look better once they have been fed through a wall of characters.

## What It Does

- Converts still images into ASCII text or rendered image files.
- Converts videos into ASCII videos, including MP4, WebM, and GIF exports.
- Accepts local image/video files and YouTube URLs as video sources.
- Shows a live preview while you adjust the output.
- Includes built-in ASCII looks, character ramps, fonts, colors, and export presets.
- Lets you save your own ASCII and export presets.
- Supports preprocessing controls such as brightness, contrast, gamma, edge finding,
  sharpen, blur, posterize, and threshold.
- Exports text, HTML, PNG, JPG, WebP, BMP, MP4, WebM, and GIF.
- Supports high-resolution rendered outputs, including 4K video.

## Screenshots / Sample Outputs

<img width="1920" height="1032" alt="vader" src="https://github.com/user-attachments/assets/50e360a0-1a4e-46ac-b294-3ccbb4a866a9" />
<img width="1920" height="1032" alt="matrix" src="https://github.com/user-attachments/assets/8cf736cf-793e-41b4-8f6c-0f11ae3c1c5f" />
<img width="1920" height="1032" alt="spiderman" src="https://github.com/user-attachments/assets/09c3e23a-0989-4194-ac78-44d75d5cc184" />

https://github.com/user-attachments/assets/3dc2e89a-010f-413d-bf41-7657d0c1c66d

https://github.com/user-attachments/assets/e9e6fba2-c4ed-49d4-b6c0-b3c3ee371688



## Why Use It

ASCII Foundry is meant to feel like a small creative workstation rather than a
command-line trick. The app keeps the source preview, generated preview, and
export controls close together so you can experiment quickly and settle on a
look before committing to a render.

The same settings can be reused across still images and videos, which makes it
easy to build a consistent style instead of starting from scratch every time.

## Video And YouTube

Video export uses FFmpeg under the hood. The Windows portable build can include
FFmpeg and FFprobe, so normal users do not need to install them separately.

YouTube URL support uses `yt-dlp`. Use it only for videos you have rights or
permission to process.

## Download And Run On Windows

The easiest way to use ASCII Foundry is the portable Windows build.

1. Download [ASCII-Foundry-Portable-Windows-x64.zip](https://github.com/rumplemovingskin/ascii-foundry/releases/download/v0.1.0/ASCII-Foundry-Portable-Windows-x64.zip) from the latest release.
2. Extract the zip.
3. Open the extracted folder.
4. Double-click `ASCII Foundry.exe`.

Windows SmartScreen may warn about unsigned apps. Choose **More info** and then **Run anyway**.

More detailed Windows notes are in [docs/INSTALL_WINDOWS.md](docs/INSTALL_WINDOWS.md).

## Build From Source

Developers can run the app from source with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev,gui,video]"
python -m ascii_foundry
```

Run tests:

```powershell
pytest
```

Build a portable Windows release zip:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

The build script creates a standalone app folder and a portable zip under
`release/`.

## Command Line

ASCII Foundry also includes a CLI for scripting and batch work:

```powershell
ascii-foundry image input.jpg --out output.png --width 120 --preset "Classic Terminal"
ascii-foundry batch .\images --out .\ascii-output --format png
ascii-foundry video input.mp4 --out output.mp4 --width 140 --fps 30
```

Most users should start with the desktop app. The CLI is there when automation
is useful.
