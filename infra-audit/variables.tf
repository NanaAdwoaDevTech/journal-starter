variable "region" {
  description = "AWS region for the audit stack."
  type        = string
  default     = "us-east-1"
}

variable "alert_email" {
  description = "Email address that receives security alerts."
  type        = string
  sensitive   = true
}

variable "log_retention_days" {
  description = "Days to keep CloudTrail log files in S3 (course minimum is 90)."
  type        = number
  default     = 100
}
