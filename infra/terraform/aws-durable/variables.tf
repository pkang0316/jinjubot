variable "aws_region" {
  description = "AWS region for the durable Lambda workflow."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project prefix used in resource names."
  type        = string
  default     = "jinjubot"
}

variable "environment" {
  description = "Environment name for tags and resource naming."
  type        = string
  default     = "dev"
}

variable "lambda_function_name" {
  description = "Base Lambda function name."
  type        = string
  default     = "jinjubot-eventbrite-nova"
}

variable "schedule_expression" {
  description = "EventBridge Scheduler expression for recurring runs."
  type        = string
  default     = "rate(1 hour)"
}

variable "enable_schedule" {
  description = "Whether to enable the recurring scheduler immediately."
  type        = bool
  default     = true
}

variable "llm_gateway_url" {
  description = "Gateway URL the Lambda should call for /plan and /extract."
  type        = string
  default     = "https://llm.jinjubot.io"
}

variable "cf_access_secret_arn" {
  description = "Secrets Manager ARN for the Cloudflare Access client ID and client secret JSON payload."
  type        = string
  default     = ""
}

variable "eventbrite_listing_url" {
  description = "Eventbrite listing page for the Northern Virginia discovery workflow."
  type        = string
  default     = "https://www.eventbrite.com/d/va--northern-virginia/events/"
}

variable "eventbrite_max_candidates" {
  description = "Maximum Eventbrite detail URLs to consider from the listing page."
  type        = number
  default     = 10
}

variable "eventbrite_max_deep_fetches" {
  description = "Maximum Eventbrite detail pages to inspect deeply per run."
  type        = number
  default     = 4
}

variable "durable_execution_timeout_seconds" {
  description = "Maximum wall-clock time for the durable execution."
  type        = number
  default     = 3600
}

variable "durable_retention_period_days" {
  description = "How long Lambda should retain durable execution history."
  type        = number
  default     = 7
}

variable "lambda_memory_size" {
  description = "Memory size for the durable Lambda function."
  type        = number
  default     = 1024
}

variable "lambda_timeout_seconds" {
  description = "Per-invocation timeout for the Lambda runtime."
  type        = number
  default     = 300
}
