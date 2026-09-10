import os
from typing import Dict, List, Any, Optional
from jinja2 import Environment, FileSystemLoader

from backend.ml.graph_solver import DiagramSpec, DiagramNode, DiagramEdge

# ── Edge Mapping Table ───────────────────────────────────────────────────────
# Resolves directed edges (Source -> Target) into specific Terraform attributes.
# Format: (Source Subtype, Target Subtype) -> "tf_attribute_name"
# e.g., ALB -> EC2 means ALB points to EC2. In Terraform, this usually means
# an aws_lb_target_group_attachment where the EC2 ID is the target.

EDGE_MAPPING = {
    # Compute -> Network (Compute in Subnet/VPC)
    ("ec2", "subnet"): "subnet_id",
    ("ec2", "vpc"): "subnet_id",  # Needs subnet resolution from VPC
    
    # ALB -> Compute (Load balancer routing traffic)
    ("alb", "ec2"): "target_group_attachment",
    
    # Compute -> Database (Compute connects to DB)
    # Typically implies security group rules, or passing endpoint via env vars.
    ("ec2", "rds"): "db_security_group_ingress",
    
    # Database -> Network
    ("rds", "subnet"): "db_subnet_group",
    ("rds", "vpc"): "db_subnet_group",
}

class TerraformGenerator:
    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            # Default to templates folder in the same directory
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate(self, spec: DiagramSpec) -> str:
        """
        Convert a DiagramSpec into a monolithic Terraform main.tf string.
        """
        # 1. Resolve Nodes
        node_map = {n.id: n for n in spec.nodes}
        
        context = {
            "vpcs": [],
            "ec2s": [],
            "albs": [],
            "rds_instances": [],
            "s3_buckets": [],
            "sqs_queues": []
        }
        
        # Group nodes by subtype
        for node in spec.nodes:
            # Give nodes a clean tf identifier
            tf_id = node.id.replace("-", "_").lower()
            
            node_ctx = {
                "id": tf_id,
                "label": node.label or node.id,
                "raw_node": node,
                "edges_out": [],
                "edges_in": [],
                "vpc_id": None,
                "subnet_id": None,
                "targets": [], # For ALBs pointing to EC2s
                "sqs_targets": [], # For EC2 pointing to SQS
                "rds_targets": [], # For EC2 pointing to RDS
                "s3_targets": [] # For EC2 pointing to S3
            }
            
            if node.subtype == "vpc":
                context["vpcs"].append(node_ctx)
            elif node.subtype == "ec2":
                context["ec2s"].append(node_ctx)
            elif node.subtype == "alb":
                context["albs"].append(node_ctx)
            elif node.subtype == "rds":
                context["rds_instances"].append(node_ctx)
            elif node.subtype == "s3":
                context["s3_buckets"].append(node_ctx)
            elif node.subtype == "sqs":
                context["sqs_queues"].append(node_ctx)
                
        # 2. Resolve Edges (Type-Pair mapping)
        # We'll attach edge context directly to the node dictionaries so the template
        # can just loop over node.targets or node.subnet_id
        
        # A quick lookup map for our context nodes
        ctx_map = {}
        for category in context.values():
            for c_node in category:
                ctx_map[c_node["raw_node"].id] = c_node
                
        # Also handle implicit VPC containment via graph_solver's parent_network
        for node in spec.nodes:
            if node.parent_network and node.id in ctx_map:
                parent_id = node.parent_network
                if parent_id in ctx_map:
                    # e.g., EC2 inside VPC
                    ctx_map[node.id]["vpc_id"] = ctx_map[parent_id]["id"]
                    
        for edge in spec.edges:
            source = node_map.get(edge.source_id)
            target = node_map.get(edge.target_id)
            if not source or not target:
                continue
                
            source_ctx = ctx_map.get(source.id)
            target_ctx = ctx_map.get(target.id)
            
            # Use subtype mapping
            s_type = source.subtype
            t_type = target.subtype
            
            mapping = EDGE_MAPPING.get((s_type, t_type))
            
            if mapping == "target_group_attachment":
                # ALB -> EC2
                source_ctx["targets"].append(target_ctx)
            elif mapping == "subnet_id":
                # EC2 -> Subnet
                source_ctx["subnet_id"] = target_ctx["id"]
                
            # Ad-hoc mappings for worker fan-out
            if s_type == "ec2" and t_type == "sqs":
                source_ctx["sqs_targets"].append(target_ctx)
                target_ctx["edges_in"].append(source_ctx)
            if s_type == "ec2" and t_type == "rds":
                source_ctx["rds_targets"].append(target_ctx)
            if s_type == "ec2" and t_type == "s3":
                source_ctx["s3_targets"].append(target_ctx)
            
        # 3. Render Template
        template = self.env.get_template("main.tf.j2")
        return template.render(**context)
