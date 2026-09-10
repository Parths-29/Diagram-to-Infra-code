import cv2
from backend.ml.detector import DiagramObjectDetector

img_path = "/Users/SHARMPX132/Downloads/Gemini_Generated_Image_k3ilzrk3ilzrk3il.png"
img = cv2.imread(img_path)

if img is None:
    print(f"Could not load {img_path}")
    exit(1)

# Run with very low confidence to see near-misses
det = DiagramObjectDetector(conf_threshold=0.05)
results = det.detect(img)

print(f"Total raw boxes detected at conf >= 0.05: {len(results)}")
results_sorted = sorted(results, key=lambda x: x.confidence, reverse=True)
for r in results_sorted:
    print(f"- Class: {r.class_name:<15} | Confidence: {r.confidence:.4f} | Bbox: {r.bbox}")
