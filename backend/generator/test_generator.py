import json
from backend.ml.graph_solver import DiagramSpec, DiagramNode, DiagramEdge
from backend.generator.engine import TerraformGenerator

def main():
    # Construct a dummy spec
    # VPC with EC2 and ALB, RDS, and S3
    spec = DiagramSpec(
        nodes=[
            DiagramNode(id="vpc_0", class_name="network", subtype="vpc", label="Main VPC"),
            DiagramNode(id="ec2_0", class_name="compute", subtype="ec2", label="Web App", parent_network="vpc_0"),
            DiagramNode(id="alb_0", class_name="load_balancer", subtype="alb", label="Public ALB"),
            DiagramNode(id="rds_0", class_name="database", subtype="rds", label="PostgreSQL DB", parent_network="vpc_0"),
            DiagramNode(id="s3_0", class_name="storage", subtype="s3", label="Static Assets")
        ],
        edges=[
            DiagramEdge(source_id="alb_0", target_id="ec2_0", confidence=0.9),
            DiagramEdge(source_id="ec2_0", target_id="rds_0", confidence=0.8)
        ]
    )

    generator = TerraformGenerator()
    tf_code = generator.generate(spec)

    out_file = "data/test_output.tf"
    with open(out_file, "w") as f:
        f.write(tf_code)
    
    print(f"Generated Terraform code saved to {out_file}")

if __name__ == "__main__":
    main()
