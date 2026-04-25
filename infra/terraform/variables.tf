variable "cloudflare_api_token" {
  description = "Cloudflare API token with permission to manage the selected zone."
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID."
  type        = string
}

variable "zone_name" {
  description = "The primary DNS zone for the website, such as example.com."
  type        = string
}

variable "site_subdomain" {
  description = "Hostname to use for the site within the zone."
  type        = string
  default     = "@"
}

variable "site_target" {
  description = "Temporary DNS target for the site deployment endpoint."
  type        = string
  default     = "example.pages.dev"
}
