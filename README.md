# Orbit serverless Python landing page

Orbit is a dependency-free Python landing page deployed to AWS Lambda and exposed through an API Gateway v2 HTTP API. Terraform creates and manages the infrastructure, stores shared state in a protected S3 bucket, and deploys application changes through GitHub Actions using short-lived AWS credentials obtained through OpenID Connect (OIDC).

The application has no database, VPC, EC2 instance, container, load balancer, NAT gateway, or persistent application storage.

## Current deployment

| Item | Value |
|---|---|
| AWS account | `598120810297` |
| AWS region | `ap-south-1` |
| Environment | `dev` |
| Application name | `orbit-site` |
| Lambda function | `orbit-site-dev` |
| API Gateway URL | <https://t2xvcz1b9k.execute-api.ap-south-1.amazonaws.com/> |
| Terraform state bucket | `orbit-site-tfstate-598120810297-ap-south-1` |
| GitHub deployment role | `orbit-site-github-actions` |
| GitHub repository | `Elzabeth-L/Task01-PaceTrainee` |
| Deployment branch | `master` |

Visual and supporting documentation:

- [Standalone SVG architecture](docs/system-architecture.svg)
- [Detailed system and workflow architecture](docs/system-architecture.md)
- [Architecture decisions and trade-offs](docs/architecture-decisions.md)
- [Deployment and operations runbook](docs/deployment-runbook.md)

## What happens when a user opens the URL?

The live request flow is:

```text
Browser
   │ HTTPS GET / or GET /path
   ▼
API Gateway v2 HTTP API
   │ $default stage → matching GET route → AWS_PROXY integration
   │ API Gateway is authorized by the Lambda resource permission
   ▼
Python Lambda: orbit-site-dev
   │ Build status code, security headers, and HTML body
   ▼
API Gateway
   │ Convert the Lambda proxy result into an HTTP response
   ▼
Browser receives HTTP 200 and renders the landing page

Lambda runtime ─────► CloudWatch Logs
                     START / END / REPORT and application logs
```

### Is CloudWatch between API Gateway and Lambda?

No. CloudWatch is not in the request path and does not forward the request.

The synchronous request path is:

```text
Browser → API Gateway → Lambda → API Gateway → Browser
```

CloudWatch is a logging side path. During and after an invocation, the Lambda service writes platform records such as `START`, `END`, and `REPORT` to the function's CloudWatch log stream. Any future Python `print()` or logging output would go to the same stream. A CloudWatch failure does not turn CloudWatch into a request proxy; API Gateway invokes Lambda directly.

### Detailed runtime sequence

1. The browser sends an HTTPS `GET` request to the API Gateway invoke URL.
2. API Gateway receives the request at the `$default` stage.
3. API Gateway matches either `GET /` or `GET /{proxy+}`.
4. The matching route targets the Lambda `AWS_PROXY` integration.
5. The integration creates an API Gateway payload format 2.0 event.
6. AWS evaluates the Lambda resource-based permission. It allows the API Gateway service principal to invoke this function only when the request originates from this API's execution ARN.
7. Lambda starts or reuses a Python 3.13 ARM64 execution environment.
8. Lambda calls `lambda_function.lambda_handler(event, context)`.
9. The handler reads `context.aws_request_id` and escapes it with `html.escape` before placing it in the page footer.
10. The handler builds the complete HTML and CSS response in memory. It makes no database, filesystem, network, or AWS SDK call.
11. The handler returns an API Gateway proxy response containing `statusCode`, `headers`, and `body`.
12. API Gateway converts that object into an HTTP response and sends it to the browser.
13. The Lambda runtime records invocation telemetry in `/aws/lambda/orbit-site-dev` in CloudWatch Logs.

## How AWS resources were created

Terraform is split into two root stacks because an S3 backend cannot be used before its bucket exists.

### Phase 1: bootstrap stack

The one-time local stack under `terraform/bootstrap` creates the state and CI identity resources. Its own state remains local and is ignored by Git.

Conceptual creation order:

```text
Read AWS account/partition
        │
        ├──► Create S3 state bucket
        │       ├──► Enable versioning
        │       ├──► Configure AES-256 encryption
        │       ├──► Block all public access
        │       └──► Attach deny-non-TLS bucket policy
        │
        └──► Read existing GitHub OIDC provider
                └──► Create GitHub Actions IAM role
                        └──► Attach Terraform deployment policy
```

Terraform builds a dependency graph and may create independent resources in parallel. The diagram represents dependencies, not a guarantee that every API call is sequential.

### Phase 2: application stack

The root stack under `terraform/environments/dev` configures the S3 backend and calls the custom module under `terraform/modules/serverless_site`.

Conceptual creation order:

```text
Create CloudWatch log group       Create API Gateway HTTP API
              │                                │
Create Lambda execution role                   ├──► Create $default stage
              │                                │
Attach logging policy                          │
              │                                │
              └──► Create Lambda ◄─────────────┘
                          │
                          ├──► Create API Gateway Lambda integration
                          │       ├──► Create GET / route
                          │       └──► Create GET /{proxy+} route
                          │
                          └──► Grant API Gateway invoke permission
```

The initial application deployment was applied locally against the S3 backend. GitHub Actions later used that same state, detected the existing resources, and updated only the changed Lambda code.

## Complete AWS resource and configuration guide

The project manages 17 AWS Terraform resource instances: 7 bootstrap resources and 10 application resources. It also reads one shared account-level OIDC provider without owning it.

### Bootstrap and remote-state resources

#### 1. S3 state bucket

Terraform address: `aws_s3_bucket.state`

Configuration:

- Name: `orbit-site-tfstate-598120810297-ap-south-1`
- `force_destroy` is not enabled.
- Terraform lifecycle `prevent_destroy = true` is enabled.

Why:

- Local and CI deployments need one authoritative application state file.
- Account ID and region make the bucket name globally unique and recognizable.
- `prevent_destroy` reduces the risk of accidentally deleting infrastructure history.
- Objects are not automatically destroyed because state recovery is more important than convenient cleanup.

#### 2. S3 versioning configuration

Terraform address: `aws_s3_bucket_versioning.state`

Configuration: `status = "Enabled"`.

Why: each state update creates an S3 object version. An operator can recover an older state version after accidental corruption or an incorrect write.

#### 3. S3 server-side encryption

Terraform address: `aws_s3_bucket_server_side_encryption_configuration.state`

Configuration: `sse_algorithm = "AES256"`.

Why: Terraform state contains resource identifiers and infrastructure metadata. S3-managed encryption protects it at rest without creating a KMS key, KMS policy, rotation configuration, or additional KMS request costs for this small project.

#### 4. S3 public access block

Terraform address: `aws_s3_bucket_public_access_block.state`

Configuration:

- `block_public_acls = true`
- `block_public_policy = true`
- `ignore_public_acls = true`
- `restrict_public_buckets = true`

Why: Terraform state must never be publicly readable. All four controls are enabled so neither ACLs nor bucket policies can accidentally expose it.

#### 5. S3 TLS-only bucket policy

Terraform address: `aws_s3_bucket_policy.state_tls`

Configuration: an explicit `Deny` for `s3:*` when `aws:SecureTransport` is `false`, covering the bucket ARN and every object ARN.

Why: an explicit deny prevents state reads or writes over unencrypted HTTP, even if another IAM policy otherwise permits the request.

#### 6. Existing GitHub OIDC provider

Terraform address: `data.aws_iam_openid_connect_provider.github`

Configuration: reads `token.actions.githubusercontent.com` by ARN.

Why:

- An AWS account uses a shared GitHub OIDC provider.
- This project references it read-only rather than importing and taking ownership of account infrastructure that other repositories may use.
- The provider lets AWS validate signed GitHub identity tokens without storing AWS access keys in GitHub.

This is a Terraform data source, not one of the 17 project-managed resources.

#### 7. GitHub Actions IAM role

Terraform address: `aws_iam_role.github_actions`

Name: `orbit-site-github-actions`.

Trust configuration:

- Principal: the existing GitHub OIDC provider.
- Action: `sts:AssumeRoleWithWebIdentity`.
- Audience must equal `sts.amazonaws.com`.
- Subject must equal `repo:Elzabeth-L/Task01-PaceTrainee:environment:dev`.
- Maximum session duration uses the IAM default of one hour.

Why:

- GitHub receives temporary AWS credentials for each deployment.
- The audience condition prevents tokens intended for another service from being accepted.
- The subject condition restricts role assumption to this repository and the protected `dev` environment.
- Pull-request jobs do not use the environment and therefore cannot assume this role.

#### 8. GitHub Terraform deployment policy

Terraform address: `aws_iam_role_policy.github_actions`

Name: `terraform-application-deploy`.

Permissions and reasons:

| Permission area | Scope | Reason |
|---|---|---|
| S3 bucket metadata | State bucket only | Terraform backend must locate and list the bucket. |
| S3 object operations | State and `.tflock` keys only | Terraform reads/writes state and creates/deletes its native lock. |
| Lambda management | Functions named `orbit-site-*` | CI must create, read, update, and delete this application's functions. |
| Lambda discovery | `ListFunctions` | AWS provider refresh and discovery. |
| CloudWatch Logs | `/aws/lambda/orbit-site-*` | CI manages this application's log groups and retention. |
| Logs discovery | Account-level describe/list calls | Some read APIs do not support resource-level ARNs. |
| API Gateway | API Gateway v2 API resources in `ap-south-1` | CI manages the HTTP API, stage, routes, and integration. |
| IAM application roles | Roles named `orbit-site-*` | CI manages and passes the Lambda execution role. |

The application stack does not declare the GitHub deployment role, so a normal application plan does not propose changes to it. The deployed IAM resource pattern is the shared `orbit-site-*` prefix; stricter defense-in-depth could narrow the role ARN to `orbit-site-*-lambda-role` or add an explicit deny for deployment-role self-modification. Bootstrap configuration changes continue to require a deliberate local apply.

### Application resources

#### 9. CloudWatch log group

Terraform address: `module.serverless_site.aws_cloudwatch_log_group.lambda`

Configuration:

- Name: `/aws/lambda/orbit-site-dev`
- Retention: 14 days
- Created before Lambda through an explicit dependency

Why:

- Creating it explicitly lets Terraform control retention and tags.
- Without explicit retention, Lambda logs can remain indefinitely and accumulate cost.
- Fourteen days is sufficient for a demo/dev workload while retaining recent troubleshooting data.

#### 10. Lambda execution IAM role

Terraform address: `module.serverless_site.aws_iam_role.lambda`

Name: `orbit-site-dev-lambda-role`.

Trust configuration: only `lambda.amazonaws.com` may call `sts:AssumeRole`.

Why: Lambda needs an execution identity, but the application does not need S3, database, VPC, or other AWS permissions.

#### 11. Lambda logging policy

Terraform address: `module.serverless_site.aws_iam_role_policy.lambda_logs`

Configuration:

- Actions: `logs:CreateLogStream` and `logs:PutLogEvents`
- Resource: only `/aws/lambda/orbit-site-dev:*`

Why: this is the minimum runtime permission needed to write logs to the existing log group. `logs:CreateLogGroup` is omitted because Terraform creates the group.

#### 12. Lambda function

Terraform address: `module.serverless_site.aws_lambda_function.app`

Configuration:

| Setting | Value | Reason |
|---|---|---|
| Function name | `orbit-site-dev` | Combines application and environment for predictable ownership. |
| Runtime | `python3.13` | Current Python runtime selected for the project. |
| Architecture | `arm64` | Cost-efficient and compatible because the handler has no native dependencies. |
| Handler | `lambda_function.lambda_handler` | Matches `app/lambda_function.py` and the exported function. |
| Package type | ZIP | Smallest and simplest option for one Python source file. |
| Memory | 128 MB | The handler only builds a small string; more memory is unnecessary. |
| Timeout | 5 seconds | The handler performs no I/O and should complete quickly; a short limit controls runaway cost. |
| Published versions | Disabled | The demo deploys `$LATEST`; aliases and traffic shifting are outside this small scope. |
| Environment variable | `APP_ENVIRONMENT=dev` | Makes the deployment environment available for future handler behavior. |
| VPC configuration | None | No private dependency exists; avoiding a VPC removes networking and NAT complexity. |
| Reserved concurrency | Unset | Lambda may use normal regional on-demand concurrency. |

Code deployment settings:

- `package_file` points to `build/orbit-site.zip`.
- The ZIP contains `lambda_function.py` at its root, which is required by the configured handler.
- `source_code_hash` is calculated from `app/lambda_function.py` with `filebase64sha256`.
- Hashing the source independently avoids false changes caused by Windows/Linux ZIP metadata differences.
- Explicit dependencies ensure the log group and role policy exist before the function is created.

#### 13. API Gateway v2 HTTP API

Terraform address: `module.serverless_site.aws_apigatewayv2_api.app`

Configuration:

- Name: `orbit-site-dev-http-api`
- Protocol: `HTTP`
- Public default execute-api endpoint
- No authorization configured on the public landing-page routes

Why:

- An HTTP API has less configuration and lower request cost than API Gateway REST API for a simple Lambda proxy.
- The landing page is intentionally public, so JWT, IAM, or Cognito request authorization is not required.
- HTTPS is supplied by the managed API Gateway endpoint.

#### 14. API Gateway Lambda proxy integration

Terraform address: `module.serverless_site.aws_apigatewayv2_integration.lambda`

Configuration:

- Integration type: `AWS_PROXY`
- Integration method: `POST`
- Payload format: `2.0`
- Integration timeout: 5,000 ms
- Integration URI: Lambda invoke ARN

Why:

- API Gateway uses `POST` internally to invoke Lambda even though the public route is `GET`.
- Proxy integration passes the request to Lambda and lets Lambda supply status, headers, and body.
- Payload v2 is the native, smaller event format for HTTP APIs.
- The integration timeout matches the Lambda timeout, so API Gateway does not wait beyond the function's allowed execution time.

#### 15. Root route

Terraform address: `module.serverless_site.aws_apigatewayv2_route.root`

Configuration: `GET /` targets the Lambda integration.

Why: this is the primary landing-page URL.

#### 16. Proxy route

Terraform address: `module.serverless_site.aws_apigatewayv2_route.proxy`

Configuration: `GET /{proxy+}` targets the same Lambda integration.

Why: nested GET paths still return the landing page instead of API Gateway's default not-found response. Other HTTP methods are not exposed.

#### 17. Default API Gateway stage

Terraform address: `module.serverless_site.aws_apigatewayv2_stage.default`

Configuration:

- Name: `$default`
- `auto_deploy = true`
- Throttling rate: 25 requests per second
- Throttling burst: 50 requests

Why:

- `$default` keeps the public URL free of a `/dev` stage suffix.
- Auto-deploy makes Terraform route/integration changes immediately active without managing a separate deployment resource.
- Throttling provides basic protection against accidental request spikes and runaway invocation cost.

#### 18. Lambda invocation permission

Terraform address: `module.serverless_site.aws_lambda_permission.api_gateway`

Configuration:

- Principal: `apigateway.amazonaws.com`
- Action: `lambda:InvokeFunction`
- Source: this HTTP API's execution ARN, covering its stages and methods

Why: creating an API Gateway integration is not enough by itself. Lambda's resource-based policy must separately authorize API Gateway to invoke the function. The source ARN prevents unrelated API Gateways from using this permission.

## Terraform configuration choices

### Terraform and provider versions

```hcl
required_version = ">= 1.10.0, < 2.0.0"
aws provider     = "~> 6.0"
```

Why:

- Terraform 1.10 or newer is required for native S3 state locking with `use_lockfile`.
- The upper bound avoids an automatic major-version jump to Terraform 2.x.
- `~> 6.0` accepts compatible AWS provider 6.x updates but not a breaking 7.x release.

### S3 application backend

```hcl
backend "s3" {
  key          = "orbit/dev/terraform.tfstate"
  encrypt      = true
  use_lockfile = true
}
```

Why:

- A fixed key gives local Terraform and GitHub Actions the same state location.
- `encrypt = true` requires encrypted S3 backend operations in addition to the bucket encryption configuration.
- `use_lockfile = true` uses the S3-native `.tflock` object and avoids a separate DynamoDB locking table.
- Bucket and region are partial backend settings supplied during `terraform init`, so the same code can be initialized after bootstrap.

### Region

Default: `ap-south-1`.

Why: it is the confirmed deployment region and is close to the intended operator location. Every regional ARN in the CI policy and application resources is consistently scoped to it.

### Naming and validation

- Default application name: `orbit-site`
- Default environment: `dev`
- Runtime prefix: `orbit-site-dev`
- Application-name validation permits 3–32 lowercase letters, numbers, and hyphens, beginning with a letter.

Why: predictable names make IAM scoping, logs, cost identification, and cleanup safer. Validation rejects characters that would create inconsistent or invalid AWS names.

### Tags

Provider-level tags:

- `Project = orbit-site`
- `Repository = github-actions` on the application provider
- `ManagedBy = Terraform` on bootstrap resources

Module tags:

- `Application = orbit-site`
- `Environment = dev`
- `ManagedBy = Terraform`
- `CostCenter = serverless-demo`

Why: tags identify ownership, environment, automation source, and cost grouping in AWS inventory and billing views.

### Custom module

The custom module `terraform/modules/serverless_site` owns one complete serverless service boundary: logs, runtime IAM, Lambda, API Gateway, routes, stage, integration, and invocation permission.

Why: the environment root stays small and provides only environment-specific values. The module can be reused for another environment without duplicating the resource graph.

## Lambda response configuration

The handler returns:

```python
{
    "statusCode": 200,
    "headers": {...},
    "body": "<!doctype html>...",
}
```

Headers and reasons:

| Header | Value | Reason |
|---|---|---|
| `Content-Type` | `text/html; charset=utf-8` | Tells the browser to render UTF-8 HTML. |
| `Cache-Control` | `public, max-age=300` | Allows five minutes of browser/intermediary caching to reduce repeat invocations. |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type guessing. |
| `Content-Security-Policy` | Restrictive default with inline styles only | Blocks scripts, external content, framing, and unsafe base-URI behavior while allowing the embedded CSS. |

The request ID is HTML-escaped before rendering. The page uses no external fonts, JavaScript, images, or CSS dependencies, keeping the deployment ZIP and cold-start work small.

## Terraform delivery workflow

### One-time local bootstrap

```powershell
terraform -chdir=terraform/bootstrap init
terraform -chdir=terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=terraform/bootstrap apply bootstrap.tfplan
```

This creates or reconciles the protected state bucket and repository-scoped GitHub role. Bootstrap state remains local and must not be committed.

### Local-first application deployment

```powershell
$bucket = terraform -chdir=terraform/bootstrap output -raw state_bucket
$region = terraform -chdir=terraform/bootstrap output -raw aws_region
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package.ps1
terraform -chdir=terraform/environments/dev init -backend-config="bucket=$bucket" -backend-config="region=$region"
terraform -chdir=terraform/environments/dev plan -out=tfplan
terraform -chdir=terraform/environments/dev apply tfplan
terraform -chdir=terraform/environments/dev output -raw site_url
```

Why plan files are saved: applying the exact reviewed `tfplan` avoids recalculating a different plan between review and execution.

### GitHub Actions variables and environment

Repository variables:

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::598120810297:role/orbit-site-github-actions` |
| `AWS_REGION` | `ap-south-1` |
| `STATE_BUCKET` | `orbit-site-tfstate-598120810297-ap-south-1` |

These are identifiers, not secrets. The `dev` GitHub environment permits deployments from `master` only.

### Pull-request workflow

Pull requests that change the app, tests, Terraform, or workflow run:

1. Repository checkout.
2. Python 3.13 setup.
3. Unit tests.
4. Lambda ZIP packaging.
5. Terraform 1.10.5 setup.
6. `terraform fmt -check`.
7. `terraform init -backend=false`.
8. `terraform validate`.

The pull-request job has no `id-token: write`, does not enter the `dev` environment, and receives no AWS credentials. Untrusted changes cannot run Terraform against the account.

### Master deployment workflow

A matching push to `master` or manual workflow dispatch runs checks first, then:

1. Enters the protected `dev` environment.
2. Requests a GitHub OIDC identity token.
3. Exchanges the token through AWS STS for a temporary `orbit-site-github-actions` session.
4. Packages `lambda_function.py` into `build/orbit-site.zip`.
5. Initializes the S3 backend from `STATE_BUCKET` and `AWS_REGION`.
6. Acquires `orbit/dev/terraform.tfstate.tflock`.
7. Refreshes current AWS state.
8. Creates and saves `tfplan`.
9. Applies exactly that saved plan.
10. Writes updated state, releases the lock, and publishes the site URL in the GitHub job summary.

The workflow concurrency group `terraform-dev` has `cancel-in-progress: false`, so deployments are serialized rather than cancelling an apply that may already be changing AWS.

## Local testing and packaging

```powershell
python -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package.ps1
```

Tests verify that the handler returns HTML, uses the correct content type, includes expected page content, and escapes a hostile request ID.

The packaging script removes the previous ZIP and creates a fresh `build/orbit-site.zip` containing `lambda_function.py` at the archive root. The application uses only Python's standard library, so there is no dependency installation step.

## Repository layout

```text
app/
  lambda_function.py                 Lambda handler and embedded landing page
scripts/
  package.ps1                        Local Lambda ZIP packaging
tests/
  test_lambda.py                     Standard-library unit tests
terraform/
  bootstrap/                         State bucket and GitHub OIDC deployment role
  environments/dev/                  Deployable dev root and S3 backend
  modules/serverless_site/           Custom application infrastructure module
.github/workflows/terraform.yml      PR validation and master deployment pipeline
docs/
  system-architecture.svg            Standalone visual architecture
  system-architecture.md             Detailed architecture and sequences
  architecture-decisions.md          Decisions, alternatives, and trade-offs
  deployment-runbook.md              Operations, rollback, and cleanup
```

Generated ZIPs, plans, local state, `terraform.tfvars`, `.terraform` working directories, and the local Zscaler CA bundle are excluded from Git.

## Cost, scaling, and operational behavior

- Lambda and API Gateway charge by usage and scale down when idle.
- Lambda automatically creates additional execution environments as concurrency increases.
- API Gateway throttles this stage at 25 requests/second with a burst of 50.
- CloudWatch log storage is limited by 14-day retention.
- S3 state storage is very small, but versioning retains old state versions until explicitly cleaned up.
- Actual cost depends on account free-tier eligibility, request volume, log volume, and AWS pricing.

## Cleanup

Destroy the application stack before considering bootstrap cleanup:

```powershell
terraform -chdir=terraform/environments/dev plan -destroy -out=destroy.tfplan
terraform -chdir=terraform/environments/dev apply destroy.tfplan
```

The state bucket is deliberately protected with `prevent_destroy`. Do not remove it until the application is destroyed, required state versions are archived, and the bucket contents are no longer needed. See the [deployment runbook](docs/deployment-runbook.md) for rollback, troubleshooting, and the deliberate bootstrap-cleanup procedure.
