variable "cloudflare_api_token" {
  description = "Cloudflare API token with permission to manage Pages resources in the selected account."
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID."
  type        = string
}

variable "cloudflare_zone_name" {
  description = "Cloudflare zone name used for DNS records, for example jinjubot.io."
  type        = string
}

variable "pages_project_name" {
  description = "Cloudflare Pages project name."
  type        = string
  default     = "jinjubot"
}

variable "github_owner" {
  description = "GitHub owner for the repository connected to the Pages project."
  type        = string
  default     = "pkang0316"
}

variable "github_owner_id" {
  description = "GitHub numeric owner ID for the connected repository."
  type        = string
  default     = "65355094"
}

variable "github_repo_name" {
  description = "GitHub repository name connected to the Pages project."
  type        = string
  default     = "jinjubot"
}

variable "github_repo_id" {
  description = "GitHub numeric repository ID for the connected repository."
  type        = string
  default     = "1221132298"
}

variable "production_branch" {
  description = "Production branch used by Cloudflare Pages."
  type        = string
  default     = "main"
}

variable "build_command" {
  description = "Command Cloudflare Pages runs to build the site."
  type        = string
  default     = "npm run build"
}

variable "build_output_dir" {
  description = "Directory emitted by the build process."
  type        = string
  default     = "out"
}

variable "build_root_dir" {
  description = "Directory within the repo where Cloudflare should run the build."
  type        = string
  default     = "site"
}

variable "custom_domains" {
  description = "Custom domains to attach to the Pages project."
  type        = set(string)
  default     = []
}

variable "enable_llm_gateway" {
  description = "Whether to create the Cloudflare Tunnel, DNS, and Access resources for the local LLM gateway."
  type        = bool
  default     = false
}

variable "llm_tunnel_name" {
  description = "User-friendly name for the Cloudflare Tunnel that fronts the local LLM gateway."
  type        = string
  default     = "jinjubot-local-llm"
}

variable "llm_gateway_subdomain" {
  description = "Subdomain used for the internet-facing LLM gateway endpoint."
  type        = string
  default     = "llm"
}

variable "llm_gateway_service" {
  description = "Local service URL that cloudflared should forward traffic to."
  type        = string
  default     = "http://localhost:8080"
}

variable "llm_access_application_name" {
  description = "Display name for the Cloudflare Access application protecting the LLM gateway."
  type        = string
  default     = "jinjubot-llm-gateway"
}

variable "llm_access_policy_name" {
  description = "Name of the Cloudflare Access policy that allows service-token traffic to the LLM gateway."
  type        = string
  default     = "jinjubot-llm-service-token"
}

variable "llm_access_policy_session_duration" {
  description = "Access session duration for the LLM gateway application."
  type        = string
  default     = "24h"
}

variable "llm_service_token_name" {
  description = "Name of the Cloudflare Access service token used for automated requests to the LLM gateway."
  type        = string
  default     = "jinjubot-llm-client"
}

variable "llm_service_token_duration" {
  description = "Lifetime of the Cloudflare Access service token used by automation."
  type        = string
  default     = "8760h"
}
