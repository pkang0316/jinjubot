output "lambda_function_name" {
  value = aws_lambda_function.eventbrite_durable.function_name
}

output "lambda_live_alias_arn" {
  value = aws_lambda_alias.live.arn
}

output "snapshot_bucket_name" {
  value = aws_s3_bucket.snapshots.bucket
}

output "public_feed_url" {
  value = "https://${aws_s3_bucket.snapshots.bucket_regional_domain_name}/public/feed.json"
}

output "public_feed_s3_url" {
  value = "https://${aws_s3_bucket.snapshots.bucket_regional_domain_name}/public/feed.json"
}

output "public_feed_domain_name" {
  value = aws_s3_bucket.snapshots.bucket_regional_domain_name
}

output "cloudfront_feed_url" {
  value = "https://${aws_cloudfront_distribution.feed.domain_name}/public/feed.json"
}

output "cloudfront_feed_domain_name" {
  value = aws_cloudfront_distribution.feed.domain_name
}

output "items_table_name" {
  value = aws_dynamodb_table.items.name
}

output "sources_table_name" {
  value = aws_dynamodb_table.sources.name
}

output "scheduler_name" {
  value = var.enable_schedule ? aws_scheduler_schedule.eventbrite_nova[0].name : null
}
