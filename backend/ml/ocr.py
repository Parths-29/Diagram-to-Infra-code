"""
Diagram OCR Module.

Extracts text from detected `text_label` bounding boxes using EasyOCR,
then spatially associates each label with the nearest infrastructure component.

Key design:
- Lazy-loads EasyOCR reader (heavy ~300MB model) once on first use
- Crops each text_label bbox region, preprocesses (grayscale, contrast, dilation),
  then runs OCR
- Associates labels to nearest non-text component by bbox centroid proximity
- Infers AWS resource subtypes from OCR text (e.g., "RDS" → "rds")
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import cv2
import numpy as np
import math

from backend.ml.detector import DetectionResult, CLASS_NAMES


# ── Component Type Inference Patterns ────────────────────────────────────────

# Maps regex patterns in OCR text to (class_name, subtype) pairs
TYPE_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # load_balancer subtypes (checked BEFORE compute so "API Gateway" → load_balancer, not compute)
    (re.compile(r"\balb\b", re.I), "load_balancer", "alb"),
    (re.compile(r"\bnlb\b", re.I), "load_balancer", "nlb"),
    (re.compile(r"\belb\b", re.I), "load_balancer", "alb"),
    (re.compile(r"\bload\s*bal", re.I), "load_balancer", "alb"),
    (re.compile(r"\blb\b", re.I), "load_balancer", "alb"),
    (re.compile(r"\bgateway\b", re.I), "load_balancer", "alb"),

    # compute subtypes
    (re.compile(r"\bec2\b", re.I), "compute", "ec2"),
    (re.compile(r"\beks\b", re.I), "compute", "eks"),
    (re.compile(r"\blambda\b", re.I), "compute", "lambda"),
    (re.compile(r"\binstance\b", re.I), "compute", "ec2"),
    (re.compile(r"\bserver\b", re.I), "compute", "ec2"),
    (re.compile(r"\bcontainer\b", re.I), "compute", "eks"),
    (re.compile(r"\bkubernetes\b|k8s\b", re.I), "compute", "eks"),
    (re.compile(r"\bnode\b", re.I), "compute", "ec2"),
    (re.compile(r"\bworker\b", re.I), "compute", "ec2"),
    (re.compile(r"\bapi\b", re.I), "compute", "ec2"),
    (re.compile(r"\bapp\b", re.I), "compute", "ec2"),
    (re.compile(r"\bweb\b", re.I), "compute", "ec2"),
    (re.compile(r"\bservice\b", re.I), "compute", "ec2"),

    # database subtypes
    (re.compile(r"\brds\b", re.I), "database", "rds"),
    (re.compile(r"\bpostgres", re.I), "database", "rds"),
    (re.compile(r"\bmysql\b", re.I), "database", "rds"),
    (re.compile(r"\baurora\b", re.I), "database", "rds"),
    (re.compile(r"\bdynamo", re.I), "database", "dynamodb"),
    (re.compile(r"\bmongo\b", re.I), "database", "rds"),
    (re.compile(r"\bqueue\b", re.I), "compute", "sqs"),
    (re.compile(r"\bsqs\b", re.I), "compute", "sqs"),
    (re.compile(r"\bredis\b", re.I), "database", "elasticache"),
    (re.compile(r"\bcache\b", re.I), "database", "elasticache"),
    (re.compile(r"\bdb\b", re.I), "database", "rds"),
    (re.compile(r"\bdatabase\b", re.I), "database", "rds"),

    # storage subtypes
    (re.compile(r"\bs3\b", re.I), "storage", "s3"),
    (re.compile(r"\bbucket\b", re.I), "storage", "s3"),
    (re.compile(r"\bstorage\b", re.I), "storage", "s3"),
    (re.compile(r"\befs\b", re.I), "storage", "efs"),
    (re.compile(r"\bblob\b", re.I), "storage", "s3"),

    # (load_balancer patterns moved to top of list for priority)

    # network subtypes
    (re.compile(r"\bvpc\b", re.I), "network", "vpc"),
    (re.compile(r"\bsubnet\b", re.I), "network", "subnet"),
    (re.compile(r"\bnetwork\b", re.I), "network", "vpc"),
    (re.compile(r"\bsecurity\s*group\b|sg\b", re.I), "network", "security_group"),
]


@dataclass
class LabelResult:
    """Result of OCR extraction for a single text_label detection."""
    text: str
    confidence: float
    bbox: List[int]              # [x1, y1, x2, y2] of the text_label detection
    inferred_type: Optional[str] = None    # e.g., "ec2", "rds", "s3", "alb"
    inferred_class: Optional[str] = None   # e.g., "compute", "database"

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 4),
            "bbox": self.bbox,
            "inferred_type": self.inferred_type,
            "inferred_class": self.inferred_class,
        }


class DiagramOCR:
    """Extracts and interprets text labels from architecture diagrams."""

    def __init__(self, languages: List[str] = None):
        self._languages = languages or ["en"]
        self._reader = None  # Lazy-loaded

    @property
    def reader(self):
        """Lazy-load EasyOCR reader on first use."""
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self._languages, gpu=False, verbose=False)
        return self._reader

    def extract_labels(
        self,
        image: np.ndarray,
        detections: List[DetectionResult]
    ) -> List[LabelResult]:
        """
        Extract text from all text_label detections in the image.

        Args:
            image: BGR numpy array of the full diagram image
            detections: List of DetectionResult from the YOLO detector

        Returns:
            List of LabelResult with extracted text and inferred types
        """
        text_detections = [d for d in detections if d.class_name == "text_label"]
        labels: List[LabelResult] = []

        for det in text_detections:
            x1, y1, x2, y2 = det.bbox
            h_img, w_img = image.shape[:2]

            # Clamp and add small padding
            pad = 5
            x1 = max(0, x1 - pad)
            y1 = max(0, y1 - pad)
            x2 = min(w_img, x2 + pad)
            y2 = min(h_img, y2 + pad)

            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Preprocess for better OCR accuracy
            processed = self._preprocess_crop(crop)

            # Run EasyOCR
            try:
                ocr_results = self.reader.readtext(processed, detail=1)
            except Exception:
                ocr_results = []

            if ocr_results:
                # Concatenate all text fragments in reading order
                texts = [r[1] for r in ocr_results]
                confidences = [r[2] for r in ocr_results]
                full_text = " ".join(texts).strip()
                avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            else:
                full_text = ""
                avg_conf = 0.0

            # Infer component type from text
            inferred_class, inferred_type = self._infer_type(full_text)

            labels.append(LabelResult(
                text=full_text,
                confidence=avg_conf,
                bbox=det.bbox,
                inferred_type=inferred_type,
                inferred_class=inferred_class,
            ))

        return labels

    def associate_labels_to_components(
        self,
        labels: List[LabelResult],
        components: List[DetectionResult]
    ) -> Dict[int, LabelResult]:
        """
        Spatially associate each text label with its nearest component.

        Uses centroid-to-centroid distance. Only associates with non-text,
        non-arrow component classes (compute, database, storage, load_balancer, network).

        Args:
            labels: List of LabelResult from extract_labels()
            components: List of DetectionResult (all detections from detector)

        Returns:
            Dict mapping component index (in the components list) to its associated LabelResult.
            Components without labels are not included.
        """
        # Filter to infrastructure components only
        infra_classes = {"compute", "database", "storage", "load_balancer", "network"}
        infra_components = [
            (i, c) for i, c in enumerate(components)
            if c.class_name in infra_classes
        ]

        if not infra_components or not labels:
            return {}

        associations: Dict[int, LabelResult] = {}
        used_labels: set = set()

        for comp_idx, comp in infra_components:
            comp_cx = (comp.bbox[0] + comp.bbox[2]) / 2
            comp_cy = (comp.bbox[1] + comp.bbox[3]) / 2

            best_label_idx = -1
            best_dist = float("inf")

            for label_idx, label in enumerate(labels):
                if label_idx in used_labels:
                    continue

                label_cx = (label.bbox[0] + label.bbox[2]) / 2
                label_cy = (label.bbox[1] + label.bbox[3]) / 2

                dist = math.sqrt((comp_cx - label_cx) ** 2 + (comp_cy - label_cy) ** 2)

                if dist < best_dist:
                    best_dist = dist
                    best_label_idx = label_idx

            # Only associate if within a reasonable distance
            # (max diagonal of the component bbox as threshold)
            if best_label_idx >= 0:
                comp_diag = math.sqrt(
                    (comp.bbox[2] - comp.bbox[0]) ** 2 +
                    (comp.bbox[3] - comp.bbox[1]) ** 2
                )
                max_dist = comp_diag * 1.5  # Allow some slack
                if best_dist <= max_dist:
                    associations[comp_idx] = labels[best_label_idx]
                    used_labels.add(best_label_idx)

        return associations

    def _preprocess_crop(self, crop: np.ndarray) -> np.ndarray:
        """Preprocess a cropped text region for better OCR accuracy."""
        # Convert to grayscale
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop.copy()

        # Upscale small crops for better OCR
        h, w = gray.shape
        if max(h, w) < 100:
            scale = 100 / max(h, w)
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)

        # Slight Gaussian blur to reduce noise, then threshold
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

        # Adaptive threshold to binarize (handles uneven lighting on whiteboards)
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )

        return binary

    @staticmethod
    def _infer_type(text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Infer AWS component class and subtype from OCR text.

        Returns:
            (inferred_class, inferred_type) or (None, None) if no match
        """
        if not text:
            return None, None

        for pattern, cls, subtype in TYPE_PATTERNS:
            if pattern.search(text):
                return cls, subtype

        return None, None
