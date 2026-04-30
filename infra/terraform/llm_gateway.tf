locals {
  llm_gateway_hostname = "${var.llm_gateway_subdomain}.${var.cloudflare_zone_name}"
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "llm" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id = var.cloudflare_account_id
  name       = var.llm_tunnel_name
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "llm" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.llm[0].id

  config = {
    ingress = [
      {
        hostname = local.llm_gateway_hostname
        service  = var.llm_gateway_service
      },
      {
        service = "http_status:404"
      }
    ]
  }
}

data "cloudflare_zero_trust_tunnel_cloudflared_token" "llm" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.llm[0].id
}

resource "cloudflare_dns_record" "llm_tunnel" {
  count = var.enable_llm_gateway ? 1 : 0

  zone_id = data.cloudflare_zone.site.id
  name    = local.llm_gateway_hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.llm[0].id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
}

resource "cloudflare_zero_trust_access_service_token" "llm" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id = var.cloudflare_account_id
  name       = var.llm_service_token_name
  duration   = var.llm_service_token_duration
}

resource "cloudflare_zero_trust_access_policy" "llm_service_token" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id       = var.cloudflare_account_id
  name             = var.llm_access_policy_name
  decision         = "non_identity"
  session_duration = var.llm_access_policy_session_duration

  include = [
    {
      service_token = {
        token_id = cloudflare_zero_trust_access_service_token.llm[0].id
      }
    }
  ]
}

resource "cloudflare_zero_trust_access_application" "llm_gateway" {
  count = var.enable_llm_gateway ? 1 : 0

  account_id = var.cloudflare_account_id
  type       = "self_hosted"
  name       = var.llm_access_application_name
  domain     = local.llm_gateway_hostname

  policies = [
    {
      id         = cloudflare_zero_trust_access_policy.llm_service_token[0].id
      precedence = 1
    }
  ]
}
