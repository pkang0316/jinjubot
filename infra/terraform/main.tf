data "cloudflare_zone" "site" {
  filter = {
    account = {
      id = var.cloudflare_account_id
    }
    name = var.cloudflare_zone_name
  }
}

resource "cloudflare_pages_project" "site" {
  account_id        = var.cloudflare_account_id
  name              = var.pages_project_name
  production_branch = var.production_branch

  build_config = {
    build_caching   = true
    build_command   = var.build_command
    destination_dir = var.build_output_dir
    root_dir        = var.build_root_dir
  }

  source = {
    type = "github"
    config = {
      owner                          = var.github_owner
      owner_id                       = var.github_owner_id
      repo_name                      = var.github_repo_name
      repo_id                        = var.github_repo_id
      production_branch              = var.production_branch
      pr_comments_enabled            = true
      preview_deployment_setting     = "all"
      production_deployments_enabled = true
    }
  }
}

resource "cloudflare_pages_domain" "custom" {
  for_each = var.custom_domains

  account_id   = var.cloudflare_account_id
  project_name = cloudflare_pages_project.site.name
  name         = each.value
}

resource "cloudflare_dns_record" "pages_apex" {
  count = contains(var.custom_domains, var.cloudflare_zone_name) ? 1 : 0

  zone_id = data.cloudflare_zone.site.id
  name    = var.cloudflare_zone_name
  type    = "CNAME"
  content = cloudflare_pages_project.site.subdomain
  proxied = true
  ttl     = 1
}

resource "cloudflare_dns_record" "pages_www" {
  count = contains(var.custom_domains, "www.${var.cloudflare_zone_name}") ? 1 : 0

  zone_id = data.cloudflare_zone.site.id
  name    = "www.${var.cloudflare_zone_name}"
  type    = "CNAME"
  content = cloudflare_pages_project.site.subdomain
  proxied = true
  ttl     = 1
}
