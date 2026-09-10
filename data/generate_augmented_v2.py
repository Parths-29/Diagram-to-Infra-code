"""
Augmented Synthetic Dataset Generator — v2

Generates additional training images specifically targeting the three
distribution gaps identified from real-world test failures:

  1. Lined / ruled / grid paper backgrounds
  2. Variable ink color (blue, dark-blue, black) + variable stroke thickness (1-4px)
  3. Perspective warp to simulate angled phone photos

Design constraints:
  - Does NOT replace the original dataset. Outputs to data/synthetic_dataset_v2/
  - Each image INDEPENDENTLY and RANDOMLY combines the three axes.
  - Ruled lines are 1px, darkened 12-18 DN from bg — not at handwriting contrast.
  - Perspective warp bounded to max 12% corner displacement.

Usage:
    python data/generate_augmented_v2.py --preview-only   # eyeball 9 samples first
    python data/generate_augmented_v2.py --count 1000     # full generation
"""

import argparse
import os
import random
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.utils import (
    BG_COLORS,
    PEN_COLORS,
    PAPER_STYLES,
    draw_paper_background,
    draw_strokes_with_variable_thickness,
    augment_perspective_warp,
    apply_augmentations,
    save_yolo_annotations,
)
from data.generate_synthetic import (
    generate_three_tier_web_app,
    generate_microservices,
    generate_data_pipeline,
    IMG_SIZES,
)

# Blue-biased ink palette to cover the real-world blue pen failure case
EXTENDED_PEN_COLORS = [
    (0, 0, 0),          # black
    (30, 30, 80),       # dark blue-black
    (0, 0, 180),        # bright blue marker
    (0, 0, 120),        # medium blue (ballpoint)
    (20, 20, 160),      # blue-black ballpoint
    (0, 60, 200),       # royal blue
    (180, 0, 0),        # red marker
    (0, 100, 0),        # dark green
    (50, 50, 50),       # dark gray
]


def generate_augmented_image(archetype_fn, img_w: int, img_h: int):
    """
    Generate one diagram image with randomised combination of all three axes.
    """
    paper_style = random.choice(PAPER_STYLES)
    pen_color   = random.choice(EXTENDED_PEN_COLORS)
    bg_color    = random.choice(BG_COLORS)
    use_warp    = random.random() < 0.5

    varied_color, thickness = draw_strokes_with_variable_thickness(None, pen_color, 2)

    # Create canvas with paper background
    img = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
    draw_paper_background(img, style=paper_style, bg_color=bg_color)

    # Generate diagram on its own canvas
    diagram_img, bboxes = archetype_fn(img_w, img_h)

    # Extract ink mask (pixels darker than 220 luminance)
    diagram_gray = cv2.cvtColor(diagram_img, cv2.COLOR_BGR2GRAY)
    _, ink_mask = cv2.threshold(diagram_gray, 220, 255, cv2.THRESH_BINARY_INV)

    # Re-colour ink to our chosen pen color (BGR order for OpenCV)
    ink_bgr = (varied_color[2], varied_color[1], varied_color[0])
    ink_layer = np.full_like(diagram_img, ink_bgr)

    # Separate text_label regions from structural ink (borders, arrows).
    # Dilation must ONLY apply to structural strokes — dilating text pixels
    # causes small-font characters to merge into illegible solid blobs.
    text_label_id = None
    try:
        from data.utils import CLASS_ID as _CID
        text_label_id = _CID.get("text_label")
    except Exception:
        pass

    # Build a mask of pixels that fall inside any text_label bbox
    text_region_mask = np.zeros_like(ink_mask)
    if text_label_id is not None:
        for b in bboxes:
            if b.class_id == text_label_id:
                x1, y1 = max(0, b.x1), max(0, b.y1)
                x2, y2 = min(img_w - 1, b.x2), min(img_h - 1, b.y2)
                text_region_mask[y1:y2, x1:x2] = 255

    structural_ink = cv2.bitwise_and(ink_mask, cv2.bitwise_not(text_region_mask))
    text_ink = cv2.bitwise_and(ink_mask, text_region_mask)

    # Cap thickness at 3px — dilate ONLY structural ink, never text
    capped_thickness = min(thickness, 3)
    if capped_thickness > 1:
        kernel = np.ones((capped_thickness - 1, capped_thickness - 1), np.uint8)
        structural_ink = cv2.dilate(structural_ink, kernel, iterations=1)

    final_ink_mask = cv2.bitwise_or(structural_ink, text_ink)
    ink_mask_3ch = cv2.cvtColor(final_ink_mask, cv2.COLOR_GRAY2BGR)
    result = np.where(ink_mask_3ch > 0, ink_layer, img).astype(np.uint8)

    if use_warp:
        result = augment_perspective_warp(result, max_offset_frac=0.12)

    # Apply remaining standard augmentations (no extra perspective — already done)
    result = apply_augmentations(result, force_perspective=False)
    return result, bboxes


def generate_preview_samples(output_dir: str):
    """
    Generate 9 preview samples covering all meaningful axis combinations.
    """
    os.makedirs(os.path.join(output_dir, "preview"), exist_ok=True)
    random.seed(7)
    np.random.seed(7)

    samples = [
        {"paper": "lined",  "pen": (0, 0, 160),  "warp": False, "label": "01_lined_blue_flat"},
        {"paper": "lined",  "pen": (20, 20, 160), "warp": True,  "label": "02_lined_blue_warp"},
        {"paper": "lined",  "pen": (10, 10, 10),  "warp": True,  "label": "03_lined_black_warp"},
        {"paper": "grid",   "pen": (0, 60, 200),  "warp": False, "label": "04_grid_blue_flat"},
        {"paper": "grid",   "pen": (0, 0, 0),     "warp": True,  "label": "05_grid_black_warp"},
        {"paper": "plain",  "pen": (0, 0, 180),   "warp": True,  "label": "06_plain_blue_warp_thick"},
        {"paper": "plain",  "pen": (180, 0, 0),   "warp": False, "label": "07_plain_red_flat"},
        {"paper": "plain",  "pen": (0, 0, 0),     "warp": True,  "label": "08_plain_black_warp"},
        {"paper": "lined",  "pen": (30, 30, 80),  "warp": True,  "label": "09_lined_darkblue_warp"},
    ]

    for s in samples:
        img_w, img_h = 640, 640
        bg_color = (248, 248, 248)

        img = np.full((img_h, img_w, 3), bg_color, dtype=np.uint8)
        draw_paper_background(img, style=s["paper"], bg_color=bg_color)

        diagram_img, diagram_bboxes = generate_microservices(img_w, img_h)
        diagram_gray = cv2.cvtColor(diagram_img, cv2.COLOR_BGR2GRAY)
        _, ink_mask = cv2.threshold(diagram_gray, 220, 255, cv2.THRESH_BINARY_INV)

        _, thickness = draw_strokes_with_variable_thickness(None, s["pen"], 2)
        ink_bgr = (s["pen"][2], s["pen"][1], s["pen"][0])
        ink_layer = np.full_like(diagram_img, ink_bgr)

        # Exclude text_label regions from dilation (same fix as main generator)
        from data.utils import CLASS_ID as _CID
        text_label_id = _CID.get("text_label")
        text_region_mask = np.zeros_like(ink_mask)
        for b in diagram_bboxes:
            if b.class_id == text_label_id:
                x1, y1 = max(0, b.x1), max(0, b.y1)
                x2, y2 = min(img_w - 1, b.x2), min(img_h - 1, b.y2)
                text_region_mask[y1:y2, x1:x2] = 255

        structural_ink = cv2.bitwise_and(ink_mask, cv2.bitwise_not(text_region_mask))
        text_ink       = cv2.bitwise_and(ink_mask, text_region_mask)
        capped_t = min(thickness, 3)
        if capped_t > 1:
            kernel = np.ones((capped_t - 1, capped_t - 1), np.uint8)
            structural_ink = cv2.dilate(structural_ink, kernel, iterations=1)
        final_mask = cv2.bitwise_or(structural_ink, text_ink)
        ink_mask_3ch = cv2.cvtColor(final_mask, cv2.COLOR_GRAY2BGR)
        result = np.where(ink_mask_3ch > 0, ink_layer, img).astype(np.uint8)

        if s["warp"]:
            result = augment_perspective_warp(result, max_offset_frac=0.12)

        out_path = os.path.join(output_dir, "preview", f"{s['label']}.png")
        cv2.imwrite(out_path, result)
        print(f"  Saved: {out_path}")


def generate_v2_dataset(output_dir: str, total_count: int = 1000, seed: int = 99):
    random.seed(seed)
    np.random.seed(seed)

    for split in ["train", "val"]:
        os.makedirs(os.path.join(output_dir, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, split, "labels"), exist_ok=True)

    val_count   = max(1, total_count // 5)
    train_count = total_count - val_count
    splits      = ["train"] * train_count + ["val"] * val_count
    random.shuffle(splits)

    archetypes = [
        generate_three_tier_web_app,
        generate_microservices,
        generate_data_pipeline,
    ]

    for idx in range(total_count):
        split        = splits[idx]
        arch_fn      = archetypes[idx % len(archetypes)]
        img_w, img_h = random.choice(IMG_SIZES)

        img, bboxes = generate_augmented_image(arch_fn, img_w, img_h)

        for b in bboxes:
            b.x1 = max(0, min(b.x1, img_w - 1))
            b.y1 = max(0, min(b.y1, img_h - 1))
            b.x2 = max(b.x1 + 1, min(b.x2, img_w))
            b.y2 = max(b.y1 + 1, min(b.y2, img_h))

        valid_bboxes = [b for b in bboxes if b.w > 3 and b.h > 3]

        name     = f"augv2_{idx:04d}"
        cv2.imwrite(os.path.join(output_dir, split, "images", f"{name}.png"), img)
        save_yolo_annotations(
            valid_bboxes,
            os.path.join(output_dir, split, "labels", f"{name}.txt"),
            img_w, img_h
        )

        if idx % 100 == 0:
            print(f"  [{idx}/{total_count}] split={split}")

    print(f"\nDone! {total_count} images in {output_dir}")
    print("\nMerge with original dataset:")
    print("  cp -r data/synthetic_dataset/train/images/* data/synthetic_dataset_v2/train/images/")
    print("  cp -r data/synthetic_dataset/train/labels/* data/synthetic_dataset_v2/train/labels/")
    print("  cp -r data/synthetic_dataset/val/images/*   data/synthetic_dataset_v2/val/images/")
    print("  cp -r data/synthetic_dataset/val/labels/*   data/synthetic_dataset_v2/val/labels/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",       type=str,  default="data/synthetic_dataset_v2")
    parser.add_argument("--count",        type=int,  default=1000)
    parser.add_argument("--seed",         type=int,  default=99)
    parser.add_argument("--preview-only", action="store_true",
                        help="Generate 9 preview samples only — inspect before full run")
    args = parser.parse_args()

    if args.preview_only:
        print("Generating 9 preview samples...")
        generate_preview_samples(args.output)
        print(f"\nInspect images at: {args.output}/preview/")
    else:
        print("Generating 9 preview samples first...")
        generate_preview_samples(args.output)
        print(f"\nPreview at: {args.output}/preview/ — proceeding with full generation...\n")
        generate_v2_dataset(args.output, args.count, args.seed)


if __name__ == "__main__":
    main()
