locals {
  name_prefix = "${var.project_name}-${var.environment}"
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "archive_file" "eventbrite_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../../research/python"
  output_path = "${path.module}/eventbrite-durable.zip"
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbrite_lambda" {
  name               = "${local.name_prefix}-eventbrite-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "lambda_policy" {
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    sid = "DurableExecution"
    actions = [
      "lambda:CheckpointDurableExecution",
      "lambda:GetDurableExecutionState",
    ]
    resources = ["*"]
  }

  statement {
    sid = "SnapshotBucket"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.snapshots.arn,
      "${aws_s3_bucket.snapshots.arn}/*",
    ]
  }

  statement {
    sid = "ItemRegistry"
    actions = [
      "dynamodb:BatchWriteItem",
      "dynamodb:GetItem",
      "dynamodb:DescribeTable",
      "dynamodb:PutItem",
      "dynamodb:Scan",
      "dynamodb:UpdateItem",
    ]
    resources = [
      aws_dynamodb_table.items.arn,
      aws_dynamodb_table.sources.arn,
    ]
  }

  dynamic "statement" {
    for_each = var.cf_access_secret_arn != "" ? [var.cf_access_secret_arn] : []

    content {
      sid = "CloudflareAccessSecret"
      actions = [
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
      ]
      resources = [statement.value]
    }
  }
}

resource "aws_iam_role_policy" "eventbrite_lambda" {
  name   = "${local.name_prefix}-eventbrite-policy"
  role   = aws_iam_role.eventbrite_lambda.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}

resource "aws_cloudwatch_log_group" "eventbrite_lambda" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = 14
  tags              = local.tags
}

resource "aws_s3_bucket" "snapshots" {
  bucket = "${local.name_prefix}-research-snapshots"
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_cors_configuration" "snapshots" {
  bucket = aws_s3_bucket.snapshots.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 300
  }
}

resource "aws_cloudfront_origin_access_control" "feed" {
  name                              = "${local.name_prefix}-feed-oac"
  description                       = "Origin access control for the published JinjuBot feed."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_response_headers_policy" "feed_cors" {
  name = "${local.name_prefix}-feed-cors"

  cors_config {
    access_control_allow_credentials = false
    origin_override                  = true

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD", "OPTIONS"]
    }

    access_control_allow_origins {
      items = ["*"]
    }

    access_control_max_age_sec = 600
  }
}

resource "aws_cloudfront_distribution" "feed" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Published JinjuBot feed JSON"

  origin {
    domain_name              = aws_s3_bucket.snapshots.bucket_regional_domain_name
    origin_id                = "snapshots-bucket"
    origin_access_control_id = aws_cloudfront_origin_access_control.feed.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "snapshots-bucket"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.feed_cors.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "snapshots_cloudfront_feed" {
  statement {
    sid = "PublicReadPublishedFeed"
    actions = [
      "s3:GetObject",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    resources = [
      "${aws_s3_bucket.snapshots.arn}/public/*",
    ]
  }

  statement {
    sid = "CloudFrontReadPublishedFeed"
    actions = [
      "s3:GetObject",
    ]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = [
      "${aws_s3_bucket.snapshots.arn}/public/*",
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.feed.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "snapshots_cloudfront_feed" {
  bucket = aws_s3_bucket.snapshots.id
  policy = data.aws_iam_policy_document.snapshots_cloudfront_feed.json

  depends_on = [aws_s3_bucket_public_access_block.snapshots]
}

resource "aws_dynamodb_table" "items" {
  name         = "${local.name_prefix}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "item_id"
  tags         = local.tags

  attribute {
    name = "item_id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "sources" {
  name         = "${local.name_prefix}-sources"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "source_id"
  tags         = local.tags

  attribute {
    name = "source_id"
    type = "S"
  }
}

resource "aws_lambda_function" "eventbrite_durable" {
  function_name    = var.lambda_function_name
  role             = aws_iam_role.eventbrite_lambda.arn
  filename         = data.archive_file.eventbrite_lambda.output_path
  source_code_hash = data.archive_file.eventbrite_lambda.output_base64sha256
  handler          = "jinjubot_research.durable_handler.lambda_handler"
  runtime          = "python3.14"
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_size
  publish          = true
  tags             = local.tags

  durable_config {
    execution_timeout = var.durable_execution_timeout_seconds
    retention_period  = var.durable_retention_period_days
  }

  environment {
    variables = merge(
      {
        EVENTBRITE_LISTING_URL      = var.eventbrite_listing_url
        EVENTBRITE_MAX_CANDIDATES   = tostring(var.eventbrite_max_candidates)
        EVENTBRITE_MAX_DEEP_FETCHES = tostring(var.eventbrite_max_deep_fetches)
        JINJUBOT_GATEWAY_URL        = var.llm_gateway_url
        SNAPSHOT_BUCKET             = aws_s3_bucket.snapshots.bucket
        SNAPSHOT_KEY                = "snapshots/eventbrite-nova.json"
        PUBLIC_FEED_BUCKET          = aws_s3_bucket.snapshots.bucket
        PUBLIC_FEED_KEY             = "public/feed.json"
        ITEMS_TABLE_NAME            = aws_dynamodb_table.items.name
        SOURCES_TABLE_NAME          = aws_dynamodb_table.sources.name
      },
      var.cf_access_secret_arn != "" ? {
        CF_ACCESS_SECRET_ARN = var.cf_access_secret_arn
      } : {}
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.eventbrite_lambda,
    aws_iam_role_policy.eventbrite_lambda,
  ]
}

resource "aws_lambda_alias" "live" {
  name             = "live"
  description      = "Stable alias for durable scheduler invocations."
  function_name    = aws_lambda_function.eventbrite_durable.function_name
  function_version = aws_lambda_function.eventbrite_durable.version
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  count              = var.enable_schedule ? 1 : 0
  name               = "${local.name_prefix}-scheduler-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = local.tags
}

data "aws_iam_policy_document" "scheduler_invoke" {
  statement {
    actions = ["lambda:InvokeFunction"]
    resources = [
      aws_lambda_alias.live.arn,
    ]
  }
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  count  = var.enable_schedule ? 1 : 0
  name   = "${local.name_prefix}-scheduler-invoke"
  role   = aws_iam_role.scheduler[0].id
  policy = data.aws_iam_policy_document.scheduler_invoke.json
}

resource "aws_scheduler_schedule" "eventbrite_nova" {
  count       = var.enable_schedule ? 1 : 0
  name        = "${local.name_prefix}-eventbrite-nova"
  group_name  = "default"
  description = "Runs the Eventbrite Northern Virginia durable research workflow."
  state       = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.schedule_expression

  target {
    arn      = aws_lambda_alias.live.arn
    role_arn = aws_iam_role.scheduler[0].arn

    input = jsonencode({
      source = "eventbridge-scheduler"
    })
  }
}
