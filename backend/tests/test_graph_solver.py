"""
Tests for the GraphSolver module.

Tests arrow endpoint resolution, VPC containment, ambiguity detection,
and DiagramSpec output structure using mock detections (no trained weights needed).
"""

import pytest
from backend.ml.detector import DetectionResult
from backend.ml.ocr import LabelResult
from backend.ml.graph_solver import (
    GraphSolver, DiagramNode, DiagramEdge, DiagramSpec, INFRA_CLASSES,
)


def _make_detection(class_name: str, bbox: list, confidence: float = 0.9) -> DetectionResult:
    """Helper to create a DetectionResult with correct class_id."""
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


class TestArrowEndpoints:
    """Test arrow tail/head resolution from bounding boxes."""

    def test_horizontal_arrow(self):
        solver = GraphSolver()
        # Wide bbox → horizontal arrow
        tail, head = solver._get_arrow_endpoints([100, 200, 300, 220])
        assert tail == (100, 210)  # left edge
        assert head == (300, 210)  # right edge

    def test_vertical_arrow(self):
        solver = GraphSolver()
        # Tall bbox → vertical arrow
        tail, head = solver._get_arrow_endpoints([200, 100, 220, 300])
        assert tail == (210, 100)  # top edge
        assert head == (210, 300)  # bottom edge

    def test_square_arrow_defaults_horizontal(self):
        solver = GraphSolver()
        # Square bbox → w >= h so defaults to horizontal
        tail, head = solver._get_arrow_endpoints([100, 100, 200, 200])
        assert tail == (100, 150)
        assert head == (200, 150)


class TestPointToBboxDistance:
    """Test the point-to-bbox edge distance calculation."""

    def test_point_inside_bbox(self):
        dist = GraphSolver._point_to_bbox_distance(150, 150, [100, 100, 200, 200])
        assert dist == 0.0

    def test_point_on_edge(self):
        dist = GraphSolver._point_to_bbox_distance(100, 150, [100, 100, 200, 200])
        assert dist == 0.0

    def test_point_outside_right(self):
        dist = GraphSolver._point_to_bbox_distance(250, 150, [100, 100, 200, 200])
        assert dist == 50.0

    def test_point_outside_corner(self):
        dist = GraphSolver._point_to_bbox_distance(230, 230, [100, 100, 200, 200])
        # distance from (230,230) to corner (200,200) = sqrt(30^2 + 30^2)
        expected = (30**2 + 30**2) ** 0.5
        assert abs(dist - expected) < 0.01


class TestBboxContainment:
    """Test VPC containment logic."""

    def test_fully_contained(self):
        assert GraphSolver._bbox_contains(
            [50, 50, 500, 500],   # outer (VPC)
            [100, 100, 200, 200]  # inner (EC2)
        ) is True

    def test_not_contained(self):
        assert GraphSolver._bbox_contains(
            [50, 50, 150, 150],   # outer
            [200, 200, 300, 300]  # inner — completely outside
        ) is False

    def test_partially_contained_below_threshold(self):
        # Inner bbox only slightly overlaps outer
        assert GraphSolver._bbox_contains(
            [50, 50, 200, 200],
            [190, 190, 300, 300],
            tolerance=0.8
        ) is False

    def test_mostly_contained(self):
        # Inner bbox mostly inside outer
        assert GraphSolver._bbox_contains(
            [50, 50, 300, 300],
            [60, 60, 280, 310],  # sticks out a little at bottom
            tolerance=0.8
        ) is True


class TestGraphSolverIntegration:
    """Integration tests for the full solve() method."""

    def test_simple_two_node_with_arrow(self):
        """Test: [compute] →→→ [database]"""
        solver = GraphSolver(arrow_distance_threshold=300)

        detections = [
            _make_detection("compute", [50, 100, 150, 200]),       # left box
            _make_detection("database", [350, 100, 450, 200]),     # right box
            _make_detection("arrow", [160, 140, 340, 160]),        # horizontal arrow between them
        ]

        # No labels for this test
        spec = solver.solve(detections, {})

        assert len(spec.nodes) == 2
        assert spec.nodes[0].class_name == "compute"
        assert spec.nodes[1].class_name == "database"

        assert len(spec.edges) == 1
        assert spec.edges[0].source_id == "compute_0"
        assert spec.edges[0].target_id == "database_0"

    def test_vpc_containment(self):
        """Test: components inside a VPC box get parent_network set."""
        solver = GraphSolver()

        detections = [
            _make_detection("network", [20, 20, 500, 500]),
            _make_detection("compute", [100, 100, 200, 200]),
            _make_detection("database", [300, 300, 400, 400]),
        ]

        spec = solver.solve(detections, {})

        network_node = next(n for n in spec.nodes if n.class_name == "network")
        compute_node = next(n for n in spec.nodes if n.class_name == "compute")
        database_node = next(n for n in spec.nodes if n.class_name == "database")

        assert compute_node.parent_network == network_node.id
        assert database_node.parent_network == network_node.id

    def test_labels_propagate_to_nodes(self):
        """Test: OCR labels are propagated to DiagramNode."""
        solver = GraphSolver()

        detections = [
            _make_detection("compute", [100, 100, 200, 200]),
        ]

        label_associations = {
            0: LabelResult(text="Web Server", confidence=0.9, bbox=[100, 80, 200, 100],
                           inferred_type="ec2", inferred_class="compute"),
        }

        spec = solver.solve(detections, label_associations)

        assert len(spec.nodes) == 1
        assert spec.nodes[0].label == "Web Server"
        assert spec.nodes[0].subtype == "ec2"

    def test_unlabeled_component_generates_ambiguity(self):
        """Test: components with no OCR text generate ambiguity questions."""
        solver = GraphSolver()

        detections = [
            _make_detection("compute", [100, 100, 200, 200]),
        ]

        spec = solver.solve(detections, {})

        assert len(spec.ambiguities) >= 1
        assert any("No label detected" in a for a in spec.ambiguities)

    def test_disconnected_component_generates_ambiguity(self):
        """Test: components with no arrow connections generate ambiguity questions."""
        solver = GraphSolver()

        detections = [
            _make_detection("compute", [100, 100, 200, 200]),
            _make_detection("database", [400, 400, 500, 500]),
            # No arrows connecting them
        ]

        spec = solver.solve(detections, {})

        assert any("no connections" in a for a in spec.ambiguities)

    def test_duplicate_subtypes_generate_ambiguity(self):
        """Test: multiple same-subtype components generate cluster question."""
        solver = GraphSolver()

        detections = [
            _make_detection("compute", [100, 100, 200, 200]),
            _make_detection("compute", [300, 100, 400, 200]),
        ]

        spec = solver.solve(detections, {})

        assert any("Multiple ec2" in a or "separate instances" in a for a in spec.ambiguities)


class TestDiagramSpecSerialization:
    """Test DiagramSpec.to_dict() output."""

    def test_to_dict_structure(self):
        spec = DiagramSpec(
            nodes=[DiagramNode(id="compute_0", class_name="compute", subtype="ec2",
                               label="Web", bbox=[10, 10, 100, 100], confidence=0.95)],
            edges=[DiagramEdge(source_id="compute_0", target_id="database_0", confidence=0.8)],
            ambiguities=["Is compute_0 an EC2 instance?"],
        )

        d = spec.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "ambiguities" in d
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["id"] == "compute_0"
        assert d["nodes"][0]["subtype"] == "ec2"
        assert d["edges"][0]["source_id"] == "compute_0"

    def test_empty_spec(self):
        spec = DiagramSpec()
        d = spec.to_dict()
        assert d == {"nodes": [], "edges": [], "ambiguities": []}
