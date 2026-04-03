#!/usr/bin/env bash
set -euo pipefail

if ! command -v terraform >/dev/null 2>&1; then
  echo "error: terraform is not installed or not available in PATH"
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_dirs=(
  "terraform"
  "terraform/modules/vpc"
  "terraform/modules/iam"
  "terraform/modules/cluster"
)

for dir in "${terraform_dirs[@]}"; do
  abs_dir="${repo_root}/${dir}"
  rm -rf "${abs_dir}/.terraform"
  echo "info: terraform init (${dir})"
  terraform -chdir="${abs_dir}" init -backend=false -input=false -lockfile=readonly >/dev/null
  echo "info: terraform validate (${dir})"
  terraform -chdir="${abs_dir}" validate >/dev/null
done

echo "info: terraform validate passed for root and modules"
