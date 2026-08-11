# Expert Smart — Production Infrastructure (AWS EKS)

## Status: SCAFFOLD ONLY

Everything under `infra/terraform/` in this commit is **structure and interface
contract only** — module skeletons, typed variables, and documented output
placeholders. **There are zero live `resource` or AWS-contacting `data`
blocks.** No AWS resource has been created by this scaffold. `terraform plan`
against these files would show no changes because there is nothing to change
against.

Implementing real resources inside these modules, bootstrapping remote state,
and running `terraform apply` are each separate, explicitly authorized phases
— not part of this commit.

## Architecture scope

```text
Cloud:      AWS
Region:     me-central-1 (Middle East — UAE), 3 Availability Zones
Platform:   Amazon EKS
IaC:        Terraform (>= 1.11, for S3-native state locking)

Database:          Amazon RDS for PostgreSQL, Multi-AZ, private
Upload storage:     Amazon EFS (ReadWriteMany — required because uploaded
                    files are written by one pod and later read by another,
                    proven from core_engine/bridge_api.py's /api/ingest and
                    /api/upload endpoints)
Secret source:      AWS Secrets Manager, projected into Kubernetes via
                    External Secrets Operator
CI-to-AWS auth:     GitHub OIDC → short-lived AWS IAM role assumption
                    (no long-lived AWS keys, no static KUBECONFIG secret)
Kubernetes Service:  ClusterIP (unchanged) — the AWS Load Balancer
                    Controller registers Pod IPs directly into the ALB
                    target group; changing the Service to type=LoadBalancer
                    would provision a second, redundant load balancer
Container registry: GHCR (retained — the R6-hardened publish/deploy
                    workflow already works; migration to ECR is not
                    currently justified)
```

## Module ownership

| Module | Future ownership |
|---|---|
| `modules/network` | VPC, AZ selection, public/private-app/private-db subnets, route tables, Internet Gateway, NAT strategy, VPC endpoints |
| `modules/eks` | EKS control plane, managed node groups, cluster add-ons (VPC CNI, CoreDNS, kube-proxy, metrics-server, EFS CSI), Karpenter, AWS Load Balancer Controller integration |
| `modules/iam` | GitHub OIDC IAM roles (CI identity), EKS access authorization, EKS workload identity / IRSA (Pod identity) — **CI identity and Pod/workload identity are distinct trust relationships, never conflated** |
| `modules/database` | RDS PostgreSQL, private DB subnet group, Multi-AZ, backup/retention configuration |
| `modules/storage` | EFS filesystem, mount targets, shared uploads persistence |
| `modules/edge` | Route 53, CloudFront, WAF, ALB/Ingress integration, ACM/TLS, edge logging |
| `modules/secrets` | AWS Secrets Manager integration, External Secrets Operator boundary, runtime secret references (never secret values) |
| `modules/observability` | CloudWatch, EKS/application/ALB/CloudFront/WAF logs, metrics, alarms, retention |

`kubernetes/` at the repository root (not under `infra/`) remains the sole
owner of namespace-scoped application resources (`Namespace`, `ServiceAccount`,
`Deployment`, `Service`, `Ingress`, `HPA`, `ExternalSecret` custom resources).
There is no `infra/kubernetes/` — that would duplicate ownership.

## Plan-before-apply governance

```text
PR
 → terraform fmt / validate / static checks
 → terraform plan
 → human review
 → merge
 → separate explicit production apply authorization
 → GitHub production Environment approval
 → terraform apply
```

**`merge to main` != `terraform apply`.**
**`merge to main` != production deploy.**

Neither infrastructure apply nor application deployment ever runs
automatically merely because a PR merged. This mirrors the same governance
already proven for the application deploy pipeline (see the R6 hardening of
`.github/workflows/ci-cd.yml`), extended to infrastructure.

## Remote state design (not bootstrapped by this commit)

* Backend: S3, versioned, SSE encrypted, public access blocked
* Locking: `use_lockfile = true` — Terraform's S3-native state locking,
  generally available since Terraform 1.11 — no DynamoDB lock table
* Separate state key/prefix for `production`, isolated from any future
  non-production environment
* Real bucket/key/region coordinates are supplied at a later, separately
  authorized state-bootstrap phase — never hard-coded here

## Secrets

No secret value of any kind is committed anywhere in this scaffold. The only
committed tfvars file is `terraform.tfvars.example`, containing placeholder
values only. Real secrets (database credentials, API keys) live exclusively
in AWS Secrets Manager and are never written to Git.

## Notes carried forward from architecture review (not defects)

These three items were raised and fully resolved during the R1 architecture
review. They are documented here for traceability — **they are not open
architecture defects and do not block this scaffold**:

1. **AI fallback chain**: `core_engine/rag_advisor.py` contains code for a
   three-tier fallback (Ollama → Anthropic API → template response) for its
   optional RAG-advisor feature, but the `anthropic` Python package is not
   listed in `core_engine/requirements.txt` — so in the canonical production
   image, the Anthropic tier is currently non-functional and falls straight
   through to the template response. This does not affect infrastructure: no
   Ollama module exists in this scaffold, and none is required — Ollama and
   Anthropic are both optional for application startup and for core
   valuation (which uses OpenAI, a separately, actually-installed
   dependency). AI hosting remains deferred.
2. **CloudFront VPC Origins**: not confirmed available in `me-central-1` as
   of this review (a documented regional list did not include it). The
   `edge` module therefore targets an internet-facing ALB (mitigated against
   direct-origin bypass via CloudFront's managed prefix list plus a rotated
   custom header) rather than assuming an internal-ALB VPC-origin model.
   This is a final, fully-buildable decision — not an unresolved gap — and
   the module intentionally avoids hard-coding the unproven regional
   capability either way.
3. **Owner inputs**: concrete values (AWS account ID, domain name,
   production hostname, database sizing, backup retention/RPO/RTO, budget)
   are apply-time inputs, expressed here purely as typed Terraform variables
   with no committed values. They do not block this scaffold and are not
   needed to understand or review the module structure.
