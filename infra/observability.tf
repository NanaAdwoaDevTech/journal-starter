resource "aws_eks_addon" "pod_identity_agent" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "eks-pod-identity-agent"

  depends_on = [aws_eks_node_group.main]
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/journal/app"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "metrics" {
  name              = "/journal/metrics"
  retention_in_days = 7
}

resource "aws_iam_role" "otel_collector" {
  name = "${local.name}-otel-collector"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
    }]
  })
}

resource "aws_iam_role_policy" "otel_collector" {
  name = "send-telemetry"
  role = aws_iam_role.otel_collector.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
        ]
        Resource = [
          aws_cloudwatch_log_group.app.arn,
          "${aws_cloudwatch_log_group.app.arn}:*",
          aws_cloudwatch_log_group.metrics.arn,
          "${aws_cloudwatch_log_group.metrics.arn}:*",
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:DescribeLogGroups"]
        Resource = "*"
      },
    ]
  })
}

# The collector pod's service account assumes the role above
resource "aws_eks_pod_identity_association" "otel_collector" {
  cluster_name    = aws_eks_cluster.main.name
  namespace       = "observability"
  service_account = "otel-collector"
  role_arn        = aws_iam_role.otel_collector.arn

  depends_on = [aws_eks_addon.pod_identity_agent]
}

# Turn application ERROR log lines into a metric we can alarm on
resource "aws_cloudwatch_log_metric_filter" "app_errors" {
  name           = "journal-app-errors"
  log_group_name = aws_cloudwatch_log_group.app.name
  pattern        = "\"ERROR\""

  metric_transformation {
    name          = "AppErrors"
    namespace     = "Journal"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "app_errors" {
  alarm_name          = "journal-api-errors"
  alarm_description   = "Three or more application errors within 5 minutes"
  namespace           = "Journal"
  metric_name         = "AppErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "journal-api"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Requests per 5 minutes"
          region = var.region
          view   = "timeSeries"
          period = 300
          metrics = [
            [{ expression = "SUM(SEARCH('Namespace=\"Journal\" MetricName=\"http.server.duration\"', 'SampleCount', 300))", label = "Requests", id = "e1" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Average latency (ms)"
          region = var.region
          view   = "timeSeries"
          period = 300
          metrics = [
            [{ expression = "AVG(SEARCH('Namespace=\"Journal\" MetricName=\"http.server.duration\"', 'Average', 300))", label = "Latency", id = "e1" }]
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Application errors"
          region  = var.region
          view    = "timeSeries"
          stat    = "Sum"
          period  = 300
          metrics = [["Journal", "AppErrors"]]
        }
      },
      {
        type   = "log"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title  = "Recent errors and exceptions"
          region = var.region
          view   = "table"
          query  = "SOURCE '/journal/app' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
        }
      },
    ]
  })
}
