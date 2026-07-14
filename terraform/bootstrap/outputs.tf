output "state_bucket" {
  description = "S3 bucket used by the application Terraform backend."
  value       = aws_s3_bucket.state.id
}

output "github_actions_role_arn" {
  description = "Set this value as the GitHub Actions repository variable AWS_ROLE_ARN."
  value       = aws_iam_role.github_actions.arn
}

output "aws_region" {
  description = "Set this value as the GitHub Actions repository variable AWS_REGION."
  value       = var.aws_region
}
