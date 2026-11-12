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