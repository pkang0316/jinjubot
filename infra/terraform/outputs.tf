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
