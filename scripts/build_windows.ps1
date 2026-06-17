param(
    [switch]$SkipFfmpeg,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildVenv = Join-Path $Root ".venv-build"
$Python = Join-Path $BuildVenv "Scripts\python.exe"
$ReleaseDir = Join-Path $Root "release"
$AppName = "ASCII Foundry"
$PortableZip = Join-Path $ReleaseDir "ASCII-Foundry-Portable-Windows-x64.zip"

function Invoke-ProjectCommand {
    param([string]$FilePath, [string[]]$Arguments)
    Write-Host "> $FilePath $($Arguments -join ' ')"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

function Ensure-BuildVenv {
    if (-not (Test-Path $Python)) {
        Write-Host "Creating build virtual environment..."
        Invoke-ProjectCommand "py" @("-3", "-m", "venv", $BuildVenv)
    }
    Invoke-ProjectCommand $Python @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-ProjectCommand $Python @("-m", "pip", "install", "-e", ".[gui,video,build]")
}

function Ensure-Ffmpeg {
    $FfmpegExe = Join-Path $Root "vendor\ffmpeg\bin\ffmpeg.exe"
    $FfprobeExe = Join-Path $Root "vendor\ffmpeg\bin\ffprobe.exe"
    if ((Test-Path $FfmpegExe) -and (Test-Path $FfprobeExe)) {
        Write-Host "Using existing FFmpeg binaries in vendor\ffmpeg\bin."
        return
    }

    $BuildDir = Join-Path $Root "build"
    $Archive = Join-Path $BuildDir "ffmpeg-release-essentials.zip"
    $ExtractDir = Join-Path $BuildDir "ffmpeg-release-essentials"
    $VendorBin = Join-Path $Root "vendor\ffmpeg\bin"
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
    New-Item -ItemType Directory -Force -Path $VendorBin | Out-Null

    if (-not (Test-Path $Archive)) {
        Write-Host "Downloading FFmpeg essentials build..."
        Invoke-WebRequest `
            -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" `
            -OutFile $Archive
    }

    if (Test-Path $ExtractDir) {
        Remove-Item -LiteralPath $ExtractDir -Recurse -Force
    }
    Expand-Archive -LiteralPath $Archive -DestinationPath $ExtractDir -Force
    $FoundFfmpeg = Get-ChildItem -Path $ExtractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    if (-not $FoundFfmpeg) {
        throw "Could not find ffmpeg.exe in downloaded archive."
    }
    $SourceBin = $FoundFfmpeg.Directory.FullName
    Copy-Item -LiteralPath (Join-Path $SourceBin "ffmpeg.exe") -Destination $VendorBin -Force
    Copy-Item -LiteralPath (Join-Path $SourceBin "ffprobe.exe") -Destination $VendorBin -Force
}

function Build-PortableZip {
    $DistApp = Join-Path $Root "dist\$AppName"
    if (Test-Path $DistApp) {
        Remove-Item -LiteralPath $DistApp -Recurse -Force
    }
    Invoke-ProjectCommand $Python @("scripts\generate_windows_icon.py")
    Invoke-ProjectCommand $Python @("-m", "PyInstaller", "--noconfirm", "packaging\windows\ascii_foundry.spec")

    Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination $DistApp -Force
    Copy-Item -LiteralPath (Join-Path $Root "docs\INSTALL_WINDOWS.md") -Destination $DistApp -Force

    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
    if (Test-Path $PortableZip) {
        Remove-Item -LiteralPath $PortableZip -Force
    }
    Compress-Archive -Path (Join-Path $DistApp "*") -DestinationPath $PortableZip -Force
    Write-Host "Portable zip ready: $PortableZip"
}

function Build-InstallerIfAvailable {
    if ($SkipInstaller) {
        return
    }
    $Iscc = Get-Command "iscc" -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        Write-Host "Inno Setup not found. Skipping installer build."
        return
    }
    Invoke-ProjectCommand $Iscc.Source @("packaging\windows\ascii_foundry.iss")
}

Set-Location $Root
Ensure-BuildVenv
if (-not $SkipFfmpeg) {
    Ensure-Ffmpeg
}
Build-PortableZip
Build-InstallerIfAvailable
