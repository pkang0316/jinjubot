data "cloudflare_zone" "site" {
  filter = {
    name = var.zone_name
  }
}

locals {
  record_name = var.site_subdomain == "@" ? var.zone_name : "${var.site_subdomain}.${var.zone_name}"
}

resource "cloudflare_dns_record" "site" {
  zone_id = data.cloudflare_zone.site.zone_id
  name    = local.record_name
  type    = "CNAME"
  content = var.site_target
  proxied = true
  ttl     = 1
}
