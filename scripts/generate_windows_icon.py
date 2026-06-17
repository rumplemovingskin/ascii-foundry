from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "build" / "assets"
    output_dir.mkdir(parents=True, exist_ok=True)
    icon_path = output_dir / "ascii-foundry.ico"

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(size) for size in sizes]
    images[-1].save(icon_path, sizes=[(size, size) for size in sizes], append_images=images[:-1])
    print(f"Wrote {icon_path}")
    return 0


def draw_icon(size: int) -> Image.Image:
    scale = size / 128
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = max(2, round(18 * scale))
    border = max(1, round(4 * scale))
    margin = max(1, round(8 * scale))
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(18, 34, 38, 255),
        outline=(116, 251, 211, 255),
        width=border,
    )
    font = load_font(max(8, round(34 * scale)))
    text = "A#"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) / 2
    y = (size - (bbox[3] - bbox[1])) / 2 - round(4 * scale)
    draw.text((x, y), text, font=font, fill=(248, 248, 242, 255))
    line_y = size - max(8, round(32 * scale))
    draw.line(
        [round(30 * scale), line_y, size - round(30 * scale), line_y],
        fill=(116, 251, 211, 255),
        width=max(1, round(3 * scale)),
    )
    return image


def load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("consolab.ttf", "Consola.ttf", "DejaVuSansMono-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


if __name__ == "__main__":
    raise SystemExit(main())
