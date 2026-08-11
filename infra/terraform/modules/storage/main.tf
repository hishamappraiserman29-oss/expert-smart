# ==============================================================================
# Module: storage
# Status: SCAFFOLD ONLY — zero live resources. Structural contract only.
# ==============================================================================
#
# Storage model choice is proven, not assumed: core_engine/bridge_api.py's
# /api/ingest and /api/upload endpoints (~line 7137, 7160) save an uploaded
# file and return only its generated filename in the SAME request — no
# synchronous processing occurs. A later, separate request reads that file,
# and Kubernetes Service/Ingress routing gives no guarantee of landing on
# the same pod that received the upload. The existing Deployment already
# runs multiple replicas (HPA minReplicas=2). EBS is strictly
# ReadWriteOnce — incompatible with this pattern. EFS (ReadWriteMany)
# requires zero application code change and is therefore selected.
#
# Future ownership (NOT implemented in this scaffold):
#   - EFS file system (encrypted at rest)
#   - Mount targets in the private application subnets (one per AZ)
#   - Access point scoped to the application's uploads path
#   - Security group permitting NFS (2049) only from the EKS node/pod
#     security group
#
# TODO(infra-apply-phase): implement aws_efs_file_system,
# aws_efs_mount_target, aws_efs_access_point under a separate, explicitly
# authorized implementation phase. This file intentionally contains no
# resource or data blocks.
