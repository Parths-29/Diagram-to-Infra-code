# ---------- VPC & Subnets ----------

# ---------- Security Groups ----------
# Default SG for compute resources
resource "aws_security_group" "default_compute_sg" {
  name   = "default-compute-sg"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # tighten in prod
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ---------- EC2 Instances ----------
resource "aws_instance" "ec2_orphan" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  # Note: No VPC containment detected, assuming default subnets or placing in first VPC
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  tags = { Name = "Floating EC2" }
}

# ---------- ALBs ----------

# ---------- RDS ----------

resource "aws_db_instance" "rds_orphan" {
  identifier             = "floating-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  username               = "admin"
  password               = "changeme123!" # Pull from var/secrets in prod
  skip_final_snapshot    = true
}

# ---------- S3 ----------
