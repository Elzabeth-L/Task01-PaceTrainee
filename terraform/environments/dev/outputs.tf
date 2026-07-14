output "site_url" {
  description = "Public URL for the deployed site."
  value       = module.serverless_site.site_url
}

output "lambda_function_name" {
  description = "Lambda function name."
  value       = module.serverless_site.lambda_function_name
}
