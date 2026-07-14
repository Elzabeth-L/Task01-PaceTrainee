provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project    = var.app_name
      Repository = "github-actions"
    }
  }
}

module "serverless_site" {
  source = "../../modules/serverless_site"

  app_name         = var.app_name
  environment      = var.environment
  package_file     = "${path.root}/../../../build/orbit-site.zip"
  source_code_hash = filebase64sha256("${path.root}/../../../app/lambda_function.py")

  tags = {
    CostCenter = "serverless-demo"
  }
}
