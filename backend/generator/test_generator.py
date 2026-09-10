import json
import subprocess
from backend.ml.graph_solver import DiagramSpec, DiagramNode, DiagramEdge
from backend.generator.engine import TerraformGenerator

def test_scenario(name: str, spec: DiagramSpec):
    print(f"\n--- Testing Scenario: {name} ---")
    generator = TerraformGenerator()
    tf_code = generator.generate(spec)

    out_file = f"data/test_{name}.tf"
    with open(out_file, "w") as f:
        f.write(tf_code)
    
    # Run terraform init (if needed) and terraform validate
    # Create an empty directory for this test to avoid conflicts
    import os, shutil
    test_dir = f"data/tf_{name}"
    os.makedirs(test_dir, exist_ok=True)
    with open(f"{test_dir}/main.tf", "w") as f:
        f.write(tf_code)
        
    try:
        # We need a provider block to validate properly
        with open(f"{test_dir}/provider.tf", "w") as f:
            f.write('provider "aws" { region = "us-east-1" }\n')
            
        print("Running terraform init...")
        subprocess.run(
            ["../../bin/terraform", "init"], 
            cwd=test_dir, 
            check=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        print("Running terraform validate...")
        result = subprocess.run(
            ["../../bin/terraform", "validate"], 
            cwd=test_dir, 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print("✅ Validation PASSED")
        else:
            print(f"❌ Validation FAILED:\n{result.stderr}")
    except Exception as e:
        print(f"❌ Error running Terraform: {e}")

def main():
    # Scenario 1: Multiplicity (1 ALB -> 2 EC2s in a VPC)
    spec_multi = DiagramSpec(
        nodes=[
            DiagramNode(id="vpc_1", class_name="network", subtype="vpc", label="Main VPC"),
            DiagramNode(id="ec2_1", class_name="compute", subtype="ec2", label="Web 1", parent_network="vpc_1"),
            DiagramNode(id="ec2_2", class_name="compute", subtype="ec2", label="Web 2", parent_network="vpc_1"),
            DiagramNode(id="alb_1", class_name="load_balancer", subtype="alb", label="Public ALB"),
        ],
        edges=[
            DiagramEdge(source_id="alb_1", target_id="ec2_1", confidence=0.9),
            DiagramEdge(source_id="alb_1", target_id="ec2_2", confidence=0.9)
        ]
    )

    # Scenario 2: Dangling Nodes (RDS and EC2 with NO VPC, NO Subnet)
    spec_dangling = DiagramSpec(
        nodes=[
            DiagramNode(id="ec2_orphan", class_name="compute", subtype="ec2", label="Floating EC2"),
            DiagramNode(id="rds_orphan", class_name="database", subtype="rds", label="Floating DB")
        ],
        edges=[]
    )

    test_scenario("multiplicity", spec_multi)
    test_scenario("dangling", spec_dangling)

if __name__ == "__main__":
    main()
