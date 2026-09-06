"""
Diagram-to-Infra-Code — FastAPI Backend

Converts photos of hand-drawn architecture diagrams into Terraform code.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


# Route stubs — implemented in Phase 6
# POST /analyze    — upload image, run ML pipeline
# POST /clarify    — submit answers to ambiguity questions
# POST /generate   — generate Terraform from refined spec
# GET  /download/  — download .tf files as ZIP
