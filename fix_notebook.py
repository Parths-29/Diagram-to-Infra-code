import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

nb = new_notebook()

nb.cells = [
    new_markdown_cell(
        "# Phase 2: YOLOv8n Training Notebook — Diagram-to-Infra-Code\n\n"
        "This notebook trains a custom **YOLOv8n** object detection model on synthetic architecture diagram data.\n\n"
        "### Target Classes (7 total):\n"
        "1. `compute` (EC2, EKS)\n"
        "2. `database` (RDS)\n"
        "3. `storage` (S3)\n"
        "4. `load_balancer` (ALB)\n"
        "5. `network` (VPC/Subnet boundary)\n"
        "6. `arrow` (directional connection)\n"
        "7. `text_label` (label box text)\n\n"
        "Run this notebook on Google Colab with GPU acceleration enabled (**Runtime -> Change runtime type -> T4 GPU**)."
    ),
    new_markdown_cell(
        "## Setup & Resume Instructions\n\n"
        "**If you disconnect during training:**\n"
        "1. Re-run Steps 1, 2, and 3 to setup the environment and dataset.\n"
        "2. **Skip Step 4 (Original Training Cell)**.\n"
        "3. **Run Step 4b (Resume Cell)** to continue training from your Google Drive checkpoint."
    ),
    new_markdown_cell("## Step 1: GPU Check, Environment Setup & Mount Drive\nWe mount Google Drive so checkpoints survive runtime disconnects."),
    new_code_cell(
        "!nvidia-smi\n"
        "!pip install -q ultralytics huggingface_hub opencv-python-headless albumentations pillow\n\n"
        "from google.colab import drive\n"
        "drive.mount('/content/drive')"
    ),
    new_markdown_cell("## Step 2: Clone Repository"),
    new_code_cell(
        "!git clone https://github.com/Parths-29/Diagram-to-Infra-code.git\n"
        "%cd Diagram-to-Infra-code"
    ),
    new_markdown_cell("## Step 3: Generate Dataset"),
    new_code_cell(
        "# Generate 500 unique diagrams + 1 copy = 1,000 total images\n"
        "!python3 data/generate_synthetic.py --output data/synthetic_dataset --count 500 --augmented-copies 1 --seed 42"
    ),
    new_markdown_cell(
        "## Step 4: Run YOLOv8n Training (Original Run)\n\n"
        "Explicit augmentation kwargs:\n"
        "- `fliplr=0.0` and `flipud=0.0` (disabled horizontal/vertical flips to preserve text & arrow orientation)\n"
        "- `degrees=10.0`, `translate=0.1`, `scale=0.2`, `mosaic=0.5`, `mixup=0.1`\n\n"
        "**Checkpoints are saved to Google Drive:** `/content/drive/MyDrive/diagram-to-infra-runs`"
    ),
    new_code_cell(
        "!python3 ml/train.py --data data/dataset.yaml --epochs 50 --batch 16 --imgsz 640 \\\n"
        "    --weights-out ml/weights --eval-out ml/eval_samples \\\n"
        "    --project /content/drive/MyDrive/diagram-to-infra-runs --name train --patience 10"
    ),
    new_markdown_cell(
        "## Step 4b: Resume Training (Use if Disconnected)\n"
        "If Colab disconnected, uncomment and run this cell *instead* of Step 4 above to resume from your last checkpoint."
    ),
    new_code_cell(
        "# from ultralytics import YOLO\n"
        "# YOLO('/content/drive/MyDrive/diagram-to-infra-runs/train/weights/last.pt').train(resume=True)"
    ),
    new_markdown_cell("## Step 5: Display Training Results & Visual Evaluation Samples"),
    new_code_cell(
        "from IPython.display import Image, display\n"
        "import glob\n\n"
        "print(\"=== Training Confusion Matrix ===\")\n"
        "display(Image(filename=\"/content/drive/MyDrive/diagram-to-infra-runs/train/confusion_matrix.png\"))\n\n"
        "print(\"=== Results Curves ===\")\n"
        "display(Image(filename=\"/content/drive/MyDrive/diagram-to-infra-runs/train/results.png\"))\n\n"
        "print(\"=== Sample Visual Predictions (from ml/eval_samples/) ===\")\n"
        "eval_images = glob.glob(\"ml/eval_samples/*.png\")[:5]\n"
        "for img_path in eval_images:\n"
        "    display(Image(filename=img_path))"
    ),
    new_markdown_cell("## Step 6: (Optional) Push Trained Weights to Hugging Face Hub"),
    new_code_cell(
        "import os\n"
        "from huggingface_hub import HfApi\n\n"
        "# Set your HF_TOKEN here if pushing to HF Hub:\n"
        "HF_TOKEN = \"\"  # e.g., \"hf_...\"\n"
        "REPO_ID = \"parths-29/diagram-to-infra-yolov8n\"\n\n"
        "if HF_TOKEN:\n"
        "    api = HfApi()\n"
        "    api.create_repo(repo_id=REPO_ID, exist_ok=True, token=HF_TOKEN)\n"
        "    api.upload_file(\n"
        "        path_or_fileobj=\"/content/drive/MyDrive/diagram-to-infra-runs/train/weights/best.pt\",\n"
        "        path_in_repo=\"best.pt\",\n"
        "        repo_id=REPO_ID,\n"
        "        token=HF_TOKEN\n"
        "    )\n"
        "    print(f\"Uploaded best.pt to https://huggingface.co/{REPO_ID}\")\n"
        "else:\n"
        "    print(\"No HF_TOKEN provided. Weights are saved in Drive at /content/drive/MyDrive/diagram-to-infra-runs/train/weights/best.pt\")"
    )
]

with open('ml/notebooks/train_yolov8.ipynb', 'w') as f:
    nbformat.write(nb, f)
