"""
Tests for the DiagramAnalysisPipeline.

Tests the orchestrator with mocked detector and OCR to verify
the end-to-end flow without requiring trained weights.
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from backend.ml.detector import DetectionResult
from backend.ml.ocr import DiagramOCR, LabelResult
from backend.ml.graph_solver import GraphSolver, DiagramSpec
from backend.ml.pipeline import DiagramAnalysisPipeline


def _make_detection(class_name: str, bbox: list, confidence: float = 0.9) -> DetectionResult:
    class_ids = {
        "compute": 0, "database": 1, "storage": 2,
        "load_balancer": 3, "network": 4, "arrow": 5, "text_label": 6,
    }
    return DetectionResult(
        class_id=class_ids[class_name],
        class_name=class_name,
        confidence=confidence,
        bbox=bbox,
    )


class TestPipelineIntegration:
    """Test the full pipeline with mocked components."""

    def test_analyze_returns_diagram_spec(self):
        """Pipeline.analyze() should return a DiagramSpec."""
        # Create mock detector
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [
            _make_detection("compute", [50, 100, 150, 200]),
            _make_detection("database", [350, 100, 450, 200]),
            _make_detection("arrow", [160, 140, 340, 160]),
            _make_detection("text_label", [60, 80, 140, 100]),
            _make_detection("text_label", [360, 80, 440, 100]),
        ]

        # Create mock OCR
        mock_ocr = MagicMock(spec=DiagramOCR)
        mock_ocr.extract_labels.return_value = [
            LabelResult(text="Web Server", confidence=0.85, bbox=[60, 80, 140, 100],
                        inferred_type="ec2", inferred_class="compute"),
            LabelResult(text="Users DB", confidence=0.9, bbox=[360, 80, 440, 100],
                        inferred_type="rds", inferred_class="database"),
        ]
        mock_ocr.associate_labels_to_components.return_value = {
            0: LabelResult(text="Web Server", confidence=0.85, bbox=[60, 80, 140, 100],
                           inferred_type="ec2", inferred_class="compute"),
            1: LabelResult(text="Users DB", confidence=0.9, bbox=[360, 80, 440, 100],
                           inferred_type="rds", inferred_class="database"),
        }

        # Use real GraphSolver
        graph_solver = GraphSolver(arrow_distance_threshold=300)

        pipeline = DiagramAnalysisPipeline(
            detector=mock_detector,
            ocr=mock_ocr,
            graph_solver=graph_solver,
        )

        # Create a dummy image
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        spec = pipeline.analyze(image)

        assert isinstance(spec, DiagramSpec)
        assert len(spec.nodes) == 2
        assert len(spec.edges) == 1

        # Verify nodes have labels
        compute_node = next(n for n in spec.nodes if n.class_name == "compute")
        assert compute_node.label == "Web Server"
        assert compute_node.subtype == "ec2"

        db_node = next(n for n in spec.nodes if n.class_name == "database")
        assert db_node.label == "Users DB"
        assert db_node.subtype == "rds"

        # Verify edge
        assert spec.edges[0].source_id == "compute_0"
        assert spec.edges[0].target_id == "database_0"

    def test_analyze_with_vpc(self):
        """Pipeline should correctly detect VPC containment."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = [
            _make_detection("network", [20, 20, 500, 500]),
            _make_detection("compute", [100, 100, 200, 200]),
            _make_detection("database", [300, 300, 400, 400]),
            _make_detection("arrow", [210, 150, 290, 310], confidence=0.85),
        ]

        mock_ocr = MagicMock(spec=DiagramOCR)
        mock_ocr.extract_labels.return_value = []
        mock_ocr.associate_labels_to_components.return_value = {}

        pipeline = DiagramAnalysisPipeline(
            detector=mock_detector,
            ocr=mock_ocr,
            graph_solver=GraphSolver(arrow_distance_threshold=300),
        )

        image = np.zeros((640, 640, 3), dtype=np.uint8)
        spec = pipeline.analyze(image)

        compute_node = next(n for n in spec.nodes if n.class_name == "compute")
        db_node = next(n for n in spec.nodes if n.class_name == "database")

        assert compute_node.parent_network is not None
        assert db_node.parent_network is not None

    def test_analyze_empty_image(self):
        """Pipeline should handle zero detections gracefully."""
        mock_detector = MagicMock()
        mock_detector.detect.return_value = []

        mock_ocr = MagicMock(spec=DiagramOCR)
        mock_ocr.extract_labels.return_value = []
        mock_ocr.associate_labels_to_components.return_value = {}

        pipeline = DiagramAnalysisPipeline(
            detector=mock_detector,
            ocr=mock_ocr,
            graph_solver=GraphSolver(),
        )

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        spec = pipeline.analyze(image)

        assert isinstance(spec, DiagramSpec)
        assert len(spec.nodes) == 0
        assert len(spec.edges) == 0
        assert len(spec.ambiguities) == 0

    def test_serialization_roundtrip(self):
        """DiagramSpec.to_dict() output should be JSON-serializable."""
        import json

        mock_detector = MagicMock()
        mock_detector.detect.return_value = [
            _make_detection("compute", [50, 100, 150, 200]),
            _make_detection("text_label", [60, 80, 140, 100]),
        ]

        mock_ocr = MagicMock(spec=DiagramOCR)
        mock_ocr.extract_labels.return_value = [
            LabelResult(text="EC2", confidence=0.9, bbox=[60, 80, 140, 100],
                        inferred_type="ec2", inferred_class="compute"),
        ]
        mock_ocr.associate_labels_to_components.return_value = {
            0: LabelResult(text="EC2", confidence=0.9, bbox=[60, 80, 140, 100],
                           inferred_type="ec2", inferred_class="compute"),
        }

        pipeline = DiagramAnalysisPipeline(
            detector=mock_detector,
            ocr=mock_ocr,
            graph_solver=GraphSolver(),
        )

        image = np.zeros((480, 640, 3), dtype=np.uint8)
        spec = pipeline.analyze(image)

        # Should not raise
        json_str = json.dumps(spec.to_dict())
        parsed = json.loads(json_str)

        assert "nodes" in parsed
        assert "edges" in parsed
        assert "ambiguities" in parsed
