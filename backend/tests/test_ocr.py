"""
Tests for the DiagramOCR module.

Tests text extraction, component type inference, and label-to-component
spatial association without requiring actual trained weights.
"""

import pytest
from backend.ml.ocr import DiagramOCR, LabelResult, TYPE_PATTERNS
from backend.ml.detector import DetectionResult


class TestTypeInference:
    """Test the _infer_type static method against all known patterns."""

    def test_ec2_keywords(self):
        cls, subtype = DiagramOCR._infer_type("EC2 Instance")
        assert cls == "compute"
        assert subtype == "ec2"

    def test_eks_keywords(self):
        cls, subtype = DiagramOCR._infer_type("EKS Cluster")
        assert cls == "compute"
        assert subtype == "eks"

    def test_rds_keywords(self):
        cls, subtype = DiagramOCR._infer_type("RDS Database")
        assert cls == "database"
        assert subtype == "rds"

    def test_postgres_keyword(self):
        cls, subtype = DiagramOCR._infer_type("PostgreSQL")
        assert cls == "database"
        assert subtype == "rds"

    def test_s3_keywords(self):
        cls, subtype = DiagramOCR._infer_type("S3 Bucket")
        assert cls == "storage"
        assert subtype == "s3"

    def test_alb_keywords(self):
        cls, subtype = DiagramOCR._infer_type("ALB")
        assert cls == "load_balancer"
        assert subtype == "alb"

    def test_load_balancer_keyword(self):
        cls, subtype = DiagramOCR._infer_type("Load Balancer")
        assert cls == "load_balancer"
        assert subtype == "alb"

    def test_vpc_keywords(self):
        cls, subtype = DiagramOCR._infer_type("VPC")
        assert cls == "network"
        assert subtype == "vpc"

    def test_empty_text(self):
        cls, subtype = DiagramOCR._infer_type("")
        assert cls is None
        assert subtype is None

    def test_unknown_text(self):
        cls, subtype = DiagramOCR._infer_type("xyzzy random noise")
        assert cls is None
        assert subtype is None

    def test_case_insensitive(self):
        cls, subtype = DiagramOCR._infer_type("rds")
        assert cls == "database"
        assert subtype == "rds"

    def test_dynamodb(self):
        cls, subtype = DiagramOCR._infer_type("DynamoDB Table")
        assert cls == "database"
        assert subtype == "dynamodb"

    def test_lambda(self):
        cls, subtype = DiagramOCR._infer_type("Lambda Function")
        assert cls == "compute"
        assert subtype == "lambda"

    def test_gateway_keyword(self):
        cls, subtype = DiagramOCR._infer_type("API Gateway")
        assert cls == "load_balancer"
        assert subtype == "alb"


class TestLabelToComponentAssociation:
    """Test spatial association of labels to components."""

    def test_label_associates_to_nearest_component(self):
        ocr = DiagramOCR()

        labels = [
            LabelResult(text="EC2", confidence=0.9, bbox=[100, 100, 150, 120]),
            LabelResult(text="RDS", confidence=0.9, bbox=[300, 300, 350, 320]),
        ]

        # Component at (90,80)-(160,140) is near label at (100,100)-(150,120)
        # Component at (280,280)-(360,340) is near label at (300,300)-(350,320)
        components = [
            DetectionResult(class_id=0, class_name="compute", confidence=0.9, bbox=[90, 80, 160, 140]),
            DetectionResult(class_id=1, class_name="database", confidence=0.9, bbox=[280, 280, 360, 340]),
            DetectionResult(class_id=5, class_name="arrow", confidence=0.8, bbox=[170, 110, 270, 130]),
        ]

        associations = ocr.associate_labels_to_components(labels, components)

        assert 0 in associations  # compute got the EC2 label
        assert associations[0].text == "EC2"
        assert 1 in associations  # database got the RDS label
        assert associations[1].text == "RDS"
        assert 2 not in associations  # arrow should not get a label

    def test_no_labels(self):
        ocr = DiagramOCR()
        components = [
            DetectionResult(class_id=0, class_name="compute", confidence=0.9, bbox=[100, 100, 200, 200]),
        ]
        associations = ocr.associate_labels_to_components([], components)
        assert associations == {}

    def test_no_components(self):
        ocr = DiagramOCR()
        labels = [LabelResult(text="EC2", confidence=0.9, bbox=[100, 100, 150, 120])]
        associations = ocr.associate_labels_to_components(labels, [])
        assert associations == {}

    def test_label_too_far_not_associated(self):
        ocr = DiagramOCR()

        labels = [
            LabelResult(text="EC2", confidence=0.9, bbox=[900, 900, 950, 920]),
        ]
        components = [
            DetectionResult(class_id=0, class_name="compute", confidence=0.9, bbox=[10, 10, 50, 50]),
        ]

        associations = ocr.associate_labels_to_components(labels, components)
        # The label is extremely far from the component; should not associate
        assert 0 not in associations


class TestLabelResult:
    """Test LabelResult data structure."""

    def test_to_dict(self):
        label = LabelResult(
            text="EC2 Instance",
            confidence=0.95123,
            bbox=[10, 20, 100, 50],
            inferred_type="ec2",
            inferred_class="compute",
        )
        d = label.to_dict()
        assert d["text"] == "EC2 Instance"
        assert d["confidence"] == 0.9512
        assert d["bbox"] == [10, 20, 100, 50]
        assert d["inferred_type"] == "ec2"
        assert d["inferred_class"] == "compute"

    def test_defaults(self):
        label = LabelResult(text="foo", confidence=0.5, bbox=[0, 0, 10, 10])
        assert label.inferred_type is None
        assert label.inferred_class is None
