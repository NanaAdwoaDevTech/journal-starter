# Extra permissions for the existing CI role, so the deploy job can reach the
# cluster and read the secrets. Removed again on destroy.
resource "aws_iam_role_policy" "ci_deploy" {
  name = "journal-ci-deploy"
  role = var.ci_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["eks:DescribeCluster"]
        Resource = aws_eks_cluster.main.arn
      },
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          aws_secretsmanager_secret.database_url.arn,
          aws_secretsmanager_secret.openai.arn,
        ]
      },
    ]
  })
}

# A fixed public address for the load balancer, so a DNS name can point at it
resource "aws_eip" "ingress" {
  domain = "vpc"

  tags = { Name = "${local.name}-ingress-eip" }
}