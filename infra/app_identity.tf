# The Journal API's own identity. Pods running as the journal-api service
# account assume this role through EKS Pod Identity, so no keys are stored.
resource "aws_iam_role" "app" {
  name = "${local.name}-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

# Read-only access to the two secrets the API needs, and nothing else
resource "aws_iam_role_policy" "app_secrets" {
  name = "read-app-secrets"
  role = aws_iam_role.app.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.database_url.arn,
        aws_secretsmanager_secret.openai.arn,
      ]
    }]
  })
}

resource "aws_eks_pod_identity_association" "app" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "journal"
  service_account = "journal-api"
  role_arn        = aws_iam_role.app.arn

  depends_on = [aws_eks_addon.pod_identity_agent]
}
