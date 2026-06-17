# Install ASCII Foundry On Windows

## Easiest Option

Download `ASCII-Foundry-Portable-Windows-x64.zip` from the release page.

1. Right-click the zip and choose **Extract All**.
2. Open the extracted folder.
3. Double-click `ASCII Foundry.exe`.

You do not need Git, Python, pip, or a terminal for the portable release.

Windows SmartScreen may warn about the app if the build is unsigned. Choose
**More info** and **Run anyway** only if you downloaded it from a trusted release.

## Video And YouTube Support

The official portable build is intended to include:

- FFmpeg and FFprobe for video frame extraction and video export
- yt-dlp for YouTube URL sources

If video export says FFmpeg is missing, install FFmpeg manually and make sure
`ffmpeg.exe` and `ffprobe.exe` are on your `PATH`, or download a release that
includes bundled FFmpeg.

Use YouTube URL support only for videos you have rights or permission to process.

## Build The Portable App Yourself

Requirements:

- Windows 10 or newer
- Python 3.10 or newer
- Internet access for Python packages and FFmpeg download

From the project folder, open PowerShell and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_windows.ps1
```

The script will:

- create `.venv-build`
- install the GUI/video dependencies and PyInstaller
- download FFmpeg essentials into `vendor\ffmpeg\bin`
- generate a Windows icon
- build `dist\ASCII Foundry\ASCII Foundry.exe`
- create `release\ASCII-Foundry-Portable-Windows-x64.zip`

To build without bundling FFmpeg:

```powershell
.\scripts\build_windows.ps1 -SkipFfmpeg
```

## Optional Installer

If Inno Setup is installed and `iscc.exe` is on your `PATH`, the build script
also creates:

```text
release\ASCII-Foundry-Setup-Windows-x64.exe
```

The portable zip is still the recommended first release format because it is
simple to inspect, extract, and run.
