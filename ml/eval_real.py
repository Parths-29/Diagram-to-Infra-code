import os
import cv2
import sys
from pathlib import Path

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ml.detector import DiagramObjectDetector

def main():
    detector = DiagramObjectDetector()

    input_dir = Path("data/real_eval/images")
    output_dir = Path("data/real_eval/results")
    
    if not input_dir.exists():
        print(f"Error: {input_dir} does not exist.")
        return
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    images = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpeg"))
    
    if not images:
        print(f"No images found in {input_dir}. Please place your photos there.")
        return
        
    print(f"Found {len(images)} images for real-world evaluation.")
    
    for img_path in images:
        print(f"Processing {img_path.name}...")
        
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"  Failed to load {img_path.name}")
            continue
            
        # Run inference
        results = detector.detect(img)
        
        # Draw bounding boxes
        annotated_img = detector.draw_detections(img, results)
        
        # Save output
        out_path = output_dir / f"eval_{img_path.name}"
        cv2.imwrite(str(out_path), annotated_img)
        print(f"  Saved to {out_path}")

    print("\nVisual evaluation complete! Check data/real_eval/results/ to review bounding boxes.")

if __name__ == "__main__":
    main()
