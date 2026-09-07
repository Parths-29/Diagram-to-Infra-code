# Diagram-to-Infra-Code

Convert hand-drawn architecture diagrams into deployable Terraform code.

Upload a photo of a whiteboard sketch → get `terraform validate`-passing `.tf` files for AWS.

## Architecture

```
[Photo Upload] → Preprocessing (OpenCV) → Object Detection (YOLOv8n)
    → OCR (EasyOCR) → Relationship Extraction (rule-based)
    → JSON Diagram Spec → Clarifying Q&A → Terraform Generation (Jinja2)
    → terraform validate (Docker sandbox) → Download .tf ZIP
```

## Tech Stack

| Layer | Technology |
|---|---|
| Object Detection | YOLOv8n (custom-trained on synthetic data) |
| OCR | EasyOCR |
| Preprocessing | OpenCV |
| Code Generation | Jinja2 templates |
| Backend | FastAPI (Python 3.11) |
| Frontend | React + TypeScript + Vite + Tailwind (UI shell pending Phase 6 backend wiring) |
| Validation | Terraform CLI in Docker sandbox |
| Training | Google Colab (GPU) |

## Supported Components (v1 — AWS only)

| Diagram Element | Terraform Resource |
|---|---|
| Compute (EC2) | `aws_instance` |
| Compute (EKS) | `aws_eks_cluster` + node group |
| Database (RDS) | `aws_db_instance` |
| Storage (S3) | `aws_s3_bucket` |
| Load Balancer (ALB) | `aws_lb` + `aws_lb_target_group` |
| Network (VPC) | `aws_vpc` + `aws_subnet` |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional — for terraform validation)

### Run with Docker Compose
```bash
docker-compose up --build
```
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

### Run Manually
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
/backend            FastAPI app
  /ml               ML pipeline (detection, OCR, relationships)
  /generator        Terraform code generation + validation
  /tests            Backend tests
/frontend           React + TS + Vite app
/ml                 Training scripts & Colab notebooks
/data               Synthetic dataset generator
/infra              Dockerfiles, docker-compose
```

## Phase Roadmap

| Phase | Deliverable | Status | Needs GPU? |
|---|---|---|---|
| 0 | Repo scaffold, Docker, CI skeleton | ✅ | No |
| 1 | Synthetic dataset generator & annotation verifier (`data/verify_annotations.py`) | ✅ | No |
| 2 | YOLOv8n training on synthetic set | ⏳ | Yes — Colab |
| 3 | Real eval set integration | ⬜ | Yes — Colab |
| 4 | OCR + rule-based relationship extraction | ⬜ | No |
| 5 | Terraform template generation + validate | ⬜ | No |
| 6 | FastAPI backend + React frontend | ⬜ | No |
| 7 | Docs, demo, polish | ⬜ | No |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/analyze` | Upload image, get diagram spec with ambiguities |
| POST | `/clarify` | Submit answers to ambiguity questions |
| POST | `/generate` | Generate Terraform from refined spec |
| GET | `/download/{id}` | Download .tf files as ZIP |

## Training

Training runs on Google Colab. See `ml/notebooks/train_yolov8.ipynb` for the training notebook. Trained weights are hosted on Hugging Face Hub at `parths-29/diagram-to-infra-yolov8n`.

## License

MIT
