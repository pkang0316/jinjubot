output "zone_id" {
  value = data.cloudflare_zone.site.zone_id
}

output "site_hostname" {
  value = cloudflare_dns_record.site.name
}
