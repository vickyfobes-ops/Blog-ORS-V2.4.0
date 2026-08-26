#!/usr/bin/env python3
"""Create the locked Origin blog PNG and WebP pair from one approved image."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageOps


TARGET_WIDTH = 1600
TARGET_HEIGHT = 900
MIN_CROP_WIDTH = 600
MIN_CROP_HEIGHT = 338


def crop_box(width: int, height: int, focal_x: float, focal_y: float) -> tuple[int, int, int, int]:
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_height = height
        crop_width = round(height * target_ratio)
        left = round((width - crop_width) * focal_x)
        left = max(0, min(left, width - crop_width))
        top = 0
    else:
        crop_width = width
        crop_height = round(width / target_ratio)
        left = 0
        top = round((height - crop_height) * focal_y)
        top = max(0, min(top, height - crop_height))
    return left, top, left + crop_width, top + crop_height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--focal-x", type=float, default=0.5)
    parser.add_argument("--focal-y", type=float, default=0.5)
    parser.add_argument("--webp-quality", type=int, default=86)
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slot):
        parser.error("--slot must use lowercase letters, digits, and single hyphens")
    if not 0.0 <= args.focal_x <= 1.0 or not 0.0 <= args.focal_y <= 1.0:
        parser.error("--focal-x and --focal-y must be between 0 and 1")
    if not 60 <= args.webp_quality <= 95:
        parser.error("--webp-quality must be between 60 and 95")
    source = args.input.expanduser().resolve()
    if not source.is_file():
        parser.error(f"input image does not exist: {source}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / f"{args.slot}.png"
    webp_path = output_dir / f"{args.slot}.webp"

    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, "white")
            image = Image.alpha_composite(background, rgba).convert("RGB")
        else:
            image = image.convert("RGB")
        box = crop_box(image.width, image.height, args.focal_x, args.focal_y)
        crop_width = box[2] - box[0]
        crop_height = box[3] - box[1]
        if crop_width < MIN_CROP_WIDTH or crop_height < MIN_CROP_HEIGHT:
            raise SystemExit(
                f"source image is too small after 16:9 crop ({crop_width}x{crop_height}); "
                f"minimum is {MIN_CROP_WIDTH}x{MIN_CROP_HEIGHT}"
            )
        image = image.crop(box).resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        image.save(png_path, format="PNG", optimize=True)
        image.save(webp_path, format="WEBP", quality=args.webp_quality, method=6)

    print(
        json.dumps(
            {
                "status": "PASS",
                "slot": args.slot,
                "png": str(png_path),
                "webp": str(webp_path),
                "width": TARGET_WIDTH,
                "height": TARGET_HEIGHT,
                "webpQuality": args.webp_quality,
                "focalPoint": {"x": args.focal_x, "y": args.focal_y},
                "sourceCrop": {"width": crop_width, "height": crop_height},
                "upscaled": crop_width < TARGET_WIDTH or crop_height < TARGET_HEIGHT,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
