resource "random_password" "db" {
  length  = 32
  special = false # letters and digits only, so it is safe inside a URL
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.database[*].id
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "PostgreSQL, reachable only from the EKS nodes"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name}-db" }
}

resource "aws_vpc_security_group_ingress_rule" "db_from_nodes" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "PostgreSQL from EKS nodes"
}

resource "aws_db_instance" "main" {
  identifier = "${local.name}-db"

  engine                     = "postgres"
  engine_version             = "18"
  auto_minor_version_upgrade = true
  instance_class             = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "journal"
  username = "journaladmin"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period = 1
  apply_immediately       = true

  # Learning environment: lets `terraform destroy` clean up completely.
  # A production database would keep a final snapshot and deletion protection.
  skip_final_snapshot = true
  deletion_protection = false
}

# The full connection URL lives in Secrets Manager, never in the repo
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "journal/database-url"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = "postgresql://${aws_db_instance.main.username}:${random_password.db.result}@${aws_db_instance.main.address}:5432/${aws_db_instance.main.db_name}"
}

# Empty on purpose: you set the OpenAI values by hand so the key never enters Terraform state
resource "aws_secretsmanager_secret" "openai" {
  name                    = "journal/openai"
  recovery_window_in_days = 0
}