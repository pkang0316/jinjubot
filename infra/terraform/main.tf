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
