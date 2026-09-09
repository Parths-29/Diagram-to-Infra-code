"""
Diagram Object Detector Module.

Uses custom-trained YOLOv8n model to detect 7 infrastructure diagram component classes:
- compute (0)
- database (1)
- storage (2)
- load_balancer (3)
- network (4)
- arrow (5)
- text_label (6)

Weight Resolution Strategy:
1. User-specified `weights_path` (if exists).
2. Hugging Face Hub download from repo `parths-29/diagram-to-infra-yolov8n` (`best.pt`).
3. Local fallback path `ml/weights/best.pt`.
4. If missing: RAISES `FileNotFoundError` (NO silent fallback to COCO weights!).
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Union, Optional
import cv2
import numpy as np

# Class definitions matching dataset.yaml
CLASS_NAMES = [
    "compute",
    "database",
    "storage",
    "load_balancer",
    "network",
    "arrow",
    "text_label"
]

CLASS_COLORS = {
    0: (0, 204, 102),     # compute - green
    1: (255, 128, 0),     # database - orange
    2: (204, 0, 204),     # storage - purple
    3: (255, 204, 0),     # load_balancer - yellow
    4: (255, 51, 204),    # network - pink
    5: (0, 0, 255),       # arrow - red
    6: (255, 0, 0)        # text_label - blue
}

@dataclass
class DetectionResult:
    class_id: int
    class_name: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]

    def to_dict(self) -> Dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": [int(v) for v in self.bbox]
        }

class DiagramObjectDetector:
    def __init__(
        self,
        weights_path: Optional[str] = None,
        hf_repo_id: str = "Parth2999/diagram-to-infra-yolov8n",
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45
    ):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.weights_file = self._resolve_weights(weights_path, hf_repo_id)
        
        # Load YOLO model
        from ultralytics import YOLO
        self.model = YOLO(str(self.weights_file))

    def _resolve_weights(self, weights_path: Optional[str], hf_repo_id: str) -> Path:
        """Resolves trained weights path or raises explicit FileNotFoundError."""
        # 1. Check explicit custom path if provided
        if weights_path:
            p = Path(weights_path)
            if p.exists():
                return p

        # 2. Try Hugging Face Hub download
        try:
            from huggingface_hub import hf_hub_download
            downloaded = hf_hub_download(
                repo_id=hf_repo_id,
                filename="best.pt",
                repo_type="model"
            )
            if Path(downloaded).exists():
                print(f"[Detector] Downloaded trained weights from HF Hub: {hf_repo_id}")
                return Path(downloaded)
        except Exception as e:
            # HF pull failed or repo doesn't exist yet
            pass

        # 3. Check local fallback path
        repo_root = Path(__file__).resolve().parent.parent.parent
        local_weights = repo_root / "ml" / "weights" / "best.pt"
        if local_weights.exists():
            print(f"[Detector] Loaded trained weights from local path: {local_weights}")
            return local_weights

        # 4. Explicit Error — DO NOT fall back to COCO yolov8n.pt!
        raise FileNotFoundError(
            f"No trained weights found for DiagramObjectDetector. "
            f"Please train the model via 'python ml/train.py' (in Google Colab) "
            f"or place trained weights at '{local_weights}' or upload to Hugging Face repo '{hf_repo_id}'."
        )

    def detect(
        self,
        image_input: Union[str, Path, bytes, np.ndarray],
        conf_threshold: Optional[float] = None
    ) -> List[DetectionResult]:
        """Runs object detection on image input and returns structured bounding boxes."""
        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        img = self._load_image(image_input)

        results = self.model.predict(
            source=img,
            conf=conf,
            iou=self.iou_threshold,
            save=False,
            verbose=False
        )

        detections: List[DetectionResult] = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()

                cls_name = CLASS_NAMES[cls_id] if 0 <= cls_id < len(CLASS_NAMES) else f"cls_{cls_id}"

                detections.append(
                    DetectionResult(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=confidence,
                        bbox=xyxy
                    )
                )

        return detections

    def draw_detections(
        self,
        image_input: Union[str, Path, bytes, np.ndarray],
        detections: List[DetectionResult],
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """Draws bounding boxes and labels onto the image for visual verification."""
        img = self._load_image(image_input).copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = CLASS_COLORS.get(det.class_id, (0, 255, 0))

            # Box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            # Label banner
            label = f"{det.class_name} {det.confidence:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, max(0, y1 - 20)), (x1 + w, y1), color, -1)
            cv2.putText(
                img,
                label,
                (x1, max(12, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_p), img)

        return img

    def _load_image(self, image_input: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
        """Helper to convert various image input formats into a BGR numpy array."""
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
            if img is None:
                raise ValueError(f"Could not read image from path: {image_input}")
            return img
        elif isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes.")
            return img
        elif isinstance(image_input, np.ndarray):
            return image_input
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")
