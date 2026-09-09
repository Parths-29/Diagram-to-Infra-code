"""
Diagram Analysis Pipeline.

Single-call orchestrator: image in → DiagramSpec out.

Ties together:
1. Object Detection (YOLOv8n) → bounding boxes for 7 classes
2. OCR (EasyOCR) → text extraction from text_label boxes
3. Graph Solver → arrow resolution, VPC containment, DiagramSpec
"""

from typing import Optional
import numpy as np

from backend.ml.detector import DiagramObjectDetector, DetectionResult
from backend.ml.ocr import DiagramOCR
from backend.ml.graph_solver import GraphSolver, DiagramSpec


class DiagramAnalysisPipeline:
    """
    End-to-end pipeline for analyzing architecture diagram images.

    Usage:
        pipeline = DiagramAnalysisPipeline()
        spec = pipeline.analyze(image)
        print(spec.to_dict())
    """

    def __init__(
        self,
        detector: Optional[DiagramObjectDetector] = None,
        ocr: Optional[DiagramOCR] = None,
        graph_solver: Optional[GraphSolver] = None,
        conf_threshold: float = 0.25,
    ):
        """
        Initialize the pipeline with optional pre-configured components.

        Args:
            detector: Custom DiagramObjectDetector instance (lazy-created if None)
            ocr: Custom DiagramOCR instance (lazy-created if None)
            graph_solver: Custom GraphSolver instance (lazy-created if None)
            conf_threshold: Minimum confidence for YOLO detections
        """
        self._detector = detector
        self._ocr = ocr
        self._graph_solver = graph_solver
        self._conf_threshold = conf_threshold

    @property
    def detector(self) -> DiagramObjectDetector:
        if self._detector is None:
            self._detector = DiagramObjectDetector(conf_threshold=self._conf_threshold)
        return self._detector

    @property
    def ocr(self) -> DiagramOCR:
        if self._ocr is None:
            self._ocr = DiagramOCR()
        return self._ocr

    @property
    def graph_solver(self) -> GraphSolver:
        if self._graph_solver is None:
            self._graph_solver = GraphSolver()
        return self._graph_solver

    def analyze(self, image: np.ndarray) -> DiagramSpec:
        """
        Run the full analysis pipeline on an architecture diagram image.

        Args:
            image: BGR numpy array of the diagram photo

        Returns:
            DiagramSpec containing nodes, edges, and ambiguity questions
        """
        # Step 1: Object Detection
        detections = self.detector.detect(image)

        # Step 2: OCR — extract text from text_label boxes
        labels = self.ocr.extract_labels(image, detections)

        # Step 3: Associate labels with components
        label_associations = self.ocr.associate_labels_to_components(labels, detections)

        # Step 4: Build architecture graph
        spec = self.graph_solver.solve(detections, label_associations)

        return spec
