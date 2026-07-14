variable "aws_region" {
  description = "AWS region in which to deploy."
  type        = string
  default     = "ap-south-1"
}

variable "app_name" {
  description = "Application and resource name prefix."
  type        = string
  default     = "orbit-site"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}
