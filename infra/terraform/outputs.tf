output "pages_project_name" {
  value = cloudflare_pages_project.site.name
}

output "pages_subdomain" {
  value = cloudflare_pages_project.site.subdomain
}

output "custom_domains" {
  value = [for domain in cloudflare_pages_domain.custom : domain.name]
}
