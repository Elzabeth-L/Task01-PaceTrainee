# Architecture decisions

## ADR-001: Lambda with API Gateway HTTP API

**Decision:** Serve the HTML response from one Python Lambda invoked by an API Gateway v2 HTTP API.

**Why:** This directly meets the Lambda requirement, has no servers to patch, scales to zero, and keeps the demonstration small. HTTP API has fewer features but lower cost and less configuration than API Gateway REST API; none of the omitted REST API features are needed here.

**Trade-off:** For a purely static production site, S3 plus CloudFront would normally be faster and cheaper. Lambda is retained because dynamic Lambda delivery is an explicit project goal. The page is dependency-free and carries a five-minute public cache header to reduce repeat invocation volume.

## ADR-002: No VPC and no database

**Decision:** Lambda runs in the AWS-managed network and stores no application data.

**Why:** A public HTTPS response needs neither private network access nor persistence. Avoiding a VPC removes NAT cost and network-interface cold-start complexity. Avoiding a database removes migrations, credentials, backups, and idle cost.

## ADR-003: ARM64 Python runtime

**Decision:** Use Python 3.13 on `arm64`, 128 MB memory, and a five-second timeout.

**Why:** The handler only creates a small string, so the smallest memory allocation is sufficient. ARM Lambda is cost-efficient and all code is pure Python, eliminating native-package compatibility concerns. The short timeout limits runaway cost.

## ADR-004: Custom Terraform module

**Decision:** Put Lambda, its execution role, log group, API, routes, integration, stage, and invocation permission in `terraform/modules/serverless_site`.

**Why:** The root stack expresses environment choices while the module encapsulates a complete deployable service boundary. Explicit resources make ownership and policy review easier than a broad third-party module. The root hashes the source file independently from platform-specific ZIP metadata, so only a real code change updates Lambda.

## ADR-005: S3 state locking and a separate bootstrap stack

**Decision:** Create a versioned, encrypted, private S3 state bucket once from a local-state bootstrap stack. The application backend uses native S3 lock files.

**Why:** Local and CI deployments must share state. Versioning aids recovery, encryption and blocked public access protect infrastructure metadata, and locking prevents concurrent writers. A separate stack solves the bootstrap dependency: Terraform cannot use a backend bucket before that bucket exists. Native S3 locking avoids a DynamoDB table and its lifecycle/cost.

**Trade-off:** Bootstrap state remains local and must be protected. It contains resource metadata but no static AWS keys. Keep it in a secure operator location and never commit it.

## ADR-006: GitHub OIDC instead of AWS access keys

**Decision:** GitHub Actions assumes an IAM role through OpenID Connect, restricted to this repository's protected `dev` environment. That environment permits deployments from `main` only.

**Why:** Each run receives short-lived credentials and there are no long-lived AWS secrets to rotate or leak. Pull requests get offline validation only; deployment credentials are issued only to the trusted deployment branch. The role can manage the named application IAM roles and required application services, but cannot modify its own bootstrap trust policy.

## Reliability and security controls

- API Gateway throttles traffic at 25 requests/second with a burst of 50.
- Lambda may write only to its own CloudWatch log group; logs expire after 14 days.
- API Gateway is the only principal granted permission to invoke the function.
- HTML includes CSP, MIME-sniffing prevention, and request-ID escaping.
- GitHub deployment concurrency is serialized, and Terraform also locks remote state.
- The S3 state bucket denies non-TLS requests and blocks all public access.
