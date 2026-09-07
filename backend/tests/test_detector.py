"""
Tests for DiagramObjectDetector module.
"""

import os
from pathlib import Path
import pytest
import numpy as np

from backend.ml.detector import DiagramObjectDetector, DetectionResult

def test_missing_weights_raises_file_not_found():
    """Verify that detector raises explicit FileNotFoundError when no trained weights exist."""
    with pytest.raises(FileNotFoundError) as exc_info:
        # Pass non-existent path and non-existent HF repo to force fallback check
        DiagramObjectDetector(
            weights_path="non_existent_weights.pt",
            hf_repo_id="invalid/repo-id-12345"
        )
    
    err_msg = str(exc_info.value)
    assert "No trained weights found" in err_msg
    assert "DiagramObjectDetector" in err_msg

def test_detection_result_dataclass():
    """Test DetectionResult schema conversion."""
    res = DetectionResult(
        class_id=0,
        class_name="compute",
        confidence=0.95421,
        bbox=[100, 150, 200, 250]
    )
    d = res.to_dict()
    assert d["class_id"] == 0
    assert d["class_name"] == "compute"
    assert d["confidence"] == 0.9542
    assert d["bbox"] == [100, 150, 200, 250]

def test_detector_with_mock_weights(tmp_path):
    """Test detector initialization and inference when a valid weight file exists."""
    from ultralytics import YOLO
    
    # Save a minimal YOLO model to tmp_path as test weights
    mock_model = YOLO("yolov8n.pt")
    mock_weights_file = tmp_path / "mock_best.pt"
    mock_model.save(str(mock_weights_file))

    # Instantiate detector with mock weights
    detector = DiagramObjectDetector(weights_path=str(mock_weights_file))
    assert detector.weights_file == mock_weights_file

    # Create dummy 640x640 image
    dummy_img = np.ones((640, 640, 3), dtype=np.uint8) * 255
    detections = detector.detect(dummy_img, conf_threshold=0.1)

    assert isinstance(detections, list)
    for det in detections:
        assert isinstance(det, DetectionResult)
        assert isinstance(det.class_id, int)
        assert isinstance(det.class_name, str)
        assert 0.0 <= det.confidence <= 1.0
        assert len(det.bbox) == 4
