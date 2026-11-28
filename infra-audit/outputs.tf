output "trail_name" {
  description = "Name of the CloudTrail trail."
  value       = aws_cloudtrail.audit.name
}

output "log_bucket" {
  description = "S3 bucket that holds the CloudTrail log files."
  value       = aws_s3_bucket.trail_logs.id
}

output "alert_topic_arn" {
  description = "SNS topic that receives security alerts."
  value       = aws_sns_topic.security_alerts.arn
}
