output "site_url" {
  description = "Public URL of the landing page."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "lambda_function_name" {
  description = "Deployed Lambda function name."
  value       = aws_lambda_function.app.function_name
}

output "api_id" {
  description = "API Gateway HTTP API identifier."
  value       = aws_apigatewayv2_api.app.id
}
