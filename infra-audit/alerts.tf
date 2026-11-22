resource "aws_sns_topic" "security_alerts" {
  name = "journal-security-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_event_rule" "sg_changes" {
  name        = "journal-security-group-changes"
  description = "Alert when a security group is created, changed or deleted."

  event_pattern = jsonencode({
    source        = ["aws.ec2"]
    "detail-type" = ["AWS API Call via CloudTrail"]
    detail = {
      eventSource = ["ec2.amazonaws.com"]
      eventName = [
        "AuthorizeSecurityGroupIngress",
        "AuthorizeSecurityGroupEgress",
        "RevokeSecurityGroupIngress",
        "RevokeSecurityGroupEgress",
        "ModifySecurityGroupRules",
        "CreateSecurityGroup",
        "DeleteSecurityGroup",
      ]
    }
  })
}

resource "aws_sns_topic_policy" "security_alerts" {
  arn = aws_sns_topic.security_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowEventBridgePublish"
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.security_alerts.arn
        Condition = {
          ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.sg_changes.arn }
        }
      }
    ]
  })
}

resource "aws_cloudwatch_event_target" "sg_changes_to_sns" {
  rule = aws_cloudwatch_event_rule.sg_changes.name
  arn  = aws_sns_topic.security_alerts.arn

  input_transformer {
    input_paths = {
      action = "$.detail.eventName"
      who    = "$.detail.userIdentity.arn"
      when   = "$.detail.eventTime"
      ip     = "$.detail.sourceIPAddress"
    }
    input_template = "\"Security group change: <action> by <who> at <when> from <ip>\""
  }

  depends_on = [aws_sns_topic_policy.security_alerts]
}
