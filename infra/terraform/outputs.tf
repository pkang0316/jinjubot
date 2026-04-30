output "pages_project_name" {
  value = cloudflare_pages_project.site.name
}

output "pages_subdomain" {
  value = cloudflare_pages_project.site.subdomain
}

output "custom_domains" {
  value = [for domain in cloudflare_pages_domain.custom : domain.name]
}

output "www_cname_target" {
  value = contains([for domain in cloudflare_pages_domain.custom : domain.name], "www.${var.cloudflare_zone_name}") ? cloudflare_pages_project.site.subdomain : null
}

output "apex_cname_target" {
  value = contains([for domain in cloudflare_pages_domain.custom : domain.name], var.cloudflare_zone_name) ? cloudflare_pages_project.site.subdomain : null
}

output "llm_gateway_hostname" {
  value = var.enable_llm_gateway ? local.llm_gateway_hostname : null
}

output "llm_tunnel_id" {
  value = var.enable_llm_gateway ? cloudflare_zero_trust_tunnel_cloudflared.llm[0].id : null
}

output "llm_tunnel_token" {
  value     = var.enable_llm_gateway ? data.cloudflare_zero_trust_tunnel_cloudflared_token.llm[0].token : null
  sensitive = true
}

output "llm_access_service_token_client_id" {
  value = var.enable_llm_gateway ? cloudflare_zero_trust_access_service_token.llm[0].client_id : null
}

output "llm_access_service_token_client_secret" {
  value     = var.enable_llm_gateway ? cloudflare_zero_trust_access_service_token.llm[0].client_secret : null
  sensitive = true
}
