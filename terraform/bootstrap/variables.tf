variable "aws_region" {
  description = "AWS region for the state bucket and deployments."
  type        = string
  default     = "ap-south-1"
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use the owner/name format."
  }
}

variable "app_name" {
  description = "Application prefix; must match the application stack."
  type        = string
  default     = "orbit-site"
}
