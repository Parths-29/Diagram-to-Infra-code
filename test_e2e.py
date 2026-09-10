import os
import cv2
import json
import subprocess
from dotenv import load_dotenv

# Load HF_TOKEN from .env
load_dotenv()

from backend.ml.pipeline import DiagramAnalysisPipeline
from backend.generator.engine import TerraformGenerator

def main():
    image_path = "data/real_eval/images/Media (11).jpeg"
    if not os.path.exists(image_path):
        print(f"Error: Could not find test image at {image_path}")
        return

    # Load image
    img = cv2.imread(image_path)
    
    print("1. Running Diagram Analysis Pipeline (ML)...")
    try:
        # Initialize pipeline (loads YOLO and EasyOCR)
        pipeline = DiagramAnalysisPipeline(conf_threshold=0.45)
        spec = pipeline.analyze(img)
        print("\n--- Extracted DiagramSpec (JSON) ---")
        print(json.dumps(spec.to_dict(), indent=2))
        
        print("\n2. Running Terraform Generator (Templates)...")
        generator = TerraformGenerator()
        tf_code = generator.generate(spec)

        out_dir = "data/tf_e2e"
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "main.tf")
        with open(out_file, "w") as f:
            f.write(tf_code)
            
        with open(os.path.join(out_dir, "provider.tf"), "w") as f:
            f.write('provider "aws" { region = "us-east-1" }\n')
            
        print(f"Generated Terraform code saved to {out_file}")
        
        print("\n3. Validating Generated Terraform...")
        subprocess.run(
            ["../../bin/terraform", "init"], 
            cwd=out_dir, 
            check=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        result = subprocess.run(
            ["../../bin/terraform", "validate"], 
            cwd=out_dir, 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print("✅ End-to-End Validation PASSED")
        else:
            print(f"❌ Validation FAILED:\n{result.stderr}")
            
    except Exception as e:
        print(f"Error during E2E test: {e}")

if __name__ == "__main__":
    main()
