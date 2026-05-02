# AWS Durable Lambda Scaffold

This directory is the first AWS-side scaffold for the Python ingestion path.

It deliberately stays separate from the Cloudflare Terraform stack in:

- `infra/terraform/`

so we can evolve AWS orchestration without mixing providers or state.

The Cloudflare root module now reads selected outputs from this AWS root module through `terraform_remote_state`. That dependency is intentionally one-way:

- this AWS root module does not read Cloudflare state
- the Cloudflare root module may read this AWS state

That keeps deploy order simple and non-circular:

1. apply `aws-durable`
2. apply `infra/terraform`

## What it creates

- one durable Lambda function for the Eventbrite Northern Virginia workflow
- a stable Lambda alias named `live`
- one S3 bucket for workflow snapshots
- one directly readable S3 `feed.json`
- one CloudFront distribution that currently exists but is not on the active frontend serving path
- DynamoDB tables for `items` and `sources`
- IAM roles and policies for Lambda and Scheduler
- an EventBridge Scheduler schedule, hourly by default

## Why durable Lambda

This stack avoids Step Functions on purpose.

The durable Lambda keeps the orchestration in Python code while still giving us:

- checkpointed multi-step execution
- replay after interruptions
- execution history retention
- the ability to grow toward longer-running agentic workflows

AWS notes that durable execution must be enabled when the function is created, and that scheduled invocations should target a qualified ARN such as a version or alias.

Sources:

- [Lambda durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-functions.html)
- [Creating Lambda durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-getting-started.html)
- [Configure Lambda durable functions](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html)

## Current packaging shape

Terraform zips:

- `research/python/`

and deploys the handler:

- `jinjubot_research.durable_handler.lambda_handler`

The scaffold keeps the Python package stdlib-only for now so packaging stays simple.

## Published frontend feed

The durable workflow now publishes two S3 artifacts:

- a run snapshot:
  - `snapshots/eventbrite-nova.json`
- a frontend-shaped published feed:
  - `public/feed.json`

Terraform exposes:

- `public_feed_url`
- `public_feed_s3_url`
- `public_feed_domain_name`
- `cloudfront_feed_url`
- `cloudfront_feed_domain_name`

The site can consume that artifact by setting:

- `JINJUBOT_FEED_URL`

in `infra/.env.local`.

The active frontend path now reads `public/feed.json` directly from the S3 bucket regional endpoint. That is the simplest path for fast refreshes because there is no CDN cache layer between Lambda writes and browser reads.

CloudFront still exists in this stack, but it is **not serving the feed for the frontend right now**. It is effectively parked infrastructure until we decide we actually want CDN caching, a custom distribution contract, or different edge behavior.

## Source registry

The `sources` table is now intended to hold both:

- source definitions for the crawl engine
- runtime status fields like `last_checked_at` and `yield_count`

The Lambda seeds default source definitions when they are missing, loads active source rows from DynamoDB, and writes status fields back with updates instead of replacing the whole item.

That means we can scale the crawler by adding new source rows rather than hardcoding every source in Python.

## Secret handling

The function needs Cloudflare Access credentials before it can call:

- `https://llm.jinjubot.io`

Best practice here is:

- keep the real `client_id` and `client_secret` in AWS Secrets Manager
- pass only the secret ARN into Lambda
- let the function fetch and cache the secret at runtime

This scaffold now supports exactly that flow.

Use a JSON secret shaped like:

```json
{
  "client_id": "6cab349170adc64740ffbc0c76d3edcb.access",
  "client_secret": "replace-me"
}
```

Then set:

- `cf_access_secret_arn`

in `terraform.tfvars`.

Terraform will:

- pass `CF_ACCESS_SECRET_ARN` to the Lambda environment
- grant the Lambda role `secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` on that one secret

If your secret uses a customer-managed KMS key instead of the AWS-managed key, add `kms:Decrypt` for that key as a follow-up.

## Local apply flow

1. Copy:

```powershell
Copy-Item .\terraform.tfvars.example .\terraform.tfvars
```

2. Fill in any overrides you want.

3. Initialize and plan:

```powershell
terraform init
terraform plan
```

## Scheduler defaults

The Terraform defaults now enable the EventBridge schedule immediately with:

- `enable_schedule = true`
- `schedule_expression = "rate(1 hour)"`

If you want to pause it during iteration, override either value in `terraform.tfvars`.
