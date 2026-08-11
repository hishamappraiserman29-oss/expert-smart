# ==============================================================================
# Module: network
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Future ownership (NOT implemented in this scaffold):
#   - VPC
#   - Availability Zone selection (me-central-1a/b/c)
#   - Public subnets     — Internet Gateway, NAT Gateways, internet-facing ALB
#   - Private app subnets — EKS worker nodes / pods
#   - Private DB subnets  — RDS, EFS mount targets
#   - Route tables (public + one per private subnet tier)
#   - NAT strategy — one NAT Gateway per AZ for true AZ-independent egress
#     (see infra/README.md for the cost-sensitive single-NAT alternative,
#     which is explicitly NOT the default given the stated multi-AZ
#     production requirement)
#   - VPC endpoints where justified (S3 gateway; ECR / CloudWatch Logs /
#     Secrets Manager interface endpoints, to avoid routing that traffic
#     through NAT)
#
# TODO(infra-apply-phase): implement aws_vpc, aws_subnet, aws_internet_gateway,
# aws_eip, aws_nat_gateway, aws_route_table, aws_route_table_association, and
# aws_vpc_endpoint resources under a separate, explicitly authorized
# implementation phase. This file intentionally contains no resource or data
# blocks.
