import io
import cv2
import numpy as np
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

# Load env variables (HF_TOKEN) early
from dotenv import load_dotenv
load_dotenv()

from backend.ml.pipeline import DiagramAnalysisPipeline
from backend.ml.graph_solver import DiagramSpec, DiagramNode, DiagramEdge
from backend.generator.engine import TerraformGenerator

app = FastAPI(
    title="Diagram-to-Infra-Code",
    description="Convert hand-drawn architecture diagrams to Terraform code",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded pipeline and generator so they don't block API startup
_pipeline: DiagramAnalysisPipeline = None
_generator: TerraformGenerator = None

def get_pipeline() -> DiagramAnalysisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DiagramAnalysisPipeline(conf_threshold=0.60)
    return _pipeline

def get_generator() -> TerraformGenerator:
    global _generator
    if _generator is None:
        _generator = TerraformGenerator()
    return _generator


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/analyze")
async def analyze_diagram(image: UploadFile = File(...)):
    """
    Upload an image of an architecture diagram and get back a structured JSON spec.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        # Read image bytes
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Could not decode image.")

        # Run pipeline
        pipeline = get_pipeline()
        spec = pipeline.analyze(img)
        
        return {"spec": spec.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_class=PlainTextResponse)
async def generate_terraform(payload: Dict[str, Any]):
    """
    Takes a JSON representation of a DiagramSpec and returns Terraform code.
    """
    try:
        spec_data = payload.get("spec")
        if not spec_data:
            raise HTTPException(status_code=400, detail="Missing 'spec' payload.")
            
        # Reconstruct DiagramSpec from dict
        nodes = []
        for n in spec_data.get("nodes", []):
            nodes.append(DiagramNode(**n))
            
        edges = []
        for e in spec_data.get("edges", []):
            edges.append(DiagramEdge(**e))
            
        ambiguities = spec_data.get("ambiguities", [])
        
        spec = DiagramSpec(nodes=nodes, edges=edges, ambiguities=ambiguities)
        
        # Run generator
        generator = get_generator()
        tf_code = generator.generate(spec)
        
        return tf_code
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
