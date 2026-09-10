# ---------- VPC & Subnets ----------
resource "aws_vpc" "vpc_1" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "Main VPC" }
}

resource "aws_internet_gateway" "vpc_1_igw" {
  vpc_id = aws_vpc.vpc_1.id
}

resource "aws_subnet" "vpc_1_public" {
  vpc_id                  = aws_vpc.vpc_1.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"
  tags = { Name = "Main VPC-public-subnet" }
}

resource "aws_subnet" "vpc_1_private" {
  vpc_id            = aws_vpc.vpc_1.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
  tags = { Name = "Main VPC-private-subnet" }
}

resource "aws_route_table" "vpc_1_public_rt" {
  vpc_id = aws_vpc.vpc_1.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.vpc_1_igw.id
  }
}

resource "aws_route_table_association" "vpc_1_public_assoc" {
  subnet_id      = aws_subnet.vpc_1_public.id
  route_table_id = aws_route_table.vpc_1_public_rt.id
}

# ---------- Security Groups ----------
# Default SG for compute resources
resource "aws_security_group" "default_compute_sg" {
  name   = "default-compute-sg"
  vpc_id = aws_vpc.vpc_1.id

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
resource "aws_instance" "ec2_1" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  # Placed inside VPC vpc_1 based on bounding box
  subnet_id              = aws_subnet.vpc_1_public.id
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  tags = { Name = "Web 1" }
}
resource "aws_instance" "ec2_2" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.micro"
  # Placed inside VPC vpc_1 based on bounding box
  subnet_id              = aws_subnet.vpc_1_public.id
  vpc_security_group_ids = [aws_security_group.default_compute_sg.id]
  tags = { Name = "Web 2" }
}

# ---------- ALBs ----------
resource "aws_lb" "alb_1" {
  name               = "public-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.default_compute_sg.id]
  subnets            = [aws_subnet.vpc_1_public.id, aws_subnet.vpc_1_private.id]
}

resource "aws_lb_target_group" "alb_1_tg" {
  name     = "public-alb-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.vpc_1.id
}

resource "aws_lb_listener" "alb_1_listener" {
  load_balancer_arn = aws_lb.alb_1.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alb_1_tg.arn
  }
}

resource "aws_lb_target_group_attachment" "alb_1_to_ec2_1" {
  target_group_arn = aws_lb_target_group.alb_1_tg.arn
  target_id        = aws_instance.ec2_1.id
  port             = 80
}
resource "aws_lb_target_group_attachment" "alb_1_to_ec2_2" {
  target_group_arn = aws_lb_target_group.alb_1_tg.arn
  target_id        = aws_instance.ec2_2.id
  port             = 80
}

# ---------- RDS ----------

# ---------- S3 ----------
