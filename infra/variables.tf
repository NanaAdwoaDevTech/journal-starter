variable "region" {
  type        = string
  description = "AWS region for all resources"
  default     = "us-east-1"
}

variable "kubernetes_version" {
  type        = string
  description = "EKS Kubernetes version (must be in standard support)"
  default     = "1.36"
}

variable "admin_principal_arn" {
  type        = string
  description = "IAM principal that administers the cluster"
  default     = "arn:aws:iam::011237053925:user/MyAdminUser"
}

variable "ci_role_name" {
  type        = string
  description = "Existing IAM role assumed by GitHub Actions"
  default     = "github-actions-journal"
}