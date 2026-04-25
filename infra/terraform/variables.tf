variable "cloudflare_api_token" {
  description = "Cloudflare API token with permission to manage Pages resources in the selected account."
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID."
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
