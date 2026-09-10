import os
import cv2
import json
from backend.ml.pipeline import DiagramAnalysisPipeline

def main():
    image_path = "data/real_eval/images/Media (11).jpeg"
    if not os.path.exists(image_path):
        print(f"Error: Could not find test image at {image_path}")
        return

    # Load image
    img = cv2.imread(image_path)
    
    # Initialize pipeline with conf=0.45 and default threshold for graph solver
    pipeline = DiagramAnalysisPipeline(conf_threshold=0.45)
    
    # Run analysis
    print("Running Diagram Analysis Pipeline...")
    try:
        spec = pipeline.analyze(img)
        print("Analysis complete! DiagramSpec JSON:")
        print(json.dumps(spec.to_dict(), indent=2))
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    main()
