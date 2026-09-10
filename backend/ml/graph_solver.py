"""
Diagram Graph Solver Module.

Converts raw YOLO detections + OCR labels into a structured architecture graph
(DiagramSpec) by resolving arrow connectivity, VPC containment, and generating
ambiguity questions.

Arrow resolution:
- For each arrow bbox, determine head (arrowhead) and tail endpoints
- Uses left-to-right / top-to-bottom flow assumption for v1
- Finds nearest component for each endpoint via bbox edge distance
- Builds directed edges: tail_component → head_component

VPC containment:
- Components whose bboxes are geometrically contained within a network bbox
  are marked as belonging to that VPC/subnet
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from backend.ml.detector import DetectionResult
from backend.ml.ocr import LabelResult


# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class DiagramNode:
    """A single infrastructure component in the architecture graph."""
    id: str                             # e.g., "compute_0", "database_1"
    class_name: str                     # "compute", "database", "storage", etc.
    subtype: Optional[str] = None       # "ec2", "rds", "s3", "alb", "eks", "vpc"
    label: str = ""                     # OCR text or generated default
    bbox: List[int] = field(default_factory=list)
    confidence: float = 0.0
    parent_network: Optional[str] = None  # ID of containing VPC/subnet node

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "class_name": self.class_name,
            "subtype": self.subtype,
            "label": self.label,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 4),
            "parent_network": self.parent_network,
        }


@dataclass
class DiagramEdge:
    """A directed connection between two components."""
    source_id: str
    target_id: str
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class DiagramSpec:
    """
    Complete structured representation of an architecture diagram.

    This is the intermediate format consumed by the Terraform code generator (Phase 5).
    """
    nodes: List[DiagramNode] = field(default_factory=list)
    edges: List[DiagramEdge] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "ambiguities": self.ambiguities,
        }


# ── Graph Solver ─────────────────────────────────────────────────────────────

INFRA_CLASSES = {"compute", "database", "storage", "load_balancer", "network"}


class GraphSolver:
    """
    Resolves spatial relationships between detected diagram components.

    Takes raw detections + OCR labels and produces a DiagramSpec with
    nodes, directed edges, and ambiguity questions.
    """

    def __init__(self, arrow_distance_threshold: float = 200.0):
        """
        Args:
            arrow_distance_threshold: Max pixel distance from an arrow endpoint
                to a component before the association is considered too weak.
        """
        self.arrow_distance_threshold = arrow_distance_threshold

    def solve(
        self,
        detections: List[DetectionResult],
        label_associations: Dict[int, LabelResult],
    ) -> DiagramSpec:
        """
        Build the architecture graph from detections and OCR labels.

        Args:
            detections: All YOLO detections for the image
            label_associations: Map from detection index → associated LabelResult

        Returns:
            DiagramSpec with nodes, edges, and ambiguity questions
        """
        spec = DiagramSpec()

        # Separate detections by type
        infra_dets: List[Tuple[int, DetectionResult]] = []
        arrow_dets: List[DetectionResult] = []

        for i, det in enumerate(detections):
            if det.class_name in INFRA_CLASSES:
                infra_dets.append((i, det))
            elif det.class_name == "arrow":
                arrow_dets.append(det)
            # text_label detections are consumed via label_associations

        # ── Step 1: Build nodes ──
        class_counters: Dict[str, int] = {}
        node_map: Dict[int, DiagramNode] = {}  # detection index → node

        for det_idx, det in infra_dets:
            count = class_counters.get(det.class_name, 0)
            class_counters[det.class_name] = count + 1

            node_id = f"{det.class_name}_{count}"

            # Get label info if associated
            label_info = label_associations.get(det_idx)
            if label_info:
                label_text = label_info.text
                subtype = label_info.inferred_type or self._default_subtype(det.class_name)
                # If OCR inferred a different class, prefer the OCR hint for subtype
                # but keep YOLO's class_name for the node type
            else:
                label_text = ""
                subtype = self._default_subtype(det.class_name)

            node = DiagramNode(
                id=node_id,
                class_name=det.class_name,
                subtype=subtype,
                label=label_text,
                bbox=det.bbox,
                confidence=det.confidence,
            )

            spec.nodes.append(node)
            node_map[det_idx] = node

        # ── Step 2: Resolve VPC containment ──
        network_nodes = [n for n in spec.nodes if n.class_name == "network"]
        non_network_nodes = [n for n in spec.nodes if n.class_name != "network"]

        for net_node in network_nodes:
            for child_node in non_network_nodes:
                if self._bbox_contains(net_node.bbox, child_node.bbox):
                    child_node.parent_network = net_node.id

        # ── Step 3: Resolve arrow edges ──
        all_infra_nodes = list(node_map.values())

        for arrow_det in arrow_dets:
            tail, head = self._get_arrow_endpoints(arrow_det.bbox)

            source_node, source_dist = self._find_nearest_node(tail, all_infra_nodes)
            target_node, target_dist = self._find_nearest_node(head, all_infra_nodes)

            if source_node and target_node and source_node.id != target_node.id:
                # Confidence is the minimum of arrow detection confidence
                # and a distance-based penalty
                dist_penalty = 1.0 - (
                    max(source_dist, target_dist) / self.arrow_distance_threshold
                )
                edge_conf = min(arrow_det.confidence, max(0.1, dist_penalty))

                edge = DiagramEdge(
                    source_id=source_node.id,
                    target_id=target_node.id,
                    confidence=edge_conf,
                )
                spec.edges.append(edge)

                # Flag low-confidence edges as ambiguities
                if edge_conf < 0.5:
                    spec.ambiguities.append(
                        f"Low confidence connection: does '{source_node.label or source_node.id}' "
                        f"connect to '{target_node.label or target_node.id}'?"
                    )

        # ── Step 4: Generate ambiguity questions ──
        self._detect_ambiguities(spec)

        return spec

    def _get_arrow_endpoints(self, bbox: List[int]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Determine arrow tail (source) and head (target) from its bounding box.

        Uses left-to-right / top-to-bottom flow assumption for v1:
        - If arrow is wider than tall → horizontal flow (left=tail, right=head)
        - If arrow is taller than wide → vertical flow (top=tail, bottom=head)
        """
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        if w >= h:
            # Horizontal arrow: left → right
            tail = (x1, cy)
            head = (x2, cy)
        else:
            # Vertical arrow: top → bottom
            tail = (cx, y1)
            head = (cx, y2)

        return tail, head

    def _find_nearest_node(
        self,
        point: Tuple[int, int],
        nodes: List[DiagramNode]
    ) -> Tuple[Optional[DiagramNode], float]:
        """
        Find the nearest infrastructure node to a given point.

        Uses minimum distance from point to bbox edge (not centroid),
        which handles large VPC boxes correctly.
        """
        if not nodes:
            return None, float("inf")

        best_node = None
        best_dist = float("inf")
        px, py = point

        for node in nodes:
            dist = self._point_to_bbox_distance(px, py, node.bbox)
            if dist < best_dist:
                best_dist = dist
                best_node = node

        # Only return if within threshold
        if best_dist <= self.arrow_distance_threshold:
            return best_node, best_dist
        return None, best_dist

    @staticmethod
    def _point_to_bbox_distance(px: int, py: int, bbox: List[int]) -> float:
        """
        Compute minimum distance from a point to a bounding box edge.

        Returns 0 if the point is inside the bbox.
        """
        x1, y1, x2, y2 = bbox

        # Clamp point to bbox range
        dx = max(x1 - px, 0, px - x2)
        dy = max(y1 - py, 0, py - y2)

        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def _bbox_contains(outer: List[int], inner: List[int], tolerance: float = 0.8) -> bool:
        """
        Check if the inner bbox is mostly contained within the outer bbox.

        Uses an overlap-area ratio: if ≥ tolerance of the inner area is
        inside the outer bbox, it counts as contained.
        """
        ox1, oy1, ox2, oy2 = outer
        ix1, iy1, ix2, iy2 = inner

        # Compute intersection
        inter_x1 = max(ox1, ix1)
        inter_y1 = max(oy1, iy1)
        inter_x2 = min(ox2, ix2)
        inter_y2 = min(oy2, iy2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return False

        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        inner_area = (ix2 - ix1) * (iy2 - iy1)

        if inner_area == 0:
            return False

        return (inter_area / inner_area) >= tolerance

    @staticmethod
    def _default_subtype(class_name: str) -> Optional[str]:
        """Return the default AWS subtype for a given class when OCR provides no text."""
        defaults = {
            "compute": "ec2",
            "database": "rds",
            "storage": "s3",
            "load_balancer": "alb",
            "network": "vpc",
        }
        return defaults.get(class_name)

    def _detect_ambiguities(self, spec: DiagramSpec) -> None:
        """Generate clarifying questions for ambiguous aspects of the diagram."""
        # 1. Unlabeled components
        for node in spec.nodes:
            if not node.label:
                spec.ambiguities.append(
                    f"No label detected for {node.class_name} component '{node.id}'. "
                    f"What is this component? (defaulting to {node.subtype})"
                )

        # 2. Disconnected components (no edges touching them)
        connected_ids = set()
        for edge in spec.edges:
            connected_ids.add(edge.source_id)
            connected_ids.add(edge.target_id)

        for node in spec.nodes:
            if node.class_name == "network":
                continue  # VPCs don't need direct arrow connections
            if node.id not in connected_ids:
                spec.ambiguities.append(
                    f"Component '{node.label or node.id}' has no connections. "
                    f"Is it connected to anything?"
                )

        # 3. Duplicate subtypes that might be a cluster
        subtype_counts: Dict[str, List[str]] = {}
        for node in spec.nodes:
            if node.subtype:
                subtype_counts.setdefault(node.subtype, []).append(node.id)

        for subtype, node_ids in subtype_counts.items():
            if len(node_ids) > 1 and subtype not in ("vpc", "subnet"):
                spec.ambiguities.append(
                    f"Multiple {subtype} components detected ({', '.join(node_ids)}). "
                    f"Are these separate instances or an auto-scaling group/cluster?"
                )
