# Deployment runbook

## Before the first deployment

Confirm the active identity and region before creating chargeable AWS resources:

```powershell
aws sts get-caller-identity
aws configure get region
terraform version
```

Follow the four numbered sections in the project README. Keep `terraform/bootstrap/terraform.tfstate` private and backed up securely.

### GitHub OIDC provider

An AWS account can have only one provider for the GitHub token URL. This project reads the existing provider as a data source so it cannot alter or destroy provider metadata shared with other repositories. If deploying into a different account, create that account-level provider once before applying this bootstrap stack.


## Normal change process

1. Edit the application or Terraform.
2. Run `python -m unittest discover -s tests -v`, `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package.ps1`, and `terraform fmt -recursive terraform`.
3. Open a pull request; offline checks validate untrusted changes without AWS credentials.
4. Merge to `main`. The protected deployment job assumes the OIDC role, plans, and applies.
5. Check the workflow summary URL and the page. For infrastructure changes, inspect the `Create plan` log before approving the protected `dev` environment.

## Verification and troubleshooting

```powershell
$url = terraform -chdir=terraform/environments/dev output -raw site_url
Invoke-WebRequest $url | Select-Object StatusCode, Headers
aws logs tail /aws/lambda/orbit-site-dev --since 10m --follow
```

- **403 from API Gateway:** Check `aws_lambda_permission.api_gateway` and that the request uses `GET`.
- **OIDC access denied:** Confirm `AWS_ROLE_ARN`, repository owner/name, the `main` branch, and the workflow's `id-token: write` permission.
- **State lock exists:** First confirm no deployment is active. Terraform normally removes the `.tflock` object; use `terraform force-unlock LOCK_ID` only after confirming the lock is stale.
- **Package path error:** Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package.ps1` before a local plan. CI packages the same handler before validation and deployment.

## Rollback

Application code is immutable in Git. Revert the faulty commit and merge/push the revert to `main`; the workflow packages and deploys the previous handler. For an urgent operator rollback, check out the known-good commit locally and run a saved plan/apply against the same backend.

## Destroy

Destroy the application before considering bootstrap resources:

```powershell
terraform -chdir=terraform/environments/dev plan -destroy -out=destroy.tfplan
terraform -chdir=terraform/environments/dev apply destroy.tfplan
```

The state bucket has `prevent_destroy`. Retaining it is the safe default. To remove the bootstrap stack permanently, first archive any state needed for audit/recovery, empty all bucket versions, deliberately remove `prevent_destroy`, and then run a reviewed bootstrap destroy. That destructive process is intentionally not automated.
