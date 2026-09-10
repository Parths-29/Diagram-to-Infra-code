import os
import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

def main():
    model_path = "ml/weights/best.pt"
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return

    model = YOLO(model_path)
    
    # Path to the complex image with 62 detections
    img_path = "data/real_eval/images/Media (11).jpeg"
    if not os.path.exists(img_path):
        print(f"Error: Image not found at {img_path}")
        return

    # IoU thresholds to test
    ious = [0.7, 0.6, 0.5, 0.45, 0.4, 0.35, 0.3]
    
    # Run inferences
    results_by_iou = {}
    for iou in ious:
        # We keep confidence at 0.45 this time, since that's what we'll likely use in prod
        res = model.predict(source=img_path, conf=0.45, iou=iou, save=False, verbose=False)
        results_by_iou[iou] = res[0]
        num_boxes = len(res[0].boxes)
        print(f"IoU {iou}: {num_boxes} detections")

    # Plot results
    cols = len(ious)
    fig, axes = plt.subplots(1, cols, figsize=(4 * cols, 4))
    
    for i, (iou, res) in enumerate(results_by_iou.items()):
        # Ultralytics plot() returns BGR image as numpy array
        img_bgr = res.plot(line_width=2, font_size=1)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        axes[i].imshow(img_rgb)
        axes[i].set_title(f"IoU: {iou}\nBoxes: {len(res.boxes)}", fontsize=12)
        axes[i].axis("off")
        
    plt.tight_layout()
    out_path = "data/real_eval/iou_test_grid.png"
    plt.savefig(out_path, dpi=200)
    print(f"\nSaved comparison grid to {out_path}")

if __name__ == "__main__":
    main()
