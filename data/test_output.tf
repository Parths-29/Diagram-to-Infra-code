# ---------- VPC & Subnets ----------
resource "aws_vpc" "vpc_0" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "Main VPC" }
}

resource "aws_internet_gateway" "vpc_0_igw" {
  vpc_id = aws_vpc.vpc_0.id
}

resource "aws_subnet" "vpc_0_public" {
  vpc_id                  = aws_vpc.vpc_0.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"
  tags = { Name = "Main VPC-public-subnet" }
}

resource "aws_subnet" "vpc_0_private" {
  vpc_id            = aws_vpc.vpc_0.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
  tags = { Name = "Main VPC-private-subnet" }
}

resource "aws_route_table" "vpc_0_public_rt" {
  vpc_id = aws_vpc.vpc_0.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.vpc_0_igw.id
  }
}

resource "aws_route_table_association" "vpc_0_public_assoc" {
  subnet_id      = aws_subnet.vpc_0_public.id
  route_table_id = aws_route_table.vpc_0_public_rt.id
}

# ---------- Security Groups ----------
# Default SG for compute resources
resource "aws_security_group" "default_compute_sg" {
  name   = "default-compute-sg"
  vpc_id = aws_vpc.vpc_0.id

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
resource "aws_instance" "ec2_0" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  # Placed inside VPC vpc_0 based on bounding box
  subnet_id              = aws_subnet.vpc_0_public.id
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  tags = { Name = "Web App" }
}

# ---------- ALBs ----------
resource "aws_lb" "alb_0" {
  name               = "public-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.default_compute_sg.id]
  subnets            = [aws_subnet.vpc_0_public.id, aws_subnet.vpc_0_private.id]
}

resource "aws_lb_target_group" "alb_0_tg" {
  name     = "public-alb-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.vpc_0.id
}

resource "aws_lb_listener" "alb_0_listener" {
  load_balancer_arn = aws_lb.alb_0.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alb_0_tg.arn
  }
}

resource "aws_lb_target_group_attachment" "alb_0_to_ec2_0" {
  target_group_arn = aws_lb_target_group.alb_0_tg.arn
  target_id        = aws_instance.ec2_0.id
  port             = 80
}

# ---------- RDS ----------
resource "aws_db_subnet_group" "rds_0_subnet_group" {
  name       = "rds_0-subnet-group"
  subnet_ids = [aws_subnet.vpc_0_private.id]
}

resource "aws_db_instance" "rds_0" {
  identifier             = "postgresql-db"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.rds_0_subnet_group.name
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  username               = "admin"
  password               = "changeme123!" # Pull from var/secrets in prod
  skip_final_snapshot    = true
}

# ---------- S3 ----------
resource "aws_s3_bucket" "s3_0" {
  bucket = "static-assets-bucket-4400"
}

resource "aws_s3_bucket_public_access_block" "s3_0_block" {
  bucket                  = aws_s3_bucket.s3_0.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
