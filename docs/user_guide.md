# ASCII Foundry User Guide

## Convert One Image

1. Launch the app with `ascii-foundry`.
2. Choose **Open Image**.
3. Adjust width, ramp, font, weight, font size, line height, colors, invert,
   brightness, contrast, and gamma.
4. Use the collapsible **Text Export** or **Image Export** groups.

The ASCII preview is rendered as an image and scaled to fit the preview pane, so
large character grids do not require scrolling just to see the full composition.
Image and video exports can use fixed output resolutions. With a fixed
resolution selected, line height changes how many ASCII rows fit in that canvas;
it does not change the final output resolution.

## Convert A Batch

The first batch workflow is available from the CLI:

```bash
ascii-foundry batch ./images --out ./ascii_output --format png --width 120
```

Use `--text` to write text files instead of rendered images.

## Convert Video

Install FFmpeg first, then run:

```bash
ascii-foundry video input.mp4 --out output.mp4 --width 140 --fps 30
```

The video workflow creates a temporary folder, extracts frames, renders ASCII
frames, and rebuilds an MP4. Add `--keep-frames` when you want to inspect the
intermediate PNG frames.

In the desktop app, open a video and use **Preview Sample Frame** to extract one
frame, render it as ASCII, and show it in the output preview. Random sampling
chooses a fresh frame each time. Turn random sampling off and provide a seed to
make the sampled frame repeatable.

Useful export options:

```bash
ascii-foundry video input.mp4 --out output --format mp4 --codec libx264 --crf 20 --mbps 8
ascii-foundry video input.mp4 --out output --format webm --codec libvpx-vp9 --mbps 4
ascii-foundry video input.mp4 --out output --format gif --fps 12 --no-audio
ascii-foundry video input.mp4 --out output.mp4 --output-width 3840 --output-height 2160
```

Enable **Keep intermediate frames** to cache extracted source frames and rendered
ASCII frames. Matching future exports of the same video/settings reuse that
cache to save time.

## Presets

Built-in presets include:

- Classic Terminal
- Block Shade
- High Detail
- Soft Poster
- Source Color
- Video Fast Preview
- Video Final Render

The desktop app can also save custom ASCII presets and export presets. ASCII
presets store conversion and appearance choices; export presets store text,
image, and video export settings.

## Troubleshooting

If video conversion fails, check:

- `ffmpeg -version`
- `ffprobe -version`
- the output folder is writable
- the input file can be read by FFmpeg
