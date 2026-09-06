"""
Bounding-box verification script.

Overlays YOLO annotations back onto sample images so you can visually confirm
that boxes line up correctly — especially for arrow and text_label classes.

Also reports per-class instance counts across the full dataset.

Usage:
    python3 data/verify_annotations.py
"""

import os
import random
import sys
from pathlib import Path
from collections import Counter

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.utils import CLASS_NAMES

# Colors per class (BGR for OpenCV)
CLASS_COLORS = {
    0: (0, 200, 0),      # compute — green
    1: (0, 140, 255),     # database — orange
    2: (255, 200, 0),     # storage — cyan
    3: (0, 255, 255),     # load_balancer — yellow
    4: (255, 0, 255),     # network — magenta
    5: (0, 0, 255),       # arrow — red
    6: (255, 0, 0),       # text_label — blue
}


def draw_yolo_boxes(img_path: str, label_path: str) -> np.ndarray:
    """Load image, parse YOLO labels, draw boxes. Return annotated image."""
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {img_path}")

    h, w = img.shape[:2]

    if not os.path.exists(label_path):
        return img

    with open(label_path) as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            continue

        class_id = int(parts[0])
        cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])

        # Denormalize
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)

        color = CLASS_COLORS.get(class_id, (128, 128, 128))
        thickness = 2

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        # Label
        label = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else str(class_id)
        label_size, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
        cv2.rectangle(img, (x1, y1 - label_size[1] - 4), (x1 + label_size[0] + 2, y1), color, -1)
        cv2.putText(img, label, (x1 + 1, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                    (255, 255, 255), 1, cv2.LINE_AA)

    return img


def count_classes(dataset_dir: str) -> Counter:
    """Count per-class instances across all label files."""
    counts: Counter = Counter()
    for split in ["train", "val"]:
        labels_dir = os.path.join(dataset_dir, split, "labels")
        if not os.path.exists(labels_dir):
            continue
        for label_file in os.listdir(labels_dir):
            if not label_file.endswith(".txt"):
                continue
            with open(os.path.join(labels_dir, label_file)) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        counts[int(parts[0])] += 1
    return counts


def main():
    dataset_dir = "data/synthetic_dataset"
    output_dir = "data/bbox_verification"
    num_samples = 15

    os.makedirs(output_dir, exist_ok=True)

    # ── Collect all image paths ──
    all_images = []
    for split in ["train", "val"]:
        img_dir = os.path.join(dataset_dir, split, "images")
        if not os.path.exists(img_dir):
            continue
        for fname in os.listdir(img_dir):
            if fname.endswith((".png", ".jpg")):
                all_images.append((split, fname))

    if not all_images:
        print("ERROR: No images found in dataset.")
        return

    # ── Sample: mix of clean and augmented ──
    clean = [(s, f) for s, f in all_images if "_aug" not in f]
    augmented = [(s, f) for s, f in all_images if "_aug" in f]

    random.seed(42)
    # 8 clean + 7 augmented (or whatever's available)
    n_clean = min(8, len(clean))
    n_aug = min(num_samples - n_clean, len(augmented))
    samples = random.sample(clean, n_clean) + random.sample(augmented, n_aug)
    random.shuffle(samples)

    print(f"Drawing bboxes on {len(samples)} sample images...\n")

    for split, fname in samples:
        img_path = os.path.join(dataset_dir, split, "images", fname)
        label_path = os.path.join(dataset_dir, split, "labels",
                                   fname.rsplit(".", 1)[0] + ".txt")

        annotated = draw_yolo_boxes(img_path, label_path)
        out_path = os.path.join(output_dir, f"{split}_{fname}")
        cv2.imwrite(out_path, annotated)
        print(f"  ✓ {out_path}")

    # ── Per-class counts ──
    print("\n── Per-class instance counts across full dataset ──\n")
    counts = count_classes(dataset_dir)
    total = sum(counts.values())

    print(f"  {'Class':<20} {'ID':>4} {'Count':>8} {'Pct':>7}")
    print(f"  {'─'*20} {'─'*4} {'─'*8} {'─'*7}")
    for class_id, name in enumerate(CLASS_NAMES):
        c = counts.get(class_id, 0)
        pct = (c / total * 100) if total > 0 else 0
        print(f"  {name:<20} {class_id:>4} {c:>8} {pct:>6.1f}%")
    print(f"  {'─'*20} {'─'*4} {'─'*8} {'─'*7}")
    print(f"  {'TOTAL':<20} {'':>4} {total:>8} {'100.0':>6}%")

    print(f"\nVerification images saved to: {output_dir}/")
    print("Inspect these to confirm bbox alignment, especially for arrows and text_labels.")


if __name__ == "__main__":
    main()
