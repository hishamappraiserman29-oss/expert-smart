# ==============================================================================
# Module: database
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Engine choice is proven, not assumed: core_engine/database/connection.py
# defaults DATABASE_URL to postgresql://localhost:5432/expert_smart via
# SQLAlchemy, core_engine/requirements.txt pins psycopg2-binary, and
# core_engine/database/models.py imports PostgreSQL-specific dialect types
# (sqlalchemy.dialects.postgresql.JSONB, .UUID) — a hard dependency on
# PostgreSQL specifically, not merely a default connection string.
#
# Future ownership (NOT implemented in this scaffold):
#   - RDS for PostgreSQL instance, Multi-AZ (locked decision — production-
#     oriented, multi-country user base)
#   - Private DB subnet group (from the network module's private_db subnets)
#   - Security group restricted to the EKS node/pod security group only
#     (publicly_accessible = false, locked decision)
#   - Backup/retention configuration (retention days is an owner input —
#     RPO/RTO — not decided in this scaffold)
#   - Parameter group
#
# TODO(infra-apply-phase): implement aws_db_instance, aws_db_subnet_group,
# and aws_db_parameter_group under a separate, explicitly authorized
# implementation phase. This file intentionally contains no resource or
# data blocks. No database credential of any kind is defined here — the
# master password is sourced from AWS Secrets Manager (see modules/secrets),
# never a Terraform variable value.
