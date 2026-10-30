from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "assets"

TEXTURES = {
    "Aged Parchment Paper Texture.png": ("paper.webp", 1500, 0.93, 1.02),
    "Dark Crimson Marble Texture.png": ("marble.webp", 1500, 0.96, 1.0),
    "Deep Burgundy Leather Texture.png": ("leather.webp", 1500, 0.94, 0.9),
    "Distressed Silver Stripe on Charcoal.png": ("silver_strip.webp", 1600, 0.9, 1.0),
    "Ornate Burgundy Waveform Engraving.png": ("waveform_banner.webp", 1600, 1.0, 1.0),
    "Vintage Burgundy Quill and Ink Wave.png": ("splash.webp", 1200, 1.0, 1.0),
}

EMBLEMS = {
    "Vintage Burgundy R Quill Emblem.png": ("crest.png", 1024),
}

KEYED = {
    "Ornate Crossed Quill and Burgundy Nib.png": ("quill.png", 1024),
    "Silver Filigree Corner with Burgundy Accents.png": ("corner.png", 1024),
    "Symmetrical Quill and Acanthus Divider.png": ("divider.png", 1400),
}


def key_white(image: Image.Image, low: int = 236, high: int = 252) -> Image.Image:
    image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    span = max(1, high - low)
    for y in range(height):
        for x in range(width):
            r, g, b, _a = pixels[x, y]
            minimum = min(r, g, b)
            if minimum >= high:
                pixels[x, y] = (r, g, b, 0)
                continue
            if minimum <= low:
                continue
            t = (minimum - low) / span
            alpha = 255 - int(255 * t)
            if alpha <= 0:
                pixels[x, y] = (r, g, b, 0)
                continue
            factor = alpha / 255.0

            def defringe(channel: int, factor: float = factor) -> int:
                return max(
                    0, min(255, int((channel - (1 - factor) * 255) / max(factor, 0.01)))
                )

            pixels[x, y] = (defringe(r), defringe(g), defringe(b), alpha)
    return image


def clean_specks(image: Image.Image, min_area: int = 40) -> Image.Image:
    try:
        import numpy as np
        from scipy import ndimage
    except Exception:  # noqa: BLE001 - asset build must also work without scipy
        return image

    alpha = np.array(image.getchannel("A"))
    mask = alpha > 0
    labels, count = ndimage.label(mask)
    if count == 0:
        return image
    sizes = ndimage.sum(mask, labels, index=np.arange(1, count + 1))
    keep = np.zeros(count + 1, dtype=bool)
    keep[1:] = sizes >= min_area
    cleaned = np.where(keep[labels], alpha, 0).astype(np.uint8)
    image.putalpha(Image.fromarray(cleaned, "L"))
    return image


def key_emblem(image: Image.Image) -> Image.Image:
    """Cut the R/quill emblem off its parchment square, leaving it transparent."""
    image = image.convert("RGBA")
    width, height = image.size

    flood = image.copy()
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        ImageDraw.floodfill(flood, corner, (255, 0, 255, 255), thresh=50)

    pixels = image.load()
    flooded = flood.load()
    alpha = Image.new("L", image.size, 255)
    alpha_pixels = alpha.load()

    for y in range(height):
        for x in range(width):
            r, g, b, _a = pixels[x, y]
            fr, fg, fb, _fa = flooded[x, y]
            if (fr, fg, fb) == (255, 0, 255):
                alpha_pixels[x, y] = 0
                continue
            if max(r, g, b) > 215 and (r - b) > 12 and (g - b) > 4:
                alpha_pixels[x, y] = 0

    image.putalpha(alpha)
    return clean_specks(image)


def pad_transparent(image: Image.Image, fraction: float = 0.06) -> Image.Image:
    pad = int(max(image.size) * fraction)
    canvas = Image.new(
        "RGBA", (image.width + 2 * pad, image.height + 2 * pad), (0, 0, 0, 0)
    )
    canvas.paste(image, (pad, pad), image)
    return canvas


def crop_alpha(image: Image.Image, margin: int = 10) -> Image.Image:
    alpha = image.split()[-1]
    box = alpha.getbbox()
    if not box:
        return image
    left, top, right, bottom = box
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(image.width, right + margin)
    bottom = min(image.height, bottom + margin)
    return image.crop((left, top, right, bottom))


def fit(image: Image.Image, longest: int) -> Image.Image:
    if max(image.size) <= longest:
        return image
    scale = longest / max(image.size)
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(size, Image.LANCZOS)


def build(masters: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not masters.exists():
        raise SystemExit(
            f"Asset masters not found: {masters}\n"
            "Set WHISPERSCRIBE_ASSET_MASTERS or pass --masters."
        )

    for filename, (target, longest, color, brightness) in TEXTURES.items():
        source = masters / filename
        if not source.exists():
            print(f"skip (missing): {filename}")
            continue
        image = Image.open(source).convert("RGB")
        image = ImageEnhance.Color(image).enhance(color)
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = fit(image, longest)
        image.save(OUT / target, "WEBP", quality=84, method=6)
        print(f"texture: {filename} -> {target}")

    for filename, (target, longest) in EMBLEMS.items():
        source = masters / filename
        if not source.exists():
            print(f"skip (missing): {filename}")
            continue
        image = key_emblem(Image.open(source))
        image = crop_alpha(image)
        image = pad_transparent(image)
        image = fit(image, longest)
        image.save(OUT / target, "PNG", optimize=True)
        print(f"emblem:  {filename} -> {target}")

    for filename, (target, longest) in KEYED.items():
        source = masters / filename
        if not source.exists():
            print(f"skip (missing): {filename}")
            continue
        image = key_white(Image.open(source))
        image = crop_alpha(image)
        image = fit(image, longest)
        image.save(OUT / target, "PNG", optimize=True)
        print(f"keyed:   {filename} -> {target}")

    grain = masters / "Seamless Fine Gray Grain Texture.png"
    if grain.exists():
        image = Image.open(grain).convert("L")
        image = fit(image, 640)
        image.save(OUT / "grain.png", "PNG", optimize=True)
        print("overlay: grain -> grain.png")

    crest = OUT / "crest.png"
    if crest.exists():
        icon = Image.open(crest).convert("RGBA")
        icon = crop_alpha(icon, margin=0)
        side = max(icon.size)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(icon, ((side - icon.width) // 2, (side - icon.height) // 2), icon)
        icon = canvas.resize((256, 256), Image.LANCZOS)
        icon.save(
            OUT / "app.ico",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print("icon:    crest -> app.ico")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--masters",
        default=os.environ.get(
            "WHISPERSCRIBE_ASSET_MASTERS", str(ROOT / "asset-masters")
        ),
    )
    args = parser.parse_args()
    build(Path(args.masters))
