"""
YOLOv8 Retrain Script — v2 Augmented Dataset
=============================================
Run this in Google Colab after uploading the merged dataset.

Steps:
  1. Install dependencies
  2. Upload merged dataset (zip of synthetic_dataset_v2/) to /content/synthetic_dataset_v2
  3. Upload original v1 val set (synthetic_dataset/val/) to /content/synthetic_dataset_v1_val
     *This is MANDATORY for Metric 2.*
  4. Run this script
  5. Download best.pt and replace ml/weights/best.pt
"""

# ── 1. Install ────────────────────────────────────────────────────────────────
# !pip install ultralytics --quiet

# ── 2. Imports ────────────────────────────────────────────────────────────────
import os, yaml, shutil, glob
from pathlib import Path
from ultralytics import YOLO

# ── 3. Dataset YAML ───────────────────────────────────────────────────────────
DATASET_ROOT = "/content/synthetic_dataset_v2"   # adjust if unzipped elsewhere

dataset_yaml = {
    "path": DATASET_ROOT,
    "train": "train/images",
    "val":   "val/images",
    "nc": 7,
    "names": [
        "compute",       # 0
        "database",      # 1
        "storage",       # 2
        "load_balancer", # 3
        "network",       # 4
        "arrow",         # 5
        "text_label",    # 6
    ],
}

yaml_path = "/content/dataset_v2.yaml"
with open(yaml_path, "w") as f:
    yaml.dump(dataset_yaml, f, default_flow_style=False)
print(f"Dataset YAML written to {yaml_path}")

# ── 4. Train ──────────────────────────────────────────────────────────────────
# Start from the v1 best.pt weights (fine-tune, don't train from scratch)
# Upload your existing best.pt to /content/best_v1.pt before running.
# 
# IMPORTANT: Double augmentation risk (Mosaic + Perspective)
# Before kicking off the full 50-epoch run, dump and visually inspect 5-10 actual training
# batches as Ultralytics sees them mid-run (check train_batch0.jpg etc. in the run folder).
# I want to confirm the mosaic + double-perspective combination isn't producing garbage-looking
# training images before we spend the full epoch budget on it.
# If it looks bad, drop Ultralytics' runtime perspective to 0 and keep degrees low, since
# our own generator already covers that augmentation axis.

V1_WEIGHTS = "/content/best_v1.pt"  # set to "yolov8n.pt" to train from scratch

model = YOLO(V1_WEIGHTS if os.path.exists(V1_WEIGHTS) else "yolov8n.pt")

results = model.train(
    data=yaml_path,
    epochs=50,           # Fewer epochs since we're fine-tuning from v1
    imgsz=640,
    batch=16,
    patience=15,         # Early stop if no improvement for 15 epochs
    lr0=0.001,           # Lower LR for fine-tuning (was 0.01 for scratch)
    lrf=0.01,
    warmup_epochs=3,
    mosaic=1.0,
    degrees=15.0,        # Extra rotation augmentation at train time
    perspective=0.001,   # Ultralytics built-in perspective augmentation
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    name="diagram_v2",
    project="/content/runs",
    save=True,
    exist_ok=True,
    device=0,            # GPU — change to "cpu" if no GPU available
)

print("\n=== Training complete ===")
best_pt = "/content/runs/diagram_v2/weights/best.pt"
print(f"Best weights: {best_pt}")

# ── 5. Evaluate — three metrics ───────────────────────────────────────────────
# Metric 1: Full v2 val set (includes augmented images — regression check)
print("\n=== Metric 1: v2 val set (400 images total, blended) ===")
m1 = model.val(data=yaml_path, split="val")
map50_v2    = m1.box.map50
map5095_v2  = m1.box.map
print(f"  mAP50:    {map50_v2:.4f}")
print(f"  mAP50-95: {map5095_v2:.4f}")

# Per-class breakdown
print("\n  Per-class mAP50:")
class_names = dataset_yaml["names"]
for i, name in enumerate(class_names):
    try:
        cls_map = m1.box.maps[i]
        print(f"    {name:<15}: {cls_map:.4f}")
    except Exception:
        print(f"    {name:<15}: N/A")

# Metric 2: Original v1 val set (clean white-paper — regression check)
# Upload `synthetic_dataset_v1_val` as part of the same Colab session before training starts, 
# not as an afterthought. This is MANDATORY. Confirm the upload and the path before you hit run.
V1_VAL_ROOT = "/content/synthetic_dataset_v1_val"
assert os.path.exists(V1_VAL_ROOT), f"ERROR: v1 val set not found at {V1_VAL_ROOT}. Please upload synthetic_dataset/val/ as synthetic_dataset_v1_val/ before running!"

v1_yaml = {
    "path": V1_VAL_ROOT,
    "train": "train/images",   # unused
    "val":   "images",         # flat val folder
    "nc": 7,
    "names": class_names,
}
v1_yaml_path = "/content/dataset_v1_val_only.yaml"
with open(v1_yaml_path, "w") as f:
    yaml.dump(v1_yaml, f)

print("\n=== Metric 2: v1 original val set (200 clean white-paper images) ===")
m2 = model.val(data=v1_yaml_path, split="val")
map50_v1   = m2.box.map50
map5095_v1 = m2.box.map
print(f"  mAP50:    {map50_v1:.4f}  (was 0.977 before retrain — check for regression)")
print(f"  mAP50-95: {map5095_v1:.4f}")

# Metric 3: v2-only val set (only the 200 new augmented images)
v2_only_txt = "/content/v2_only_val.txt"
with open(v2_only_txt, "w") as f:
    for img_path in glob.glob(f"{DATASET_ROOT}/val/images/augv2_*.png"):
        f.write(f"{img_path}\n")

v2_only_yaml = {
    "path": DATASET_ROOT,
    "train": "train/images",
    "val": v2_only_txt,
    "nc": 7,
    "names": class_names,
}
v2_only_yaml_path = "/content/dataset_v2_only_val.yaml"
with open(v2_only_yaml_path, "w") as f:
    yaml.dump(v2_only_yaml, f)

print("\n=== Metric 3: v2-only val set (200 hard/augmented images) ===")
m3 = model.val(data=v2_only_yaml_path, split="val")
map50_v2_only   = m3.box.map50
map5095_v2_only = m3.box.map
print(f"  mAP50:    {map50_v2_only:.4f}")
print(f"  mAP50-95: {map5095_v2_only:.4f}")

# ── 6. Download ───────────────────────────────────────────────────────────────
print("\n=== To download best.pt ===")
print("from google.colab import files")
print(f"files.download('{best_pt}')")
print("\nThen replace: ml/weights/best.pt in your local repo.")
