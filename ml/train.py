"""
YOLOv8n Training & Evaluation Script.

Trains custom YOLOv8n object detection model on synthetic architecture diagram dataset.

Hyperparameters:
- epochs: 50
- imgsz: 640
- batch: 16
- lr0: 0.01 (AdamW)
- Augmentations:
  - degrees: 10.0
  - translate: 0.1
  - scale: 0.2
  - mosaic: 0.5
  - mixup: 0.1
  - fliplr: 0.0 (DISABLED — text and arrow direction must be preserved)
  - flipud: 0.0 (DISABLED — cloud flow direction must be preserved)

Post-training:
- Logs mAP50, mAP50-95, per-class precision/recall metrics.
- Saves 10-15 validation detection samples to ml/eval_samples/.
- Optionally pushes model to Hugging Face Hub (parths-29/diagram-to-infra-yolov8n).
"""

import argparse
import os
import random
import sys
from pathlib import Path
import cv2
import torch
from ultralytics import YOLO

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CLASS_NAMES = [
    "compute",
    "database",
    "storage",
    "load_balancer",
    "network",
    "arrow",
    "text_label"
]

CLASS_COLORS = {
    0: (0, 204, 102),     # compute - green
    1: (255, 128, 0),     # database - orange
    2: (204, 0, 204),     # storage - purple
    3: (255, 204, 0),     # load_balancer - yellow
    4: (255, 51, 204),    # network - pink
    5: (0, 0, 255),       # arrow - red
    6: (255, 0, 0)        # text_label - blue
}

def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLOv8n model on diagram dataset")
    parser.add_argument("--data", type=str, default="data/dataset.yaml", help="Path to dataset.yaml")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--weights-out", type=str, default="ml/weights", help="Directory to save final model weights")
    parser.add_argument("--eval-out", type=str, default="ml/eval_samples", help="Directory to save eval samples")
    parser.add_argument("--hf-repo", type=str, default="parths-29/diagram-to-infra-yolov8n", help="Hugging Face repo ID")
    parser.add_argument("--hf-token", type=str, default=os.getenv("HF_TOKEN"), help="Hugging Face API token")
    return parser.parse_args()

def generate_eval_samples(model: YOLO, val_images_dir: str, output_dir: str, num_samples: int = 15):
    """Run model inference on validation images and save visual detection overlays."""
    val_path = Path(val_images_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if not val_path.exists():
        print(f"Validation images directory not found: {val_path}")
        return

    images = list(val_path.glob("*.png")) + list(val_path.glob("*.jpg"))
    if not images:
        print(f"No images found in {val_path}")
        return

    selected_images = random.sample(images, min(num_samples, len(images)))
    print(f"\nGenerating visual evaluation samples in {out_path}...")

    for img_path in selected_images:
        results = model.predict(source=str(img_path), conf=0.25, save=False, verbose=False)
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy

                color = CLASS_COLORS.get(cls_id, (0, 255, 0))
                cls_name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"cls_{cls_id}"

                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

                # Draw label banner
                label = f"{cls_name} {conf:.2f}"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(img, (x1, max(0, y1 - 20)), (x1 + w, y1), color, -1)
                cv2.putText(img, label, (x1, max(12, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        out_file = out_path / f"eval_{img_path.name}"
        cv2.imwrite(str(out_file), img)
        print(f"  ✓ Saved {out_file.name}")

def push_to_huggingface(weights_path: str, repo_id: str, token: str):
    """Optionally push trained best.pt weights to Hugging Face Hub."""
    if not token:
        print("\n[HF Hub] No HF_TOKEN provided. Skipping Hugging Face upload.")
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi()
        print(f"\n[HF Hub] Uploading {weights_path} to {repo_id}...")
        api.create_repo(repo_id=repo_id, exist_ok=True, token=token)
        api.upload_file(
            path_or_fileobj=weights_path,
            path_in_repo="best.pt",
            repo_id=repo_id,
            token=token
        )
        print(f"[HF Hub] Successfully uploaded weights to https://huggingface.co/{repo_id}")
    except Exception as e:
        print(f"[HF Hub] Upload warning (non-fatal): {e}")

def main():
    args = parse_args()
    print("=== Phase 2: YOLOv8n Diagram Model Training ===")
    print(f"Dataset config : {args.data}")
    print(f"Epochs         : {args.epochs}")
    print(f"Batch size     : {args.batch}")
    print(f"Image size     : {args.imgsz}")

    # Initialize pretrained YOLOv8n architecture backbone
    model = YOLO("yolov8n.pt")

    # Explicit augmentation kwargs as specified
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        optimizer="AdamW",
        lr0=0.01,
        degrees=10.0,
        translate=0.1,
        scale=0.2,
        mosaic=0.5,
        mixup=0.1,
        fliplr=0.0,   # Preserves text & arrow left-to-right orientation
        flipud=0.0,   # Preserves top-to-bottom architecture flow
        project="runs/detect",
        name="diagram_yolov8n",
        exist_ok=True
    )

    print("\n=== Training Completed ===")
    
    # Validation evaluation
    val_metrics = model.val()
    print("\n── Final Validation Metrics ──")
    print(f"  mAP50    : {val_metrics.box.map50:.4f}")
    print(f"  mAP50-95 : {val_metrics.box.map:.4f}")

    # Ensure output weights directory exists and copy best.pt
    weights_dir = Path(args.weights_out)
    weights_dir.mkdir(parents=True, exist_ok=True)
    best_weights_src = Path("runs/detect/diagram_yolov8n/weights/best.pt")
    best_weights_dst = weights_dir / "best.pt"

    if best_weights_src.exists():
        import shutil
        shutil.copy(str(best_weights_src), str(best_weights_dst))
        print(f"Saved best weights to {best_weights_dst}")

    # Generate 10-15 visual eval samples
    val_img_dir = "data/synthetic_dataset/val/images"
    generate_eval_samples(model, val_img_dir, args.eval_out, num_samples=15)

    # Push to Hugging Face if configured
    if best_weights_dst.exists():
        push_to_huggingface(str(best_weights_dst), args.hf_repo, args.hf_token)

if __name__ == "__main__":
    main()
