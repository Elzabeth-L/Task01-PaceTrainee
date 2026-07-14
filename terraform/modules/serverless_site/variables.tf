variable "app_name" {
  description = "Short name used as a prefix for resources."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,31}$", var.app_name))
    error_message = "app_name must be 3-32 lowercase letters, numbers, or hyphens, beginning with a letter."
  }
}

variable "package_file" {
  description = "Path to the deployment ZIP containing lambda_function.py at its root."
  type        = string
}

variable "source_code_hash" {
  description = "Base64 SHA-256 of application source, used to detect code changes deterministically."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Additional tags applied to supported resources."
  type        = map(string)
  default     = {}
}
